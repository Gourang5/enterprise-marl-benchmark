from dataclasses import dataclass

@dataclass(frozen=True)
class ToolResult:
    success: bool
    message: str
    data: dict
    changed: bool = False
    coordination: bool = False
    informative: bool = False
