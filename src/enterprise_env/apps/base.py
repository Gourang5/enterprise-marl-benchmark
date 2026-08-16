from ..core.models import ToolResult
class BaseApp:
    name=""
    def __init__(self,repo,env): self.repo,self.env=repo,env
    def authorize(self,agent,action):
        if not self.repo.permission(agent,f"{self.name}.{action}"):
            return ToolResult(False,f"Unauthorized: {self.name}.{action}",{})
