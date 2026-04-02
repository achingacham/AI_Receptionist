from .general import GENERAL_PROMPT
from .trial_followup import TRIAL_FOLLOWUP_PROMPT
from .appointment import APPOINTMENT_PROMPT
from .appointment_confirmation import APPOINTMENT_CONFIRMATION_PROMPT
from .clinic_reschedule import CLINIC_RESCHEDULE_PROMPT
from .feedback_call import FEEDBACK_CALL_PROMPT

SCENARIO_PROMPTS: dict[str, str] = {
    "general": GENERAL_PROMPT,
    "trial_followup": TRIAL_FOLLOWUP_PROMPT,
    "appointment": APPOINTMENT_PROMPT,
    "appointment_confirmation": APPOINTMENT_CONFIRMATION_PROMPT,
    "clinic_reschedule": CLINIC_RESCHEDULE_PROMPT,
    "feedback_call": FEEDBACK_CALL_PROMPT,
}

__all__ = ["SCENARIO_PROMPTS"]
