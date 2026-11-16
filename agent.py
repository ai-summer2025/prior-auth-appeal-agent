"""
Prior Auth Appeal Agent — Core Orchestrator.

Runs a 7-step autonomous agentic pipeline:
  1. CLASSIFY  — Identify denial type from code / reason text
  2. PROFILE   — Build structured clinical context
  3. RESEARCH  — Look up applicable medical necessity criteria
  4. EVIDENCE  — Extract supporting facts from the case
  5. STRATEGY  — Select optimal appeal approach
  6. DRAFT     — Generate the appeal letter
  7. FINALIZE  — Predict success probability and package output
"""
import datetime
from typing import Any, Dict

from denial_analyzer    import DenialAnalyzer
from evidence_researcher import EvidenceResearcher
from appeal_writer      import AppealWriter
from success_predictor  import SuccessPredictor


class PriorAuthAppealAgent:
    """
    Autonomous agent that orchestrates end-to-end prior-authorization
    appeal generation from a structured case dictionary.
    """

    def __init__(self, verbose: bool = False):
        self.verbose          = verbose
        self.denial_analyzer  = DenialAnalyzer()
        self.evidence_researcher = EvidenceResearcher()
        self.appeal_writer    = AppealWriter()
        self.success_predictor = SuccessPredictor()
        self.execution_log = []

    # ── Public interface ─────────────────────────────────────────────────────

    def run(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the 7-step appeal generation pipeline and return results."""
        self.execution_log = []

        # ── Step 1: CLASSIFY ──────────────────────────────────────────────
        self._log("STEP 1 — CLASSIFY", "Analyzing denial code and reason text…")
        denial_info = self.denial_analyzer.classify(
            denial_code    = case.get("denial_code", ""),
            denial_reason  = case.get("denial_reason", ""),
            procedure_code = case.get("procedure_code", ""),
        )
        self._log(
            "STEP 1 — CLASSIFY",
            f"Type: {denial_info['type']} | Category: {denial_info['category']} "
            f"| Matched by: {denial_info['matched_by']}",
        )

        # ── Step 2: PROFILE ───────────────────────────────────────────────
        self._log("STEP 2 — PROFILE", "Building structured clinical context…")
        clinical_profile = self._build_profile(case, denial_info)
        self._log(
            "STEP 2 — PROFILE",
            f"Condition: {clinical_profile['primary_condition']} | "
            f"Urgency: {clinical_profile['urgency']} | "
            f"Age category: {clinical_profile['age_category']}",
        )

        # ── Step 3: RESEARCH ──────────────────────────────────────────────
        self._log("STEP 3 — RESEARCH", "Looking up applicable medical necessity criteria…")
        criteria = self.evidence_researcher.find_criteria(
            procedure_code = case.get("procedure_code", ""),
            diagnosis_code = case.get("diagnosis_code", ""),
            denial_type    = denial_info["type"],
        )
        self._log(
            "STEP 3 — RESEARCH",
            f"Procedure: {criteria['procedure_name']} | "
            f"{len(criteria['criteria'])} criteria | "
            f"{len(criteria['guidelines'])} guideline sources",
        )

        # ── Step 4: EVIDENCE ──────────────────────────────────────────────
        self._log("STEP 4 — EVIDENCE", "Extracting supporting clinical evidence from case…")
        evidence = self.evidence_researcher.extract_evidence(case, criteria)
        self._log(
            "STEP 4 — EVIDENCE",
            f"Strength: {evidence['strength']} | "
            f"Criteria met: {len(evidence['criteria_met'])}/{len(criteria['criteria'])} | "
            f"Supporting facts: {len(evidence['supporting_facts'])}",
        )

        # ── Step 5: STRATEGY ──────────────────────────────────────────────
        self._log("STEP 5 — STRATEGY", "Selecting optimal appeal strategy…")
        strategy = self._select_strategy(denial_info, evidence, clinical_profile)
        self._log("STEP 5 — STRATEGY", f"Selected: {strategy['name']}")

        # ── Step 6: DRAFT ─────────────────────────────────────────────────
        self._log("STEP 6 — DRAFT", "Generating appeal letter…")
        draft = self.appeal_writer.draft(
            case             = case,
            denial_info      = denial_info,
            evidence         = evidence,
            criteria         = criteria,
            strategy         = strategy,
            clinical_profile = clinical_profile,
        )
        self._log(
            "STEP 6 — DRAFT",
            f"Letter complete: {draft['word_count']} words, {len(draft['sections'])} sections",
        )

        # ── Step 7: FINALIZE ──────────────────────────────────────────────
        self._log("STEP 7 — FINALIZE", "Predicting appeal success probability…")
        assessment = self.success_predictor.predict(
            denial_info = denial_info,
            evidence    = evidence,
            strategy    = strategy,
            case        = case,
        )
        self._log(
            "STEP 7 — FINALIZE",
            f"Probability: {assessment['probability']}% | "
            f"Confidence: {assessment['confidence']} | "
            f"Risk: {assessment['risk']}",
        )

        deadline = self._deadline(case.get("denial_date", ""), denial_info)

        return {
            "appeal_letter":      draft["letter"],
            "denial_type":        denial_info["type"],
            "denial_category":    denial_info["category"],
            "strategy":           strategy["name"],
            "success_probability": assessment["probability"],
            "confidence":         assessment["confidence"],
            "risk":               assessment["risk"],
            "deadline":           deadline,
            "steps_completed":    7,
            "execution_log":      self.execution_log,
            "evidence_summary":   evidence,
            "assessment_detail":  assessment,
        }

    # ── Private helpers ──────────────────────────────────────────────────────

    def _log(self, step: str, message: str) -> None:
        entry = {
            "step":      step,
            "message":   message,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.execution_log.append(entry)
        if self.verbose:
            print(f"  [{step}] {message}")

    def _build_profile(self, case: dict, denial_info: dict) -> dict:
        age   = case.get("patient_age", 0)
        notes = case.get("clinical_notes", "").lower()
        labs  = case.get("labs", {})

        urgency = "ROUTINE"
        urgent_keywords = ["emergency", "urgent", "life-threatening", "critical", "severe", "immediate"]
        if any(w in notes for w in urgent_keywords):
            urgency = "URGENT"
        if labs.get("severe_hypoglycemia_ed_visits", 0) >= 2:
            urgency = "URGENT"

        return {
            "primary_condition":     case.get("primary_diagnosis", "Unknown"),
            "age":                   age,
            "age_category":          "pediatric" if age < 18 else ("geriatric" if age >= 65 else "adult"),
            "urgency":               urgency,
            "prior_treatments_count": len(case.get("prior_treatments", [])),
            "has_lab_data":          bool(labs),
            "has_prior_treatments":  bool(case.get("prior_treatments")),
        }

    def _select_strategy(self, denial_info: dict, evidence: dict, profile: dict) -> dict:
        strategies = {
            "medical_necessity": {
                "name":     "Medical Necessity with Clinical Evidence",
                "approach": "Document necessity with patient-specific data, failed alternatives, and guideline citations",
                "tone":     "clinical",
            },
            "experimental": {
                "name":     "Evidence-Based Medicine Defense",
                "approach": "Cite peer-reviewed studies and professional society guidelines supporting efficacy",
                "tone":     "scientific",
            },
            "not_covered": {
                "name":     "Coverage Interpretation Appeal",
                "approach": "Challenge coverage denial using plan document language and regulatory requirements",
                "tone":     "legal",
            },
            "coding_error": {
                "name":     "Corrective Resubmission with Clinical Rationale",
                "approach": "Correct coding errors with supporting documentation",
                "tone":     "technical",
            },
            "prior_auth": {
                "name":     "Retroactive Authorization with Medical Necessity",
                "approach": "Demonstrate urgency that precluded prior auth and document medical necessity",
                "tone":     "clinical",
            },
        }

        strategy = dict(strategies.get(denial_info.get("type", ""), {
            "name":     "Comprehensive Multi-Ground Appeal",
            "approach": "Address all potential denial grounds with clinical evidence and guideline support",
            "tone":     "clinical",
        }))

        if profile.get("urgency") == "URGENT":
            strategy["name"]      = "EXPEDITED — " + strategy["name"]
            strategy["expedited"] = True

        return strategy

    def _deadline(self, denial_date: str, denial_info: dict) -> str:
        """Return appeal filing deadline string."""
        try:
            dt   = datetime.datetime.strptime(denial_date, "%Y-%m-%d")
            days = 180 if denial_info.get("payer_type") == "medicare" else 120
            return (dt + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        except Exception:
            return "Within 120–180 days of denial date (verify with payer)"
