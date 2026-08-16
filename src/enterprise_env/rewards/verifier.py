class TaskVerifier:
    def __init__(self,task):self.task=task
    def progress(self,repo):return self.task.progress(repo)
    def complete(self,repo):return self.task.complete(repo)
    def subgoals(self,repo):return {x.id:self.task.achieved(repo,x.id) for x in self.task.subgoals()}
