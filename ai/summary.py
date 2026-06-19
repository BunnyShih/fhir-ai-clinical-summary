"""
AI Clinical Summary Generator
================================
Sends a de-identified FHIR Bundle to Claude AI and generates:
  1. A clinician-facing summary (bilingual)
  2. A traffic-light risk flag table for abnormal lab values
"""

import os
import json
import requests
from datetime import datetime

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = """You are a clinical decision support assistant reviewing de-identified 
FHIR data for a physician. You are NOT diagnosing — you are summarising and flagging 
patterns for a clinician's review.

You will receive a FHIR Bundle containing Observation resources (lab results, already 
flagged High/Low/Normal) and a DiagnosticReport (radiology conclusion).

Produce a bilingual report (English + Traditional Chinese) in Markdown with this exact structure:

# Clinical Summary

## Summary (English)
2-4 sentences. Mention any abnormal labs and the radiology impression. Neutral, clinical tone.

## 病人摘要（繁體中文）
Same summary in Traditional Chinese.

## Lab Results — Risk Flags
A markdown table: Test | Value | Reference Range | Flag (🔴 High Risk / 🟡 Monitor / 🟢 Normal)
Use 🔴 for clinically significant abnormal values, 🟡 for borderline/mild abnormalities, 🟢 for normal.

## Radiology Findings
1-2 sentence plain-language summary of the radiology conclusion.

## Suggested Follow-up (for clinician review)
2-3 bullet points. Always phrase as suggestions for clinician consideration, never as 
directives or diagnoses. Include a disclaimer that this is AI-assisted summarisation only.

Do not invent any values not present in the input data."""

def build_prompt(fhir_bundle: dict) -> str:
    return f"""Review this de-identified FHIR Bundle and generate the clinical summary report.

FHIR Bundle:
{json.dumps(fhir_bundle, indent=2, default=str)}

Generate the bilingual clinical summary now."""

def run_summary(fhir_bundle: dict, api_key: str) -> str:
    if not api_key:
        return _demo_summary(fhir_bundle)

    prompt = build_prompt(fhir_bundle)
    resp = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 2000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]

def _demo_summary(fhir_bundle: dict) -> str:
    """Rule-based demo report when no API key is set."""
    observations = [e["resource"] for e in fhir_bundle["entry"] if e["resource"]["resourceType"] == "Observation"]
    diag_reports = [e["resource"] for e in fhir_bundle["entry"] if e["resource"]["resourceType"] == "DiagnosticReport"]

    rows = []
    abnormal_count = 0
    for obs in observations:
        code_text = obs["code"]["text"]
        value = obs["valueQuantity"]["value"]
        unit = obs["valueQuantity"]["unit"]
        ref = obs["referenceRange"][0]
        low, high = ref["low"]["value"], ref["high"]["value"]
        interp = obs["interpretation"][0]["coding"][0]["code"]

        if interp == "H":
            flag = "🔴 High" if value > high * 1.3 else "🟡 Monitor"
            abnormal_count += 1
        elif interp == "L":
            flag = "🔴 Low" if value < low * 0.7 else "🟡 Monitor"
            abnormal_count += 1
        else:
            flag = "🟢 Normal"

        rows.append(f"| {code_text} | {value} {unit} | {low}-{high} {unit} | {flag} |")

    radiology_text = diag_reports[0]["conclusion"] if diag_reports else "N/A"
    impression = radiology_text.split("IMPRESSION:")[-1].strip()[:200] if "IMPRESSION:" in radiology_text else radiology_text[:200]

    return f"""# Clinical Summary
*(Demo mode — set ANTHROPIC_API_KEY for live AI-generated summary)*

## Summary (English)
This de-identified record shows {abnormal_count} lab value(s) outside the reference range 
out of {len(observations)} total tests. Radiology impression: {impression}
This is an AI-assisted summary for clinician review only — not a diagnosis.

## 病人摘要（繁體中文）
此去識別化病歷中，共 {len(observations)} 項檢驗中有 {abnormal_count} 項數值超出參考範圍。
影像學結論：{impression}
本摘要為 AI 輔助生成，僅供醫師參考，非診斷依據。

## Lab Results — Risk Flags
| Test | Value | Reference Range | Flag |
|---|---|---|---|
{chr(10).join(rows)}

## Radiology Findings
{impression}

## Suggested Follow-up (for clinician review)
- Review flagged lab values in context of patient's clinical presentation
- Consider repeat testing for any 🔴 High Risk values if clinically indicated
- Correlate radiology findings with current symptoms

*This report is AI-assisted summarisation only and does not constitute a medical diagnosis. 
All findings require clinician review and confirmation.*
"""

def save_report(report: str, output_dir: str = "output") -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"clinical_summary_{ts}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    return path
