from __future__ import annotations
import random
from ..core.actions import Action


class RandomPolicy:
    """Valid-but-naive baseline. It samples legal tools and syntactically valid parameters."""
    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def action(self, env) -> Action:
        agent = self.rng.choice(list(env.AGENTS))
        legal = env.legal_tools(agent)
        tool = self.rng.choice(legal)
        app, action = tool.split(".", 1)
        repo = env.repo
        if tool == "gmail.search_emails": p = {"query": self.rng.choice(["launch","incident","customer","auth"])}
        elif tool == "gmail.read_email":
            inbox = repo.inbox_headers(agent); p = {"email_id": self.rng.choice(inbox)["email_id"]} if inbox else {"email_id":"missing"}
        elif tool == "gmail.send_email": p = {"recipient_id": self.rng.choice(list(env.AGENTS)), "subject":"Status update", "body":"Automated status update."}
        elif tool == "slack.search_messages": p = {"query": self.rng.choice(["launch","incident","review"])}
        elif tool in {"slack.read_channel","slack.send_message"}:
            chans = repo.channels_for(agent); cid = self.rng.choice(chans)["channel_id"] if chans else "missing"
            p = {"channel_id":cid} if action == "read_channel" else {"channel_id":cid,"text":"Automated coordination update."}
        elif tool == "jira.search_issues": p = {"query": self.rng.choice(["launch","authentication","review","production"])}
        elif tool in {"jira.read_issue","jira.assign_issue","jira.add_comment","jira.change_status"}:
            issues = repo.all("SELECT issue_id FROM jira_issues"); iid = self.rng.choice(issues)["issue_id"] if issues else "missing"
            if action == "read_issue": p = {"issue_id":iid}
            elif action == "assign_issue": p = {"issue_id":iid,"assignee_id":self.rng.choice(list(env.AGENTS))}
            elif action == "add_comment": p = {"issue_id":iid,"comment":"Automated investigation update."}
            else: p = {"issue_id":iid,"status":self.rng.choice(["open","in_progress","resolved"])}
        elif tool == "calendar.read_calendar": p = {}
        elif tool == "calendar.create_event": p = {"title":"Automated Review","participants":[],"start_time":720,"end_time":780}
        elif tool == "calendar.reschedule_event":
            events = repo.events_for(agent); eid = self.rng.choice(events)["event_id"] if events else "missing"
            p = {"event_id":eid,"start_time":720,"end_time":780}
        else: p = {}
        return Action(agent, app, action, p)
