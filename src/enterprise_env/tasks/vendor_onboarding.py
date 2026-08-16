from .base import BaseTask, Subgoal
import random


class VendorOnboardingTask(BaseTask):
    task_id = "vendor_onboarding_v1"
    name = "TechNova Solutions Vendor Onboarding"
    max_steps = 40
    start_agent = "pm_01"
    instruction = (
        "TechNova Solutions has submitted a vendor onboarding request. "
        "Discover the request, locate the main procurement ticket (VEND-401), "
        "have Legal (product_01) review and clear VEND-402, "
        "have IT (eng_01) confirm provisioning in VEND-403, "
        "get Engineering Manager approval on VEND-401, "
        "mark the vendor as ACTIVE in the vendor tracker sheet, "
        "schedule an onboarding kickoff meeting, "
        "and announce the completed onboarding in the procurement channel. "
        "Role boundaries: only pm_01 may write the vendor sheet; "
        "only product_01 may record legal clearance; "
        "only eng_01 may record IT provisioning; "
        "only mgr_01 may approve the procurement ticket."
    )

    def setup(self, repo, seed):
        # Register vendor project (new project, must insert before Jira issues)
        repo.add("INSERT INTO projects VALUES(?,?,?)", ("PROJ-VENDOR", "Vendor & Procurement", "pm_01"))

        # Onboarding request email
        repo.add("INSERT INTO emails VALUES(?,?,?,?,?,?,0)", (
            "vendor-request-001", "cs_01", "pm_01",
            "New Vendor Onboarding Request: TechNova Solutions",
            "TechNova Solutions has been selected as our new data analytics vendor. "
            "Please initiate the onboarding process: legal review, IT provisioning, "
            "and procurement sign-off are all required before go-live.",
            5,
        ))

        # Main procurement ticket
        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)", (
            "VEND-401", "PROJ-VENDOR",
            "Vendor Onboarding: TechNova Solutions — Procurement Approval",
            "Full onboarding for TechNova Solutions analytics platform. "
            "Requires legal clearance (VEND-402), IT provisioning (VEND-403), "
            "and manager sign-off before vendor can be marked active.",
            "open", "high", None, "pm_01",
        ))

        # Legal review sub-ticket
        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)", (
            "VEND-402", "PROJ-VENDOR",
            "Legal Review: TechNova Solutions Vendor Contract",
            "Review the TechNova Solutions vendor agreement for compliance with "
            "procurement policies, data handling requirements, and SLA terms.",
            "open", "high", None, "product_01",
        ))

        # IT provisioning sub-ticket
        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)", (
            "VEND-403", "PROJ-VENDOR",
            "IT Provisioning: TechNova Solutions Environment Setup",
            "Provision access credentials, API keys, and sandbox environment "
            "for TechNova Solutions integration with our data pipeline.",
            "open", "high", None, "eng_01",
        ))

        # Vendor tracker sheet
        repo.add("INSERT INTO spreadsheets VALUES(?,?,?)", ("SHEET-VENDOR", "Vendor Tracker", "pm_01"))
        for eid, role in {
            "pm_01": "owner", "mgr_01": "editor", "product_01": "viewer",
            "eng_01": "viewer", "cs_01": "viewer",
        }.items():
            repo.add("INSERT INTO sheet_members VALUES(?,?,?)", ("SHEET-VENDOR", eid, role))
        for cell, value in {
            "A1": "Vendor", "B1": "Status", "C1": "Legal Cleared", "D1": "IT Ready",
            "A2": "TechNova Solutions", "B2": "PENDING", "C2": "PENDING", "D2": "PENDING",
        }.items():
            repo.add(
                "INSERT INTO sheet_cells(sheet_id,cell,value,updated_by,updated_at) VALUES(?,?,?,?,?)",
                ("SHEET-VENDOR", cell, value, "pm_01", 0),
            )

        # Procurement channel (new channel for vendor coordination)
        repo.add("INSERT INTO channels VALUES(?,?)", ("CH-PROCUREMENT", "#procurement"))
        for eid in ["pm_01", "product_01", "eng_01", "mgr_01", "cs_01"]:
            repo.add("INSERT INTO channel_members VALUES(?,?)", ("CH-PROCUREMENT", eid))

        # Seed Slack message to make channel visible in observations
        repo.add("INSERT INTO slack_messages VALUES(?,?,?,?,?)", (
            "vendor-msg-1", "CH-PROCUREMENT", "cs_01",
            "TechNova Solutions contract has been signed. Procurement process can begin.", 2,
        ))

        # Distractor noise
        rng = random.Random(seed)
        noise_tickets = [
            ("VEND-398", "PROJ-VENDOR", "Vendor audit — legacy supplier",
             "Routine annual audit of legacy data provider contracts.", "resolved", "low", None, "mgr_01"),
            ("VEND-399", "PROJ-VENDOR", "Vendor offboarding — OldVendorCo",
             "Sunset integration with OldVendorCo; non-critical.", "open", "low", None, "pm_01"),
            ("VEND-400", "PROJ-VENDOR", "Software license renewal — internal tools",
             "Standard annual renewal for productivity suite.", "resolved", "low", None, "product_01"),
        ]
        rng.shuffle(noise_tickets)
        for row in noise_tickets[: 1 + seed % 3]:
            repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)", row)

    def subgoals(self):
        return [
            Subgoal("discover_request",  "pm_01 reads the vendor onboarding request email"),
            Subgoal("find_main_ticket",  "pm_01 searches Jira and reads the VEND-401 procurement ticket",  ("discover_request",)),
            Subgoal("legal_review",      "product_01 records legal clearance on VEND-402",                ("discover_request",)),
            Subgoal("it_provisioning",   "eng_01 confirms IT provisioning in VEND-403",                   ("discover_request",)),
            Subgoal("manager_approval",  "mgr_01 approves the onboarding on VEND-401",                    ("find_main_ticket",)),
            Subgoal("update_vendor_sheet", "pm_01 marks the vendor ACTIVE in the tracker sheet",          ("manager_approval",)),
            Subgoal("schedule_kickoff",  "Schedule an onboarding kickoff with pm_01, eng_01, product_01", ("legal_review", "it_provisioning")),
            Subgoal("announce_live",     "pm_01 announces vendor onboarding completion in Slack",          ("schedule_kickoff", "update_vendor_sheet")),
        ]

    def verify_subgoal(self, repo, g):
        if g == "discover_request":
            return (
                bool(repo.email("vendor-request-001")["read"])
                and repo.has_action("pm_01", "gmail", "read_email", "vendor-request-001")
            )
        if g == "find_main_ticket":
            return (
                repo.has_action("pm_01", "jira", "search_issues")
                and repo.has_action("pm_01", "jira", "read_issue", "VEND-401")
            )
        if g == "legal_review":
            return any(
                c["author_id"] == "product_01"
                and any(kw in c["comment"].lower() for kw in ("legal", "cleared", "compliant", "approved", "review"))
                for c in repo.comments("VEND-402")
            )
        if g == "it_provisioning":
            return any(
                c["author_id"] == "eng_01"
                and any(kw in c["comment"].lower() for kw in ("setup", "provisioned", "configured", "ready", "complete"))
                for c in repo.comments("VEND-403")
            )
        if g == "manager_approval":
            return any(
                c["author_id"] == "mgr_01" and "approved" in c["comment"].lower()
                for c in repo.comments("VEND-401")
            )
        if g == "update_vendor_sheet":
            cell = repo.sheet_cell("SHEET-VENDOR", "B2")
            return (
                cell is not None
                and cell["updated_by"] == "pm_01"
                and "active" in cell["value"].lower()
            )
        if g == "schedule_kickoff":
            for e in repo.events_for("pm_01"):
                title_lower = e["title"].lower()
                if not any(kw in title_lower for kw in ("kickoff", "onboarding", "technova")):
                    continue
                parts = set(repo.participants(e["event_id"]))
                creator = e.get("organizer_id") or ""
                if creator:
                    parts.add(creator)
                if {"pm_01", "eng_01", "product_01"}.issubset(parts):
                    return True
            return False
        if g == "announce_live":
            return any(
                m["sender_id"] == "pm_01"
                and "VEND-401" in m["text"]
                and any(kw in m["text"].lower() for kw in ("approved", "onboarded", "complete", "live"))
                for m in repo.messages("CH-PROCUREMENT")
            )
        return False
