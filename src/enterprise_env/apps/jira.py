from .base import BaseApp
from ..core.models import ToolResult

class JiraApp(BaseApp):
    name="jira"
    def execute(self,agent,action,p):
        denied=self.authorize(agent,action)
        if denied:return denied
        if action=="search_issues":
            q=p.get("query","").strip()
            if not q:return ToolResult(False,"query is required",{})
            return ToolResult(True,"Jira search complete",{"results":self.repo.search_issues(q)},False,False,self.repo.count_action(agent,"jira","search_issues",f"query:{q}")==0)
        issue=self.repo.issue(p.get("issue_id",""))
        if not issue:return ToolResult(False,"Issue not found",{})
        if action=="read_issue":return ToolResult(True,"Issue read",{**issue,"comments":self.repo.comments(p["issue_id"])},False,False,self.repo.count_action(agent,"jira","read_issue",p["issue_id"])==0)
        if action=="assign_issue":
            if not self.repo.employee(p["assignee_id"]):return ToolResult(False,"Assignee not found",{})
            if issue["assignee_id"]==p["assignee_id"]:return ToolResult(True,"Already assigned",issue)
            self.repo.execute("UPDATE jira_issues SET assignee_id=? WHERE issue_id=?",(p["assignee_id"],p["issue_id"]))
            return ToolResult(True,"Issue assigned",self.repo.issue(p["issue_id"]),True,True)
        if action=="change_status":
            if p["status"] not in {"open","in_progress","resolved"}:return ToolResult(False,"Invalid status",{})
            if issue["status"]==p["status"]:return ToolResult(True,"Already in status",issue)
            self.repo.execute("UPDATE jira_issues SET status=? WHERE issue_id=?",(p["status"],p["issue_id"]))
            return ToolResult(True,"Status changed",self.repo.issue(p["issue_id"]),True)
        if action=="add_comment":
            self.repo.add("INSERT INTO jira_comments(issue_id,author_id,comment,timestamp) VALUES(?,?,?,?)",(p["issue_id"],agent,p["comment"],self.env.time))
            return ToolResult(True,"Comment added",{},True,bool(p.get("mentions")))
        return ToolResult(False,"Unknown Jira action",{})
