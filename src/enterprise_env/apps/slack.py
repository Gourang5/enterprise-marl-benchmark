import uuid
from .base import BaseApp
from ..core.models import ToolResult

class SlackApp(BaseApp):
    name="slack"
    def execute(self,agent,action,p):
        denied=self.authorize(agent,action)
        if denied:return denied
        visible={x["channel_id"] for x in self.repo.channels_for(agent)}
        if action=="search_messages":
            q=p.get("query","").strip()
            if not q:return ToolResult(False,"query is required",{})
            return ToolResult(True,"Slack search complete",{"results":self.repo.search_messages(agent,q)},False,False,self.repo.count_action(agent,"slack","search_messages",f"query:{q}")==0)
        if p.get("channel_id") not in visible and action in {"read_channel","send_message"}: return ToolResult(False,"Channel not visible",{})
        if action=="read_channel": return ToolResult(True,"Channel read",{"messages":self.repo.messages(p["channel_id"])},False,False,self.repo.count_action(agent,"slack","read_channel",p["channel_id"])==0)
        if action=="send_message":
            mid=p.get("message_id",f"msg-{uuid.uuid4().hex[:8]}")
            self.repo.add("INSERT INTO slack_messages VALUES(?,?,?,?,?)",(mid,p["channel_id"],agent,p["text"],self.env.time))
            return ToolResult(True,"Message sent",{"message_id":mid},True,bool(p.get("mentions")))
        return ToolResult(False,"Unknown Slack action",{})
