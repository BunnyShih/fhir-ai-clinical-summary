"""
Mock Legacy HIS/EMR Data
=========================
Simulates the kind of data exported from a legacy Hospital Information System:
  1. Structured lab results (typical CSV/SQL export format, with messy field names)
  2. Semi-structured radiology report (free text, as a clinician would dictate it)

In a real deployment, this would come from an HL7 v2 feed, a HIS database export,
or a PACS/RIS report export.
"""

import random
from datetime import datetime, timedelta

# ── Structured Lab Data ────────────────────────────────────────────────────────
# Field names intentionally mimic messy legacy system exports
# (inconsistent casing, abbreviations, no units in some fields)

LAB_REFERENCE_RANGES = {
    "WBC":      {"unit": "10^3/uL", "low": 4.0,  "high": 11.0, "name": "White Blood Cell Count"},
    "RBC":      {"unit": "10^6/uL", "low": 4.2,  "high": 5.9,  "name": "Red Blood Cell Count"},
    "HGB":      {"unit": "g/dL",    "low": 13.0, "high": 17.5, "name": "Hemoglobin"},
    "HCT":      {"unit": "%",       "low": 38.0, "high": 50.0, "name": "Hematocrit"},
    "PLT":      {"unit": "10^3/uL", "low": 150,  "high": 400,  "name": "Platelet Count"},
    "GLU":      {"unit": "mg/dL",   "low": 70,   "high": 100,  "name": "Glucose (Fasting)"},
    "BUN":      {"unit": "mg/dL",   "low": 7,    "high": 20,   "name": "Blood Urea Nitrogen"},
    "CREAT":    {"unit": "mg/dL",   "low": 0.6,  "high": 1.3,  "name": "Creatinine"},
    "AST_SGOT": {"unit": "U/L",     "low": 10,   "high": 40,   "name": "AST (SGOT)"},
    "ALT_SGPT": {"unit": "U/L",     "low": 7,    "high": 56,   "name": "ALT (SGPT)"},
    "NA":       {"unit": "mmol/L",  "low": 135,  "high": 145,  "name": "Sodium"},
    "K":        {"unit": "mmol/L",  "low": 3.5,  "high": 5.1,  "name": "Potassium"},
}

def generate_lab_panel(patient_id: str, abnormal_bias: bool = True) -> list[dict]:
    """
    Generate a mock CBC + Liver/Renal panel for one patient.
    abnormal_bias=True injects a few realistic out-of-range values
    (simulating a patient who actually needs clinical attention).
    """
    rows = []
    collected_at = (datetime.now() - timedelta(hours=random.randint(2, 36))).isoformat()

    abnormal_picks = random.sample(list(LAB_REFERENCE_RANGES.keys()), k=3) if abnormal_bias else []

    for code, ref in LAB_REFERENCE_RANGES.items():
        low, high = ref["low"], ref["high"]
        if code in abnormal_picks:
            # push value outside range
            if random.random() > 0.5:
                value = round(high * random.uniform(1.15, 1.6), 2)
            else:
                value = round(low * random.uniform(0.4, 0.85), 2)
        else:
            value = round(random.uniform(low, high), 2)

        rows.append({
            "pat_id": patient_id,
            "test_cd": code,                # legacy abbreviated code
            "result_val": value,
            "unit_cd": ref["unit"],
            "ref_low": low,
            "ref_high": high,
            "collected_dt": collected_at,
            "status": "F",                  # legacy status code: F = Final
        })
    return rows

# ── Semi-Structured Radiology Report ──────────────────────────────────────────

RADIOLOGY_TEMPLATES = [
    """CHEST X-RAY, PA AND LATERAL

CLINICAL HISTORY: Shortness of breath, rule out pneumonia.

FINDINGS:
The lungs are clear bilaterally with no focal consolidation. No pleural 
effusion or pneumothorax identified. Cardiac silhouette is within normal 
limits. Mediastinal contours are unremarkable. No acute osseous abnormality.

IMPRESSION:
No acute cardiopulmonary process. No evidence of pneumonia.""",

    """CT ABDOMEN/PELVIS WITH CONTRAST

CLINICAL HISTORY: Right upper quadrant pain, elevated liver enzymes.

FINDINGS:
Liver is mildly enlarged measuring 17.5 cm in craniocaudal dimension with 
mild diffuse fatty infiltration. No focal hepatic lesion identified. 
Gallbladder is unremarkable without evidence of cholelithiasis. Pancreas, 
spleen, and kidneys appear within normal limits. No free fluid or 
lymphadenopathy.

IMPRESSION:
1. Mild hepatomegaly with diffuse fatty infiltration, correlate clinically 
   with liver function tests.
2. No biliary obstruction or cholelithiasis.""",

    """CHEST X-RAY, PA AND LATERAL

CLINICAL HISTORY: Follow-up, history of pneumonia 2 weeks ago.

FINDINGS:
Interval improvement of previously noted right lower lobe consolidation. 
Mild residual streaky opacity remains, likely representing resolving 
infectious process. No new consolidation. No pleural effusion. Heart size 
normal.

IMPRESSION:
Improving right lower lobe pneumonia. Recommend clinical correlation and 
follow-up imaging in 4-6 weeks if symptoms persist.""",
]

def generate_radiology_report(patient_id: str) -> dict:
    report_text = random.choice(RADIOLOGY_TEMPLATES)
    return {
        "pat_id": patient_id,
        "report_type": "Radiology",
        "modality": "XR" if "X-RAY" in report_text else "CT",
        "report_dt": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat(),
        "report_text": report_text,
        "status": "F",
    }

def generate_patient_bundle(patient_id: str = "PT-00123") -> dict:
    """Generate a complete mock legacy record for one patient encounter."""
    return {
        "patient_id": patient_id,
        "demographics": {
            "name": "DEMO PATIENT",     # always synthetic — never real PHI
            "mrn": patient_id,
            "dob": "1965-03-14",
            "sex": "F",
        },
        "labs": generate_lab_panel(patient_id, abnormal_bias=True),
        "radiology": generate_radiology_report(patient_id),
    }
