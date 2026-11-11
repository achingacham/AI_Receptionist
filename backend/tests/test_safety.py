from backend.app.safety import (
    check_safety_circuit_breaker,
    EMERGENCY_CIRCUIT_BREAKER_RESPONSE,
    CLINICAL_ADVICE_DISCLAIMER_RESPONSE,
)


def test_safety_circuit_breaker_sudden_hearing_loss():
    override = check_safety_circuit_breaker("I suddenly lost hearing in my left ear this morning")
    assert override == EMERGENCY_CIRCUIT_BREAKER_RESPONSE


def test_safety_circuit_breaker_ear_bleeding():
    override = check_safety_circuit_breaker("Help, there is bleeding from my ear after an accident")
    assert override == EMERGENCY_CIRCUIT_BREAKER_RESPONSE


def test_safety_circuit_breaker_foreign_object():
    override = check_safety_circuit_breaker("A bead is stuck inside my daughter's ear")
    assert override == EMERGENCY_CIRCUIT_BREAKER_RESPONSE


def test_safety_circuit_breaker_stroke_symptoms():
    override = check_safety_circuit_breaker(
        "My grandfather is suddenly slurring his speech and can't speak"
    )
    assert override == EMERGENCY_CIRCUIT_BREAKER_RESPONSE


def test_clinical_advice_disclaimer_prescriptions():
    override = check_safety_circuit_breaker("What medicine should I take for ear infection?")
    assert override == CLINICAL_ADVICE_DISCLAIMER_RESPONSE


def test_normal_queries_pass_through():
    assert check_safety_circuit_breaker("What are your clinic hours?") is None
    assert check_safety_circuit_breaker("Can I book a hearing test for tomorrow at 11am?") is None
    assert check_safety_circuit_breaker("Where can I park my car?") is None
    assert check_safety_circuit_breaker("How much does Pure Tone Audiometry cost?") is None
