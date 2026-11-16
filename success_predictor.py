"""
Success Predictor — Estimates prior-auth appeal success probability.
Step 7 of the Prior Auth Appeal Agent pipeline.

Probability estimates derived from published healthcare appeals outcome
research (AMA, KFF, HFMA) — no AI computation; pure rule-based scoring.
"""

# Base success rates by denial type (sources: KFF 2023 appeals study,
# HFMA revenue cycle benchmarks, AMA advocacy reports)
BASE_RATES = {
    "medical_necessity": 55,
    "experimental":      30,
    "not_covered":       25,
    "prior_auth":        65,
    "coding_error":      75,
    "duplicate":         70,
    "timely_filing":     20,
    "out_of_network":    40,
    "deductible":        10,
    "coverage_lapse":    45,
    "default":           45,
}


class SuccessPredictor:

    def predict(self, denial_info: dict, evidence: dict, strategy: dict, case: dict) -> dict:
        """
        Estimate appeal success probability and return a structured assessment.
        """
        denial_type = denial_info.get("type", "default")
        base = BASE_RATES.get(denial_type, 45)

        factors    = []
        adjustment = 0

        # ── Evidence strength ────────────────────────────────────────────────
        strength = evidence.get("strength", "MODERATE")
        if "STRONG" in strength:
            adjustment += 15
            factors.append("+15% — Strong evidence tier (>= 80% criteria documented)")
        elif "MODERATE" in strength:
            adjustment += 5
            factors.append("+5% — Moderate evidence tier (55-79% criteria documented)")
        else:
            adjustment -= 10
            factors.append("-10% — Weak evidence (< 55% criteria documented; gather more records)")

        # ── Criteria met ratio ───────────────────────────────────────────────
        met_ratio = evidence.get("met_ratio", 0.5)
        if met_ratio >= 0.80:
            adjustment += 10
            factors.append(f"+10% — {int(met_ratio*100)}% of medical necessity criteria met")
        elif met_ratio < 0.40:
            adjustment -= 15
            factors.append(f"-15% — Only {int(met_ratio*100)}% of criteria explicitly documented")

        # ── Objective lab / clinical data ────────────────────────────────────
        if evidence.get("labs"):
            adjustment += 5
            factors.append("+5% — Objective lab/clinical data present")

        # ── Step therapy / prior treatments ──────────────────────────────────
        tx_count = len(evidence.get("prior_treatments", []))
        if tx_count >= 3:
            adjustment += 10
            factors.append(f"+10% — Robust step therapy: {tx_count} prior treatments documented")
        elif tx_count >= 1:
            adjustment += 5
            factors.append(f"+5% — Step therapy documented ({tx_count} prior treatment(s))")

        # ── Expedited / urgent case ──────────────────────────────────────────
        if strategy.get("expedited"):
            adjustment += 7
            factors.append("+7% — Expedited review flag for documented clinical urgency")

        # ── Specialist ordering physician ─────────────────────────────────────
        physician = case.get("treating_physician", "").lower()
        specialist_terms = ["endocrinol", "cardiolog", "oncolog", "neurologo", "rheumatol",
                            "gastroenterol", "pulmonol", "nephrolog", "dermatol"]
        if any(sp in physician for sp in specialist_terms):
            adjustment += 5
            factors.append("+5% — Specialist ordering physician (adds clinical authority)")

        # ── Final clamped probability ─────────────────────────────────────────
        probability = max(5, min(95, base + adjustment))
        confidence  = "HIGH" if met_ratio >= 0.70 else "MEDIUM" if met_ratio >= 0.40 else "LOW"
        risk        = (
            "FAVORABLE"      if probability >= 65 else
            "MODERATE RISK"  if probability >= 40 else
            "CHALLENGING"
        )

        return {
            "probability":   probability,
            "base_rate":     base,
            "adjustment":    adjustment,
            "confidence":    confidence,
            "risk":          risk,
            "factors":       factors,
            "recommendation": self._recommendation(probability, evidence),
        }

    # ── Private ─────────────────────────────────────────────────────────────

    def _recommendation(self, probability: int, evidence: dict) -> str:
        gaps = evidence.get("gaps", [])

        if probability >= 70:
            return (
                "Strong case — submit appeal promptly with all supporting "
                "documentation. Consider peer-to-peer call if payer offers one."
            )
        elif probability >= 50:
            recs = ["Address outstanding documentation gaps before submission"]
            if gaps:
                recs.append(
                    "Key gaps: " + "; ".join(g.replace("⚠  Documentation recommended: ", "") for g in gaps[:2])
                )
            return ". ".join(recs) + "."
        else:
            return (
                "Consider scheduling a peer-to-peer review call and obtaining "
                "additional specialist attestation before filing formal appeal. "
                "Clinical documentation gaps significantly reduce success probability."
            )
