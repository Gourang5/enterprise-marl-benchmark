"""Experimental PettingZoo AEC adapter for enterprise_env.

Status: EXPERIMENTAL — not a production-grade AEC implementation.

This adapter wraps EnterpriseEnv in the PettingZoo AEC interface to allow
compatibility with standard MARL training libraries. Known limitations:

1. Action space: agents communicate via structured ``Action`` objects, not
   flat numpy arrays. ``action_space(agent)`` returns a ``gymnasium.spaces.Dict``
   that describes valid tool/parameter combinations but is not exhaustive.
   Standard array-based RL algorithms need a custom action encoder.

2. Turn enforcement: ``step()`` raises ``ValueError`` if the action's
   ``agent_id`` does not match ``agent_selection``.  Use ``EnterpriseEnv``
   directly (``strict_turns=False``, the default) for oracle/scripted baselines
   that schedule agents freely.

3. API compliance: ``pettingzoo.test.api_test`` requires gymnasium spaces and
   may surface further gaps. Run it with ``render_mode=None`` and check the
   output before claiming full PettingZoo compliance.

Install with: pip install -e '.[rl]'
The core benchmark does NOT depend on PettingZoo.
"""
from __future__ import annotations

try:
    from pettingzoo import AECEnv
except ImportError as exc:  # pragma: no cover
    AECEnv = object
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

try:
    import gymnasium.spaces as _spaces

    def _make_action_space():
        return _spaces.Dict({
            "agent_id":   _spaces.Text(min_length=1, max_length=32),
            "tool":       _spaces.Text(min_length=3, max_length=64),
            "parameters": _spaces.Dict({}),  # open-ended; validated by env.step()
        })

    def _make_observation_space():
        return _spaces.Dict({
            "agent":    _spaces.Dict({}),
            "inbox":    _spaces.Sequence(_spaces.Dict({})),
            "channels": _spaces.Sequence(_spaces.Dict({})),
            "calendar": _spaces.Sequence(_spaces.Dict({})),
            "sheets":   _spaces.Sequence(_spaces.Dict({})),
            "task":     _spaces.Dict({}),
            "time":     _spaces.Discrete(10_000),
        })
except ImportError:
    def _make_action_space():
        raise ImportError("gymnasium is required for action_space(); pip install gymnasium")

    def _make_observation_space():
        raise ImportError("gymnasium is required for observation_space(); pip install gymnasium")

from ..factory import make_env
from ..core.actions import Action


class EnterpriseAECEnv(AECEnv):  # pragma: no cover - optional integration
    """Experimental PettingZoo AEC adapter. See module docstring for limitations."""

    metadata = {"name": "enterprise_marl_v1", "is_parallelizable": False}

    def __init__(self, task_name: str = "customer_incident"):
        if _IMPORT_ERROR is not None:
            raise ImportError(
                "Install the rl extra: pip install -e '.[rl]'"
            ) from _IMPORT_ERROR
        super().__init__()
        self.core = make_env(task_name)
        self.possible_agents = list(self.core.AGENTS)
        self.agents = list(self.possible_agents)
        self.agent_selection = self.core.agent_selection
        self.rewards = {a: 0.0 for a in self.agents}
        self.terminations = {a: False for a in self.agents}
        self.truncations = {a: False for a in self.agents}
        self.infos = {a: {} for a in self.agents}
        self._last_eval_info: dict = {}

    # ── PettingZoo spaces ──────────────────────────────────────────────────
    def action_space(self, agent: str):
        return _make_action_space()

    def observation_space(self, agent: str):
        return _make_observation_space()

    # ── PettingZoo lifecycle ───────────────────────────────────────────────
    def reset(self, seed=None, options=None):
        self.core.reset(seed or 0)
        self.agents = list(self.possible_agents)
        self.agent_selection = self.core.agent_selection
        self.rewards = {a: 0.0 for a in self.agents}
        self.terminations = {a: False for a in self.agents}
        self.truncations = {a: False for a in self.agents}
        self.infos = {a: {} for a in self.agents}
        self._last_eval_info = {}

    def observe(self, agent: str):
        return self.core.observe(agent)

    def step(self, action: Action):
        if not isinstance(action, Action):
            raise TypeError(
                "EnterpriseAECEnv.step() expects an enterprise_env.core.actions.Action object. "
                "Construct it with Action(agent_id, app, action_type, parameters)."
            )
        # Strict AEC turn enforcement
        if action.agent_id != self.agent_selection:
            raise ValueError(
                f"AEC turn violation: agent_selection='{self.agent_selection}' "
                f"but action.agent_id='{action.agent_id}'. "
                "The acting agent must match agent_selection."
            )
        _, r, done, trunc, info = self.core.step(action)
        self.rewards = {a: 0.0 for a in self.agents}
        self.rewards[action.agent_id] = r
        if done:
            self.terminations = {a: True for a in self.agents}
        if trunc:
            self.truncations = {a: True for a in self.agents}
        # Strip evaluator state from agent-facing infos to prevent leakage.
        self._last_eval_info = info.pop("eval", {})
        self.infos[action.agent_id] = info  # only success/message/step
        self.agent_selection = self.core.agent_selection

    def close(self):
        self.core.close()
