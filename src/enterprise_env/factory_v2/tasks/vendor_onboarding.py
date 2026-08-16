"""Generated variant of the vendor_onboarding task.

Uses entity IDs from a GeneratedWorld rather than the static hardcoded IDs
in tasks/vendor_onboarding.py. The static task is untouched.

Also provides GeneratedVendorOnboardingBaseline — an oracle scripted policy
that uses the world's entity IDs, enabling automated solvability verification.
"""
from __future__ import annotations
from ...tasks.base import BaseTask, Subgoal, _affirms
from ...evaluation.baseline import ScriptedPolicy
from ...core.actions import Action
from ..world import GeneratedWorld


class GeneratedVendorOnboardingTask(BaseTask):
    """Vendor onboarding task parameterized by a GeneratedWorld.

    Structurally identical to VendorOnboardingTask but all hardcoded entity
    IDs (vendor email, ticket IDs, sheet ID, channel ID) come from the world.
    Subgoal verifiers use world IDs, so generated and static tasks coexist
    without interfering.
    """
    max_steps = 40
    start_agent = "pm_01"

    def __init__(self, world: GeneratedWorld) -> None:
        self.world = world
        v = world.vendor
        pm   = world.employee_by_role("project_manager")
        eng  = world.employee_by_role("engineer")
        prod = world.employee_by_role("product_manager")
        mgr  = world.employee_by_role("engineering_manager")
        self.task_id = f"vendor_onboarding_gen_v1_seed{world.spec.seed}"
        self.name = f"{v.name} Vendor Onboarding"
        self.instruction = (
            f"{v.name} has submitted a vendor onboarding request. "
            f"Discover the request, locate the main procurement ticket ({v.main_ticket}), "
            f"have Legal ({prod.agent_id}) review and clear {v.legal_ticket}, "
            f"have IT ({eng.agent_id}) confirm provisioning in {v.it_ticket}, "
            f"get Engineering Manager approval on {v.main_ticket}, "
            f"mark the vendor as ACTIVE in the vendor tracker sheet, "
            f"schedule an onboarding kickoff meeting, "
            f"and announce the completed onboarding in the procurement channel. "
            f"Role boundaries: only {pm.agent_id} may write the vendor sheet; "
            f"only {prod.agent_id} may record legal clearance; "
            f"only {eng.agent_id} may record IT provisioning; "
            f"only {mgr.agent_id} may approve the procurement ticket."
        )

    # ------------------------------------------------------------------
    # Task setup — called after seed_company() in env.reset()
    # ------------------------------------------------------------------

    def setup(self, repo, seed: int) -> None:
        v    = self.world.vendor
        pm   = self.world.employee_by_role("project_manager")
        eng  = self.world.employee_by_role("engineer")
        prod = self.world.employee_by_role("product_manager")
        mgr  = self.world.employee_by_role("engineering_manager")
        cs   = self.world.employee_by_role("customer_success")
        all_agents = [pm, eng, prod, mgr, cs]

        # Override static employee names/emails with generated ones
        for emp in all_agents:
            repo.add(
                "UPDATE employees SET name=?, email=? WHERE employee_id=?",
                (emp.display_name, emp.email, emp.agent_id),
            )

        project_id = f"PROJ-VENDOR-{self.world.spec.seed}"
        repo.add("INSERT INTO projects VALUES(?,?,?)",
                 (project_id, "Vendor & Procurement", pm.agent_id))

        repo.add("INSERT INTO emails VALUES(?,?,?,?,?,?,0)", (
            v.email_id, cs.agent_id, pm.agent_id,
            f"New Vendor Onboarding Request: {v.name}",
            f"{v.name} has been selected as our new data analytics vendor. "
            "Please initiate the onboarding process: legal review, IT provisioning, "
            "and procurement sign-off are all required before go-live.",
            5,
        ))

        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)", (
            v.main_ticket, project_id,
            f"Vendor Onboarding: {v.name} — Procurement Approval",
            f"Full onboarding for {v.name}. Requires legal clearance ({v.legal_ticket}), "
            f"IT provisioning ({v.it_ticket}), and manager sign-off.",
            "open", "high", None, pm.agent_id,
        ))
        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)", (
            v.legal_ticket, project_id,
            f"Legal Review: {v.name} Vendor Contract",
            f"Review the {v.name} vendor agreement for compliance.",
            "open", "high", None, prod.agent_id,
        ))
        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)", (
            v.it_ticket, project_id,
            f"IT Provisioning: {v.name} Environment Setup",
            f"Provision access credentials and sandbox environment for {v.name}.",
            "open", "high", None, eng.agent_id,
        ))

        # Vendor tracker sheet — pm_01 is owner (write); others viewer
        repo.add("INSERT INTO spreadsheets VALUES(?,?,?)",
                 (v.sheet_id, "Vendor Tracker", pm.agent_id))
        for emp, role in [
            (pm, "owner"), (prod, "viewer"),
            (eng, "viewer"), (mgr, "viewer"), (cs, "viewer"),
        ]:
            repo.add("INSERT INTO sheet_members VALUES(?,?,?)",
                     (v.sheet_id, emp.agent_id, role))
        for cell, value in {
            "A1": "Vendor", "B1": "Status", "C1": "Legal Cleared", "D1": "IT Ready",
            "A2": v.name,   "B2": "PENDING", "C2": "PENDING",      "D2": "PENDING",
        }.items():
            repo.add(
                "INSERT INTO sheet_cells(sheet_id,cell,value,updated_by,updated_at)"
                " VALUES(?,?,?,?,?)",
                (v.sheet_id, cell, value, pm.agent_id, 0),
            )

        # Procurement Slack channel
        repo.add("INSERT INTO channels VALUES(?,?)", (v.channel_id, "#procurement"))
        for emp in all_agents:
            repo.add("INSERT INTO channel_members VALUES(?,?)",
                     (v.channel_id, emp.agent_id))

    # ------------------------------------------------------------------
    # Subgoal definitions and verifiers — use world entity IDs
    # ------------------------------------------------------------------

    def subgoals(self):
        return [
            Subgoal("discover_request",    "pm_01 reads the vendor onboarding request email"),
            Subgoal("find_main_ticket",    "pm_01 searches Jira and reads the main ticket",
                    ("discover_request",)),
            Subgoal("legal_review",        "product_01 records legal clearance",
                    ("discover_request",)),
            Subgoal("it_provisioning",     "eng_01 confirms IT provisioning",
                    ("discover_request",)),
            Subgoal("manager_approval",    "mgr_01 approves the onboarding",
                    ("find_main_ticket",)),
            Subgoal("update_vendor_sheet", "pm_01 marks the vendor ACTIVE",
                    ("manager_approval",)),
            Subgoal("schedule_kickoff",    "Schedule kickoff with pm_01, eng_01, product_01",
                    ("legal_review", "it_provisioning")),
            Subgoal("announce_live",       "pm_01 announces completion in Slack",
                    ("schedule_kickoff", "update_vendor_sheet")),
        ]

    def verify_subgoal(self, repo, g: str) -> bool:
        v    = self.world.vendor
        pm   = self.world.employee_by_role("project_manager")
        eng  = self.world.employee_by_role("engineer")
        prod = self.world.employee_by_role("product_manager")
        mgr  = self.world.employee_by_role("engineering_manager")

        if g == "discover_request":
            email = repo.email(v.email_id)
            return (
                email is not None
                and bool(email.get("read"))
                and repo.has_action(pm.agent_id, "gmail", "read_email", v.email_id)
            )
        if g == "find_main_ticket":
            return (
                repo.has_action(pm.agent_id, "jira", "search_issues")
                and repo.has_action(pm.agent_id, "jira", "read_issue", v.main_ticket)
            )
        if g == "legal_review":
            return any(
                c["author_id"] == prod.agent_id
                and any(_affirms(c["comment"], kw)
                        for kw in ("legal", "cleared", "compliant", "approved"))
                for c in repo.comments(v.legal_ticket)
            )
        if g == "it_provisioning":
            return any(
                c["author_id"] == eng.agent_id
                and any(_affirms(c["comment"], kw)
                        for kw in ("setup", "provisioned", "configured", "complete"))
                for c in repo.comments(v.it_ticket)
            )
        if g == "manager_approval":
            return any(
                c["author_id"] == mgr.agent_id and _affirms(c["comment"], "approved")
                for c in repo.comments(v.main_ticket)
            )
        if g == "update_vendor_sheet":
            cell = repo.sheet_cell(v.sheet_id, "B2")
            return (
                cell is not None
                and cell["updated_by"] == pm.agent_id
                and _affirms(cell["value"], "active")
            )
        if g == "schedule_kickoff":
            vname_kw = v.name.lower().split()[0]  # first word of vendor name
            for e in repo.events_for(pm.agent_id):
                title_lower = e["title"].lower()
                if not any(kw in title_lower
                           for kw in ("kickoff", "onboarding", vname_kw)):
                    continue
                parts = set(repo.participants(e["event_id"]))
                organizer = e.get("organizer_id") or ""
                if organizer:
                    parts.add(organizer)
                if {pm.agent_id, eng.agent_id, prod.agent_id}.issubset(parts):
                    return True
            return False
        if g == "announce_live":
            return any(
                m["sender_id"] == pm.agent_id
                and v.main_ticket in m["text"]
                and any(_affirms(m["text"], kw)
                        for kw in ("approved", "onboarded", "complete", "live"))
                for m in repo.messages(v.channel_id)
            )
        return False


class GeneratedVendorOnboardingBaseline(ScriptedPolicy):
    """Oracle scripted policy for a GeneratedVendorOnboardingTask.

    Uses the world's entity IDs so the oracle works regardless of which
    vendor name / ticket prefix was generated for this seed.
    """

    def __init__(self, world: GeneratedWorld) -> None:
        v    = world.vendor
        pm   = world.employee_by_role("project_manager")
        eng  = world.employee_by_role("engineer")
        prod = world.employee_by_role("product_manager")
        mgr  = world.employee_by_role("engineering_manager")
        vkw  = v.name.lower().split()[0]  # first word for search query

        super().__init__([
            Action(pm.agent_id,   "gmail", "read_email",
                   {"email_id": v.email_id}),
            Action(pm.agent_id,   "jira",  "search_issues",
                   {"query": f"{v.ticket_prefix} onboarding {vkw}"}),
            Action(pm.agent_id,   "jira",  "read_issue",
                   {"issue_id": v.main_ticket}),
            Action(prod.agent_id, "jira",  "add_comment", {
                "issue_id": v.legal_ticket,
                "comment": (
                    f"Legal review complete. {v.name} vendor agreement is compliant "
                    "with procurement and data handling policies."
                ),
            }),
            Action(eng.agent_id,  "jira",  "add_comment", {
                "issue_id": v.it_ticket,
                "comment": (
                    f"IT setup complete. Access credentials and API keys provisioned. "
                    f"Sandbox environment configured for {v.name} integration."
                ),
            }),
            Action(mgr.agent_id,  "jira",  "add_comment", {
                "issue_id": v.main_ticket,
                "comment": (
                    "Vendor onboarding approved. Legal and IT have both confirmed "
                    "readiness. Proceed with kickoff."
                ),
            }),
            Action(pm.agent_id,   "sheets", "read_sheet",
                   {"sheet_id": v.sheet_id}),
            Action(pm.agent_id,   "sheets", "update_cell",
                   {"sheet_id": v.sheet_id, "cell": "B2", "value": "ACTIVE"}),
            Action(pm.agent_id,   "calendar", "create_event", {
                "title": f"{v.name} Onboarding Kickoff",
                "participants": [prod.agent_id, eng.agent_id, mgr.agent_id],
                "start_time": 720,
                "end_time":   780,
            }),
            Action(pm.agent_id,   "slack", "send_message", {
                "channel_id": v.channel_id,
                "text": (
                    f"{v.main_ticket} approved. {v.name} onboarding is complete. "
                    "Legal cleared, IT provisioned, kickoff scheduled."
                ),
                "mentions": [prod.agent_id, eng.agent_id, mgr.agent_id],
            }),
        ])
