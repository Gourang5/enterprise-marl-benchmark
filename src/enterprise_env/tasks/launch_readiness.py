from .base import BaseTask, Subgoal, _affirms
import random


class LaunchReadinessTask(BaseTask):
    task_id = "launch_readiness_v1"
    name = "Cross-Team Launch Readiness"
    max_steps = 45
    start_agent = "cs_01"
    instruction = (
        "Prepare the Marketplace Checkout launch readiness review. Customer Success has a private partner commitment, "
        "Engineering owns the blocker investigation, Product owns the readiness sheet, and Engineering Management "
        "must approve. Coordinate across Gmail, Slack, Jira, Sheets, and Calendar without bypassing role or access "
        "boundaries. Only product_01 may write the readiness sheet."
    )

    def setup(self, repo, seed):
        repo.add("INSERT INTO emails VALUES(?,?,?,?,?,?,0)", (
            "lr-email-001", "pm_01", "cs_01",
            "Partner checkout commitment for launch",
            "Acme Retail Partner requires checkout retry readiness confirmed before the 16:00 launch review. "
            "Customer-facing commitment is launch-blocking.", 20,
        ))
        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)", (
            "READY-301", "PROJ-LAUNCH",
            "Checkout retry readiness blocker",
            "Validate payment retry telemetry and production alerts before launch approval.",
            "open", "P1", "eng_01", "product_01",
        ))
        repo.add("INSERT INTO spreadsheets VALUES(?,?,?)", ("SHEET-LAUNCH", "Marketplace Launch Readiness", "product_01"))
        # Only product_01 may write; eng_01 is viewer to enforce role boundary stated in task instruction.
        for eid, role in {
            "product_01": "owner",
            "eng_01": "viewer",
            "pm_01": "viewer",
            "mgr_01": "viewer",
            "cs_01": "viewer",
        }.items():
            repo.add("INSERT INTO sheet_members VALUES(?,?,?)", ("SHEET-LAUNCH", eid, role))
        for cell, value in {
            "A1": "Area", "B1": "Status", "C1": "Evidence",
            "A2": "Partner commitment", "B2": "UNKNOWN", "C2": "",
            "A3": "Retry telemetry",    "B3": "BLOCKED",  "C3": "READY-301",
            "A4": "Manager approval",   "B4": "PENDING",  "C4": "",
        }.items():
            repo.add(
                "INSERT INTO sheet_cells(sheet_id,cell,value,updated_by,updated_at) VALUES(?,?,?,?,?)",
                ("SHEET-LAUNCH", cell, value, "product_01", 0),
            )
        rng = random.Random(seed)
        # Realistic near-miss distractor emails
        distractions = [
            ("lr-noise-1", "mgr_01", "cs_01",
             "Sandbox pilot status", "Sandbox-only pilot is not a blocker for the production launch.", 4),
            ("lr-noise-2", "product_01", "cs_01",
             "Post-launch marketing copy", "Marketing copy review is scheduled for after launch day.", 3),
            ("lr-noise-3", "pm_01", "cs_01",
             "Quarterly invoice export", "Finance team invoice export request — unrelated to launch.", 2),
        ]
        rng.shuffle(distractions)
        for row in distractions[: 1 + seed % 3]:
            repo.add("INSERT INTO emails VALUES(?,?,?,?,?,?,0)", row)
        repo.add("INSERT INTO slack_messages VALUES(?,?,?,?,?)", (
            "lr-msg-seed", "CH-PRODUCT", "product_01",
            "Readiness review requires evidence, not assumptions.", 1,
        ))

    def subgoals(self):
        return [
            Subgoal("cs_discovers_commitment", "Customer Success reads the private partner commitment"),
            Subgoal("cs_handoff",              "Customer Success communicates the commitment to Product",
                    ("cs_discovers_commitment",)),
            Subgoal("engineering_investigates","Engineering inspects and documents the Jira blocker",
                    ("cs_handoff",)),
            Subgoal("product_records_evidence","Product records partner and engineering evidence in the readiness sheet",
                    ("engineering_investigates",)),
            Subgoal("manager_approves",        "Engineering manager records launch approval",
                    ("product_records_evidence",)),
            Subgoal("product_records_approval","Product records manager approval in the sheet",
                    ("manager_approves",)),
            Subgoal("schedule_review",         "Product schedules the cross-team launch review",
                    ("product_records_approval",)),
            Subgoal("announce_ready",          "Product announces readiness with the blocker and sheet reference",
                    ("schedule_review",)),
        ]

    def verify_subgoal(self, repo, g):
        if g == "cs_discovers_commitment":
            return (
                bool(repo.email("lr-email-001")["read"])
                and repo.has_action("cs_01", "gmail", "read_email", "lr-email-001")
            )
        if g == "cs_handoff":
            return any(
                m["sender_id"] == "cs_01"
                and "16:00" in m["text"]
                and "partner" in m["text"].lower()
                for m in repo.messages("CH-PRODUCT")
            )
        if g == "engineering_investigates":
            issue = repo.issue("READY-301")
            # Negation-hardened: "NOT telemetry" must not satisfy the investigation check
            return (
                repo.has_action("eng_01", "jira", "read_issue", "READY-301")
                and any(
                    c["author_id"] == "eng_01" and _affirms(c["comment"], "telemetry")
                    for c in repo.comments("READY-301")
                )
                and issue["status"] in {"in_progress", "resolved"}
            )
        if g == "product_records_evidence":
            b2 = repo.sheet_cell("SHEET-LAUNCH", "B2")
            b3 = repo.sheet_cell("SHEET-LAUNCH", "B3")
            c2 = repo.sheet_cell("SHEET-LAUNCH", "C2")
            c3 = repo.sheet_cell("SHEET-LAUNCH", "C3")
            return (
                all(x and x["updated_by"] == "product_01" for x in (b2, b3, c2, c3))
                and b2["value"].upper() == "READY"
                and b3["value"].upper() == "READY"
                and "16:00" in c2["value"]
                and "READY-301" in c3["value"]
            )
        if g == "manager_approves":
            # Negation-hardened: "NOT approved" must not pass
            return any(
                c["author_id"] == "mgr_01" and _affirms(c["comment"], "approved")
                for c in repo.comments("READY-301")
            )
        if g == "product_records_approval":
            b4 = repo.sheet_cell("SHEET-LAUNCH", "B4")
            c4 = repo.sheet_cell("SHEET-LAUNCH", "C4")
            return (
                b4 is not None and c4 is not None
                and b4["updated_by"] == "product_01"
                and b4["value"].upper() == "APPROVED"
                and "Daniel" in c4["value"]
            )
        if g == "schedule_review":
            return any(
                "Launch Readiness" in e["title"]
                and {"product_01", "eng_01", "mgr_01", "cs_01"}.issubset(
                    set(repo.participants(e["event_id"]))
                )
                for e in repo.events_for("product_01")
            )
        if g == "announce_ready":
            return any(
                m["sender_id"] == "product_01"
                and "READY-301" in m["text"]
                and "SHEET-LAUNCH" in m["text"]
                and _affirms(m["text"], "ready")
                for m in repo.messages("CH-PRODUCT")
            )
        return False
