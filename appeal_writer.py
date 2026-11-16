"""
Appeal Writer — Generates structured prior-authorization appeal letters.
Step 6 of the Prior Auth Appeal Agent pipeline.
"""
import datetime


class AppealWriter:

    def draft(
        self,
        case:             dict,
        denial_info:      dict,
        evidence:         dict,
        criteria:         dict,
        strategy:         dict,
        clinical_profile: dict,
    ) -> dict:
        """Assemble a complete, clinician-ready appeal letter."""
        today = datetime.date.today().strftime("%B %d, %Y")
        sections = []

        header    = self._header(case, today);         sections.append("HEADER")
        opening   = self._opening(case, denial_info);  sections.append("OPENING")
        clinical  = self._clinical_summary(case, evidence, clinical_profile); sections.append("CLINICAL")
        necessity = self._medical_necessity(case, evidence, criteria, denial_info); sections.append("MEDICAL_NECESSITY")
        guideline = self._guideline_support(criteria); sections.append("GUIDELINES")
        closing   = self._closing(case);               sections.append("CLOSING")

        full_letter = "\n\n".join([header, opening, clinical, necessity, guideline, closing])

        return {
            "letter":     full_letter,
            "sections":   sections,
            "word_count": len(full_letter.split()),
        }

    # ── Private section builders ─────────────────────────────────────────────

    def _header(self, case: dict, today: str) -> str:
        return (
            f"APPEAL OF CLAIM DENIAL\n"
            f"{'='*60}\n"
            f"Date:              {today}\n"
            f"Patient ID:        {case.get('patient_id', 'N/A')}\n"
            f"Patient:           {case.get('patient_age', '—')}-year-old {case.get('patient_sex', '')}\n"
            f"Diagnosis:         {case.get('primary_diagnosis', 'N/A')} ({case.get('diagnosis_code', '')})\n"
            f"Requested Service: {case.get('procedure_requested', 'N/A')} ({case.get('procedure_code', '')})\n"
            f"Denial Code:       {case.get('denial_code', 'N/A')}\n"
            f"Date of Denial:    {case.get('denial_date', 'N/A')}\n"
            f"Insurance Plan:    {case.get('insurance_plan', 'N/A')}\n"
            f"Treating Provider: {case.get('treating_physician', 'N/A')}\n"
            f"{'='*60}"
        )

    def _opening(self, case: dict, denial_info: dict) -> str:
        procedure = case.get("procedure_requested", "the requested procedure")
        denial_date = case.get("denial_date", "")
        denial_desc = denial_info.get("description", "lack of medical necessity")
        return (
            f"RE: FORMAL FIRST-LEVEL APPEAL — {procedure}\n"
            f"    Denial Code: {case.get('denial_code', '')} — {denial_desc}\n\n"
            f"Dear Medical Director / Utilization Review Committee,\n\n"
            f"We write on behalf of our patient to formally appeal the denial of coverage "
            f"for {procedure}, issued on {denial_date}. The denial cited "
            f'"{denial_desc}." We respectfully submit that this determination is '
            f"inconsistent with the clinical evidence, applicable medical necessity criteria, "
            f"and established professional practice standards, and we request full reversal.\n\n"
            f"Given the documented clinical urgency, we respectfully request expedited review "
            f"within 72 hours."
        )

    def _clinical_summary(self, case: dict, evidence: dict, profile: dict) -> str:
        urgency_banner = ""
        if profile.get("urgency") == "URGENT":
            urgency_banner = (
                "\n⚠  URGENT CLINICAL SITUATION — Patient has documented acute risk "
                "requiring timely intervention. Delay in approval may result in "
                "preventable hospitalization.\n"
            )

        treatments = evidence.get("prior_treatments", [])
        tx_lines = "\n".join(f"  • {t}" for t in treatments) if treatments else "  • See attached clinical notes"

        labs = evidence.get("labs", {})
        lab_lines = ""
        if labs:
            items = [f"  • {k.replace('_', ' ').title()}: {v}" for k, v in labs.items()]
            lab_lines = "\nObjective Laboratory / Clinical Data:\n" + "\n".join(items)

        return (
            f"CLINICAL SUMMARY\n"
            f"{'-'*40}"
            f"{urgency_banner}\n"
            f"Primary Diagnosis:  {case.get('primary_diagnosis', 'N/A')}\n"
            f"Requested Service:  {case.get('procedure_requested', 'N/A')}\n\n"
            f"Clinical Background:\n"
            f"{case.get('clinical_notes', 'Please refer to attached clinical documentation.')}\n"
            f"\nStep Therapy / Prior Treatments Attempted:\n"
            f"{tx_lines}"
            f"{lab_lines}"
        )

    def _medical_necessity(
        self, case: dict, evidence: dict, criteria: dict, denial_info: dict
    ) -> str:
        procedure = case.get("procedure_requested", "the requested procedure")
        condition = case.get("primary_diagnosis", "the documented condition")

        facts = evidence.get("supporting_facts", [])
        facts_text = (
            "\n".join(facts)
            if facts
            else "  Clinical documentation supports all applicable criteria (see attached records)."
        )

        denial_code = case.get("denial_code", "")
        counters = criteria.get("denial_counters", {})
        counter_text = counters.get(
            denial_code,
            (
                "The clinical evidence demonstrates that this patient satisfies all applicable "
                "medical necessity criteria for the requested service. The denial rationale does "
                "not align with the documented clinical facts."
            ),
        )

        gaps = evidence.get("gaps", [])
        gap_note = ""
        if gaps:
            gap_note = (
                "\n\nNote: The following criteria require additional documentation, "
                "which is attached:\n" + "\n".join(f"  {g}" for g in gaps[:3])
            )

        return (
            f"MEDICAL NECESSITY ARGUMENT\n"
            f"{'-'*40}\n\n"
            f"The treating physician has determined that {procedure} is medically necessary "
            f"for this patient. The following clinical evidence demonstrates that the patient "
            f"satisfies all applicable coverage criteria:\n\n"
            f"CRITERIA DOCUMENTATION:\n"
            f"{facts_text}"
            f"{gap_note}\n\n"
            f"RESPONSE TO DENIAL RATIONALE:\n"
            f"{counter_text}\n\n"
            f"This patient carries an established diagnosis of {condition}, confirmed by clinical "
            f"evaluation, objective laboratory findings, and specialist assessment. "
            f"{procedure} represents the medically appropriate next step following documented "
            f"failure of or contraindication to alternative treatments.\n\n"
            f"Denial of this service would result in continued suboptimal disease management, "
            f"increased risk of acute complications, and preventable emergency utilization — "
            f"all of which carry substantially greater clinical and financial cost than the "
            f"requested intervention."
        )

    def _guideline_support(self, criteria: dict) -> str:
        guidelines = criteria.get("guidelines", [])
        gl_text = "\n".join(f"  {i+1}. {g}" for i, g in enumerate(guidelines))

        return (
            f"SUPPORTING MEDICAL LITERATURE AND GUIDELINES\n"
            f"{'-'*40}\n\n"
            f"The following professional society guidelines and published clinical evidence "
            f"support the medical necessity of the requested service:\n\n"
            f"{gl_text}\n\n"
            f"Evidence Summary: {criteria.get('evidence_base', 'Published clinical evidence supports the requested intervention.')}\n\n"
            f"The applicable coverage criteria, properly applied to this patient's clinical "
            f"presentation, support approval. We respectfully submit that a thorough, "
            f"clinically informed review of the attached documentation will confirm that "
            f"all coverage requirements are met."
        )

    def _closing(self, case: dict) -> str:
        procedure = case.get("procedure_requested", "the requested service")
        physician = case.get("treating_physician", "Treating Physician")
        plan      = case.get("insurance_plan", "")

        return (
            f"REQUESTED ACTION\n"
            f"{'-'*40}\n\n"
            f"We respectfully request:\n"
            f"  1. Immediate reversal of the denial and approval of {procedure}\n"
            f"  2. If additional information is required, please contact our office within 5 business days\n"
            f"  3. If denial is upheld at this level, written explanation with specific clinical rationale\n\n"
            f"Should this appeal be denied, we will pursue all available levels of review, "
            f"including external independent review as required by state and federal law "
            f"(ERISA § 503; ACA § 2719; state insurance code).\n\n"
            f"Attachments:\n"
            f"  • Complete clinical notes and office visit records\n"
            f"  • Laboratory results and diagnostic imaging reports\n"
            f"  • Step therapy documentation and treatment history\n"
            f"  • Supporting peer-reviewed medical literature\n\n"
            f"We appreciate your prompt attention to this clinically urgent matter.\n\n"
            f"Respectfully submitted,\n\n"
            f"{physician}\n"
            f"{'cc: ' + plan + ' Member Services' if plan else ''}\n\n"
            f"{'─'*60}\n"
            f"Generated by Prior Auth Appeal Agent | "
            f"All clinical determinations must be reviewed and co-signed by the treating "
            f"physician before submission. This output does not constitute legal or medical advice."
        )
