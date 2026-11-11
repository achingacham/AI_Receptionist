"""Safety Perimeter and Medical Circuit Breaker.

Provides deterministic enforcement against clinical liability, symptom diagnosis,
and medical emergencies.
"""

import re

# Deterministic emergency triggers requiring immediate hospital/112 referral
_ACUTE_EMERGENCY_PATTERNS = [
    r"\b(sudden(ly)?\s+(lost|loss\s+of)?\s*(my\s+)?hearing)\b",
    r"\b(woke\s+up\s+(deaf|unable\s+to\s+hear))\b",
    r"\b(blood|bleeding)\s+(from|in)\s+(my\s+|the\s+)?ear\b",
    r"\b(object|insect|bug|bead|cotton\s*swab|foreign\s+(body|object)?)\b.*?\b(stuck|lodged|inside|trapped)\b.*?\bear\b",
    r"\b(eardrum\s+(rupture[d]?|burst|tear|perforat(ed|ion)))\b",
    r"\b(severe|excruciating|unbearable)\s+(ear\s*)?pain\s+with\s+(fever|discharge)\b",
    r"\b(sudden(ly)?\s+(slurr(ed|ing)|unable\s+to\s+speak|facial\s+droop|paralysis))\b",
    r"\b(choking|can'?t\s+breathe|swallowed\s+a\s+(battery|object))\b",
    r"\b(stroke|heart\s+attack|unconscious|fainted|seizure)\b",
]

_ACUTE_EMERGENCY_REGEX = re.compile("|".join(_ACUTE_EMERGENCY_PATTERNS), re.IGNORECASE)

# Inquiries seeking clinical prescription, drug dosages, or home diagnosis
_CLINICAL_ADVICE_PATTERNS = [
    r"\b(what|which)\s+(medicine|drug|pill|drops|antibiotic|ointment)\s+(should|can)\s+i\s+(take|use|put)\b",
    r"\b(cure|heal|treat)\s+(my\s+)?(tinnitus|hearing\s+loss|vertigo|ear\s+infection)\s+at\s+home\b",
    r"\b(diagnose|do\s+i\s+have)\s+(an?\s+)?(infection|tumor|cholesteatoma|meniere'?s)\b",
]

_CLINICAL_ADVICE_REGEX = re.compile("|".join(_CLINICAL_ADVICE_PATTERNS), re.IGNORECASE)

EMERGENCY_CIRCUIT_BREAKER_RESPONSE = (
    "EMERGENCY PROTOCOL: This inquiry describes an acute medical condition or emergency "
    "requiring immediate professional attention. Please contact emergency services (112 in India, "
    "or 911/local emergency) or visit the nearest hospital emergency room immediately. "
    "As an automated administrative receptionist, I cannot provide clinical triage or emergency guidance."
)

CLINICAL_ADVICE_DISCLAIMER_RESPONSE = (
    "CLINICAL BOUNDARY: As an automated receptionist, I cannot prescribe medications, "
    "diagnose medical conditions, or recommend treatments. We invite you to schedule a consultation "
    "with our certified audiologist or ENT specialist for an in-person clinical assessment."
)


def check_safety_circuit_breaker(text: str) -> str | None:
    """Evaluate text against Safety Perimeter rules.

    Returns an authoritative override message if a Circuit Breaker is tripped,
    or None if the inquiry is safe to process generatively.
    """
    if not text or not text.strip():
        return None

    cleaned = text.strip()

    # Priority 1: Acute Medical Emergency Circuit Breaker
    if _ACUTE_EMERGENCY_REGEX.search(cleaned):
        return EMERGENCY_CIRCUIT_BREAKER_RESPONSE

    # Priority 2: Medical Advice / Prescription Boundary
    if _CLINICAL_ADVICE_REGEX.search(cleaned):
        return CLINICAL_ADVICE_DISCLAIMER_RESPONSE

    return None
