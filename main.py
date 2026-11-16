#!/usr/bin/env python3
"""
Prior Auth Appeal Agent — CLI Entry Point
=========================================
An autonomous 7-step AI agent that analyzes insurance claim denials
and generates evidence-based prior-authorization appeal letters.

Usage:
  python main.py --demo                       # Run with built-in demo case
  python main.py --case mycase.json -v        # Run with your own case (verbose)
  python main.py --demo --output letter.txt   # Save letter to file
  python main.py --list-cases                 # Show all built-in demo cases
"""
import argparse
import json
import sys
from agent import PriorAuthAppealAgent

# ── Built-in demo cases ────────────────────────────────────────────────────

DEMO_CASES = {
    "insulin-pump": {
        "patient_id":           "PT-20261116-001",
        "patient_age":          52,
        "patient_sex":          "Female",
        "primary_diagnosis":    "Type 1 Diabetes Mellitus with hypoglycemia unawareness",
        "diagnosis_code":       "E10.641",
        "procedure_requested":  "Continuous Subcutaneous Insulin Infusion (CSII) — Insulin Pump",
        "procedure_code":       "E0784",
        "denial_code":          "CO-50",
        "denial_reason":        (
            "Not medically necessary. Insulin pump therapy not covered when oral medications "
            "or multiple daily injections have not been tried."
        ),
        "denial_date":          "2026-10-01",
        "insurance_plan":       "Commercial Healthcare Plan — PPO",
        "treating_physician":   "Specialist, Endocrinology & Metabolism",
        "clinical_notes": (
            "Patient has Type 1 diabetes mellitus for 25 years. Currently on MDI (4+ "
            "injections per day) with poorly controlled HbA1c of 8.9%. Patient has "
            "documented hypoglycemia unawareness — 3 ED visits in the past 6 months for "
            "severe hypoglycemia. CGM data shows significant glycemic variability. "
            "Comprehensive diabetes education completed. Endocrinologist recommends CSII "
            "for improved glycemic control and hypoglycemia risk reduction."
        ),
        "prior_treatments": [
            "Multiple Daily Injections (MDI) — 25 years",
            "Various basal-bolus insulin regimens trialed",
            "Continuous Glucose Monitor (CGM) active",
            "Comprehensive diabetes self-management education completed",
        ],
        "labs": {
            "HbA1c":                        "8.9%",
            "hypoglycemia_episodes_6mo":    12,
            "severe_hypoglycemia_ed_visits": 3,
        },
    },

    "knee-replacement": {
        "patient_id":          "PT-20261116-002",
        "patient_age":         67,
        "patient_sex":         "Male",
        "primary_diagnosis":   "Severe osteoarthritis of the right knee",
        "diagnosis_code":      "M17.11",
        "procedure_requested": "Total Knee Arthroplasty (TKA)",
        "procedure_code":      "27447",
        "denial_code":         "CO-50",
        "denial_reason":       "Not medically necessary. Conservative treatment not exhausted.",
        "denial_date":         "2026-10-15",
        "insurance_plan":      "Commercial Healthcare Plan — HMO",
        "treating_physician":  "Specialist, Orthopedic Surgery",
        "clinical_notes": (
            "67-year-old male with 5-year history of severe right knee OA. Weight-bearing "
            "X-rays show Kellgren-Lawrence grade IV changes with bone-on-bone contact. "
            "Patient has failed 6 months of physical therapy, 12 months of NSAIDs (with "
            "GI intolerance), and 3 intra-articular corticosteroid injections. KOOS pain "
            "score 22/100. Patient unable to ambulate > 1 block without severe pain."
        ),
        "prior_treatments": [
            "Physical therapy — 6 months (2x per week)",
            "NSAIDs — 12 months (discontinued due to GI intolerance)",
            "Intra-articular corticosteroid injections x 3",
            "Weight management program completed",
        ],
        "labs": {},
    },
}


def print_banner():
    print("\n" + "="*60)
    print("  Prior Auth Appeal Agent  v1.0")
    print("  Autonomous 7-step insurance denial appeal generator")
    print("="*60 + "\n")


def run_case(case: dict, verbose: bool, output_path, label: str):
    print(f"Case: {label}\n")
    agent = PriorAuthAppealAgent(verbose=verbose)

    if verbose:
        print("Agent pipeline starting…\n")

    result = agent.run(case)

    # ── Print letter ───────────────────────────────────────────────────────
    print("\n" + "-"*60)
    print(result["appeal_letter"])
    print("-"*60)

    # ── Print assessment summary ───────────────────────────────────────────
    print("\nAppeal Assessment")
    print(f"   Denial Type:         {result['denial_type']}")
    print(f"   Appeal Strategy:     {result['strategy']}")
    print(f"   Success Probability: {result['success_probability']}%")
    print(f"   Confidence:          {result['confidence']}")
    print(f"   Risk Level:          {result['risk']}")
    print(f"   Filing Deadline:     {result['deadline']}")
    print(f"   Pipeline Steps:      {result['steps_completed']}/7 completed")

    if result["assessment_detail"].get("factors"):
        print("\n   Probability Factors:")
        for f in result["assessment_detail"]["factors"]:
            print(f"     {f}")

    rec = result["assessment_detail"].get("recommendation", "")
    if rec:
        print(f"\nRecommendation: {rec}")

    # ── Save to file ───────────────────────────────────────────────────────
    if output_path:
        with open(output_path, "w") as fh:
            fh.write(result["appeal_letter"])
        print(f"\nAppeal letter saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Prior Auth Appeal Agent — autonomous AI insurance appeal generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--demo",        action="store_true", help="Run with the built-in insulin pump demo case")
    parser.add_argument("--demo-case",   default="insulin-pump",
                        choices=list(DEMO_CASES.keys()),
                        help="Choose which built-in demo case to use (default: insulin-pump)")
    parser.add_argument("--case",        type=str,            help="Path to a JSON file containing the denial case")
    parser.add_argument("--output",      type=str,            help="Save the appeal letter to this file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show agent reasoning steps")
    parser.add_argument("--list-cases",  action="store_true", help="List all built-in demo cases")
    args = parser.parse_args()

    print_banner()

    if args.list_cases:
        print("Built-in demo cases:")
        for k, v in DEMO_CASES.items():
            print(f"  --demo-case {k:<20}  {v['primary_diagnosis']}")
        sys.exit(0)

    if args.case:
        with open(args.case) as fh:
            case = json.load(fh)
        label = f"Custom case — {case.get('procedure_requested', 'N/A')}"
    elif args.demo:
        case  = DEMO_CASES[args.demo_case]
        label = f"Demo: {args.demo_case}"
    else:
        print("Run with --demo for a demo, or --case <file.json> for your own case.")
        print("Use --help for all options.\n")
        sys.exit(0)

    run_case(case=case, verbose=args.verbose, output_path=args.output, label=label)


if __name__ == "__main__":
    main()
