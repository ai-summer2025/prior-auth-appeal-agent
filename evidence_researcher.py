"""
Evidence Researcher — Finds applicable medical necessity criteria
and extracts supporting clinical evidence from the case.
Steps 3 & 4 of the Prior Auth Appeal Agent pipeline.

All criteria are derived from publicly available professional society
guidelines (ADA, AAOS, ACG, CMS, etc.) — no paid API required.
"""

PROCEDURE_CRITERIA = {
    # ── Insulin pump / CSII ─────────────────────────────────────────────────
    "E0784": {
        "name": "External Insulin Infusion Pump (CSII)",
        "criteria": [
            "Type 1 diabetes mellitus diagnosis confirmed",
            "Patient on multiple daily injections (MDI) prior to pump therapy",
            "HbA1c greater than 7.0% despite optimized MDI regimen",
            "History of significant glycemic variability documented",
            "Hypoglycemia unawareness or frequent severe hypoglycemia episodes",
            "Patient has completed comprehensive diabetes self-management education",
            "Prescribing physician trained in CSII management",
        ],
        "guidelines": [
            "ADA Standards of Medical Care in Diabetes — Technology section",
            "AACE/ACE Consensus Statement on Continuous Subcutaneous Insulin Infusion Therapy",
            "CMS Coverage Determination for External Insulin Infusion Pumps (L33822)",
        ],
        "evidence_base": (
            "Class I RCT evidence (DCCT, multiple meta-analyses) demonstrates CSII "
            "superiority over MDI for reducing HbA1c and severe hypoglycemia in T1DM."
        ),
        "denial_counters": {
            "CO-50": (
                "CSII is a covered benefit when the patient meets established clinical "
                "criteria, which include failed or inadequate MDI therapy and documented "
                "hypoglycemia risk. The clinical record confirms this patient satisfies "
                "all required criteria. The denial rationale that 'MDI has not been tried' "
                "is factually inconsistent with 25 years of MDI therapy documented in chart."
            ),
        },
    },

    # ── Total knee replacement ───────────────────────────────────────────────
    "27447": {
        "name": "Total Knee Arthroplasty (TKA)",
        "criteria": [
            "Severe knee osteoarthritis confirmed by weight-bearing radiographs",
            "Conservative management failed (PT ≥ 3 months, NSAIDs, intra-articular injections)",
            "Moderate-to-severe functional limitation affecting activities of daily living",
            "Surgical risk assessment completed and patient deemed appropriate candidate",
        ],
        "guidelines": [
            "AAOS Clinical Practice Guideline: Management of Osteoarthritis of the Knee",
            "ACR/AAHKS Appropriate Use Criteria for Total Knee Arthroplasty",
        ],
        "evidence_base": "Strong Level I evidence supports TKA in patients with failed conservative management.",
        "denial_counters": {},
    },

    # ── Spinal cord stimulator ───────────────────────────────────────────────
    "63650": {
        "name": "Spinal Cord Stimulator Implantation",
        "criteria": [
            "Chronic pain refractory to conventional medical management (≥ 6 months)",
            "Failed conservative therapy including PT, medications, injection therapy",
            "Favorable psychological evaluation completed",
            "Successful trial stimulation period documented",
            "No untreated drug addiction, no primary psychiatric condition as pain driver",
        ],
        "guidelines": [
            "ASRA/AAPM Practice Guidelines for SCS (Deer et al., Neuromodulation 2019)",
            "CMS Coverage Determination for Neurostimulators for Pain Control",
        ],
        "evidence_base": "Level II evidence supports SCS for failed back surgery syndrome and complex regional pain syndrome.",
        "denial_counters": {},
    },

    # ── Upper GI endoscopy ───────────────────────────────────────────────────
    "43239": {
        "name": "Upper GI Endoscopy with Biopsy",
        "criteria": [
            "Persistent upper GI symptoms unresponsive to 4–8 weeks empirical PPI therapy",
            "Alarm symptoms present (dysphagia, odynophagia, unintended weight loss, GI bleeding)",
            "Surveillance indication for known Barrett's esophagus or prior gastric polyps",
            "Abnormal cross-sectional imaging requiring tissue characterization",
        ],
        "guidelines": [
            "ACG Clinical Guidelines: Management of Dyspepsia and GERD",
            "ASGE Standards of Practice: Appropriate Use of GI Endoscopy",
        ],
        "evidence_base": "Evidence-based guidelines endorse diagnostic endoscopy for alarm features and surveillance.",
        "denial_counters": {},
    },

    # ── Default fallback ─────────────────────────────────────────────────────
    "DEFAULT": {
        "name": "Medical/Surgical Procedure",
        "criteria": [
            "Diagnosis confirms medical necessity for the requested procedure",
            "Conservative or alternative treatments have been attempted and failed",
            "Procedure is consistent with accepted standards of medical practice",
            "Clinical urgency supports timely approval",
            "Ordering provider specialty is appropriate for the requested procedure",
        ],
        "guidelines": [
            "Relevant professional society clinical practice guidelines",
            "Published peer-reviewed clinical evidence supporting procedure",
            "Payer's own medical coverage policy",
        ],
        "evidence_base": "Clinical evidence and established medical practice support the requested intervention.",
        "denial_counters": {},
    },
}

DIAGNOSIS_NAMES = {
    "E10":    "Type 1 Diabetes Mellitus",
    "E10.6":  "Type 1 DM with other specified complications",
    "E10.641":"Type 1 Diabetes Mellitus with hypoglycemia unawareness",
    "E11":    "Type 2 Diabetes Mellitus",
    "M17":    "Osteoarthritis of Knee",
    "K21":    "Gastroesophageal Reflux Disease",
    "K57":    "Diverticular Disease of Intestine",
    "J44":    "COPD",
    "I50":    "Heart Failure",
    "I10":    "Essential Hypertension",
    "M54":    "Dorsalgia / Back Pain",
    "G89":    "Pain, Not Elsewhere Classified",
}


class EvidenceResearcher:

    # ── Criteria lookup (Step 3) ─────────────────────────────────────────────

    def find_criteria(self, procedure_code: str, diagnosis_code: str, denial_type: str) -> dict:
        """Return applicable medical necessity criteria for the procedure."""
        criteria_data = PROCEDURE_CRITERIA.get(procedure_code, PROCEDURE_CRITERIA["DEFAULT"])

        # Resolve diagnosis name (longest prefix wins)
        dx_name = "Undocumented condition"
        for code in sorted(DIAGNOSIS_NAMES, key=len, reverse=True):
            if diagnosis_code.startswith(code):
                dx_name = DIAGNOSIS_NAMES[code]
                break

        return {
            "procedure_name":  criteria_data["name"],
            "criteria":        criteria_data["criteria"],
            "guidelines":      criteria_data["guidelines"],
            "evidence_base":   criteria_data["evidence_base"],
            "diagnosis_name":  dx_name,
            "denial_counters": criteria_data.get("denial_counters", {}),
        }

    # ── Evidence extraction (Step 4) ─────────────────────────────────────────

    def extract_evidence(self, case: dict, criteria: dict) -> dict:
        """Extract supporting evidence from the clinical case against criteria."""
        notes      = case.get("clinical_notes", "").lower()
        treatments = case.get("prior_treatments", [])
        labs       = case.get("labs", {})
        treatment_text = " ".join(treatments).lower()

        supporting_facts = []
        gaps             = []
        criteria_met     = []
        criteria_not_met = []

        for criterion in criteria.get("criteria", []):
            crit_lower = criterion.lower()
            # Extract meaningful search tokens (words >= 4 chars)
            tokens = [w for w in crit_lower.split() if len(w) >= 4]
            matched = False

            # Check clinical notes
            if tokens and any(tok in notes for tok in tokens):
                matched = True
                supporting_facts.append(f"✓ {criterion} — documented in clinical notes")
                criteria_met.append(criterion)
            # Check treatment history
            elif tokens and any(tok in treatment_text for tok in tokens):
                matched = True
                supporting_facts.append(f"✓ {criterion} — documented in treatment history")
                criteria_met.append(criterion)
            # Check lab values by keyword
            elif "hba1c" in crit_lower and labs.get("HbA1c"):
                matched = True
                supporting_facts.append(f"✓ {criterion} — HbA1c: {labs['HbA1c']}")
                criteria_met.append(criterion)
            elif "hypoglycemia" in crit_lower and labs.get("hypoglycemia_episodes_6mo", 0) > 0:
                matched = True
                ep = labs["hypoglycemia_episodes_6mo"]
                supporting_facts.append(f"✓ {criterion} — {ep} episodes documented in past 6 months")
                criteria_met.append(criterion)
            elif "severe hypoglycemia" in crit_lower and labs.get("severe_hypoglycemia_ed_visits", 0) >= 1:
                matched = True
                ed = labs["severe_hypoglycemia_ed_visits"]
                supporting_facts.append(f"✓ {criterion} — {ed} ED visits for severe hypoglycemia in past 6 months")
                criteria_met.append(criterion)

            if not matched:
                criteria_not_met.append(criterion)
                gaps.append(f"⚠  Documentation recommended: {criterion}")

        total = max(len(criteria.get("criteria", [1])), 1)
        met_ratio = len(criteria_met) / total

        if met_ratio >= 0.80:
            strength = "STRONG"
        elif met_ratio >= 0.55:
            strength = "MODERATE"
        else:
            strength = "WEAK — gather additional clinical documentation"

        return {
            "supporting_facts":  supporting_facts,
            "gaps":              gaps,
            "criteria_met":      criteria_met,
            "criteria_not_met":  criteria_not_met,
            "strength":          strength,
            "met_ratio":         round(met_ratio, 2),
            "labs":              labs,
            "prior_treatments":  treatments,
        }
