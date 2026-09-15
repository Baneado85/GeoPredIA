"""SQLite local store with append-only evaluation snapshots and review events."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .data import now, seed_zones, evaluate_demo


class Conflict(Exception):
    pass


class Store:
    def __init__(self, path, seed_demo=True):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS zones (id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evaluations (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, zone_id TEXT NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS agent_runs (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, evaluation_id TEXT NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS telemetry (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, zone_id TEXT NOT NULL, device_id TEXT NOT NULL, observed_at TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(device_id, observed_at));
                CREATE TABLE IF NOT EXISTS reviews (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, evaluation_id TEXT NOT NULL UNIQUE, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS workflows (evaluation_id TEXT PRIMARY KEY, instance_id TEXT, status TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS hana_exports (event_id TEXT PRIMARY KEY, exported_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, action TEXT NOT NULL, resource_id TEXT NOT NULL, detail TEXT NOT NULL);
            """)
            if seed_demo and not db.execute("SELECT COUNT(*) FROM zones").fetchone()[0]:
                for zone in seed_zones():
                    db.execute("INSERT INTO zones VALUES (?, ?)", (zone["id"], json.dumps(zone)))
                    evaluation = evaluate_demo(zone)
                    db.execute("INSERT INTO evaluations (id,zone_id,body) VALUES (?,?,?)", (evaluation["id"], zone["id"], json.dumps(evaluation)))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def audit_in(db, action, resource_id, detail):
        db.execute("INSERT INTO audit(created_at,action,resource_id,detail) VALUES (?,?,?,?)", (now(), action, resource_id, detail))

    def zones(self):
        with self.connection() as db:
            result = []
            for row in db.execute("SELECT body FROM zones ORDER BY id"):
                zone = json.loads(row["body"])
                evaluation = db.execute("SELECT body FROM evaluations WHERE zone_id=? ORDER BY seq DESC LIMIT 1", (zone["id"],)).fetchone()
                zone["latest_evaluation"] = self.with_status(db, json.loads(evaluation["body"])) if evaluation else None
                result.append(zone)
            return result

    @staticmethod
    def with_status(db, evaluation):
        review = db.execute("SELECT body FROM reviews WHERE evaluation_id=?", (evaluation["id"],)).fetchone()
        evaluation["review_status"] = json.loads(review["body"])["decision"] if review else "pending"
        return evaluation

    def evaluation(self, eid):
        with self.connection() as db:
            row = db.execute("SELECT body FROM evaluations WHERE id=?", (eid,)).fetchone()
            return self.with_status(db, json.loads(row["body"])) if row else None

    def add_evaluations(self, evaluations):
        with self.connection() as db:
            for e in evaluations:
                if not db.execute("SELECT 1 FROM zones WHERE id=?", (e["zone_id"],)).fetchone():
                    zone = {"id": e["zone_id"], "name": e["zone_id"], "region": "Importada de SAC",
                            "latitude": None, "longitude": None, "source": "sac", "evidence": []}
                    db.execute("INSERT INTO zones VALUES (?,?)", (zone["id"], json.dumps(zone)))
                db.execute("INSERT INTO evaluations(id,zone_id,body) VALUES (?,?,?)", (e["id"], e["zone_id"], json.dumps(e)))
                self.audit_in(db, "evaluation.created", e["id"], e["source"])

    def add_run(self, run):
        with self.connection() as db:
            db.execute("INSERT INTO agent_runs(id,evaluation_id,body) VALUES (?,?,?)", (run["id"], run["evaluation_id"], json.dumps(run)))
            self.audit_in(db, "agents.completed", run["id"], run["mode"])

    def list_records(self, kind, filter_value=None):
        # All identifiers come from this allowlist, never user input.
        table, column = {"runs": ("agent_runs", "evaluation_id"), "telemetry": ("telemetry", "zone_id"), "reviews": ("reviews", "evaluation_id")}[kind]
        with self.connection() as db:
            where, params = (f" WHERE {column}=?", (filter_value,)) if filter_value else ("", ())
            return [json.loads(row[0]) for row in db.execute(f"SELECT body FROM {table}{where} ORDER BY seq DESC LIMIT 200", params)]

    def add_telemetry(self, data):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            duplicate = db.execute("SELECT body FROM telemetry WHERE device_id=? AND observed_at=?", (data["device_id"], data["observed_at"])).fetchone()
            if duplicate:
                existing = json.loads(duplicate[0])
                if any(existing[k] != data[k] for k in ("zone_id", "source", "readings")):
                    raise Conflict("La misma lectura ya existe con otro contenido.")
                return existing
            db.execute("INSERT INTO telemetry(id,zone_id,device_id,observed_at,body) VALUES (?,?,?,?,?)", (data["id"], data["zone_id"], data["device_id"], data["observed_at"], json.dumps(data)))
            self.audit_in(db, "telemetry.received", data["id"], data["source"])
        return data

    def add_review(self, review):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM reviews WHERE evaluation_id=?", (review["evaluation_id"],)).fetchone():
                raise Conflict("La evaluación ya tiene decisión. Crea otra versión para revisarla nuevamente.")
            if review["source"] == "local-demo" and db.execute("SELECT 1 FROM workflows WHERE evaluation_id=?", (review["evaluation_id"],)).fetchone():
                raise Conflict("La evaluación fue enviada a BPA. Registra la decisión en ese proceso.")
            if review["decision"] == "approved":
                row = db.execute("SELECT body FROM evaluations WHERE id=?", (review["evaluation_id"],)).fetchone()
                if not row or json.loads(row[0])["global_risk"] is None:
                    raise Conflict("Completa la evaluación antes de aprobarla; puedes registrar observaciones.")
            db.execute("INSERT INTO reviews(id,evaluation_id,body) VALUES (?,?,?)", (review["id"], review["evaluation_id"], json.dumps(review)))
            self.audit_in(db, "review." + review["decision"], review["evaluation_id"], review["source"])
        return review

    def audit(self):
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM audit ORDER BY seq DESC LIMIT 200")]

    def export_events(self):
        result = []
        definitions = (("evaluations", "evaluation", "evaluation", "evaluated_at"),
                       ("agent_runs", "run", "agent_run", "created_at"),
                       ("telemetry", "telemetry", "telemetry", "observed_at"),
                       ("reviews", "review", "review", "decided_at"))
        with self.connection() as db:
            for table, prefix, kind, timestamp in definitions:
                # Read original persisted bodies, not projections with mutable review status.
                rows = db.execute(f"SELECT body FROM {table} s WHERE NOT EXISTS (SELECT 1 FROM hana_exports h WHERE h.event_id = ? || s.id) ORDER BY seq LIMIT ?", (prefix + ":", 1000 - len(result)))
                for row in rows:
                    payload = json.loads(row[0])
                    result.append({"id": prefix + ":" + payload["id"], "type": kind,
                                   "created_at": payload[timestamp], "payload": payload})
                if len(result) == 1000:
                    break
        return result

    def mark_exported(self, events):
        with self.connection() as db:
            db.executemany("INSERT OR IGNORE INTO hana_exports(event_id,exported_at) VALUES (?,?)", [(event["id"], now()) for event in events])
            self.audit_in(db, "hana.events_published", "hana", str(len(events)))
