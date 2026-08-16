from .config import EnvConfig
from .core.actions import Action
from .core.action_schema import validate_parameters
from .core.models import ToolResult
from .database.repository import CompanyRepository
from .database.seed import seed_company
from .observations import ObservationBuilder
from .rewards.reward import RewardEngine
from .rewards.verifier import TaskVerifier
from .apps.gmail import GmailApp
from .apps.slack import SlackApp
from .apps.jira import JiraApp
from .apps.calendar import CalendarApp
from .apps.sheets import SheetsApp


class EnterpriseEnv:
    """Actor-selected sequential multi-agent enterprise simulator.

    ``step()`` returns two levels of info:
    - Agent-facing keys (``success``, ``message``, ``step``) — safe to expose to policies.
    - Evaluator keys under ``info["eval"]`` (``progress``, ``subgoals``, ``reward_components``)
      — privileged evaluator data for benchmarking/logging only.  RL policies trained on
      this environment MUST NOT condition on ``info["eval"]``; the PettingZoo adapter
      (``EnterpriseAECEnv``) strips it automatically.

    Set ``config.strict_turns = True`` (``EnvConfig`` field, default ``False``) to enforce
    that ``action.agent_id`` must match ``agent_selection``.  Oracle/scripted baselines use
    the default ``False`` to allow free agent scheduling.
    """

    AGENTS = ("pm_01", "eng_01", "product_01", "mgr_01", "cs_01")

    def __init__(self, task, config=None):
        self.task = task
        self.config = config or EnvConfig(max_steps=task.max_steps)
        self.repo = None
        self.time = 0
        self.step_count = 0
        self._agent_selection = "pm_01"
        self.trajectory = []
        self.obs = ObservationBuilder()
        self.verifier = TaskVerifier(task)
        self.reward = RewardEngine(self.verifier, self.config.reward)
        self.apps = {}

    @property
    def agent_selection(self):
        return self._agent_selection

    def reset(self, seed=0):
        if self.repo:
            self.repo.close()
        self.repo = CompanyRepository(self.config.db_path)
        seed_company(self.repo)
        self.task.setup(self.repo, seed)
        self.time = 0
        self.step_count = 0
        self._agent_selection = getattr(self.task, "start_agent", "pm_01")
        self.trajectory = []
        self.reward.reset()
        self._init_apps()
        return self.observe(), {
            "task_id": self.task.task_id,
            "seed": seed,
            "setting": "Walmart Global Tech (fictionalized synthetic instance)",
        }

    def _init_apps(self):
        self.apps = {
            "gmail":    GmailApp(self.repo, self),
            "slack":    SlackApp(self.repo, self),
            "jira":     JiraApp(self.repo, self),
            "calendar": CalendarApp(self.repo, self),
            "sheets":   SheetsApp(self.repo, self),
        }

    def observe(self, agent=None):
        return self.obs.build(self.repo, agent or self.agent_selection, self.task, self.time)

    def legal_tools(self, agent=None):
        agent = agent or self.agent_selection
        out = []
        tools = {
            "gmail":    ["search_emails", "read_email", "send_email"],
            "slack":    ["search_messages", "read_channel", "send_message"],
            "jira":     ["search_issues", "read_issue", "assign_issue", "add_comment", "change_status"],
            "calendar": ["read_calendar", "create_event", "reschedule_event"],
            "sheets":   ["list_sheets", "read_sheet", "update_cell", "append_row"],
        }
        for app, actions in tools.items():
            for a in actions:
                if self.repo.permission(agent, f"{app}.{a}"):
                    out.append(f"{app}.{a}")
        return out

    def _resource_id(self, action):
        p = action.parameters
        if action.action_type == "read_calendar":
            return action.agent_id
        for key in ("email_id", "issue_id", "event_id", "channel_id", "sheet_id", "cell"):
            if key in p:
                return str(p[key])
        if "query" in p:
            return f"query:{p['query']}"
        return None

    def step(self, action: Action):
        if self.repo is None:
            raise RuntimeError("Call reset() first")
        action.validate()
        if action.agent_id not in self.AGENTS:
            raise ValueError(f"Unknown agent {action.agent_id}")

        # Optional strict-turn enforcement (default off for oracle/debug compatibility).
        strict = getattr(self.config, "strict_turns", False)
        if strict and action.agent_id != self._agent_selection:
            raise ValueError(
                f"Strict-turn violation: expected {self._agent_selection}, got {action.agent_id}. "
                "Set config.strict_turns=False to allow free agent scheduling (oracle/debug mode)."
            )

        tool = f"{action.app}.{action.action_type}"
        if action.app not in self.apps:
            result = ToolResult(False, f"Unknown app {action.app}", {})
        else:
            validation_error = validate_parameters(tool, action.parameters)
            result = (
                ToolResult(False, validation_error, {})
                if validation_error
                else self.apps[action.app].execute(action.agent_id, action.action_type, action.parameters)
            )

        self.step_count += 1
        self.time += 1
        resource_id = self._resource_id(action)
        self.repo.log_action(
            self.step_count, action.agent_id, action.app, action.action_type,
            resource_id, result.success, result.changed,
        )

        terminated = self.verifier.complete(self.repo)
        truncated = self.step_count >= self.config.max_steps and not terminated
        reward, components = self.reward.compute(self.repo, result, terminated, truncated)

        # Evaluator/debug state — do NOT expose to RL policies.
        progress = self.verifier.progress(self.repo)
        subgoals_state = self.verifier.subgoals(self.repo)

        # Agent-facing info: only what a legitimate policy should observe.
        agent_info = {
            "success": result.success,
            "message": result.message,
            "step":    self.step_count,
        }
        # Full info dict: agent keys at top level, evaluator keys under "eval".
        info = {
            **agent_info,
            "eval": {
                "progress":          progress,
                "subgoals":          subgoals_state,
                "reward_components": components,
            },
        }

        self.trajectory.append({
            "step":             self.step_count,
            "agent":            action.agent_id,
            "app":              action.app,
            "action":           action.action_type,
            "parameters":       action.parameters,
            "result":           result.__dict__.copy(),
            "reward":           reward,
            "progress":         progress,
            "reward_components":components,
            "subgoals":         subgoals_state.copy(),
        })

        mentions = (
            action.parameters.get("mentions", [])
            if isinstance(action.parameters, dict) else []
        )
        self._agent_selection = (
            mentions[0] if mentions and mentions[0] in self.AGENTS
            else action.agent_id
        )
        return self.observe(), reward, terminated, truncated, info

    def render(self):
        return (
            f"task={self.task.task_id} step={self.step_count} "
            f"suggested_agent={self.agent_selection} "
            f"progress={self.verifier.progress(self.repo):.2f}"
        )

    def close(self):
        if self.repo:
            self.repo.close()
            self.repo = None

    def get_trajectory(self):
        return list(self.trajectory)
