from .base import BaseTask,Subgoal
import random

class CustomerIncidentTask(BaseTask):
    task_id="customer_incident_v2"; name="P0 Partner Authentication Incident"; max_steps=35
    instruction=("A strategic retail partner reports a production authentication outage. Triage the report, correlate it to the right Jira incident, "
                 "coordinate an engineering owner, record investigation progress, schedule a review, resolve only after investigation, and notify Customer Success.")
    def setup(self,repo,seed):
        # Relevant report plus realistic distractors.
        emails=[
            ("seed-email-001","cs_01","pm_01","URGENT partner auth failures after API rollout","Acme Retail Partner reports production API authentication failures beginning after the morning identity rollout. Treat as P0 and provide an update.",5),
            ("seed-email-002","product_01","pm_01","Q4 launch copy review","Can you review the launch copy before Friday?",3),
            ("seed-email-003","mgr_01","pm_01","Weekly planning","Planning doc is ready for the weekly sync.",2),
            ("seed-email-004","cs_01","pm_01","Invoice export question","A customer asked about invoice export formatting; non-urgent.",1),
        ]
        for x in emails: repo.add("INSERT INTO emails VALUES(?,?,?,?,?,?,0)",x)
        issues=[
            ("INC-421","PROJ-ALPHA","Production API authentication failures","P0: partner tokens rejected following identity rollout. Suspected auth gateway regression.","open","P0",None,"cs_01"),
            ("INC-418","PROJ-ALPHA","Staging login intermittency","Staging-only flaky login during load tests.","open","P2","eng_01","eng_01"),
            ("BUG-177","PROJ-ALPHA","Password reset email delay","Transactional email delay; authentication itself succeeds.","open","P2",None,"product_01"),
            ("OPS-099","PROJ-ALPHA","Rotate sandbox credentials","Routine sandbox credential rotation.","open","P3",None,"mgr_01"),
        ]
        for x in issues: repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)",x)
        rng=random.Random(seed)
        topics=[("VPN access renewal","Routine access renewal request."),("Sandbox token expiry","Non-production sandbox token expired."),("Dashboard latency","Analytics dashboard is slow but available."),("Mobile login UX","Design feedback about the mobile sign-in flow."),("Catalog webhook retry","Non-critical webhook retry discussion.")]
        rng.shuffle(topics)
        for idx,(subject,body) in enumerate(topics[:3 + seed % 3], start=10):
            repo.add("INSERT INTO emails VALUES(?,?,?,?,?,?,0)",(f"noise-email-{seed}-{idx}","product_01","pm_01",subject,body,idx))
        issue_topics=[("OPS","Refresh test credentials","Routine non-production credential work."),("BUG","Login button alignment","Cosmetic sign-in page issue."),("TASK","Update auth runbook","Documentation maintenance only."),("OBS","Metrics dashboard cleanup","Observability housekeeping.")]
        rng.shuffle(issue_topics)
        for idx,(prefix,title,desc) in enumerate(issue_topics[:2 + seed % 2], start=1):
            repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)",(f"{prefix}-{800+seed%50+idx}","PROJ-ALPHA",title,desc,"open","P3",None,"product_01"))
        repo.add("INSERT INTO slack_messages VALUES(?,?,?,?,?)",("seed-msg-1","CH-INCIDENTS","mgr_01","Reminder: use #incidents only for confirmed production impact.",1))
        repo.add("INSERT INTO slack_messages VALUES(?,?,?,?,?)",("seed-msg-2","CH-RANDOM","eng_01","Lunch at 12:30?",2))
    def subgoals(self):
        return [
            Subgoal("discover_report","Discover and read the partner report"),
            Subgoal("identify_incident","Search for and inspect the matching incident",("discover_report",)),
            Subgoal("assign_engineer","Assign the incident to Arjun",("identify_incident",)),
            Subgoal("notify_engineer","Notify Arjun in the incident channel",("assign_engineer",)),
            Subgoal("investigate","Arjun records investigation and moves incident in progress",("notify_engineer",)),
            Subgoal("schedule_review","Schedule an incident review with Arjun",("notify_engineer",)),
            Subgoal("resolve","Resolve after investigation",("investigate",)),
            Subgoal("notify_customer","Notify Customer Success of resolution",("resolve",)),
        ]
    def verify_subgoal(self,repo,g):
        issue=repo.issue("INC-421")
        if g=="discover_report": return bool(repo.email("seed-email-001")["read"])
        if g=="identify_incident": return repo.has_action("pm_01","jira","search_issues") and repo.has_action("pm_01","jira","read_issue","INC-421")
        if g=="assign_engineer": return issue["assignee_id"]=="eng_01"
        if g=="notify_engineer": return any("INC-421" in m["text"] and "Arjun" in m["text"] for m in repo.messages("CH-INCIDENTS"))
        if g=="investigate":
            comments=repo.comments("INC-421")
            return issue["status"] in {"in_progress","resolved"} and any(c["author_id"]=="eng_01" and "investig" in c["comment"].lower() for c in comments)
        if g=="schedule_review": return any("INC-421" in e["title"] for e in repo.events_for("eng_01"))
        if g=="resolve": return issue["assignee_id"]=="eng_01" and issue["status"]=="resolved"
        if g=="notify_customer": return any("INC-421" in (e["subject"]+" "+e["body"]) and "resolved" in (e["subject"]+" "+e["body"]).lower() for e in repo.all("SELECT * FROM emails WHERE sender_id='pm_01' AND recipient_id='cs_01'"))
        return False
