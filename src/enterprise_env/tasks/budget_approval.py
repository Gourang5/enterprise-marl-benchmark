from .base import BaseTask, Subgoal, _affirms
import random


class BudgetApprovalTask(BaseTask):
    task_id = "budget_approval_v1"
    name = "Q1 Initiative Budget Approval"
    max_steps = 35
    start_agent = "product_01"
    instruction = (
        "A customer has requested a Q1 Analytics Dashboard initiative. Discover the request, locate the budget "
        "approval ticket, have Engineering estimate the cost, get Engineering Manager approval, record the decision "
        "in the budget tracker sheet, schedule a project kickoff meeting, and announce the approval to the team. "
        "Role boundaries: only product_01 may write the budget sheet — Engineering and the Manager comment only "
        "on the Jira ticket, not on the spreadsheet."
    )

    def setup(self, repo, seed):
        repo.add("INSERT INTO emails VALUES(?,?,?,?,?,?,0)", (
            "budget-email-001", "cs_01", "product_01",
            "Q1 Analytics Dashboard Budget Request",
            "Acme Retail Partner needs an advanced analytics dashboard for order tracking. "
            "Engineering team should estimate cost and get manager sign-off before committing resources.",
            10,
        ))
        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)", (
            "BUDGET-201", "PROJ-LAUNCH",
            "Q1 Analytics Dashboard — Budget Approval",
            "Estimate engineering cost and obtain manager approval before committing sprint capacity "
            "to the analytics dashboard initiative.",
            "open", "high", None, "product_01",
        ))
        repo.add("INSERT INTO spreadsheets VALUES(?,?,?)", ("SHEET-BUDGET", "Q1 Budget Tracker", "product_01"))
        # Only product_01 may write; eng_01 and mgr_01 are viewers to enforce the stated role boundary.
        for eid, role in {
            "product_01": "owner",
            "pm_01": "viewer",
            "mgr_01": "viewer",
            "eng_01": "viewer",
            "cs_01": "viewer",
        }.items():
            repo.add("INSERT INTO sheet_members VALUES(?,?,?)", ("SHEET-BUDGET", eid, role))
        for cell, value in {
            "A1": "Initiative", "B1": "Estimate (days)", "C1": "Status",
            "A2": "Q1 Analytics Dashboard", "B2": "", "C2": "PENDING",
        }.items():
            repo.add(
                "INSERT INTO sheet_cells(sheet_id,cell,value,updated_by,updated_at) VALUES(?,?,?,?,?)",
                ("SHEET-BUDGET", cell, value, "product_01", 0),
            )
        rng = random.Random(seed)
        # Realistic near-miss Jira noise
        noise = [
            ("BUDGET-198", "PROJ-LAUNCH", "Office supplies reorder",
             "Routine supply restock; submit via procurement portal.", "resolved", "low", None, "mgr_01"),
            ("BUDGET-199", "PROJ-LAUNCH", "Annual conference travel",
             "Pre-approved travel to industry conference; standard renewal.", "open", "low", None, "product_01"),
            ("BUDGET-200", "PROJ-LAUNCH", "Software license renewal",
             "Standard SaaS license renewal — no new spend, already budgeted.", "resolved", "low", None, "mgr_01"),
        ]
        rng.shuffle(noise)
        for row in noise[: 1 + seed % 3]:
            repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)", row)
        repo.add("INSERT INTO slack_messages VALUES(?,?,?,?,?)", (
            "budget-msg-1", "CH-PRODUCT", "cs_01",
            "Acme Retail Partner is asking about analytics features — need a timeline.", 1,
        ))

    def subgoals(self):
        return [
            Subgoal("discover_request",  "Product manager reads the budget request email"),
            Subgoal("find_ticket",        "Locate and read the budget Jira ticket",          ("discover_request",)),
            Subgoal("engineering_estimate","Engineering records cost estimate in Jira",       ("find_ticket",)),
            Subgoal("manager_approval",   "Engineering manager approves the budget in Jira",  ("engineering_estimate",)),
            Subgoal("update_budget_sheet","Product records the approval in the budget tracker",("manager_approval",)),
            Subgoal("schedule_kickoff",   "Schedule a project kickoff meeting",               ("update_budget_sheet",)),
            Subgoal("announce_approval",  "Announce budget approval in the product channel",  ("schedule_kickoff",)),
        ]

    def verify_subgoal(self, repo, g):
        if g == "discover_request":
            return bool(repo.email("budget-email-001")["read"]) and repo.has_action(
                "product_01", "gmail", "read_email", "budget-email-001"
            )
        if g == "find_ticket":
            return repo.has_action("product_01", "jira", "search_issues") and repo.has_action(
                "product_01", "jira", "read_issue", "BUDGET-201"
            )
        if g == "engineering_estimate":
            # Negation-hardened: "NOT an estimate" must not pass
            return any(
                c["author_id"] == "eng_01" and _affirms(c["comment"], "estimate")
                for c in repo.comments("BUDGET-201")
            )
        if g == "manager_approval":
            # Negation-hardened: "NOT approved" must not pass
            return any(
                c["author_id"] == "mgr_01" and _affirms(c["comment"], "approved")
                for c in repo.comments("BUDGET-201")
            )
        if g == "update_budget_sheet":
            c2 = repo.sheet_cell("SHEET-BUDGET", "C2")
            # Exact APPROVED value written by product_01 only (sheet RBAC enforces writer)
            return (
                c2 is not None
                and c2["updated_by"] == "product_01"
                and _affirms(c2["value"], "approved")
            )
        if g == "schedule_kickoff":
            return any(
                (
                    "analytics" in e["title"].lower()
                    or "kickoff" in e["title"].lower()
                    or "budget" in e["title"].lower()
                )
                and {"product_01", "eng_01"}.issubset(set(repo.participants(e["event_id"])))
                for e in repo.events_for("product_01")
            )
        if g == "announce_approval":
            return any(
                m["sender_id"] == "product_01"
                and "BUDGET-201" in m["text"]
                and _affirms(m["text"], "approved")
                for m in repo.messages("CH-PRODUCT")
            )
        return False
