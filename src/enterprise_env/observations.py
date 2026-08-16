class ObservationBuilder:
    def build(self,repo,agent,task,time):
        e=repo.employee(agent)
        return {
            "agent":e,
            "time":time,
            "inbox":repo.inbox_headers(agent),
            "channels":repo.channels_for(agent),
            "calendar":repo.events_for(agent),
            "sheets":repo.sheets_for(agent),
            "task":{"id":task.task_id,"name":task.name,"instruction":task.instruction},
        }
