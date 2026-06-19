"""
PHI De-identification Layer
=============================
Removes/masks Protected Health Information (PHI) from a FHIR Bundle 
before any data is sent to an external AI API.

Follows the general approach of HIPAA Safe Harbor de-identification:
direct identifiers are removed or pseudonymised, clinical content is kept intact.

NOTE: This is a demonstration of the de-identification *pattern*. 
A real production system would need a formal HIPAA compliance review.
"""

import hashlib
import re
import copy
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

AUDIT_LOG: list[dict] = []

DIRECT_IDENTIFIER_FIELDS = {"name", "birthDate"}  # fields removed entirely from Patient
PSEUDONYMIZE_FIELDS = {"value"}  # identifier.value gets pseudonymised, not removed

def _pseudo(value: str) -> str:
    h = hashlib.sha256(str(value).encode()).hexdigest()[:10].upper()
    return f"DEID-{h}"

def deidentify_patient(patient_resource: dict) -> dict:
    """Remove direct identifiers, pseudonymise MRN, generalise birth date to year only."""
    resource = copy.deepcopy(patient_resource)

    # Pseudonymise MRN
    if "identifier" in resource:
        for ident in resource["identifier"]:
            if "value" in ident:
                ident["value"] = _pseudo(ident["value"])

    # Generalise birth date to year only (common Safe Harbor technique)
    if "birthDate" in resource:
        year = resource["birthDate"].split("-")[0]
        resource["birthDate"] = f"{year}-01-01"  # generalised

    return resource

def scan_text_for_phi(text: str) -> tuple[str, list[str]]:
    """
    Scan free-text radiology/pathology report for residual PHI patterns
    (names accidentally dictated, dates of birth, phone numbers, MRNs).
    Returns (cleaned_text, list_of_flags).
    """
    flags = []
    cleaned = text

    patterns = {
        "phone":      re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "mrn_like":   re.compile(r"\bMRN[:\s]*\d{4,}\b", re.IGNORECASE),
        "dob_like":   re.compile(r"\b(0[1-9]|1[0-2])[/-](0[1-9]|[12]\d|3[01])[/-](19|20)\d{2}\b"),
        "ssn_like":   re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    }

    for label, pattern in patterns.items():
        if pattern.search(cleaned):
            flags.append(label)
            cleaned = pattern.sub("[REDACTED]", cleaned)

    return cleaned, flags

def deidentify_bundle(fhir_bundle: dict, requester: str = "ai_pipeline") -> dict:
    """
    De-identify an entire FHIR Bundle before AI processing.
    Returns a new bundle; original is never mutated.
    """
    bundle = copy.deepcopy(fhir_bundle)
    phi_flags_total = []

    for entry in bundle.get("entry", []):
        resource = entry["resource"]
        rtype = resource.get("resourceType")

        if rtype == "Patient":
            entry["resource"] = deidentify_patient(resource)

        elif rtype == "DiagnosticReport":
            conclusion = resource.get("conclusion", "")
            cleaned, flags = scan_text_for_phi(conclusion)
            resource["conclusion"] = cleaned
            phi_flags_total.extend(flags)

        elif rtype == "Observation":
            # Observations reference Patient/{id} — pseudonymise the reference too
            if "subject" in resource and "reference" in resource["subject"]:
                ref = resource["subject"]["reference"]
                if ref.startswith("Patient/"):
                    pid = ref.split("/")[1]
                    resource["subject"]["reference"] = f"Patient/{_pseudo(pid)}"

    _audit(requester=requester, resource_count=len(bundle.get("entry", [])), phi_flags=phi_flags_total)
    return bundle

def _audit(requester: str, resource_count: int, phi_flags: list[str]):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "requester": requester,
        "resources_processed": resource_count,
        "residual_phi_flags": phi_flags,
        "action": "de-identified",
    }
    AUDIT_LOG.append(entry)
    logger.info("PHI_AUDIT | %s", entry)

def get_audit_log() -> list[dict]:
    return list(AUDIT_LOG)
