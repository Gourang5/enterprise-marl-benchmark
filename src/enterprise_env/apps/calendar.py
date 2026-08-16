import uuid
from .base import BaseApp
from ..core.models import ToolResult
class CalendarApp(BaseApp):
    name="calendar"
    def _conflict(self,participants,start,end,ignore=None):
        for pid in participants:
            for e in self.repo.events_for(pid):
                if ignore and e["event_id"]==ignore:continue
                if start<e["end_time"] and end>e["start_time"]:return e
        return None
    def execute(self,agent,action,p):
        denied=self.authorize(agent,action)
        if denied:return denied
        if action=="read_calendar":return ToolResult(True,"Calendar read",{"events":self.repo.events_for(agent)},False,False,self.repo.count_action(agent,"calendar","read_calendar",agent)==0)
        if action=="create_event":
            participants=list(dict.fromkeys([agent,*p["participants"]]))
            if any(not self.repo.employee(x) for x in participants):return ToolResult(False,"Unknown participant",{})
            if self._conflict(participants,p["start_time"],p["end_time"]):return ToolResult(False,"Calendar conflict",{})
            eid=p.get("event_id",f"event-{uuid.uuid4().hex[:8]}")
            self.repo.add("INSERT INTO calendar_events VALUES(?,?,?,?,?)",(eid,p["title"],agent,p["start_time"],p["end_time"]))
            for pid in participants:self.repo.add("INSERT INTO event_participants VALUES(?,?)",(eid,pid))
            return ToolResult(True,"Event created",{"event_id":eid},True,True)
        if action=="reschedule_event":
            e=self.repo.get("SELECT * FROM calendar_events WHERE event_id=?",(p["event_id"],))
            if not e:return ToolResult(False,"Event not found",{})
            if e["organizer_id"]!=agent:return ToolResult(False,"Only organizer may reschedule",{})
            participants=self.repo.participants(p["event_id"])
            if self._conflict(participants,p["start_time"],p["end_time"],p["event_id"]):return ToolResult(False,"New time conflicts",{})
            self.repo.execute("UPDATE calendar_events SET start_time=?,end_time=? WHERE event_id=?",(p["start_time"],p["end_time"],p["event_id"]))
            return ToolResult(True,"Event rescheduled",{"event_id":p["event_id"]},True,True)
        return ToolResult(False,"Unknown Calendar action",{})
