# Legacy EMR → FHIR → AI Clinical Summary

> Converts legacy hospital system data (lab results + radiology reports) into standard FHIR R4 resources, de-identifies PHI, and generates a bilingual AI clinical summary with risk flags.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![FHIR](https://img.shields.io/badge/FHIR-R4-red) ![Claude API](https://img.shields.io/badge/Claude-API-orange) ![PHI](https://img.shields.io/badge/PHI-De--identified-green)

⚠️ **All patient data in this project is synthetic.** No real PHI is generated, used, or stored at any point.

---

## The Problem

Most hospital systems still run on legacy HIS/EMR platforms that store lab results and 
radiology reports in proprietary, inconsistent formats. Getting that data into a modern 
AI tool means three unresolved problems:

1. **No standard format** — legacy lab codes (`WBC`, `GLU`, `CREAT`) aren't portable across systems
2. **PHI exposure risk** — sending raw patient data to any external API is a compliance risk
3. **No clinical readability** — raw structured data isn't useful to a clinician without interpretation

This project solves all three in one pipeline.

---

## Architecture

```
[Legacy HIS Data]
   ├─ Structured: Lab Panel (CBC, Liver, Renal — legacy field codes)
   └─ Semi-structured: Radiology Report (free-text dictation)
        ↓
[FHIR R4 Mapper]
   ├─ Lab results  → Observation resources (mapped to LOINC codes)
   ├─ Radiology     → DiagnosticReport resource
   └─ Demographics  → Patient resource
        ↓  (FHIR Bundle)
[PHI De-identification Layer]
   ├─ MRN pseudonymised (SHA-256, deterministic)
   ├─ Birth date generalised to year only (HIPAA Safe Harbor pattern)
   └─ Free-text scanned for residual PHI (phone, DOB, SSN patterns)
        ↓  (de-identified FHIR Bundle)
[Claude AI]
   ├─ Bilingual clinical summary (English + Traditional Chinese)
   ├─ Lab risk-flag table (🔴 High Risk / 🟡 Monitor / 🟢 Normal)
   └─ Suggested follow-up (phrased as suggestions, never directives)
        ↓
   📄 clinical_summary.md
```

---

## Why FHIR Matters Here

FHIR (Fast Healthcare Interoperability Resources) is the HL7 industry standard most 
modern health IT, EHR vendors (Epic, Cerner/Oracle Health), and health AI tools require. 
Legacy systems almost never speak FHIR natively — this mapper is the bridge.

Lab codes are mapped to **LOINC**, the universal lab test coding standard, so the 
output Bundle is portable to any FHIR-compliant system, not just this pipeline.

---

## Security Design

| Risk | Mitigation |
|---|---|
| Direct identifiers (name, DOB) sent to AI | Removed/generalised before any AI call |
| MRN re-identification | Pseudonymised with deterministic SHA-256 hashing |
| PHI hidden in free-text radiology dictation | Regex scan for phone/DOB/SSN/MRN patterns, auto-redacted |
| No audit trail | Every de-identification action logged with timestamp |

This follows the general pattern of **HIPAA Safe Harbor de-identification** — a real 
production deployment would require formal compliance review, but the architecture 
demonstrates the correct approach.

---

## Quick Start

```bash
git clone https://github.com/BunnyShih/fhir-ai-clinical-summary
cd fhir-ai-clinical-summary

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Demo mode (rule-based summary, no API key needed)
python main.py

# Live mode with Claude AI
export ANTHROPIC_API_KEY=sk-ant-...
python main.py
```

---

## Sample Output

```
[1/5] Generating mock legacy HIS record (synthetic patient)...
      Patient PT-00123: 12 lab results + 1 radiology report
[2/5] Mapping legacy data to FHIR R4 resources...
      Built FHIR Bundle: 14 resources (12 Observation, 1 DiagnosticReport, 1 Patient)
[3/5] De-identifying PHI before AI processing...
      MRN pseudonymised, birth date generalised to year
[4/5] Generating AI clinical summary...
[5/5] Saving report...
      ✅ Report saved → output/clinical_summary_20260619.md
```

**Generated report includes:**

| Test | Value | Reference Range | Flag |
|---|---|---|---|
| RBC | 2.13 10^6/uL | 4.2–5.9 10^6/uL | 🔴 Low |
| PLT | 633.3 10^3/uL | 150–400 10^3/uL | 🔴 High |
| WBC | 5.41 10^3/uL | 4.0–11.0 10^3/uL | 🟢 Normal |

Plus a bilingual summary, radiology findings in plain language, and clinician follow-up suggestions.

---

## Project Structure

```
fhir-ai-clinical-summary/
├── legacy_data/
│   └── mock_his.py        # Synthetic lab panel + radiology report generator
├── fhir/
│   └── mapper.py           # Legacy data → FHIR R4 (Patient, Observation, DiagnosticReport)
├── security/
│   └── deidentify.py       # PHI removal, pseudonymisation, audit logging
├── ai/
│   └── summary.py          # Claude API integration, bilingual report generation
├── output/                 # Generated FHIR bundles + reports (gitignored)
└── main.py
```

---

## Skills Demonstrated

| Skill | Implementation |
|---|---|
| **Legacy Data to AI** | Legacy HIS lab codes + free-text reports → FHIR R4 → AI |
| **Healthcare Data Standards** | FHIR R4 resources, LOINC code mapping |
| **AI Security & PHI Protection** | De-identification, pseudonymisation, audit trail |
| **Clinical Domain Knowledge** | Realistic lab panels, radiology report structure, risk flagging |

---

## Extending This Project

- **Real FHIR server integration**: point at a HAPI FHIR server instead of building Bundles locally
- **HL7 v2 ingestion**: add a parser for real HL7 v2 ADT/ORU messages as the legacy input
- **More resource types**: extend to `MedicationRequest`, `Condition`, `Encounter`
- **Full HIPAA Safe Harbor**: extend de-identification to cover all 18 identifier categories

---

## Disclaimer

This is a portfolio/demonstration project using entirely synthetic data. It is not a 
certified medical device, does not provide medical advice, and is not intended for use 
with real patient data without a full compliance and security review.

## License

MIT
