import re
import sqlite3


class CompanyRepository:
    def __init__(self, db_path=":memory:"):
        self.conn=sqlite3.connect(db_path)
        self.conn.row_factory=sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
    def close(self): self.conn.close()
    def executescript(self,sql): self.conn.executescript(sql); self.conn.commit()
    def add(self,sql,params=()):
        cur=self.conn.execute(sql,params); self.conn.commit(); return cur.lastrowid
    def execute(self,sql,params=()): self.conn.execute(sql,params); self.conn.commit()
    def get(self,sql,params=()):
        r=self.conn.execute(sql,params).fetchone(); return dict(r) if r else None
    def all(self,sql,params=()): return [dict(r) for r in self.conn.execute(sql,params).fetchall()]
    def employee(self,eid): return self.get("SELECT * FROM employees WHERE employee_id=?",(eid,))
    def employees(self): return self.all("SELECT * FROM employees ORDER BY employee_id")
    def permission(self,eid,p): return bool(self.get("SELECT 1 FROM permissions WHERE employee_id=? AND permission=?",(eid,p)))
    def email(self,eid): return self.get("SELECT * FROM emails WHERE email_id=?",(eid,))
    def inbox_headers(self,eid):
        return self.all("SELECT email_id,sender_id,subject,timestamp,read FROM emails WHERE recipient_id=? ORDER BY timestamp DESC,email_id",(eid,))
    def unread_emails(self,eid): return self.inbox_headers(eid)

    @staticmethod
    def _query_terms(q):
        # Enterprise search should tolerate natural-language queries rather than
        # requiring the entire query to appear as one contiguous substring.
        # Keep tokens conservative so IDs such as INC-421 and LAUNCH-101 survive.
        return [x for x in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", q.casefold()) if len(x) >= 2]

    @classmethod
    def _search_score(cls,q,*fields):
        query=q.casefold().strip()
        text=" ".join(str(x or "") for x in fields).casefold()
        terms=cls._query_terms(query)
        if not query or not terms:return 0
        phrase_bonus=8 if query in text else 0
        hits=sum(1 for term in terms if term in text)
        # Require at least one lexical hit. Ranking prefers rows matching more
        # query concepts and exact phrases, which keeps distractors below the target.
        return phrase_bonus + hits

    def search_emails(self,eid,q):
        rows=self.all("SELECT email_id,sender_id,subject,body,timestamp,read FROM emails WHERE recipient_id=?",(eid,))
        ranked=[]
        for row in rows:
            score=self._search_score(q,row.get("subject"),row.get("body"),row.get("sender_id"))
            if score:
                public={k:v for k,v in row.items() if k!="body"}
                ranked.append((score,int(row.get("timestamp",0)),public))
        ranked.sort(key=lambda x:(-x[0],-x[1],x[2]["email_id"]))
        return [row for _,_,row in ranked[:10]]

    def mark_read(self,eid): self.execute("UPDATE emails SET read=1 WHERE email_id=?",(eid,))
    def issue(self,iid): return self.get("SELECT * FROM jira_issues WHERE issue_id=?",(iid,))
    def search_issues(self,q):
        rows=self.all("SELECT issue_id,title,description,status,priority,assignee_id,reporter_id FROM jira_issues")
        ranked=[]
        priority_rank={"P0":0,"high":1,"P1":2,"P2":3,"P3":4,"low":5}
        for row in rows:
            score=self._search_score(q,row.get("issue_id"),row.get("title"),row.get("description"))
            if score:
                public={k:v for k,v in row.items() if k!="description"}
                ranked.append((score,priority_rank.get(str(row.get("priority")),9),row["issue_id"],public))
        ranked.sort(key=lambda x:(-x[0],x[1],x[2]))
        return [row for _,_,_,row in ranked[:10]]

    def comments(self,iid): return self.all("SELECT * FROM jira_comments WHERE issue_id=? ORDER BY comment_id",(iid,))
    def channels_for(self,eid): return self.all("SELECT c.* FROM channels c JOIN channel_members m ON m.channel_id=c.channel_id WHERE m.employee_id=?",(eid,))
    def messages(self,cid): return self.all("SELECT * FROM slack_messages WHERE channel_id=? ORDER BY timestamp,message_id",(cid,))
    def search_messages(self,eid,q):
        rows=self.all("SELECT m.* FROM slack_messages m JOIN channel_members cm ON cm.channel_id=m.channel_id WHERE cm.employee_id=?",(eid,))
        ranked=[]
        for row in rows:
            score=self._search_score(q,row.get("text"),row.get("channel_id"),row.get("sender_id"))
            if score: ranked.append((score,int(row.get("timestamp",0)),row))
        ranked.sort(key=lambda x:(-x[0],-x[1],x[2]["message_id"]))
        return [row for _,_,row in ranked[:10]]

    def events_for(self,eid): return self.all("SELECT e.* FROM calendar_events e JOIN event_participants p ON p.event_id=e.event_id WHERE p.employee_id=? ORDER BY e.start_time",(eid,))
    def participants(self,event_id): return [x["employee_id"] for x in self.all("SELECT employee_id FROM event_participants WHERE event_id=?",(event_id,))]

    def sheets_for(self,eid):
        return self.all("SELECT s.sheet_id,s.name,m.role FROM spreadsheets s JOIN sheet_members m ON m.sheet_id=s.sheet_id WHERE m.employee_id=? ORDER BY s.sheet_id",(eid,))
    def sheet_cells(self,sheet_id):
        return self.all("SELECT cell,value,updated_by,updated_at FROM sheet_cells WHERE sheet_id=? ORDER BY cell",(sheet_id,))
    def sheet_cell(self,sheet_id,cell):
        r=self.get("SELECT value,updated_by,updated_at FROM sheet_cells WHERE sheet_id=? AND cell=?",(sheet_id,cell))
        return r
    def upsert_sheet_cell(self,sheet_id,cell,value,updated_by,updated_at=0):
        self.execute("INSERT INTO sheet_cells(sheet_id,cell,value,updated_by,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(sheet_id,cell) DO UPDATE SET value=excluded.value,updated_by=excluded.updated_by,updated_at=excluded.updated_at",(sheet_id,cell,value,updated_by,updated_at))
    def next_sheet_row(self,sheet_id):
        import re as _re
        rows=[]
        for x in self.sheet_cells(sheet_id):
            m=_re.search(r"(\d+)$",x["cell"])
            if m: rows.append(int(m.group(1)))
        return max(rows,default=0)+1

    def log_action(self,step,agent,app,action,resource_id,success,changed):
        self.add("INSERT INTO audit_log(step,agent_id,app,action_type,resource_id,success,changed) VALUES(?,?,?,?,?,?,?)",(step,agent,app,action,resource_id,int(success),int(changed)))
    def has_action(self,agent,app,action,resource_id=None):
        if resource_id is None:
            return bool(self.get("SELECT 1 FROM audit_log WHERE agent_id=? AND app=? AND action_type=? AND success=1",(agent,app,action)))
        return bool(self.get("SELECT 1 FROM audit_log WHERE agent_id=? AND app=? AND action_type=? AND resource_id=? AND success=1",(agent,app,action,resource_id)))
    def count_action(self,agent,app,action,resource_id=None):
        if resource_id is None:
            r=self.get("SELECT count(*) n FROM audit_log WHERE agent_id=? AND app=? AND action_type=? AND success=1",(agent,app,action))
        else:
            r=self.get("SELECT count(*) n FROM audit_log WHERE agent_id=? AND app=? AND action_type=? AND resource_id=? AND success=1",(agent,app,action,resource_id))
        return int(r["n"] if r else 0)
