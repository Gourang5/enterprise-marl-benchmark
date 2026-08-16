from .base import BaseTask,Subgoal
import random

class ProductLaunchTask(BaseTask):
    task_id="product_launch_v2"; name="Checkout Launch Go/No-Go"; max_steps=35; start_agent="product_01"
    instruction=("Prepare a go/no-go decision for the marketplace checkout launch. Find the launch ticket and blockers, confirm engineering ownership, "
                 "get an engineering-manager approval recorded in Jira, coordinate in Slack, schedule the review, then close the launch ticket.")
    def setup(self,repo,seed):
        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)",("LAUNCH-101","PROJ-LAUNCH","Marketplace checkout launch readiness","Go/no-go ticket. Blocked until payment retry validation and engineering manager approval are recorded.","open","high",None,"product_01"))
        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)",("LAUNCH-102","PROJ-LAUNCH","Validate payment retry telemetry","Engineering validation required before launch review.","open","high","eng_01","product_01"))
        repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)",("LAUNCH-099","PROJ-LAUNCH","Update launch FAQ","Documentation-only task; not a launch blocker.","resolved","low","product_01","product_01"))
        repo.add("INSERT INTO slack_messages VALUES(?,?,?,?,?)",("launch-msg-1","CH-PRODUCT","product_01","Launch review depends on payment retry validation and manager approval.",1))
        rng=random.Random(seed)
        noise=[("Update checkout screenshots","Documentation refresh; not blocking launch."),("Localize FAQ copy","Translation task after launch."),("Archive old experiment","Cleanup task with no launch dependency."),("Review analytics naming","Metrics naming discussion only.")]
        rng.shuffle(noise)
        for idx,(title,desc) in enumerate(noise[:2 + seed % 3], start=1):
            repo.add("INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)",(f"LAUNCH-N{seed%100:02d}-{idx}","PROJ-LAUNCH",title,desc,"open","low","product_01","product_01"))
    def subgoals(self):
        return [
            Subgoal("review","Search and inspect launch readiness"),
            Subgoal("assign","Assign engineering owner",("review",)),
            Subgoal("validation","Engineering validates retry telemetry",("assign",)),
            Subgoal("approval","Engineering manager records approval",("validation",)),
            Subgoal("coordinate","Coordinate go/no-go status in Slack",("approval",)),
            Subgoal("meeting","Schedule launch review",("coordinate",)),
            Subgoal("complete","Close launch readiness ticket",("meeting",)),
        ]
    def verify_subgoal(self,repo,g):
        i=repo.issue("LAUNCH-101")
        if g=="review": return repo.has_action("product_01","jira","search_issues") and repo.has_action("product_01","jira","read_issue","LAUNCH-101")
        if g=="assign": return i["assignee_id"]=="eng_01"
        if g=="validation": return any(c["author_id"]=="eng_01" and "validated" in c["comment"].lower() for c in repo.comments("LAUNCH-101"))
        if g=="approval": return any(c["author_id"]=="mgr_01" and "approved" in c["comment"].lower() for c in repo.comments("LAUNCH-101"))
        if g=="coordinate": return any("LAUNCH-101" in m["text"] and "go/no-go" in m["text"].lower() for m in repo.messages("CH-PRODUCT"))
        if g=="meeting": return any("Go/No-Go" in e["title"] for e in repo.events_for("product_01"))
        if g=="complete": return i["status"]=="resolved"
        return False
