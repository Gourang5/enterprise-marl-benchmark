from .base import BaseTask, Subgoal
import random


class MeetingConflictTask(BaseTask):
    task_id = "meeting_conflict_v2"
    name = "Priority Meeting Conflict"
    max_steps = 25
    start_agent = "pm_01"
    instruction = (
        "A double-booking notification has arrived: the Engineering Review conflicts with the Strategic Customer Call at 10:00. "
        "Read the notification, inspect both calendars to confirm the conflict, move the Engineering Review to the earliest "
        "feasible one-hour slot that keeps Sarah and Arjun available, then notify participants via Slack."
    )

    def setup(self, repo, seed):
        self.initial_conflict = True
        # Conflict notification email from the organiser of EV-1 to the organiser of EV-2
        repo.add("INSERT INTO emails VALUES(?,?,?,?,?,?,0)", (
            "conflict-email-001", "product_01", "pm_01",
            "Calendar double-booking: Engineering Review conflicts with your 10am Strategic Customer Call",
            "Hi Sarah, your Engineering Review (EV-2) is scheduled at 10:00–11:00, overlapping with the Strategic "
            "Customer Call (EV-1) at the same time. The Customer Call is a customer-facing commitment and cannot move. "
            "Please resolve the conflict by rescheduling the Engineering Review.",
            0,
        ))
        # Times are minutes from start of workday. Customer call is 10:00–11:00 and immovable.
        repo.add("INSERT INTO calendar_events VALUES(?,?,?,?,?)", ("EV-1", "Strategic Customer Call", "product_01", 600, 660))
        for p in ["product_01", "pm_01"]:
            repo.add("INSERT INTO event_participants VALUES(?,?)", ("EV-1", p))
        repo.add("INSERT INTO calendar_events VALUES(?,?,?,?,?)", ("EV-2", "Engineering Review", "pm_01", 600, 660))
        for p in ["pm_01", "eng_01"]:
            repo.add("INSERT INTO event_participants VALUES(?,?)", ("EV-2", p))
        # 11:00–12:00 is blocked for Arjun, making 12:00 the earliest feasible hour.
        repo.add("INSERT INTO calendar_events VALUES(?,?,?,?,?)", ("EV-3", "Platform Standup", "eng_01", 660, 720))
        repo.add("INSERT INTO event_participants VALUES(?,?)", ("EV-3", "eng_01"))
        rng = random.Random(seed)
        distractors = [
            ("Focus Block", 480, 510, "pm_01"),
            ("Metrics Review", 840, 870, "eng_01"),
            ("Product Sync", 900, 930, "pm_01"),
            ("Office Hours", 930, 960, "eng_01"),
        ]
        rng.shuffle(distractors)
        for idx, (title, start, end, owner) in enumerate(distractors[: 1 + seed % 3], start=10):
            eid = f"EV-N{seed}-{idx}"
            repo.add("INSERT INTO calendar_events VALUES(?,?,?,?,?)", (eid, title, owner, start, end))
            repo.add("INSERT INTO event_participants VALUES(?,?)", (eid, owner))

    def subgoals(self):
        return [
            Subgoal("discover_conflict", "Read the double-booking notification email"),
            Subgoal("inspect_pm", "Inspect Sarah's calendar", ("discover_conflict",)),
            Subgoal("inspect_eng", "Inspect Arjun's calendar", ("discover_conflict",)),
            Subgoal("reschedule", "Move Engineering Review to earliest feasible slot", ("inspect_pm", "inspect_eng")),
            Subgoal("notify", "Notify affected participants via Slack", ("reschedule",)),
        ]

    def verify_subgoal(self, repo, g):
        b = repo.get("SELECT * FROM calendar_events WHERE event_id='EV-2'")
        if g == "discover_conflict":
            return bool(repo.email("conflict-email-001")["read"]) and repo.has_action(
                "pm_01", "gmail", "read_email", "conflict-email-001"
            )
        if g == "inspect_pm":
            return repo.has_action("pm_01", "calendar", "read_calendar", "pm_01")
        if g == "inspect_eng":
            return repo.has_action("eng_01", "calendar", "read_calendar", "eng_01")
        if g == "reschedule":
            return b["start_time"] == 720 and b["end_time"] == 780
        if g == "notify":
            return any("EV-2" in m["text"] and "12:00" in m["text"] for m in repo.messages("CH-PROJECT"))
        return False
