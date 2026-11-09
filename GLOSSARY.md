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

**Hermetic Test**:
A test executed in complete isolation from external networks, live credentials, and third-party infrastructure, asserting behavior strictly against controlled local contracts.
_Avoid_: Unit test, offline test

**Live Preflight**:
A non-blocking or fail-fast readiness probe executed during server initialization to verify upstream provider connectivity and model deployment validity before accepting client traffic.
_Avoid_: Sanity check, ping

**Upstream Fault**:
An execution failure originating within an external dependency (such as an LLM provider, STT service, or calendar API) rather than the application codebase itself, requiring distinct error classification.
_Avoid_: Internal server error, system bug


