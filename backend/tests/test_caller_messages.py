from backend.app.storage import save_caller_message, list_caller_messages
from backend.app.messages import record_caller_message
from backend.app import calendar_intent


def test_save_and_list_caller_messages():
    msg_id = save_caller_message(
        caller_name="Rajesh Sharma",
        caller_phone="+91 98765 43210",
        inquiry_text="Do you have specialized pediatric cochlear implant programming?",
    )
    assert isinstance(msg_id, int)

    messages = list_caller_messages(status="pending")
    matched = [m for m in messages if m["id"] == msg_id]
    assert len(matched) == 1
    assert matched[0]["caller_name"] == "Rajesh Sharma"
    assert matched[0]["caller_phone"] == "+91 98765 43210"
    assert "cochlear implant" in matched[0]["inquiry_text"]


def test_record_caller_message_dispatch():
    msg_id = record_caller_message(
        caller_name="Pooja Rao",
        caller_phone="9988776655",
        inquiry_text="What are your charges for home-visit audiometry?",
    )
    assert isinstance(msg_id, int)


def test_calendar_intent_leave_message_action(monkeypatch):
    # Mock LLM intent extraction to return leave_message
    fake_intent = {
        "action": "leave_message",
        "attendee_name": "Arun Kumar",
        "attendee_phone": "+91 91234 56789",
        "inquiry_text": "Do you accept HDFC Ergo health insurance reimbursement?",
    }
    monkeypatch.setattr(calendar_intent, "_extract_intent", lambda msgs: fake_intent)

    context = calendar_intent.get_calendar_context(
        [{"role": "user", "content": "I want to leave a message"}]
    )
    assert "[Message System] Caller message recorded successfully" in context
    assert "Arun Kumar" in context


def test_calendar_intent_leave_message_missing_details(monkeypatch):
    fake_intent = {
        "action": "leave_message",
        "attendee_name": "Arun Kumar",
        "attendee_phone": None,
        "inquiry_text": None,
    }
    monkeypatch.setattr(calendar_intent, "_extract_intent", lambda msgs: fake_intent)

    context = calendar_intent.get_calendar_context(
        [{"role": "user", "content": "Please leave a message"}]
    )
    assert (
        "[Message System] Caller wishes to leave a message. Please ask for missing details"
        in context
    )
    assert "phone/contact" in context
