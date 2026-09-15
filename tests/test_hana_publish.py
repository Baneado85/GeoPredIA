"""HANA publishing contract tests with a mocked DB-API; no remote connection."""
import copy
import hashlib
import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from agents.hana_publish import publish_events
from agents.integrations import IntegrationUnavailable


def event(number=1):
    return {
        "id": f"evaluation:00000000-0000-0000-0000-{number:012d}",
        "type": "evaluation",
        "created_at": "2026-09-15T15:00:00Z",
        "payload": {"source": "demo", "subindices": {"social": None}, "label": "Zona Perú"},
    }


def canonical(payload):
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


class HanaPublishTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.fetchone.return_value = None
        self.dbapi = types.SimpleNamespace(connect=MagicMock(return_value=self.connection))
        self.patches = [
            patch.dict(os.environ, {"HANA_ADDRESS": "tenant.invalid", "HANA_PORT": "443",
                                   "HANA_USER": "test-user", "HANA_PASSWORD": "test-secret",
                                   "HANA_TEAM_SCHEMA": "GEOPREDIA_TEAM"}, clear=True),
            patch.dict(sys.modules, {"hdbcli": types.SimpleNamespace(dbapi=self.dbapi)}),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_parameterized_insert_tls_and_canonical_hash(self):
        item = event()
        before = copy.deepcopy(item)
        result = publish_events([item])
        self.assertEqual(result, {"published": 1, "already_present": 0})
        self.assertEqual(item, before)
        kwargs = self.dbapi.connect.call_args.kwargs
        self.assertTrue(kwargs["encrypt"])
        self.assertTrue(kwargs["sslValidateCertificate"])
        self.assertFalse(kwargs["autocommit"])
        self.connection.setautocommit.assert_called_once_with(False)
        sql, params = self.cursor.execute.call_args_list[1].args
        self.assertIn('"GEOPREDIA_TEAM"."GPI_EVENT_STORE"', sql)
        self.assertNotIn(item["id"], sql)
        self.assertEqual(sql.count("?"), 5)
        self.assertEqual(params[2], canonical(item["payload"]))
        self.assertEqual(params[4], hashlib.sha256(params[2].encode("utf-8")).hexdigest())
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()
        self.connection.close.assert_called_once()

    def test_identical_existing_event_is_idempotent(self):
        item = event()
        digest = hashlib.sha256(canonical(item["payload"]).encode("utf-8")).hexdigest()
        self.cursor.fetchone.return_value = (digest, item["type"], item["created_at"])
        self.assertEqual(publish_events([item]), {"published": 0, "already_present": 1})
        self.assertEqual(self.cursor.execute.call_count, 1)

    def test_conflict_rolls_back_entire_batch(self):
        self.cursor.fetchone.side_effect = [None, ("different-hash", "evaluation", event()["created_at"])]
        with self.assertRaisesRegex(IntegrationUnavailable, "Conflicto"):
            publish_events([event(1), event(2)])
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()
        self.connection.close.assert_called_once()

    def test_metadata_change_also_conflicts(self):
        item = event()
        digest = hashlib.sha256(canonical(item["payload"]).encode("utf-8")).hexdigest()
        self.cursor.fetchone.return_value = (digest, "review", item["created_at"])
        with self.assertRaises(IntegrationUnavailable):
            publish_events([item])
        self.connection.rollback.assert_called_once()

    def test_duplicate_in_batch_counts_once(self):
        item = event()
        self.assertEqual(publish_events([item, copy.deepcopy(item)]), {"published": 1, "already_present": 1})
        self.assertEqual(self.cursor.execute.call_count, 2)

    def test_conflicting_duplicate_is_rejected_before_connect(self):
        item, changed = event(), event()
        changed["payload"]["source"] = "sac"
        with self.assertRaises(IntegrationUnavailable):
            publish_events([item, changed])
        self.dbapi.connect.assert_not_called()

    def test_invalid_payload_or_timestamp_is_rejected_before_connect(self):
        bad_number, no_zone, bad_id = event(), event(), event()
        bad_number["payload"]["value"] = float("nan")
        no_zone["created_at"] = "2026-09-15T15:00:00"
        bad_id["id"] = "evaluation:arbitrary-text"
        for item in (bad_number, no_zone, bad_id):
            with self.subTest(item=item), self.assertRaises(IntegrationUnavailable):
                publish_events([item])
        self.dbapi.connect.assert_not_called()

    def test_schema_injection_rejected_before_connect(self):
        os.environ["HANA_TEAM_SCHEMA"] = 'TEAM"; DROP TABLE EXAMPLE; --'
        with self.assertRaises(IntegrationUnavailable):
            publish_events([event()])
        self.dbapi.connect.assert_not_called()

    def test_driver_error_sanitized_even_if_cleanup_fails(self):
        self.cursor.execute.side_effect = RuntimeError("test-secret tenant.invalid raw payload")
        self.connection.rollback.side_effect = RuntimeError("cleanup-secret")
        self.connection.close.side_effect = RuntimeError("close-secret")
        with self.assertRaises(IntegrationUnavailable) as caught:
            publish_events([event()])
        self.assertNotIn("secret", str(caught.exception))
        self.assertNotIn("tenant.invalid", str(caught.exception))
        self.connection.commit.assert_not_called()
        self.connection.rollback.assert_called_once()

    def test_empty_and_oversized_batch(self):
        self.assertEqual(publish_events([]), {"published": 0, "already_present": 0})
        with self.assertRaises(IntegrationUnavailable):
            publish_events([event()] * 1001)
        self.dbapi.connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
