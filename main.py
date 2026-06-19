#!/usr/bin/env python3
"""
Legacy EMR to FHIR + AI Clinical Summary
===========================================
Pipeline: Legacy HIS data → FHIR R4 Bundle → De-identification → AI Summary

Usage:
    python main.py
    ANTHROPIC_API_KEY=sk-ant-... python main.py

⚠️ All patient data in this demo is synthetic. No real PHI is used or stored.
"""

import os
import json

from legacy_data.mock_his import generate_patient_bundle
from fhir.mapper import build_fhir_bundle
from security.deidentify import deidentify_bundle, get_audit_log
from ai.summary import run_summary, save_report

BANNER = """
╔════════════════════════════════════════════════════════╗
║   Legacy EMR → FHIR → AI Clinical Summary  v1.0       ║
║   Legacy Data │ FHIR R4 │ PHI De-identification │ AI  ║
╚════════════════════════════════════════════════════════╝

⚠️  All data in this demo is SYNTHETIC. No real patient data is used.
"""

def main():
    print(BANNER)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # 1. Legacy data ingestion
    print("[1/5] Generating mock legacy HIS record (synthetic patient)...")
    patient_bundle = generate_patient_bundle(patient_id="PT-00123")
    print(f"      Patient {patient_bundle['patient_id']}: "
          f"{len(patient_bundle['labs'])} lab results + 1 radiology report")

    # 2. FHIR mapping
    print("[2/5] Mapping legacy data to FHIR R4 resources...")
    fhir_bundle = build_fhir_bundle(patient_bundle)
    resource_types = [e["resource"]["resourceType"] for e in fhir_bundle["entry"]]
    print(f"      Built FHIR Bundle: {len(fhir_bundle['entry'])} resources "
          f"({resource_types.count('Observation')} Observation, "
          f"{resource_types.count('DiagnosticReport')} DiagnosticReport, "
          f"{resource_types.count('Patient')} Patient)")

    # Save raw FHIR bundle for inspection
    os.makedirs("output", exist_ok=True)
    with open("output/fhir_bundle_raw.json", "w") as f:
        json.dump(fhir_bundle, f, indent=2, default=str)
    print("      Saved → output/fhir_bundle_raw.json")

    # 3. De-identification
    print("[3/5] De-identifying PHI before AI processing...")
    deidentified_bundle = deidentify_bundle(fhir_bundle, requester="demo_user")
    audit = get_audit_log()[-1]
    print(f"      MRN pseudonymised, birth date generalised to year, "
          f"{len(audit['residual_phi_flags'])} residual PHI patterns scanned in free text")

    with open("output/fhir_bundle_deidentified.json", "w") as f:
        json.dump(deidentified_bundle, f, indent=2, default=str)
    print("      Saved → output/fhir_bundle_deidentified.json")

    # 4. AI summary
    print("[4/5] Generating AI clinical summary...")
    if not api_key:
        print("      ⚠️  No ANTHROPIC_API_KEY set — using rule-based demo summary.")
    report = run_summary(deidentified_bundle, api_key)

    # 5. Save
    print("[5/5] Saving report...")
    path = save_report(report, output_dir="output")
    print(f"      ✅ Report saved → {path}")

    print("\n" + "=" * 64)
    print(report)
    print("=" * 64)

if __name__ == "__main__":
    main()
