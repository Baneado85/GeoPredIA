"""Offline checks for evidence boundaries and immutable SAC snapshots."""

import copy
import json
import os
import unittest
from unittest.mock import patch

from agents.engine import run_agents


def scenario():
    evaluation = {
        "id": "evaluation-1", "zone_id": "zone-1", "source": "sac",
        "subindices": {"geological": 76, "environmental": 42, "social": 20},
        "global_risk": 50.8, "missing_fields": [], "model_version": "sac-v1",
    }
    zone = {
        "id": "zone-1", "name": "Zona de prueba", "region": "Demo",
        "evidence": [
            {"id": f"ev-{dimension}", "dimension": dimension, "metric": f"{dimension}.observations", "label": "Observaciones", "value": 3, "unit": "registros", "source": "dataset-prueba", "quality": "synthetic"}
            for dimension in ("geological", "environmental", "social")
        ],
    }
    return evaluation, zone, []


class AgentEngineTests(unittest.TestCase):
    def test_sac_values_and_evidence_are_unchanged(self):
        arguments = scenario()
        original = copy.deepcopy(arguments)
        with patch("agents.engine._request_llm") as provider:
            result = run_agents(*arguments)
        self.assertEqual(arguments, original)
        self.assertEqual(result["mode"], "rules")
        self.assertEqual(len(result["findings"]), 3)
        self.assertTrue(result["coordinator"]["needs_human_review"])
        self.assertNotIn("global_risk", result)
        self.assertIn("76/100", result["findings"][0]["summary"])
        provider.assert_not_called()

    def test_missing_subindex_is_not_zero_and_gap_is_scoped(self):
        evaluation, zone, readings = scenario()
        evaluation["subindices"]["social"] = None
        evaluation["missing_fields"] = ["social.community_consultation"]
        zone["evidence"][2]["value"] = None
        zone["evidence"][2]["quality"] = "missing"
        result = run_agents(evaluation, zone, readings)
        social = result["findings"][2]
        self.assertEqual(social["status"], "missing_data")
        self.assertIn("subindices.social", social["missing_fields"])
        self.assertIn("no equivale a riesgo cero", social["summary"])
        self.assertNotIn("nivel bajo", social["summary"])
        self.assertEqual(result["findings"][0]["status"], "ok")

    def test_true_zero_is_valid_but_nonfinite_score_is_missing(self):
        evaluation, zone, readings = scenario()
        evaluation["subindices"]["social"] = 0
        evaluation["subindices"]["environmental"] = float("nan")
        result = run_agents(evaluation, zone, readings)
        self.assertIn("0/100", result["findings"][2]["summary"])
        self.assertEqual(result["findings"][2]["status"], "ok")
        self.assertEqual(result["findings"][1]["status"], "missing_data")

    def test_telemetry_is_local_and_synthetic_is_explicit(self):
        evaluation, zone, _ = scenario()
        readings = [
            {"id": "local", "zone_id": "zone-1", "source": "simulator", "readings": {"air_temperature_c": 23.5}},
            {"id": "other", "zone_id": "zone-2", "source": "device", "readings": {"air_temperature_c": 99}},
            {"id": "unsupported", "zone_id": "zone-1", "source": "device", "readings": {"ph": 8}},
        ]
        result = run_agents(evaluation, zone, readings)
        environmental = result["findings"][1]
        self.assertIn("23.5 °C (sintético)", environmental["summary"])
        self.assertNotIn("99", environmental["summary"])
        self.assertIn("local", environmental["evidence_ids"])
        self.assertNotIn("other", environmental["evidence_ids"])
        self.assertNotIn("unsupported", environmental["evidence_ids"])

    def test_imported_scores_request_original_causes_and_provenance(self):
        evaluation, zone, readings = scenario()
        for item in zone["evidence"]:
            item["quality"] = "imported"
        result = run_agents(evaluation, zone, readings)
        for finding in result["findings"]:
            self.assertIn("su origen no se ha verificado", finding["summary"])
        self.assertTrue(any("variables y fuentes originales" in reason for reason in result["coordinator"]["review_reasons"]))

    def test_mismatched_zone_is_rejected(self):
        evaluation, zone, readings = scenario()
        zone["id"] = "zone-2"
        with self.assertRaises(ValueError):
            run_agents(evaluation, zone, readings)

    def test_no_key_never_calls_provider(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}), patch("agents.engine._request_llm") as provider:
            result = run_agents(*scenario(), llm_enabled=True)
        self.assertEqual(result["mode"], "rules_fallback")
        provider.assert_not_called()

    def test_key_alone_cannot_enable_paid_requests(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake-offline-key"}), patch("agents.engine._request_llm") as provider:
            result = run_agents(*scenario())
        self.assertEqual(result["mode"], "rules")
        provider.assert_not_called()

    def test_llm_cannot_discard_missing_data(self):
        evaluation, zone, readings = scenario()
        evaluation["missing_fields"] = ["subindices.social"]
        def ignores_gap(payload, *_):
            return {"focus": "verify_sources", "evidence_ids": payload["allowed_evidence_ids"]}
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake-offline-key"}), patch("agents.engine._request_llm", side_effect=ignores_gap):
            result = run_agents(evaluation, zone, readings, llm_enabled=True)
        self.assertEqual(result["mode"], "rules_fallback")
        self.assertEqual(result["findings"][2]["status"], "missing_data")
        self.assertEqual(result["findings"][0]["status"], "ok")

    def test_hallucinated_reference_discards_all_llm_output(self):
        def hallucination(payload, *_):
            return {"focus": "verify_sources", "evidence_ids": ["invented-reference"]}
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake-offline-key"}), patch("agents.engine._request_llm", side_effect=hallucination):
            result = run_agents(*scenario(), llm_enabled=True)
        self.assertEqual(result["mode"], "rules_fallback")
        self.assertNotIn("invented-reference", json.dumps(result))
        self.assertNotIn("Interpretación asistida", json.dumps(result, ensure_ascii=False))
        self.assertTrue(result["coordinator"]["needs_human_review"])

    def test_attempt_to_write_score_is_rejected(self):
        def score_override(payload, *_):
            return {"focus": "verify_sources", "evidence_ids": payload["allowed_evidence_ids"], "global_risk": 0}
        arguments = scenario()
        original = copy.deepcopy(arguments)
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake-offline-key"}), patch("agents.engine._request_llm", side_effect=score_override):
            result = run_agents(*arguments, llm_enabled=True)
        self.assertEqual(result["mode"], "rules_fallback")
        self.assertEqual(arguments, original)

    def test_validated_llm_focus_is_labelled_and_stays_advisory(self):
        def grounded_response(payload, *_):
            return {"focus": "verify_sources", "evidence_ids": payload["allowed_evidence_ids"]}
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake-offline-key"}), patch("agents.engine._request_llm", side_effect=grounded_response) as provider:
            result = run_agents(*scenario(), llm_enabled=True)
        self.assertEqual(result["mode"], "llm")
        self.assertEqual(provider.call_count, 3)
        self.assertTrue(result["coordinator"]["needs_human_review"])
        for finding in result["findings"]:
            self.assertIn("Interpretación asistida por LLM", finding["summary"])
            self.assertIn("no una fuente de hechos nuevos", finding["summary"])

    def test_provider_failure_falls_back_without_exposing_secrets(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "secret-test-value"}), patch("agents.engine._request_llm", side_effect=RuntimeError("Authorization: secret-test-value")):
            result = run_agents(*scenario(), llm_enabled=True)
        self.assertEqual(result["mode"], "rules_fallback")
        self.assertNotIn("secret-test-value", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
