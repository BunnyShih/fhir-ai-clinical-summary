"""
FHIR R4 Mapper
===============
Converts legacy HIS lab/radiology data into standard FHIR R4 resources:
  - Observation  (lab results)
  - DiagnosticReport (radiology report)
  - Patient (demographics)
  - Bundle (wraps everything together)

This is the core "Legacy Data to AI" bridge: legacy systems speak in 
proprietary codes, FHIR is the industry-standard interchange format that
AI tooling and modern health IT systems can actually consume.

Reference: HL7 FHIR R4 — https://hl7.org/fhir/R4/
"""

from datetime import datetime
import uuid

# Maps legacy lab codes to LOINC codes (the real-world standard)
# In production this mapping table would be much larger and maintained centrally.
LOINC_MAP = {
    "WBC":      {"code": "6690-2",  "display": "Leukocytes [#/volume] in Blood"},
    "RBC":      {"code": "789-8",   "display": "Erythrocytes [#/volume] in Blood"},
    "HGB":      {"code": "718-7",   "display": "Hemoglobin [Mass/volume] in Blood"},
    "HCT":      {"code": "4544-3",  "display": "Hematocrit [Volume Fraction] of Blood"},
    "PLT":      {"code": "777-3",   "display": "Platelets [#/volume] in Blood"},
    "GLU":      {"code": "1558-6",  "display": "Fasting glucose [Mass/volume] in Serum or Plasma"},
    "BUN":      {"code": "3094-0",  "display": "Urea nitrogen [Mass/volume] in Serum or Plasma"},
    "CREAT":    {"code": "2160-0",  "display": "Creatinine [Mass/volume] in Serum or Plasma"},
    "AST_SGOT": {"code": "1920-8",  "display": "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma"},
    "ALT_SGPT": {"code": "1742-6",  "display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma"},
    "NA":       {"code": "2951-2",  "display": "Sodium [Moles/volume] in Serum or Plasma"},
    "K":        {"code": "2823-3",  "display": "Potassium [Moles/volume] in Serum or Plasma"},
}

def _uid() -> str:
    return str(uuid.uuid4())

def to_fhir_patient(demographics: dict, patient_id: str) -> dict:
    """Map legacy demographics to a FHIR Patient resource."""
    return {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [{"system": "urn:legacy-his:mrn", "value": demographics["mrn"]}],
        "gender": {"M": "male", "F": "female"}.get(demographics.get("sex"), "unknown"),
        "birthDate": demographics.get("dob"),
    }

def to_fhir_observation(lab_row: dict) -> dict:
    """Map one legacy lab result row to a FHIR Observation resource."""
    code = lab_row["test_cd"]
    loinc = LOINC_MAP.get(code, {"code": "unknown", "display": code})

    value = lab_row["result_val"]
    low, high = lab_row["ref_low"], lab_row["ref_high"]
    interpretation = "N"  # Normal
    if value > high:
        interpretation = "H"  # High
    elif value < low:
        interpretation = "L"  # Low

    return {
        "resourceType": "Observation",
        "id": _uid(),
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": loinc["code"], "display": loinc["display"]}],
            "text": code,
        },
        "subject": {"reference": f"Patient/{lab_row['pat_id']}"},
        "effectiveDateTime": lab_row["collected_dt"],
        "valueQuantity": {
            "value": value,
            "unit": lab_row["unit_cd"],
        },
        "referenceRange": [{"low": {"value": low}, "high": {"value": high}}],
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": interpretation}]
        }],
    }

def to_fhir_diagnostic_report(radiology: dict) -> dict:
    """Map legacy radiology report text to a FHIR DiagnosticReport resource."""
    return {
        "resourceType": "DiagnosticReport",
        "id": _uid(),
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD"}]
        }],
        "code": {"text": f"{radiology['modality']} Report"},
        "subject": {"reference": f"Patient/{radiology['pat_id']}"},
        "effectiveDateTime": radiology["report_dt"],
        "conclusion": radiology["report_text"],
    }

def build_fhir_bundle(patient_bundle: dict) -> dict:
    """
    Convert a complete legacy patient record into a FHIR Bundle
    containing Patient, Observation (x N), and DiagnosticReport resources.
    """
    patient_resource = to_fhir_patient(patient_bundle["demographics"], patient_bundle["patient_id"])
    observations = [to_fhir_observation(row) for row in patient_bundle["labs"]]
    diagnostic_report = to_fhir_diagnostic_report(patient_bundle["radiology"])

    entries = [{"resource": patient_resource}]
    entries += [{"resource": obs} for obs in observations]
    entries.append({"resource": diagnostic_report})

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entry": entries,
    }
