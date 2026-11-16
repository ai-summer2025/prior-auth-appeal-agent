"""
Denial Analyzer — Classifies insurance claim denial codes and reasons.
Step 1 of the Prior Auth Appeal Agent pipeline.
"""

DENIAL_CODE_MAP = {
    "CO-4":  {"type": "coding_error",       "category": "Administrative", "description": "Service/procedure inconsistent with modifier"},
    "CO-11": {"type": "coding_error",       "category": "Administrative", "description": "Diagnosis inconsistent with procedure"},
    "CO-50": {"type": "medical_necessity",  "category": "Clinical",       "description": "Not medically necessary"},
    "CO-57": {"type": "medical_necessity",  "category": "Clinical",       "description": "Payment denied — prior auth not obtained"},
    "CO-96": {"type": "not_covered",        "category": "Benefit",        "description": "Non-covered charge"},
    "CO-97": {"type": "coverage_lapse",     "category": "Administrative", "description": "Payment included in another service"},
    "CO-109":{"type": "not_covered",        "category": "Benefit",        "description": "Claim not covered by this payer"},
    "CO-167":{"type": "medical_necessity",  "category": "Clinical",       "description": "Diagnosis not covered"},
    "CO-197":{"type": "prior_auth",         "category": "Administrative", "description": "Precertification / authorization absent"},
    "OA-23": {"type": "experimental",       "category": "Clinical",       "description": "Experimental / investigational procedure"},
    "OA-125":{"type": "not_covered",        "category": "Benefit",        "description": "Benefit maximum reached"},
    "PR-1":  {"type": "deductible",         "category": "Patient Liability","description": "Deductible amount"},
    "PR-2":  {"type": "coinsurance",        "category": "Patient Liability","description": "Coinsurance amount"},
}

KEYWORD_MAP = [
    (["not medically necessary", "medical necessity"],      "medical_necessity"),
    (["experimental", "investigational", "not proven"],     "experimental"),
    (["not covered", "non-covered", "benefit exclusion"],   "not_covered"),
    (["prior auth", "precertification", "authorization"],   "prior_auth"),
    (["coding error", "incorrect code", "modifier", "inconsistent"], "coding_error"),
    (["duplicate", "already billed", "already paid"],       "duplicate"),
    (["timely filing", "filing deadline", "time limit"],    "timely_filing"),
    (["out of network", "out-of-network", "non-participating"], "out_of_network"),
]

CATEGORY_MAP = {
    "medical_necessity": "Clinical",
    "experimental":      "Clinical",
    "not_covered":       "Benefit",
    "prior_auth":        "Administrative",
    "coding_error":      "Administrative",
    "duplicate":         "Administrative",
    "timely_filing":     "Administrative",
    "out_of_network":    "Network",
    "deductible":        "Patient Liability",
    "coinsurance":       "Patient Liability",
}


class DenialAnalyzer:
    """Classifies a claim denial by code and reason text."""

    def classify(self, denial_code: str, denial_reason: str, procedure_code: str = "") -> dict:
        code = denial_code.upper().strip().replace(" ", "-")

        if code in DENIAL_CODE_MAP:
            info = dict(DENIAL_CODE_MAP[code])
            info["code"] = denial_code
            info["matched_by"] = "code"
            return info

        for mapped_code, info in DENIAL_CODE_MAP.items():
            if code in mapped_code or mapped_code in code:
                result = dict(info)
                result["code"] = denial_code
                result["matched_by"] = "partial_code"
                return result

        reason_lower = denial_reason.lower()
        for keywords, denial_type in KEYWORD_MAP:
            if any(kw in reason_lower for kw in keywords):
                return {
                    "code": denial_code,
                    "type": denial_type,
                    "category": CATEGORY_MAP.get(denial_type, "Clinical"),
                    "description": denial_reason[:120],
                    "matched_by": "keyword",
                }

        return {
            "code": denial_code,
            "type": "medical_necessity",
            "category": "Clinical",
            "description": denial_reason[:120] if denial_reason else "Unspecified denial",
            "matched_by": "default",
            "note": "Denial type inferred — verify before submission",
        }
