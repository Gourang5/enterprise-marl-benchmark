from enterprise_env.factory import make_env
from enterprise_env.core.actions import Action


def test_malformed_action_becomes_invalid_transition_not_crash():
    e=make_env("customer_incident");e.reset(1)
    _,r,done,trunc,info=e.step(Action("pm_01","jira","assign_issue",{"issue_id":"INC-421"}))
    assert info["success"] is False and "Missing required parameter" in info["message"] and r < 0 and not done
    e.close()


def test_unknown_parameter_is_rejected():
    e=make_env("customer_incident");e.reset(1)
    _,r,_,_,info=e.step(Action("pm_01","gmail","search_emails",{"query":"auth","extra":1}))
    assert info["success"] is False and "Unknown parameter" in info["message"] and r < 0
    e.close()


def test_seed_changes_scenario_noise_but_not_solvability():
    e1=make_env("customer_incident");e1.reset(1);n1=len(e1.repo.inbox_headers("pm_01"));e1.close()
    e2=make_env("customer_incident");e2.reset(2);n2=len(e2.repo.inbox_headers("pm_01"));e2.close()
    assert n1 != n2


def test_meeting_conflict_verifier_checks_actual_overlap():
    e=make_env("meeting_conflict");e.reset(3)
    # Initial state has a real overlap between EV-1 and EV-2, but discovery is gated by reading the notification email.
    a=e.repo.get("SELECT * FROM calendar_events WHERE event_id='EV-1'")
    b=e.repo.get("SELECT * FROM calendar_events WHERE event_id='EV-2'")
    assert a["start_time"] < b["end_time"] and a["end_time"] > b["start_time"]
    # No actions taken yet: notification email unread, calendars unread, conflict unresolved.
    sg=e.verifier.subgoals(e.repo)
    assert sg["discover_conflict"] is False
    assert sg["reschedule"] is False
    e.close()
