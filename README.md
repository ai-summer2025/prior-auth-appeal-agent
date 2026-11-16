# prior-auth-appeal-agent

![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![No API Key Required](https://img.shields.io/badge/API%20Key-None%20Required-brightgreen)
![Tests Passing](https://img.shields.io/badge/Tests-Passing-success)
![Healthcare AI](https://img.shields.io/badge/Domain-Healthcare%20AI-red)

**An autonomous 7-step AI agent that analyzes insurance claim denials and generates evidence-based prior-authorization appeal letters — with zero paid APIs and zero LLM calls required.**

---

## The Problem

**41% of all healthcare claims are denied.** Hospitals collectively spend over **$5.9 billion per year** manually fighting these denials, dedicating entire teams of nurses, physicians, and billing specialists to writing appeal letters that often follow the same evidence-based patterns.

The manual appeal process is broken:
- Clinicians spend 2–4 hours drafting a single appeal letter
- Appeals must cite specific medical necessity criteria, professional society guidelines, and step-therapy documentation — most of which is already in the chart
- Errors in appeal structure reduce success rates significantly
- Deadlines are missed, leaving revenue on the table
- **And yet, 75% of medical necessity appeals are overturned when properly documented and filed** (AMA, 2024)

The gap isn't medical knowledge — it's time. This agent closes that gap.

---

## How It Works — The 7-Step Agentic Pipeline

```
Case JSON
   │
   ▼
╔══════════════════════════════════════════════════════╗
║  Step 1: CLASSIFY    — Identify denial type from     ║
║          code (CO-50, OA-23…) or reason text         ║
╠══════════════════════════════════════════════════════╣
║  Step 2: PROFILE     — Build structured clinical     ║
║          context (urgency, age category, tx history) ║
╠══════════════════════════════════════════════════════╣
║  Step 3: RESEARCH    — Look up applicable medical    ║
║          necessity criteria for the procedure        ║
╠══════════════════════════════════════════════════════╣
║  Step 4: EVIDENCE    — Extract supporting facts from ║
║          clinical notes, labs, treatment history     ║
╠══════════════════════════════════════════════════════╣
║  Step 5: STRATEGY    — Select optimal appeal         ║
║          approach based on denial type & evidence    ║
╠══════════════════════════════════════════════════════╣
║  Step 6: DRAFT       — Generate structured appeal    ║
║          letter with clinical rationale              ║
╠══════════════════════════════════════════════════════╣
║  Step 7: FINALIZE    — Predict success probability   ║
║          and package clinician-ready output          ║
╚══════════════════════════════════════════════════════╝
   │
   ▼
Appeal Letter + Success % + Deadline + Action Plan
```

**Key design decisions:**
- Pure Python with zero external API calls — works fully offline
- All medical necessity criteria derived from public professional society guidelines (ADA, AAOS, ACG, CMS)
- Modular — each pipeline stage is a separate class, easy to extend
- Evidence extraction uses structured pattern matching against criteria, not fuzzy LLM guessing
- Success probability calibrated against published appeals outcome research (KFF, HFMA, AMA)

---

## Installation

```bash
git clone https://github.com/ai-summer2025/prior-auth-appeal-agent
cd prior-auth-appeal-agent
pip install pytest   # only dependency needed for testing
```

No API keys. No `.env` file. No LLM subscription. Just Python 3.9+.

---

## Usage

### Quick demo (insulin pump denial case)

```bash
python main.py --demo
```

### Demo with verbose agent reasoning

```bash
python main.py --demo -v
```

Expected output:
```
  [STEP 1 — CLASSIFY] Analyzing denial code and reason text…
  [STEP 1 — CLASSIFY] Type: medical_necessity | Category: Clinical | Matched by: code
  [STEP 2 — PROFILE]  Building structured clinical context…
  [STEP 2 — PROFILE]  Condition: Type 1 Diabetes… | Urgency: URGENT | Age: adult
  [STEP 3 — RESEARCH] Looking up applicable medical necessity criteria…
  ...
  [STEP 7 — FINALIZE] Probability: 82% | Confidence: HIGH | Risk: FAVORABLE
```

### Save the appeal letter to a file

```bash
python main.py --demo --output appeal_letter.txt
```

### Use a different built-in demo

```bash
python main.py --demo --demo-case knee-replacement -v
```

### Run with your own case

Create `mycase.json`:

```json
{
  "patient_id": "PT-20261116-001",
  "patient_age": 52,
  "patient_sex": "Female",
  "primary_diagnosis": "Type 1 Diabetes Mellitus with hypoglycemia unawareness",
  "diagnosis_code": "E10.641",
  "procedure_requested": "Continuous Subcutaneous Insulin Infusion (CSII) — Insulin Pump",
  "procedure_code": "E0784",
  "denial_code": "CO-50",
  "denial_reason": "Not medically necessary",
  "denial_date": "2026-10-01",
  "insurance_plan": "Commercial Healthcare Plan PPO",
  "treating_physician": "Specialist, Endocrinology",
  "clinical_notes": "Patient has T1DM for 25 years, on MDI with HbA1c 8.9%, documented hypoglycemia unawareness, 3 ED visits for severe hypoglycemia in past 6 months.",
  "prior_treatments": ["Multiple Daily Injections (MDI)", "Various insulin formulations", "CGM active", "Diabetes education completed"],
  "labs": {
    "HbA1c": "8.9%",
    "hypoglycemia_episodes_6mo": 12,
    "severe_hypoglycemia_ed_visits": 3
  }
}
```

Then:
```bash
python main.py --case mycase.json -v --output letter.txt
```

---

## Example Output

```
APPEAL OF CLAIM DENIAL
============================================================
Date:              November 16, 2026
Patient ID:        PT-20261116-001
Patient:           52-year-old Female
Diagnosis:         Type 1 Diabetes Mellitus... (E10.641)
Requested Service: CSII — Insulin Pump (E0784)
Denial Code:       CO-50
...

RE: FORMAL FIRST-LEVEL APPEAL — Insulin Pump Therapy
...

CLINICAL SUMMARY
⚠ URGENT CLINICAL SITUATION — 3 ED visits for severe hypoglycemia

MEDICAL NECESSITY ARGUMENT
✓ Type 1 diabetes mellitus diagnosis confirmed
✓ Patient on multiple daily injections (MDI) prior to pump therapy
✓ HbA1c greater than 7.0% — HbA1c: 8.9%
✓ Hypoglycemia unawareness — 12 episodes, 3 ED visits documented
...

📊 Appeal Assessment
   Success Probability: 82%
   Risk Level:          FAVORABLE
   Filing Deadline:     2027-01-29
```

---

## Supported Denial Codes

| Code   | Type              | Base Success Rate |
|--------|-------------------|-------------------|
| CO-50  | Medical Necessity | 55% → up to 82%+  |
| CO-57  | Medical Necessity | 55%               |
| CO-197 | Prior Auth        | 65%               |
| OA-23  | Experimental      | 30%               |
| CO-96  | Not Covered       | 25%               |
| CO-11  | Coding Error      | 75%               |
| CO-4   | Coding Error      | 75%               |
| *Any*  | Keyword Fallback  | Classified + rated |

---

## Supported Procedures (Deep Criteria)

| Code  | Procedure                              |
|-------|----------------------------------------|
| E0784 | External Insulin Pump (CSII)           |
| 27447 | Total Knee Arthroplasty                |
| 63650 | Spinal Cord Stimulator                 |
| 43239 | Upper GI Endoscopy with Biopsy         |
| *Any* | Generic medical necessity framework    |

> Adding new procedures is a 10-line JSON addition to `evidence_researcher.py`.

---

## Running Tests

```bash
python -m pytest test_main.py -v
```

Expected:
```
test_main.py::TestDenialAnalyzer::test_known_code_co50_classified_as_medical_necessity PASSED
test_main.py::TestDenialAnalyzer::test_keyword_fallback_medical_necessity PASSED
...
test_main.py::TestFullAgentPipeline::test_pipeline_completes_all_7_steps PASSED
test_main.py::TestFullAgentPipeline::test_pipeline_handles_minimal_case PASSED

33 passed in 0.3s ✅
```

---

## Project Structure

```
prior-auth-appeal-agent/
├── main.py                 # CLI entry point, demo cases
├── agent.py                # 7-step pipeline orchestrator
├── denial_analyzer.py      # Step 1: denial code classification
├── evidence_researcher.py  # Steps 3 & 4: criteria lookup + evidence extraction
├── appeal_writer.py        # Step 6: letter generation
├── success_predictor.py    # Step 7: appeal success probability
├── test_main.py            # 33-test suite (all stdlib)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Why This Matters

Hospitals lose approximately **$262 billion** annually to underpaid and unrecovered denied claims. A fully autonomous appeal agent could recover a significant fraction of that — not by being cleverer than a physician, but by being faster, more consistent, and always aware of the right criteria to cite.

The same agentic pattern (classify → research → evidence → draft → assess) applies to:
- **Step therapy exceptions** — when a patient can't take the first-line drug
- **Out-of-network emergency appeals** — citing surprise billing protections
- **Experimental treatment appeals** — citing compassionate use criteria
- **Peer-to-peer review preparation** — the agent as a physician's prep coach

This repo is a working foundation for all of the above.

---

## Contributing

1. Fork this repo
2. Add a new procedure to `evidence_researcher.py` (follow the existing pattern)
3. Add corresponding tests in `test_main.py`
4. Open a PR with a real use case or clinical scenario

Areas where contributions are especially welcome:
- More procedure codes with deep criteria (oncology, cardiology, rare disease)
- Integration with FHIR / HL7 patient data formats
- Automated deadline tracking and calendar reminders
- Integration with the free NLM PubMed API for real-time evidence retrieval

---

## License

MIT License — free to use, fork, and build upon.

---

## Disclaimer

This tool generates appeal letters for physician review. All output must be reviewed, verified, and co-signed by the treating physician before submission. This software does not constitute legal or medical advice. Clinical determinations remain the responsibility of the licensed clinician.

---

*Built with Python and zero paid APIs. Designed to be forked, extended, and deployed.*
