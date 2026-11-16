"""
Test suite for Prior Auth Appeal Agent
=======================================
Covers all major pipeline components plus the full end-to-end agent loop.
Run with: python -m pytest test_main.py -v
     OR:  python test_main.py
"""
import unittest

from denial_analyzer     import DenialAnalyzer
from evidence_researcher import EvidenceResearcher
from appeal_writer       import AppealWriter
from success_predictor   import SuccessPredictor
from agent               import PriorAuthAppealAgent


# ── Shared fixture ─────────────────────────────────────────────────────────

SAMPLE_CASE = {
    "patient_id":          "PT-TEST-001",
    "patient_age":         52,
    "patient_sex":         "Female",
    "primary_diagnosis":   "Type 1 Diabetes Mellitus with hypoglycemia unawareness",
    "diagnosis_code":      "E10.641",
    "procedure_requested": "Insulin Pump Therapy (CSII)",
    "procedure_code":      "E0784",
    "denial_code":         "CO-50",
    "denial_reason":       "Not medically necessary",
    "denial_date":         "2026-10-01",
    "insurance_plan":      "Commercial PPO",
    "treating_physician":  "Specialist, Endocrinology",
    "clinical_notes": (
        "Patient has Type 1 diabetes for 25 years, on multiple daily injections "
        "with hypoglycemia unawareness. HbA1c 8.9%. Completed diabetes education. "
        "Severe hypoglycemia episodes require emergency evaluation."
    ),
    "prior_treatments": [
        "Multiple Daily Injections (MDI) — 25 years",
        "Various insulin formulations trialed",
        "Continuous Glucose Monitor (CGM) active",
    ],
    "labs": {
        "HbA1c":                        "8.9%",
        "hypoglycemia_episodes_6mo":    12,
        "severe_hypoglycemia_ed_visits": 3,
    },
}


# ── DenialAnalyzer ─────────────────────────────────────────────────────────

class TestDenialAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = DenialAnalyzer()

    def test_known_code_co50_classified_as_medical_necessity(self):
        result = self.analyzer.classify("CO-50", "Not medically necessary", "E0784")
        self.assertEqual(result["type"],     "medical_necessity")
        self.assertEqual(result["category"], "Clinical")
        self.assertEqual(result["matched_by"], "code")

    def test_known_code_co11_classified_as_coding_error(self):
        result = self.analyzer.classify("CO-11", "Diagnosis inconsistent with procedure", "")
        self.assertEqual(result["type"], "coding_error")

    def test_keyword_fallback_medical_necessity(self):
        result = self.analyzer.classify("ZZ-99", "Service not medically necessary per review", "")
        self.assertEqual(result["type"], "medical_necessity")
        self.assertEqual(result["matched_by"], "keyword")

    def test_keyword_fallback_experimental(self):
        result = self.analyzer.classify("UNK-1", "Procedure deemed experimental/investigational", "")
        self.assertEqual(result["type"], "experimental")

    def test_unknown_code_defaults_gracefully(self):
        result = self.analyzer.classify("XX-999", "Some totally unknown denial xyz", "")
        self.assertIn("type",     result)
        self.assertIn("category", result)
        self.assertIsInstance(result["type"], str)

    def test_prior_auth_code_classified_correctly(self):
        result = self.analyzer.classify("CO-197", "Authorization absent", "")
        self.assertEqual(result["type"], "prior_auth")

    def test_result_always_has_required_keys(self):
        result = self.analyzer.classify("", "", "")
        for key in ("type", "category", "code", "matched_by"):
            self.assertIn(key, result)


# ── EvidenceResearcher ─────────────────────────────────────────────────────

class TestEvidenceResearcher(unittest.TestCase):

    def setUp(self):
        self.researcher = EvidenceResearcher()

    def test_known_procedure_returns_specific_criteria(self):
        result = self.researcher.find_criteria("E0784", "E10.641", "medical_necessity")
        self.assertGreater(len(result["criteria"]),   0)
        self.assertGreater(len(result["guidelines"]), 0)
        self.assertIn("Insulin", result["procedure_name"])

    def test_unknown_procedure_returns_default_criteria(self):
        result = self.researcher.find_criteria("UNKNOWN999", "Z99.9", "medical_necessity")
        self.assertGreater(len(result["criteria"]), 0)

    def test_diagnosis_code_resolves_to_name(self):
        result = self.researcher.find_criteria("E0784", "E10.641", "medical_necessity")
        self.assertIn("Diabetes", result["diagnosis_name"])

    def test_extract_evidence_finds_supporting_facts(self):
        criteria = self.researcher.find_criteria("E0784", "E10.641", "medical_necessity")
        evidence = self.researcher.extract_evidence(SAMPLE_CASE, criteria)
        self.assertGreater(len(evidence["supporting_facts"]), 0)

    def test_extract_evidence_includes_lab_data(self):
        criteria = self.researcher.find_criteria("E0784", "E10.641", "medical_necessity")
        evidence = self.researcher.extract_evidence(SAMPLE_CASE, criteria)
        self.assertIn("HbA1c", evidence["labs"])

    def test_met_ratio_is_valid_proportion(self):
        criteria = self.researcher.find_criteria("E0784", "E10.641", "medical_necessity")
        evidence = self.researcher.extract_evidence(SAMPLE_CASE, criteria)
        self.assertGreaterEqual(evidence["met_ratio"], 0.0)
        self.assertLessEqual(evidence["met_ratio"],    1.0)

    def test_extract_evidence_has_strength_field(self):
        criteria = self.researcher.find_criteria("E0784", "E10.641", "medical_necessity")
        evidence = self.researcher.extract_evidence(SAMPLE_CASE, criteria)
        self.assertIn("strength", evidence)
        self.assertIsInstance(evidence["strength"], str)

    def test_extract_evidence_minimal_case(self):
        """Evidence extraction should not crash on a minimal case dict."""
        criteria = self.researcher.find_criteria("UNKNOWN", "", "default")
        evidence = self.researcher.extract_evidence({}, criteria)
        self.assertIn("met_ratio", evidence)


# ── AppealWriter ───────────────────────────────────────────────────────────

class TestAppealWriter(unittest.TestCase):

    def setUp(self):
        self.writer     = AppealWriter()
        self.analyzer   = DenialAnalyzer()
        self.researcher = EvidenceResearcher()

    def _inputs(self):
        denial_info = self.analyzer.classify("CO-50", "Not medically necessary", "E0784")
        criteria    = self.researcher.find_criteria("E0784", "E10.641", "medical_necessity")
        evidence    = self.researcher.extract_evidence(SAMPLE_CASE, criteria)
        strategy    = {
            "name":     "Medical Necessity with Clinical Evidence",
            "approach": "Document necessity with patient-specific data",
            "tone":     "clinical",
        }
        profile = {
            "primary_condition":     "T1DM",
            "age":                   52,
            "urgency":               "URGENT",
            "age_category":          "adult",
            "prior_treatments_count": 3,
            "has_lab_data":          True,
            "has_prior_treatments":  True,
        }
        return denial_info, criteria, evidence, strategy, profile

    def test_draft_produces_non_empty_letter(self):
        denial_info, criteria, evidence, strategy, profile = self._inputs()
        result = self.writer.draft(SAMPLE_CASE, denial_info, evidence, criteria, strategy, profile)
        self.assertIn("letter", result)
        self.assertGreater(len(result["letter"]), 200)

    def test_draft_includes_medical_necessity_section(self):
        denial_info, criteria, evidence, strategy, profile = self._inputs()
        result = self.writer.draft(SAMPLE_CASE, denial_info, evidence, criteria, strategy, profile)
        self.assertIn("MEDICAL NECESSITY", result["letter"])

    def test_draft_includes_guideline_section(self):
        denial_info, criteria, evidence, strategy, profile = self._inputs()
        result = self.writer.draft(SAMPLE_CASE, denial_info, evidence, criteria, strategy, profile)
        self.assertIn("GUIDELINES", result["letter"])

    def test_draft_includes_denial_code(self):
        denial_info, criteria, evidence, strategy, profile = self._inputs()
        result = self.writer.draft(SAMPLE_CASE, denial_info, evidence, criteria, strategy, profile)
        self.assertIn(SAMPLE_CASE["denial_code"], result["letter"])

    def test_draft_includes_procedure_code(self):
        denial_info, criteria, evidence, strategy, profile = self._inputs()
        result = self.writer.draft(SAMPLE_CASE, denial_info, evidence, criteria, strategy, profile)
        self.assertIn(SAMPLE_CASE["procedure_code"], result["letter"])

    def test_draft_all_sections_present(self):
        denial_info, criteria, evidence, strategy, profile = self._inputs()
        result = self.writer.draft(SAMPLE_CASE, denial_info, evidence, criteria, strategy, profile)
        for section in ("HEADER", "OPENING", "CLINICAL", "MEDICAL_NECESSITY", "GUIDELINES", "CLOSING"):
            self.assertIn(section, result["sections"], f"Missing section: {section}")


# ── SuccessPredictor ───────────────────────────────────────────────────────

class TestSuccessPredictor(unittest.TestCase):

    def setUp(self):
        self.predictor = SuccessPredictor()

    def _strong_inputs(self):
        denial_info = {"type": "medical_necessity", "category": "Clinical"}
        evidence    = {
            "strength":         "STRONG",
            "met_ratio":        0.85,
            "labs":             {"HbA1c": "8.9%"},
            "prior_treatments": ["MDI", "CGM", "Education"],
            "gaps":             [],
        }
        strategy = {"name": "Medical Necessity", "expedited": True}
        return denial_info, evidence, strategy

    def test_probability_in_valid_range(self):
        denial_info, evidence, strategy = self._strong_inputs()
        result = self.predictor.predict(denial_info, evidence, strategy, SAMPLE_CASE)
        self.assertGreaterEqual(result["probability"], 5)
        self.assertLessEqual(result["probability"],   95)

    def test_strong_evidence_beats_weak(self):
        denial_info, strong_evidence, strategy = self._strong_inputs()
        result_strong = self.predictor.predict(denial_info, strong_evidence, strategy, SAMPLE_CASE)

        weak_evidence = dict(strong_evidence, strength="WEAK", met_ratio=0.2, prior_treatments=[], labs={})
        result_weak   = self.predictor.predict(denial_info, weak_evidence, strategy, SAMPLE_CASE)
        self.assertGreater(result_strong["probability"], result_weak["probability"])

    def test_coding_error_higher_than_experimental(self):
        evidence = {"strength": "MODERATE", "met_ratio": 0.5, "labs": {}, "prior_treatments": [], "gaps": []}
        strategy = {"name": "Test"}
        r_code  = self.predictor.predict({"type": "coding_error"},   evidence, strategy, {})
        r_exper = self.predictor.predict({"type": "experimental"}, evidence, strategy, {})
        self.assertGreater(r_code["probability"], r_exper["probability"])

    def test_recommendation_is_non_empty_string(self):
        denial_info, evidence, strategy = self._strong_inputs()
        result = self.predictor.predict(denial_info, evidence, strategy, SAMPLE_CASE)
        self.assertIsInstance(result["recommendation"], str)
        self.assertGreater(len(result["recommendation"]), 10)

    def test_result_contains_all_required_keys(self):
        denial_info, evidence, strategy = self._strong_inputs()
        result = self.predictor.predict(denial_info, evidence, strategy, SAMPLE_CASE)
        for key in ("probability", "base_rate", "adjustment", "confidence", "risk",
                    "factors", "recommendation"):
            self.assertIn(key, result, f"Missing key: {key}")


# ── Full agent pipeline ────────────────────────────────────────────────────

class TestFullAgentPipeline(unittest.TestCase):

    def setUp(self):
        self.agent = PriorAuthAppealAgent(verbose=False)

    def test_pipeline_completes_all_7_steps(self):
        result = self.agent.run(SAMPLE_CASE)
        self.assertEqual(result["steps_completed"], 7)

    def test_pipeline_produces_appeal_letter(self):
        result = self.agent.run(SAMPLE_CASE)
        self.assertIn("appeal_letter", result)
        self.assertGreater(len(result["appeal_letter"]), 300)

    def test_pipeline_produces_valid_probability(self):
        result = self.agent.run(SAMPLE_CASE)
        self.assertIn("success_probability", result)
        self.assertGreaterEqual(result["success_probability"],  5)
        self.assertLessEqual(result["success_probability"],    95)

    def test_pipeline_produces_deadline(self):
        result = self.agent.run(SAMPLE_CASE)
        self.assertIn("deadline", result)
        self.assertIsInstance(result["deadline"], str)
        self.assertGreater(len(result["deadline"]), 0)

    def test_pipeline_handles_minimal_case(self):
        """Agent must not crash when optional fields are absent."""
        minimal = {
            "primary_diagnosis":   "Hypertension",
            "diagnosis_code":      "I10",
            "procedure_requested": "Cardiac Monitoring",
            "procedure_code":      "93228",
            "denial_code":         "CO-50",
            "denial_reason":       "Not medically necessary",
            "denial_date":         "2026-11-01",
        }
        result = self.agent.run(minimal)
        self.assertEqual(result["steps_completed"], 7)
        self.assertIn("appeal_letter", result)

    def test_execution_log_has_7_entries(self):
        result = self.agent.run(SAMPLE_CASE)
        self.assertGreaterEqual(len(result["execution_log"]), 7)

    def test_pipeline_knee_replacement_case(self):
        """Test with a different procedure to confirm generality."""
        knee_case = {
            "patient_id":          "PT-TEST-002",
            "patient_age":         67,
            "primary_diagnosis":   "Severe osteoarthritis of the right knee",
            "diagnosis_code":      "M17.11",
            "procedure_requested": "Total Knee Arthroplasty",
            "procedure_code":      "27447",
            "denial_code":         "CO-50",
            "denial_reason":       "Not medically necessary. Conservative treatment not exhausted.",
            "denial_date":         "2026-10-15",
            "prior_treatments":    ["Physical therapy 6 months", "NSAIDs 12 months", "Corticosteroid injections x3"],
            "labs":                {},
        }
        result = self.agent.run(knee_case)
        self.assertEqual(result["steps_completed"], 7)
        self.assertIn("appeal_letter", result)


# ── Runner ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
