from dataclasses import dataclass

@dataclass(frozen=True)
class Subgoal:
    id:str
    description:str
    depends_on:tuple[str,...]=()

class BaseTask:
    task_id=""; name=""; instruction=""; max_steps=30; start_agent="pm_01"
    def setup(self,repo,seed): raise NotImplementedError
    def subgoals(self): raise NotImplementedError
    def verify_subgoal(self,repo,g): raise NotImplementedError
    def achieved(self,repo,gid):
        sg=next(x for x in self.subgoals() if x.id==gid)
        if any(not self.achieved(repo,d) for d in sg.depends_on): return False
        return bool(self.verify_subgoal(repo,gid))
    def progress(self,repo):
        gs=self.subgoals(); return sum(self.achieved(repo,x.id) for x in gs)/len(gs)
    def complete(self,repo): return all(self.achieved(repo,x.id) for x in self.subgoals())
