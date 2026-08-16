# RL Interface Reference — Enterprise MARL Benchmark

This document defines the reinforcement learning interface of `EnterpriseEnv` precisely.
All structures are derived from live inspection of the running environment.

---

## 1. Episode Lifecycle

```python
from enterprise_env.factory import make_env
from enterprise_env.core.actions import Action

env = make_env("vendor_onboarding", max_steps=45)

obs, info = env.reset(seed=42)          # deterministic reset
while True:
    action = Action(
        agent_id   = "pm_01",
        app        = "gmail",
        action_type= "search_emails",
        parameters = {"query": "TechNova vendor onboarding"},
    )
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        break

env.close()
```

`reset(seed)` is deterministic: the same integer seed always produces the same initial company state.

---

## 2. Observation Space

`reset()` and `step()` both return an observation dict. **Each call returns the observation
for the agent who just acted (or for the first agent at reset).**

```python
obs: dict = {
    "agent":    dict,   # employee record of the acting agent
    "time":     int,    # current step counter (0-indexed)
    "inbox":    list,   # email headers visible to this agent (bodies require read_email)
    "channels": list,   # Slack channel IDs this agent is a member of
    "calendar": list,   # calendar events for this agent
    "sheets":   list,   # sheets this agent can access, with role
    "task":     dict,   # task id, task name, natural-language instruction
}
```

### Field details

| Field | Type | Notes |
|---|---|---|
| `obs["agent"]["employee_id"]` | `str` | e.g. `"pm_01"` |
| `obs["agent"]["name"]` | `str` | e.g. `"Sarah"` |
| `obs["agent"]["role"]` | `str` | e.g. `"project_manager"` |
| `obs["agent"]["team_id"]` | `str` | e.g. `"team_pm"` |
| `obs["time"]` | `int` | Step count at time of observation |
| `obs["inbox"]` | `list[dict]` | Headers only: `{email_id, from, to, subject, timestamp}` |
| `obs["channels"]` | `list[dict]` | `{channel_id, name}` for each accessible channel |
| `obs["calendar"]` | `list[dict]` | `{event_id, title, attendees, timestamp}` |
| `obs["sheets"]` | `list[dict]` | `{sheet_id, name, role}` — role ∈ {owner, editor, viewer} |
| `obs["task"]["instruction"]` | `str` | Natural-language task description |

**Partial observability is structural:** an agent can only see their own inbox, their own calendar,
and channels they belong to. There is no shared global observation. Email bodies are hidden behind
`read_email`; ticket details behind `read_issue`; sheet cell values behind `read_sheet`.

---

## 3. Action Space

Actions are Python dataclass instances. There is no flat integer or Box space exposed by default —
that encoding is a deliberate integration boundary (see §6).

```python
@dataclass(frozen=True)
class Action:
    agent_id:    str            # must match a valid employee_id
    app:         str            # one of: gmail, slack, jira, calendar, sheets
    action_type: str            # must be a valid action for this app
    parameters:  dict[str, Any] # call-specific key-value pairs
```

### Complete action catalogue

| App | action_type | Required parameters | Writes DB? |
|---|---|---|---|
| `gmail` | `search_emails` | `query: str` | No |
| `gmail` | `read_email` | `email_id: str` | No |
| `gmail` | `send_email` | `to: str, subject: str, body: str` | Yes |
| `slack` | `search_messages` | `query: str` | No |
| `slack` | `read_channel` | `channel_id: str` | No |
| `slack` | `send_message` | `channel_id: str, text: str` | Yes |
| `jira` | `search_issues` | `query: str` | No |
| `jira` | `read_issue` | `issue_id: str` | No |
| `jira` | `assign_issue` | `issue_id: str, assignee: str` | Yes |
| `jira` | `add_comment` | `issue_id: str, text: str` | Yes |
| `jira` | `change_status` | `issue_id: str, status: str` | Yes |
| `calendar` | `read_calendar` | _(none)_ | No |
| `calendar` | `create_event` | `title: str, attendees: list, timestamp: int` | Yes |
| `calendar` | `reschedule_event` | `event_id: str, timestamp: int` | Yes |
| `sheets` | `list_sheets` | _(none)_ | No |
| `sheets` | `read_sheet` | `sheet_id: str` | No |
| `sheets` | `update_cell` | `sheet_id: str, cell: str, value: str` | Yes |
| `sheets` | `append_row` | `sheet_id: str, values: list` | Yes |

---

## 4. Permission Matrix (Action Masking)

Not every agent can call every action. Permission is enforced at step time — an unauthorized
call returns `{"success": false, "message": "Unauthorized: app.action_type"}` and yields a
small step cost with no DB change.

The valid action set per agent is fixed and derived from their role:

| Permission | pm_01 | eng_01 | product_01 | mgr_01 | cs_01 |
|---|:---:|:---:|:---:|:---:|:---:|
| gmail.search_emails | ✓ | ✓ | ✓ | ✓ | ✓ |
| gmail.read_email | ✓ | ✓ | ✓ | ✓ | ✓ |
| gmail.send_email | ✓ | ✓ | ✓ | ✓ | ✓ |
| slack.search_messages | ✓ | ✓ | ✓ | ✓ | ✓ |
| slack.read_channel | ✓ | ✓ | ✓ | ✓ | ✓ |
| slack.send_message | ✓ | ✓ | ✓ | ✓ | ✓ |
| jira.search_issues | ✓ | ✓ | ✓ | ✓ | ✓ |
| jira.read_issue | ✓ | ✓ | ✓ | ✓ | ✓ |
| jira.assign_issue | ✓ | — | ✓ | ✓ | — |
| jira.add_comment | ✓ | ✓ | ✓ | ✓ | ✓ |
| jira.change_status | ✓ | ✓ | — | ✓ | — |
| calendar.read_calendar | ✓ | ✓ | ✓ | ✓ | ✓ |
| calendar.create_event | ✓ | ✓ | ✓ | ✓ | ✓ |
| calendar.reschedule_event | ✓ | — | ✓ | ✓ | — |
| sheets.list_sheets | ✓ | ✓ | ✓ | ✓ | ✓ |
| sheets.read_sheet | ✓ | ✓ | ✓ | ✓ | ✓ |
| sheets.update_cell | ✓ | ✓ | ✓ | ✓ | ✓ |
| sheets.append_row | ✓ | — | ✓ | ✓ | — |

**Total action slots per agent:** pm_01=18, eng_01=15, product_01=17, mgr_01=18, cs_01=14.

This permission table is the **action mask** for conventional RL: before sampling, set logits for
disallowed (app, action_type) pairs to −∞. The mask is static per agent (role-based), not
dynamic per timestep.

---

## 5. Step Return

```python
obs, reward, terminated, truncated, info = env.step(action)
```

| Return value | Type | Meaning |
|---|---|---|
| `obs` | `dict` | Next observation for the agent who just acted |
| `reward` | `float` | Scalar reward for this transition |
| `terminated` | `bool` | `True` if episode succeeded (all subgoals complete) |
| `truncated` | `bool` | `True` if step budget exhausted without success |
| `info` | `dict` | Agent-visible metadata (see below) |

### `info` structure

```python
info: dict = {
    "success": bool,    # True if this step completed the episode
    "message": str,     # human-readable result of the action
    "step":    int,     # current step index
    "eval": {           # evaluator-only state — NOT shown to agents
        "progress":          float,        # fraction of subgoals achieved (0.0–1.0)
        "subgoals":          dict,         # {subgoal_id: bool} — which are achieved
        "reward_components": dict,         # breakdown of reward signal
    }
}
```

`info["eval"]` is **evaluator-only**. A learning agent must not condition on it during execution.
It is available for research analysis, reward shaping experiments, and evaluator debugging.

---

## 6. Reward Signal

Reward is shaped across the episode to provide a learning signal over the dependency-gated DAG.

| Component | Value | Trigger |
|---|---|---|
| Valid tool execution | +0.25 | Any action that succeeds on the DB |
| Subgoal unlocked | +8 × (1/N) | N = total subgoals; fires once per subgoal |
| Coordination bonus | +2.0 | Subgoal that required a prior agent's action |
| Terminal success | +75.0 | All subgoals complete |
| Redundant action | −1.0 | Repeating an action already applied |
| Step cost | −0.10 | Applied every step (efficiency pressure) |
| Timeout penalty | −15.0 | Episode truncated without success |

**Typical episode reward (oracle, vendor_onboarding):** ~90.5 over 10 steps.

The shaped subgoal reward enables credit assignment without requiring the learner to discover
all dependencies from terminal reward alone — this is the primary advantage over sparse
success-only reward.

---

## 7. Termination and Truncation

| Condition | `terminated` | `truncated` | Notes |
|---|---|---|---|
| All subgoals complete | `True` | `False` | Success |
| Step budget exhausted | `False` | `True` | Timeout; max_steps exceeded |
| Mid-episode (normal step) | `False` | `False` | Continue |

Step budgets by difficulty: easy/medium ≈ 25 steps, hard ≈ 35 steps, adversarial ≈ 45 steps.
Task budgets vary: `meeting_conflict` is shorter (4 oracle steps) than `launch_readiness` (17).

---

## 8. Action Encoding for Conventional RL

Standard policy-gradient and Q-learning libraries (RLlib, Stable-Baselines3, CleanRL) expect a
flat action space — an integer index or a vector. `EnterpriseEnv` uses a structured semantic
space instead. Bridging this gap requires an **action encoder** at the integration boundary.

### Recommended encoding pattern

```python
# Build an ordered list of (app, action_type) pairs for this agent
AGENT_ACTIONS = {
    "pm_01": [
        ("gmail", "search_emails"), ("gmail", "read_email"), ("gmail", "send_email"),
        ("slack", "search_messages"), ("slack", "read_channel"), ("slack", "send_message"),
        ("jira", "search_issues"), ("jira", "read_issue"), ("jira", "assign_issue"),
        ("jira", "add_comment"), ("jira", "change_status"),
        ("calendar", "read_calendar"), ("calendar", "create_event"), ("calendar", "reschedule_event"),
        ("sheets", "list_sheets"), ("sheets", "read_sheet"), ("sheets", "update_cell"), ("sheets", "append_row"),
    ],
    # ... similarly for other agents
}

# Discrete action space size per agent
action_space_size = len(AGENT_ACTIONS[agent_id])   # 14–18 depending on agent

# Decode integer → Action
def decode_action(agent_id, action_idx, parameters):
    app, action_type = AGENT_ACTIONS[agent_id][action_idx]
    return Action(agent_id=agent_id, app=app, action_type=action_type, parameters=parameters)
```

**Parameters remain a separate problem.** Most parameters contain entity IDs (email IDs, issue IDs,
sheet IDs) that must be discovered through search actions first. Approaches used in practice:

- **Scripted oracle / template-based**: hard-code entity IDs per task (works for fixed scenarios)
- **Retrieval-augmented**: observe returned IDs from prior search actions and sample from them
- **Language model backbone**: generate parameters as text, then parse into the dict schema

The permission table in §4 directly provides the **action mask** for the discrete space:
mask[i] = 0 if `AGENT_ACTIONS[agent_id][i]` is not in the agent's permission set, else 1.

---

## 9. CTDE: Centralized Training, Decentralized Execution

The benchmark is designed for CTDE-style research:

| Phase | What is centralized | What remains per-agent |
|---|---|---|
| **Training** | Joint replay buffer, global reward, `info["eval"]` subgoal labels | Individual policy networks |
| **Execution** | Nothing — each agent acts on its own obs only | Policy, action selection |

The `info["eval"]` dict is available during training to supply subgoal labels for value
function conditioning, reward shaping, or auxiliary tasks. During deployment, only
`info["success"]` and `info["message"]` are needed.

Multi-agent algorithms that benefit from this structure: MAPPO (shared critic), QMIX
(monotonic value mixing), COMA (counterfactual baseline), IQL (independent learners as
lower bound).

---

## 10. Trajectory Export → Offline RL

`run_episode()` returns a complete trajectory dict. Trajectory data supports:

- **Behavioral Cloning**: learn from oracle or hint-guided trajectories
- **Imitation Learning (GAIL/AIRL)**: use oracle trajectories as demonstrations
- **Offline RL (IQL, CQL)**: train on a fixed dataset of mixed-quality episodes
- **Reward modeling**: learn a verifier approximation from trajectory labels

```python
from enterprise_env.evaluation.runner import run_episode

result = run_episode("vendor_onboarding", seed=42)

# result["trajectory"]: list of step dicts
# Each step: {step, agent, app, action, parameters, result, reward, progress}

# result["success"]: bool
# result["reward"]:  float (total episode reward)
# result["progress"]: float (fraction of subgoals achieved at termination)
```

The `ScenarioFactory` can generate seed-disjoint train/dev/test splits, enabling standard
offline RL train/eval protocols:

```python
factory = ScenarioFactory()
factory.export_dataset("generated_scenarios", train=1000, dev=200, test=500)
# → train.jsonl, dev.jsonl, test.jsonl, manifest.json
```

---

## 11. Research Questions This Interface Opens

| Question | Method | Environment feature used |
|---|---|---|
| Can BC close the 0%→93% hint-guided gap? | Behavioral Cloning on oracle trajectories | Trajectory export, deterministic seed |
| Does CTDE outperform IQL on DAG credit assignment? | MAPPO vs IQL | `info["eval"]["subgoals"]` for critic |
| Does action masking speed convergence? | PPO ± permission mask | Permission table §4 |
| How does distractor density affect sample efficiency? | RL across difficulty levels | easy→adversarial presets |
| Can a policy generalize to unseen seeds? | Train on split 0–999k, test on 2M–3M | Seed-disjoint splits |
| Does shaped subgoal reward outperform sparse? | Compare reward variants | Reward components §6 |
| Can offline RL recover near-oracle behavior? | IQL/CQL on oracle dataset | export_dataset() |
| What is the coordination bottleneck? | Ablate coordination bonus | Per-subgoal reward labels |

---

## 12. PettingZoo AEC Adapter (Experimental)

An experimental AEC-compatible wrapper is available for libraries that consume PettingZoo environments:

```bash
pip install -e ".[rl]"
```

```python
from enterprise_env.rl.pettingzoo_adapter import EnterpriseAECEnv

aec_env = EnterpriseAECEnv(task_name="vendor_onboarding", seed=42)
aec_env.reset()
for agent in aec_env.agent_iter():
    obs, reward, terminated, truncated, info = aec_env.last()
    action = policy(agent, obs)
    aec_env.step(action)
```

The adapter wraps the sequential turn-based execution of `EnterpriseEnv` into the AEC
protocol. Not all AEC-compatible algorithms have been tested.
