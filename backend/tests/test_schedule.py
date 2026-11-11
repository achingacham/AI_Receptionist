from datetime import datetime
import zoneinfo
import pytest

from backend.app.schedule import ClinicSchedule


@pytest.fixture
def schedule():
    return ClinicSchedule(timezone_str="Asia/Kolkata")


def test_clinic_open_during_weekday_hours(schedule):
    tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    # Wednesday at 2:30 PM (weekday=2)
    dt = datetime(2026, 11, 11, 14, 30, tzinfo=tz)
    status = schedule.evaluate(dt)
    assert status.is_open is True
    assert "OPEN" in status.status_summary
    assert status.next_opening is None


def test_clinic_closed_after_hours_weekday(schedule):
    tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    # Wednesday at 8:00 PM
    dt = datetime(2026, 11, 11, 20, 0, tzinfo=tz)
    status = schedule.evaluate(dt)
    assert status.is_open is False
    assert "CLOSED" in status.status_summary
    assert status.next_opening is not None
    # Next opening should be Thursday at 10:00 AM
    assert status.next_opening.weekday() == 3
    assert status.next_opening.hour == 10
    assert status.next_opening.minute == 0


def test_clinic_closed_on_weekend(schedule):
    tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    # Saturday at 11:00 AM (weekday=5)
    dt = datetime(2026, 11, 14, 11, 0, tzinfo=tz)
    status = schedule.evaluate(dt)
    assert status.is_open is False
    assert "CLOSED" in status.status_summary
    # Next opening should be Monday at 10:00 AM
    assert status.next_opening.weekday() == 0
    assert status.next_opening.hour == 10


def test_prompt_context_contains_status_and_policy(schedule):
    tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    dt = datetime(2026, 11, 11, 21, 0, tzinfo=tz)
    context = schedule.get_prompt_context(dt)
    assert "CLINIC SCHEDULE & OPERATING STATUS:" in context
    assert "CLOSED" in context
    assert "OPERATING HOURS INSTRUCTIONS:" in context
    assert "Do NOT proactively state or announce that the clinic is closed" in context
    assert "OFF-HOURS SLOT REQUESTS" in context
    assert (
        "Courteously inform the caller that the requested time falls outside regular clinic hours"
        in context
    )
    assert "NEVER book an appointment for today while closed" in context
    assert "next opening: Thursday at 10:00 AM" in context


def test_prompt_context_during_open_hours(schedule):
    tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    dt = datetime(2026, 11, 11, 14, 30, tzinfo=tz)
    context = schedule.get_prompt_context(dt)
    assert "OPEN (Closes today at 06:30 PM)" in context
    assert "Do NOT proactively state or announce that the clinic is closed" in context
    assert "OFF-HOURS SLOT REQUESTS" in context
    assert "next opening: Thursday at 10:00 AM" in context
