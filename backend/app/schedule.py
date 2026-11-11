"""Deterministic Clinic Schedule evaluator.

Evaluates real-time open/closed status using Python's zoneinfo, calculates next
opening windows, and emits unambiguous schedule context for the receptionist LLM.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
import zoneinfo

from .config import settings


@dataclass(frozen=True)
class ScheduleStatus:
    is_open: bool
    status_summary: str
    next_opening: datetime | None
    local_now: datetime


class ClinicSchedule:
    """Deterministic schedule calculator for clinic operating hours."""

    def __init__(
        self,
        timezone_str: str | None = None,
        # Mon-Fri: 10:00 to 18:30 (0=Mon, 4=Fri)
        weekday_open: time = time(10, 0),
        weekday_close: time = time(18, 30),
    ):
        tz_name = timezone_str or settings.calcom_timezone or "Asia/Kolkata"
        try:
            self.tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            self.tz = zoneinfo.ZoneInfo("Asia/Kolkata")

        self.weekday_open = weekday_open
        self.weekday_close = weekday_close

    def get_local_now(self) -> datetime:
        return datetime.now(self.tz)

    def is_open(self, dt: datetime | None = None) -> bool:
        status = self.evaluate(dt)
        return status.is_open

    def evaluate(self, dt: datetime | None = None) -> ScheduleStatus:
        now = dt if dt is not None else self.get_local_now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=self.tz)
        else:
            now = now.astimezone(self.tz)

        weekday = now.weekday()  # 0=Monday, 6=Sunday
        current_time = now.time()

        # Monday through Friday
        if weekday < 5:
            if self.weekday_open <= current_time < self.weekday_close:
                close_fmt = self.weekday_close.strftime("%I:%M %p")
                return ScheduleStatus(
                    is_open=True,
                    status_summary=f"OPEN (Closes today at {close_fmt})",
                    next_opening=None,
                    local_now=now,
                )

        # Currently closed — calculate next opening
        next_open = self._calculate_next_opening(now)
        next_fmt = next_open.strftime("%A at %I:%M %p")
        return ScheduleStatus(
            is_open=False,
            status_summary=f"CLOSED (Next opening: {next_fmt})",
            next_opening=next_open,
            local_now=now,
        )

    def _calculate_next_opening(self, now: datetime) -> datetime:
        # Check if reopening later today
        if now.weekday() < 5 and now.time() < self.weekday_open:
            return now.replace(
                hour=self.weekday_open.hour,
                minute=self.weekday_open.minute,
                second=0,
                microsecond=0,
            )

        # Advance day-by-day until next weekday
        candidate = now + timedelta(days=1)
        while candidate.weekday() >= 5:  # Skip Saturday and Sunday
            candidate += timedelta(days=1)

        return candidate.replace(
            hour=self.weekday_open.hour,
            minute=self.weekday_open.minute,
            second=0,
            microsecond=0,
        )

    def get_prompt_context(self, dt: datetime | None = None) -> str:
        status = self.evaluate(dt)
        local_time_fmt = status.local_now.strftime("%A %I:%M %p")
        tz_name = self.tz.key

        next_open = status.next_opening or self._calculate_next_opening(status.local_now)
        next_fmt = next_open.strftime("%A at %I:%M %p")

        lines = [
            "CLINIC SCHEDULE & OPERATING STATUS:",
            f"- Current Clinic Local Time: {local_time_fmt} ({tz_name})",
            f"- Current Status: {status.status_summary}",
            "- Regular Hours: Monday to Friday 10:00 AM – 06:30 PM; Weekends by appointment.",
            "",
            "OPERATING HOURS INSTRUCTIONS:",
            "- GREETING & GENERAL INQUIRIES: Answer inquiries, provide clinic information, and assist normally at all times, regardless of the current local time. Do NOT proactively state or announce that the clinic is closed when greeting the caller or answering general questions.",
            "- OFF-HOURS SLOT REQUESTS: If and only if the caller requests an appointment time slot that falls outside clinic operating hours (e.g., before 10:00 AM, after 06:30 PM, on weekends, or requesting a same-day/immediate appointment when the clinic is already closed):",
            f"  * Courteously inform the caller that the requested time falls outside regular clinic hours (Monday to Friday 10:00 AM – 06:30 PM; next opening: {next_fmt}).",
            "  * If they request a weekend slot, politely explain that weekend visits are by special appointment through clinic staff, and offer to take a Caller Message or book the next available weekday.",
            "  * NEVER book an appointment for today while closed or during past hours.",
            "  * Proactively offer alternative appointment slots during upcoming open operating hours.",
            "- If the caller cannot find a suitable time or needs staff assistance, offer to take a Caller Message.",
        ]

        return "\n".join(lines)


# Singleton instance
clinic_schedule = ClinicSchedule()
