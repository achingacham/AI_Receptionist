# AI Receptionist

An automated telephony and chat receptionist handling client inquiries, emergency routing, and appointment scheduling via calendar integrations.

## Language

**Safety Perimeter**:
The set of defensive boundaries protecting the receptionist against prompt injection, medical liability overreach, unauthorized calendar modification, and privacy leakage.
_Avoid_: Firewall, filter list

**Guardrail**:
An independent inspection layer evaluated before and after language model invocations to enforce boundaries on user inputs, tool actions, and generated outputs.
_Avoid_: Validator, filter

**Circuit Breaker**:
A deterministic override mechanism that halts standard generative dialogue upon detecting an emergency or severe policy violation and immediately returns an authoritative safety protocol.
_Avoid_: Abort, kill switch

**Action Authorization**:
The verification of caller identity (via caller phone number or booking reference code) required prior to modifying or canceling existing bookings.
_Avoid_: Access control, permissions

**PII Scrubbing**:
The automated redaction of personally identifiable and protected health information prior to persisting data in logs or storage.
_Avoid_: Anonymization, hashing

