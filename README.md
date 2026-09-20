# prior-auth-appeal-agent

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

**An agentic AI system that autonomously fights insurance prior authorization denials.**

## The Problem

Over **4 million** prior authorization requests are denied each year in the US. 
More than **80%** of those denials are overturned on appeal — but only **~11%** of 
denials are ever challenged, because clinicians and staff simply don't have time 
to research and write formal appeal letters.

The result: patients go without needed medications, surgeries, and devices — not 
because care is medically inappropriate, but because no one fought back.

> Sources: AMA Prior Authorization Physician Survey (2024); Ganguli et al., "Trends in Prior Authorization Denials," *JAMA Internal Medicine* (2023);
> CMS Office of Inspector General, "Medicare Advantage Prior Authorization Denials" (2023)

## How It Works (Agentic Architecture)

The agent runs an **8-step autonomous reasoning loop** for each denial case:

```
STEP 1  Parse denial letter → extract diagnosis/procedure codes
STEP 2  Classify denial reason → identify optimal rebuttal strategy
STEP 3  Build targeted literature search queries
STEP 4  Search PubMed (free NCBI API) for supporting evidence
STEP 5  Score and rank evidence by relevance to the specific case
STEP 6  Retrieve applicable clinical guidelines per diagnosis codes
STEP 7  Compute appeal strength score (confidence 0-100%)
STEP 8  Generate complete, formatted appeal letter with citations
```

No hardcoded templates -- each appeal is dynamically constructed from the 
evidence retrieved and the specific denial reason pattern detected.

## Install

```bash
git clone https://github.com/ai-summer2025/prior-auth-appeal-agent.git
cd prior-auth-appeal-agent
pip install -r requirements.txt
```

**No paid API keys required.** Uses the free [NCBI PubMed E-utilities API](https://www.ncbi.nlm.nih.gov/books/NBK25500/).

## Usage

```bash
# Run appeal for a sample rheumatoid arthritis case (step-therapy denial)
python agent.py --case CASE-001

# Run appeal for a sample lung cancer immunotherapy case (experimental denial)
python agent.py --case CASE-002

# Run appeal for a diabetes CGM case (medical necessity denial)
python agent.py --case CASE-003

# List all available cases
python agent.py --list-cases

# Save the generated appeal to a file
python agent.py --case CASE-001 --output my_appeal.txt

# Quiet mode (suppress step logging)
python agent.py --case CASE-001 --quiet
```

## Example Output

```
============================================================
  PRIOR AUTH APPEAL AGENT  |  CASE-001
============================================================

  [Agent] STEP 1: Analyzing denial for case CASE-001
  [Agent] Denial reason: Not medically necessary; patient has not completed required step therapy
  [Agent] STEP 2: Running denial pattern analysis
  [Agent] Rebuttal angle: step therapy exception
  [Agent] STEP 3: Building evidence search queries
  [Agent] STEP 4: Searching PubMed for supporting evidence
  [Agent]   Searching: "Subcutaneous Biologic Therapy TNF Inhibitor med..."
  [Agent]   Searching: "M06.09 M05.79 treatment guidelines systematic r..."
  [Agent] STEP 5: Scoring evidence relevance
  [Agent] Top evidence items: 6
  [Agent] STEP 6: Retrieving applicable clinical guidelines
  [Agent] Guidelines found: 1
  [Agent]   Guideline: American College of Rheumatology (2024)
  [Agent] STEP 7: Computing appeal strength score
  [Agent] Appeal strength: Strong (confidence: 82%)
  [Agent] STEP 8: Generating appeal letter
  [Agent] COMPLETE: Appeal package ready for case CASE-001

============================================================
  Appeal Strength:  Strong
  Confidence:       82%
  Evidence Items:   6
============================================================

PRIOR AUTHORIZATION APPEAL LETTER
Case ID: CASE-001
...
```

## Why This Matters

- **Physicians spend ~13 hours/week** on prior auth administrative tasks (AMA)
- **94% of physicians** say prior auth delays access to necessary care
- An automated appeal agent could **recover millions in denied claims** annually
- Small practices especially lack staff to write evidence-backed appeals

## Running Tests

```bash
python test_agent.py
# or
python -m pytest test_agent.py -v
```

All tests use mock data fallbacks, so they pass even without internet access.

## Project Structure

```
prior-auth-appeal-agent/
├── agent.py          # Main agentic system
├── test_agent.py     # Unit tests (20+ assertions)
├── requirements.txt  # Dependencies (mostly stdlib)
├── .gitignore
└── README.md
```

## Extending the Agent

To add a real denial case, create a `DenialCase` object:

```python
from agent import DenialCase, PriorAuthAppealAgent

case = DenialCase(
    case_id="MY-CASE-001",
    patient_age=55,
    patient_gender="Male",
    diagnosis_codes=["I25.10"],        # ICD-10 codes
    requested_procedure="Cardiac Catheterization",
    procedure_codes=["93458"],         # CPT codes
    denial_reason="Not medically necessary",
    payer_name="Acme Insurance",
    treating_physician="Dr. Jane Smith, MD",
    clinical_notes_summary="...",
)

agent = PriorAuthAppealAgent(verbose=True)
result = agent.run(case)
print(result.letter_text)
```

## Contributing

Pull requests welcome! Ideas for expansion:
- PDF parsing of actual denial letters (PyPDF2)
- Integration with free FHIR APIs for patient data
- Web interface for clinic staff
- Appeal outcome tracking database
- Support for state-specific appeal regulations

## License

MIT License — see LICENSE for details.

---
*Built to help the 88% of patients whose denials were never challenged.*
