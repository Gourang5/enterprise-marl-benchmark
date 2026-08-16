from dataclasses import dataclass

@dataclass(frozen=True)
class RewardConfig:
    valid_action: float = 0.25
    progress_per_full_subgoal: float = 8.0
    coordination_bonus: float = 2.0
    invalid_action: float = -4.0
    redundant_action: float = -1.0
    step_cost: float = -0.10
    terminal_success: float = 75.0
    timeout: float = -15.0

@dataclass(frozen=True)
class EnvConfig:
    max_steps: int = 30
    db_path: str = ":memory:"
    reward: RewardConfig = RewardConfig()
    strict_turns: bool = False
