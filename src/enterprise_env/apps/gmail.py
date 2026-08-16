import uuid
from .base import BaseApp
from ..core.models import ToolResult

class GmailApp(BaseApp):
    name="gmail"
    def execute(self,agent,action,p):
        denied=self.authorize(agent,action)
        if denied:return denied
        if action=="search_emails":
            q=p.get("query","").strip()
            if not q:return ToolResult(False,"query is required",{})
            return ToolResult(True,"Email search complete",{"results":self.repo.search_emails(agent,q)},False,False,self.repo.count_action(agent,"gmail","search_emails",f"query:{q}")==0)
        if action=="read_email":
            e=self.repo.email(p["email_id"])
            if not e or e["recipient_id"]!=agent:return ToolResult(False,"Email not visible",{})
            changed=not bool(e["read"])
            if changed:self.repo.mark_read(p["email_id"])
            return ToolResult(True,"Email read",self.repo.email(p["email_id"]),changed,False,changed)
        if action=="send_email":
            if not self.repo.employee(p["recipient_id"]): return ToolResult(False,"Recipient not found",{})
            eid=p.get("email_id",f"email-{uuid.uuid4().hex[:8]}")
            self.repo.add("INSERT INTO emails VALUES(?,?,?,?,?,?,0)",(eid,agent,p["recipient_id"],p["subject"],p["body"],self.env.time))
            return ToolResult(True,"Email sent",{"email_id":eid},True,True)
        return ToolResult(False,"Unknown Gmail action",{})
