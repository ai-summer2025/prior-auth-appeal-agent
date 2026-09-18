"""
Tests for Prior Authorization Appeal Agent
"""
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from agent import (
    DenialCase, DenialAnalyzerTool, ClinicalGuidelineTool,
    PubMedSearchTool, PriorAuthAppealAgent, AppealLetterWriter,
    EvidenceItem, SAMPLE_CASES
)


class TestDenialAnalyzerTool(unittest.TestCase):
    def setUp(self):
        self.analyzer = DenialAnalyzerTool()

    def test_detects_medical_necessity_denial(self):
        strategy = self.analyzer.analyze("Not medically necessary per payer criteria")
        self.assertEqual(strategy["rebuttal_angle"], "medical necessity")
        self.assertGreater(len(strategy["key_arguments"]), 0)

    def test_detects_experimental_denial(self):
        strategy = self.analyzer.analyze("Treatment is experimental and investigational")
        self.assertEqual(strategy["rebuttal_angle"], "established clinical evidence")

    def test_detects_step_therapy_denial(self):
        strategy = self.analyzer.analyze("Patient has not completed required step therapy protocol")
        self.assertEqual(strategy["rebuttal_angle"], "step therapy exception")

    def test_detects_out_of_network_denial(self):
        strategy = self.analyzer.analyze("Provider is out of network")
        self.assertEqual(strategy["rebuttal_angle"], "network adequacy / continuity of care")

    def test_default_strategy_for_unknown_denial(self):
        strategy = self.analyzer.analyze("Some completely novel denial reason xyz")
        self.assertIn("rebuttal_angle", strategy)
        self.assertIn("key_arguments", strategy)
        self.assertIn("urgency", strategy)

    def test_urgency_is_valid_value(self):
        for denial_reason in ["Not medically necessary", "experimental", "step therapy"]:
            strategy = self.analyzer.analyze(denial_reason)
            self.assertIn(strategy["urgency"], ["high", "medium", "low"])


class TestClinicalGuidelineTool(unittest.TestCase):
    def setUp(self):
        self.tool = ClinicalGuidelineTool()

    def test_rheumatology_codes(self):
        guidelines = self.tool.get_guidelines(["M06.09", "M05.79"])
        orgs = [g["org"] for g in guidelines]
        self.assertIn("American College of Rheumatology", orgs)

    def test_oncology_codes(self):
        guidelines = self.tool.get_guidelines(["C34.10"])
        orgs = [g["org"] for g in guidelines]
        self.assertIn("National Comprehensive Cancer Network", orgs)

    def test_diabetes_codes(self):
        guidelines = self.tool.get_guidelines(["E11.649"])
        orgs = [g["org"] for g in guidelines]
        self.assertIn("American Diabetes Association", orgs)

    def test_returns_list(self):
        guidelines = self.tool.get_guidelines(["M06.09"])
        self.assertIsInstance(guidelines, list)
        self.assertGreater(len(guidelines), 0)

    def test_deduplication(self):
        # Same prefix should not yield duplicates
        guidelines = self.tool.get_guidelines(["M06.09", "M05.79", "M79.3"])
        orgs = [g["org"] for g in guidelines]
        self.assertEqual(len(orgs), len(set(orgs)))

    def test_unknown_code_uses_default(self):
        guidelines = self.tool.get_guidelines(["Z99.99"])
        self.assertGreater(len(guidelines), 0)
        orgs = [g["org"] for g in guidelines]
        self.assertIn("U.S. Preventive Services Task Force", orgs)


class TestPubMedSearchTool(unittest.TestCase):
    def setUp(self):
        self.tool = PubMedSearchTool()

    def test_mock_results_return_list(self):
        results = self.tool._mock_results("rheumatoid arthritis")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_mock_results_have_required_fields(self):
        results = self.tool._mock_results("test query")
        for r in results:
            self.assertIn("title", r)
            self.assertIn("source", r)
            self.assertIn("year", r)

    def test_real_search_or_fallback(self):
        # Either returns real results or mock fallback -- both are valid
        results = self.tool.search("rheumatoid arthritis biologic treatment", max_results=2)
        self.assertIsInstance(results, list)
        # Should return at least something (mock fallback if network unavailable)
        self.assertGreater(len(results), 0)


class TestPriorAuthAppealAgent(unittest.TestCase):
    def setUp(self):
        self.agent = PriorAuthAppealAgent(verbose=False)

    def test_run_returns_appeal_letter(self):
        case = SAMPLE_CASES["CASE-001"]
        result = self.agent.run(case)
        self.assertIsNotNone(result)
        self.assertEqual(result.case_id, "CASE-001")

    def test_appeal_letter_has_required_sections(self):
        case = SAMPLE_CASES["CASE-001"]
        result = self.agent.run(case)
        letter = result.letter_text
        self.assertIn("APPEAL LETTER", letter)
        self.assertIn("SECTION I", letter)
        self.assertIn("SECTION II", letter)
        self.assertIn("SECTION IV", letter)

    def test_appeal_strength_is_valid(self):
        case = SAMPLE_CASES["CASE-002"]
        result = self.agent.run(case)
        self.assertIn(result.appeal_strength, ["Strong", "Moderate", "Weak"])

    def test_confidence_score_in_range(self):
        case = SAMPLE_CASES["CASE-003"]
        result = self.agent.run(case)
        self.assertGreaterEqual(result.confidence_score, 0.0)
        self.assertLessEqual(result.confidence_score, 1.0)

    def test_evidence_count_positive(self):
        case = SAMPLE_CASES["CASE-001"]
        result = self.agent.run(case)
        self.assertGreater(result.evidence_count, 0)

    def test_letter_contains_case_metadata(self):
        case = SAMPLE_CASES["CASE-001"]
        result = self.agent.run(case)
        self.assertIn("CASE-001", result.letter_text)
        self.assertIn("M06.09", result.letter_text)
        self.assertIn(case.treating_physician, result.letter_text)

    def test_all_sample_cases_run_successfully(self):
        for case_id, case in SAMPLE_CASES.items():
            with self.subTest(case_id=case_id):
                result = self.agent.run(case)
                self.assertIsNotNone(result)
                self.assertGreater(len(result.letter_text), 500)

    def test_evidence_scoring_orders_by_relevance(self):
        evidence_dicts = [
            {"title": "random unrelated paper", "year": "2020", "source": "Journal A"},
            {"title": "systematic review biologic therapy rheumatoid arthritis M06.09", "year": "2025", "source": "NEJM"},
        ]
        items = self.agent._score_evidence(evidence_dicts, ["biologic", "rheumatoid", "M06.09"])
        if len(items) >= 2:
            # Higher relevance should come first
            self.assertGreaterEqual(items[0].relevance_score, items[-1].relevance_score)


class TestAppealLetterWriter(unittest.TestCase):
    def setUp(self):
        self.writer = AppealLetterWriter()
        self.case = SAMPLE_CASES["CASE-001"]
        self.strategy = {
            "rebuttal_angle": "medical necessity",
            "key_arguments": ["Argument one", "Argument two"],
            "urgency": "high",
        }
        self.evidence = [
            EvidenceItem(title="Test Study", source="JAMA", pmid="12345", year="2024",
                         relevance_score=0.8, key_finding="Strong evidence found")
        ]
        self.guidelines = [
            {"org": "Test Org", "guideline": "Test Guidelines", "year": "2024"}
        ]

    def test_letter_is_string(self):
        letter = self.writer.write(self.case, self.strategy, self.evidence, self.guidelines)
        self.assertIsInstance(letter, str)

    def test_letter_minimum_length(self):
        letter = self.writer.write(self.case, self.strategy, self.evidence, self.guidelines)
        self.assertGreater(len(letter), 800)

    def test_letter_includes_payer_name(self):
        letter = self.writer.write(self.case, self.strategy, self.evidence, self.guidelines)
        self.assertIn(self.case.payer_name, letter)

    def test_letter_includes_diagnosis_codes(self):
        letter = self.writer.write(self.case, self.strategy, self.evidence, self.guidelines)
        for code in self.case.diagnosis_codes:
            self.assertIn(code, letter)

    def test_letter_includes_evidence_pmid(self):
        letter = self.writer.write(self.case, self.strategy, self.evidence, self.guidelines)
        self.assertIn("12345", letter)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
