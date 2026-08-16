"""Tests that verifiers reject negation exploits like 'NOT approved' and 'NOT validated'.

Each test injects a negated comment/message and asserts the subgoal does NOT pass.
A paired positive test confirms the same keyword phrase DOES pass when un-negated.
"""
from enterprise_env.tasks.base import _affirms


# ── _affirms unit tests ────────────────────────────────────────────────────────

def test_affirms_basic_positive():
    assert _affirms("The ticket has been approved by management.", "approved")

def test_affirms_not_negated():
    assert not _affirms("This ticket has NOT been approved.", "approved")

def test_affirms_never_negated():
    assert not _affirms("Never approved this request.", "approved")

def test_affirms_failed_negated():
    assert not _affirms("Review failed: not approved by manager.", "approved")

def test_affirms_rejected_negated():
    assert not _affirms("Manager rejected; not approved.", "approved")

def test_affirms_validated_positive():
    assert _affirms("Specs have been validated by engineering.", "validated")

def test_affirms_not_validated():
    assert not _affirms("Specs have NOT been validated.", "validated")

def test_affirms_investigated_positive():
    assert _affirms("Investigated the root cause thoroughly.", "investig")

def test_affirms_not_investigated():
    assert not _affirms("NOT investigated yet; still pending.", "investig")

def test_affirms_resolved_positive():
    assert _affirms("Customer issue is resolved and closed.", "resolved")

def test_affirms_not_resolved():
    assert not _affirms("Issue is NOT resolved; still open.", "resolved")

def test_affirms_approved_window_boundary():
    # Negation more than 60 chars before keyword should NOT block it
    prefix = "A" * 70  # 70 neutral chars
    assert _affirms(prefix + " approved", "approved")

def test_affirms_post_keyword_no_rejected():
    # "Approved? No, this request is rejected." — negation AFTER the keyword
    assert not _affirms("Approved? No, this request is rejected.", "approved")

def test_affirms_post_keyword_validated_no():
    # "Validated? No. Telemetry is missing." — negation AFTER the keyword
    assert not _affirms("Validated? No. Telemetry is missing.", "validated")

def test_affirms_provisioned_positive():
    assert _affirms("IT setup complete: system is provisioned.", "provisioned")

def test_affirms_not_provisioned():
    assert not _affirms("NOT provisioned yet; waiting on credentials.", "provisioned")

def test_affirms_active_positive():
    assert _affirms("Vendor status changed to active in the tracker.", "active")

def test_affirms_not_active():
    assert not _affirms("Vendor is not active; onboarding blocked.", "active")

def test_affirms_ready_positive():
    assert _affirms("System is ready for launch.", "ready")

def test_affirms_not_ready():
    assert not _affirms("System is NOT ready for launch.", "ready")

def test_affirms_cleared_positive():
    assert _affirms("Legal team has cleared the contract.", "cleared")

def test_affirms_not_cleared():
    assert not _affirms("Legal has NOT cleared the contract.", "cleared")

def test_affirms_telemetry_positive():
    assert _affirms("Reviewed telemetry and all metrics look good.", "telemetry")

def test_affirms_no_telemetry():
    assert not _affirms("No telemetry available for review.", "telemetry")


# ── Integration: verifiers reject negation exploits in full env ─────────────

from enterprise_env.factory import make_env
from enterprise_env.core.actions import Action


def _step(env, agent, app, action_type, **params):
    return env.step(Action(agent, app, action_type, params))


def test_product_launch_not_validated_fails():
    env = make_env("product_launch")
    env.reset(seed=42)
    # Inject a negated validation comment on LAUNCH-102 — must NOT pass the validation subgoal
    env.repo.add(
        "INSERT INTO jira_comments(issue_id,author_id,comment,timestamp) VALUES(?,?,?,?)",
        ("LAUNCH-102", "eng_01", "This has NOT been validated.", 99),
    )
    sg = env.verifier.subgoals(env.repo)
    assert not sg.get("validation", False), "Negated 'validated' must not pass the validation subgoal"
    env.close()


def test_product_launch_not_approved_fails():
    env = make_env("product_launch")
    env.reset(seed=42)
    env.repo.add(
        "INSERT INTO jira_comments(issue_id,author_id,comment,timestamp) VALUES(?,?,?,?)",
        ("LAUNCH-101", "mgr_01", "NOT approved, please revise.", 99),
    )
    sg = env.verifier.subgoals(env.repo)
    assert not sg.get("approval", False), "Negated 'approved' must not pass the approval subgoal"
    env.close()


def test_budget_approval_not_approved_fails():
    env = make_env("budget_approval")
    env.reset(seed=42)
    env.repo.add(
        "INSERT INTO jira_comments(issue_id,author_id,comment,timestamp) VALUES(?,?,?,?)",
        ("BUDGET-201", "mgr_01", "NOT approved — cost too high.", 99),
    )
    sg = env.verifier.subgoals(env.repo)
    assert not sg.get("manager_approval", False), "Negated 'approved' must not pass budget manager_approval"
    env.close()


def test_vendor_onboarding_not_approved_fails():
    env = make_env("vendor_onboarding")
    env.reset(seed=42)
    env.repo.add(
        "INSERT INTO jira_comments(issue_id,author_id,comment,timestamp) VALUES(?,?,?,?)",
        ("VEND-401", "mgr_01", "NOT approved: compliance issue found.", 99),
    )
    sg = env.verifier.subgoals(env.repo)
    assert not sg.get("manager_approval", False), "Negated 'approved' must not pass vendor manager_approval"
    env.close()


def test_launch_readiness_not_approved_fails():
    env = make_env("launch_readiness")
    env.reset(seed=42)
    env.repo.add(
        "INSERT INTO jira_comments(issue_id,author_id,comment,timestamp) VALUES(?,?,?,?)",
        ("READY-301", "mgr_01", "NOT approved; telemetry check failed.", 99),
    )
    sg = env.verifier.subgoals(env.repo)
    assert not sg.get("manager_approves", False), "Negated 'approved' must not pass launch manager_approves"
    env.close()


def test_info_eval_hidden_from_top_level():
    """Evaluator state must be under info['eval'], not exposed at the top level."""
    env = make_env("customer_incident")
    env.reset(seed=42)
    action = Action("pm_01", "gmail", "search_emails", {"query": "authentication"})
    _, _, _, _, info = env.step(action)
    assert "progress"          not in info, "progress must be in info['eval'], not top-level"
    assert "subgoals"          not in info, "subgoals must be in info['eval'], not top-level"
    assert "reward_components" not in info, "reward_components must be in info['eval'], not top-level"
    assert "eval" in info,                  "info['eval'] must exist for evaluator access"
    assert "progress"          in info["eval"]
    assert "subgoals"          in info["eval"]
    assert "reward_components" in info["eval"]
    # Agent-safe keys remain at top level
    assert "success" in info
    assert "message" in info
    assert "step"    in info
    env.close()
