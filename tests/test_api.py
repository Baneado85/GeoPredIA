import csv
import io
import os
import tempfile
from pathlib import Path
from uuid import uuid4
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from agents.api import create_app
from agents.data import evaluate_demo, seed_zones
from agents.integrations import IntegrationUnavailable


def snapshot_csv(**changes):
    row = dict(zone_id="SAC-001", evaluated_at="2026-09-15T12:00:00Z", model_version="sac-v1", dataset_version="event-v1", geological="10", environmental="20", social="30", global_risk="93")
    row.update(changes)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    return out.getvalue()


class APIContractTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"APP_API_KEY": "", "DEVICE_API_KEY": "test-device-only", "BPA_CALLBACK_KEY": "test-workflow-only", "LLM_ENABLED": "false", "SEED_DEMO": "true"})
        self.env.start()
        self.test_db = Path(__file__).resolve().parents[1] / ".local" / ("test-" + uuid4().hex + ".db")
        self.app = create_app(self.test_db)
        self.client = TestClient(self.app)
        self.zones = self.client.get("/api/zones").json()
        self.eid = self.zones[0]["latest_evaluation"]["id"]

    def tearDown(self):
        self.client.close()
        self.test_db.unlink(missing_ok=True)
        self.env.stop()

    def test_demo_has_three_dimensions_and_explicit_missing(self):
        self.assertEqual(len(self.zones), 6)
        missing = self.zones[4]["latest_evaluation"]
        self.assertIsNone(missing["global_risk"])
        self.assertIn("environmental", missing["missing_fields"])

    def test_scenario_validates_weights(self):
        response = self.client.post("/api/evaluations", json={"zone_id": "Z-001", "weights": {"geological": .8, "environmental": .8, "social": .8}})
        self.assertEqual(response.status_code, 422)

    def test_scenario_creates_new_snapshot(self):
        response = self.client.post("/api/evaluations", json={"zone_id": "Z-001", "weights": {"geological": .25, "environmental": .5, "social": .25}})
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(response.json()["id"], self.eid)
        self.assertEqual(response.json()["global_risk"], 29.5)
        self.assertEqual(self.client.get("/api/evaluations/" + self.eid).json()["global_risk"], 28.6)

    def test_sac_preserves_global_instead_of_recomputing(self):
        response = self.client.post("/api/sac/import", json={"csv": snapshot_csv()})
        self.assertEqual(response.status_code, 201)
        value = response.json()["evaluations"][0]
        self.assertEqual(value["global_risk"], 93)
        self.assertFalse(value["provenance_verified"])
        self.assertEqual(self.client.post("/api/evaluations", json={"zone_id": "SAC-001"}).status_code, 409)

    def test_sac_rejects_nonfinite_and_partial_global(self):
        for fields in ({"global_risk": "NaN"}, {"global_risk": "inf"}, {"geological": "", "global_risk": "12"}, {"global_risk": "101"}):
            self.assertEqual(self.client.post("/api/sac/import", json={"csv": snapshot_csv(**fields)}).status_code, 422)

    def test_sac_import_is_atomic(self):
        text = snapshot_csv() + snapshot_csv(zone_id="SAC-002", global_risk="bad").splitlines()[-1] + "\n"
        self.assertEqual(self.client.post("/api/sac/import", json={"csv": text}).status_code, 422)
        self.assertEqual(len(self.client.get("/api/zones").json()), 6)

    def test_sac_zero_valid_and_no_fake_demo_evidence(self):
        response = self.client.post("/api/sac/import", json={"csv": snapshot_csv(zone_id="Z-001", geological="0", environmental="0", social="0", global_risk="0")})
        eid = response.json()["evaluations"][0]["id"]
        run = self.client.post("/api/agent-runs", json={"evaluation_id": eid}).json()
        self.assertEqual(run["input_snapshot"]["evaluation"]["global_risk"], 0)
        self.assertTrue(all(e["quality"] == "imported" for e in run["input_snapshot"]["evaluation"]["evidence"]))

    def test_agent_run_persisted_and_score_immutable(self):
        response = self.client.post("/api/agent-runs", json={"evaluation_id": self.eid})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json()["findings"]), 3)
        self.assertTrue(response.json()["coordinator"]["needs_human_review"])
        self.assertEqual(len(self.client.get("/api/agent-runs", params={"evaluation_id": self.eid}).json()), 1)
        self.assertEqual(self.client.get("/api/evaluations/" + self.eid).json()["review_status"], "pending")

    def test_assistant_is_traceable_and_not_claimed_as_joule(self):
        response = self.client.post("/api/assistant/query", json={"zone_id": "Z-001", "question": "¿Qué factor explica más el riesgo?"})
        self.assertEqual(response.status_code, 200)
        value = response.json()
        self.assertEqual(value["evaluation_id"], self.eid)
        self.assertFalse(value["joule_deployed"])
        self.assertIn("dimensión más alta", value["answer"])

    def test_assistant_rejects_unknown_zone(self):
        self.assertEqual(self.client.post("/api/assistant/query", json={"zone_id": "NO-EXISTE", "question": "Resume el riesgo"}).status_code, 404)

    def review_body(self, eid=None):
        return {"evaluation_id": eid or self.eid, "reviewer": "Especialista Demo", "decision": "approved", "justification": "Revisión de demostración con evidencia sintética."}

    def test_human_review_is_versioned_and_cannot_be_overwritten(self):
        response = self.client.post("/api/reviews", json=self.review_body())
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()["identity_verified"])
        self.assertEqual(self.client.post("/api/reviews", json=self.review_body()).status_code, 409)
        self.assertEqual(self.client.get("/api/evaluations/" + self.eid).json()["review_status"], "approved")

    def test_missing_score_cannot_be_approved(self):
        body = self.review_body(self.zones[4]["latest_evaluation"]["id"])
        self.assertEqual(self.client.post("/api/reviews", json=body).status_code, 409)
        body["decision"] = "observed"
        self.assertEqual(self.client.post("/api/reviews", json=body).status_code, 201)

    def test_blank_justification_rejected(self):
        body = self.review_body()
        body["justification"] = " " * 20
        self.assertEqual(self.client.post("/api/reviews", json=body).status_code, 422)

    def telemetry(self):
        return {"device_id": "test-01", "zone_id": "Z-001", "observed_at": datetime.now(timezone.utc).isoformat(), "source": "device", "readings": {"soil_moisture_pct": 45, "water_temperature_c": None}}

    def test_telemetry_requires_key_and_deduplicates(self):
        payload = self.telemetry()
        self.assertEqual(self.client.post("/api/telemetry", json=payload).status_code, 401)
        headers = {"X-Device-Key": "test-device-only"}
        one = self.client.post("/api/telemetry", json=payload, headers=headers)
        two = self.client.post("/api/telemetry", json=payload, headers=headers)
        self.assertEqual(one.status_code, 201)
        self.assertEqual(one.json()["id"], two.json()["id"])
        payload["readings"]["soil_moisture_pct"] = 50
        self.assertEqual(self.client.post("/api/telemetry", json=payload, headers=headers).status_code, 409)

    def test_telemetry_invalid_range_and_naive_time(self):
        payload = self.telemetry()
        payload["readings"]["soil_moisture_pct"] = 101
        self.assertEqual(self.client.post("/api/telemetry", json=payload, headers={"X-Device-Key": "test-device-only"}).status_code, 422)
        payload["readings"]["soil_moisture_pct"] = 50
        payload["observed_at"] = "2026-09-15T12:00:00"
        self.assertEqual(self.client.post("/api/telemetry", json=payload, headers={"X-Device-Key": "test-device-only"}).status_code, 422)

    def test_simulator_is_explicit(self):
        response = self.client.post("/api/telemetry/simulate", json={"zone_id": "Z-001"})
        self.assertEqual(response.json()["source"], "simulator")
        self.assertEqual(response.json()["quality"], "synthetic")

    def test_cross_origin_write_rejected(self):
        response = self.client.post("/api/reviews", json=self.review_body(), headers={"Origin": "https://unrelated.example"})
        self.assertEqual(response.status_code, 403)

    def test_remote_client_denied_without_key(self):
        remote = TestClient(self.app, client=("192.0.2.1", 1234))
        self.assertEqual(remote.get("/api/zones").status_code, 401)
        remote.close()

    def test_dns_rebinding_host_denied(self):
        response = self.client.get("/api/zones", headers={"Host": "attacker.invalid", "Origin": "http://attacker.invalid"})
        self.assertEqual(response.status_code, 400)

    def test_failed_sensor_reading_is_marked_missing(self):
        payload = self.telemetry()
        payload["readings"] = {}
        response = self.client.post("/api/telemetry", json=payload, headers={"X-Device-Key": "test-device-only"})
        self.assertEqual(response.json()["quality"], "missing")

    def test_bpa_requires_matching_workflow_instance(self):
        body = self.review_body()
        body["workflow_instance_id"] = "not-started"
        self.assertEqual(self.client.post("/api/integrations/bpa/callback", json=body, headers={"X-Workflow-Key": "test-workflow-only"}).status_code, 409)

    def test_bpa_blocks_local_review_and_callback_is_idempotent(self):
        with self.app.state.store.connection() as db:
            db.execute("INSERT INTO workflows VALUES (?,?,'started')", (self.eid, "workflow-123"))
        self.assertEqual(self.client.post("/api/reviews", json=self.review_body()).status_code, 409)
        body = self.review_body()
        body["workflow_instance_id"] = "workflow-123"
        headers = {"X-Workflow-Key": "test-workflow-only"}
        first = self.client.post("/api/integrations/bpa/callback", json=body, headers=headers)
        self.assertEqual(first.status_code, 200)
        second = self.client.post("/api/integrations/bpa/callback", json=body, headers=headers)
        self.assertEqual(first.json()["id"], second.json()["id"])

    def test_hana_export_uses_immutable_snapshot_and_marks_confirmed_batch(self):
        original = self.app.state.store.export_events()
        self.client.post("/api/reviews", json=self.review_body())
        after_review = self.app.state.store.export_events()
        before = next(e for e in original if e["id"] == "evaluation:" + self.eid)
        after = next(e for e in after_review if e["id"] == "evaluation:" + self.eid)
        self.assertEqual(before, after)
        with patch("agents.hana_publish.publish_events", return_value={"published": len(after_review), "already_present": 0}) as publish:
            response = self.client.post("/api/integrations/hana/publish")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["more"])
        self.assertEqual(publish.call_args.args[0], after_review)
        self.assertEqual(self.app.state.store.export_events(), [])

    def test_hana_failure_keeps_events_pending(self):
        with patch("agents.hana_publish.publish_events", side_effect=IntegrationUnavailable("Conexión no confirmada")):
            response = self.client.post("/api/integrations/hana/publish")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(self.app.state.store.export_events()), 6)


if __name__ == "__main__":
    unittest.main()
