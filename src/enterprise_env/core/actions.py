from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Action:
    agent_id: str
    app: str
    action_type: str
    parameters: dict[str, Any]

    def validate(self):
        if not self.agent_id: raise ValueError("agent_id is required")
        if not self.app: raise ValueError("app is required")
        if not self.action_type: raise ValueError("action_type is required")
