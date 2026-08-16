"""Optional PettingZoo AEC adapter.

Install with: pip install -e '.[rl]'
The core benchmark does not depend on PettingZoo.
"""
from __future__ import annotations
try:
    from pettingzoo import AECEnv
except ImportError as exc:  # pragma: no cover
    AECEnv = object
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from ..factory import make_env
from ..core.actions import Action

class EnterpriseAECEnv(AECEnv):  # pragma: no cover - optional integration
    metadata={"name":"enterprise_marl_v1"}
    def __init__(self,task_name="customer_incident"):
        if _IMPORT_ERROR is not None:
            raise ImportError("Install the rl extra: pip install -e '.[rl]'") from _IMPORT_ERROR
        super().__init__()
        self.core=make_env(task_name)
        self.possible_agents=list(self.core.AGENTS); self.agents=list(self.possible_agents)
        self.agent_selection=self.core.agent_selection
        self.rewards={a:0.0 for a in self.agents};self.terminations={a:False for a in self.agents};self.truncations={a:False for a in self.agents};self.infos={a:{} for a in self.agents}
    def reset(self,seed=None,options=None):
        self.core.reset(seed or 0);self.agents=list(self.possible_agents);self.agent_selection=self.core.agent_selection
        self.rewards={a:0.0 for a in self.agents};self.terminations={a:False for a in self.agents};self.truncations={a:False for a in self.agents};self.infos={a:{} for a in self.agents}
    def observe(self,agent):return self.core.observe(agent)
    def step(self,action):
        if not isinstance(action,Action):raise TypeError("AEC adapter expects enterprise_env.core.actions.Action")
        _,r,done,trunc,info=self.core.step(action);self.rewards={a:0.0 for a in self.agents};self.rewards[action.agent_id]=r
        if done:self.terminations={a:True for a in self.agents}
        if trunc:self.truncations={a:True for a in self.agents}
        self.infos[action.agent_id]=info;self.agent_selection=self.core.agent_selection
    def close(self):self.core.close()
