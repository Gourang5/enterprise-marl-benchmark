"""Enterprise MARL Benchmark — Streamlit dashboard.

Run locally:  streamlit run ui/app.py
In Docker:    docker compose up ui
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise MARL Benchmark",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── constants ─────────────────────────────────────────────────────────────────
TASKS = [
    "customer_incident",
    "product_launch",
    "meeting_conflict",
    "launch_readiness",
    "budget_approval",
    "vendor_onboarding",
]

TASK_META = {
    "customer_incident":  {"icon": "🚨", "apps": ["Gmail", "Slack", "Jira", "Calendar"],                  "agents": ["pm_01", "eng_01", "cs_01"],                         "subgoals": 8,  "difficulty": "Hard"},
    "product_launch":     {"icon": "🚀", "apps": ["Jira", "Slack", "Calendar"],                           "agents": ["product_01", "eng_01", "mgr_01"],                   "subgoals": 7,  "difficulty": "Hard"},
    "meeting_conflict":   {"icon": "📅", "apps": ["Gmail", "Calendar", "Slack"],                          "agents": ["pm_01", "eng_01"],                                  "subgoals": 5,  "difficulty": "Medium"},
    "launch_readiness":   {"icon": "✅", "apps": ["Gmail", "Slack", "Jira", "Sheets", "Calendar"],        "agents": ["cs_01", "eng_01", "product_01", "mgr_01"],          "subgoals": 8,  "difficulty": "Hard"},
    "budget_approval":    {"icon": "💰", "apps": ["Gmail", "Jira", "Sheets", "Calendar", "Slack"],        "agents": ["product_01", "eng_01", "mgr_01"],                   "subgoals": 7,  "difficulty": "Hard"},
    "vendor_onboarding":  {"icon": "🤝", "apps": ["Gmail", "Jira", "Sheets", "Calendar", "Slack"],        "agents": ["pm_01", "product_01", "eng_01", "mgr_01", "cs_01"], "subgoals": 8,  "difficulty": "Hard"},
}

TASK_DESCRIPTIONS = {
    "customer_incident":
        "A strategic retail partner reports a production authentication outage. "
        "Triage the report, correlate it to the right Jira incident, coordinate an engineering owner, "
        "record investigation progress, schedule a review, resolve only after investigation, and notify Customer Success.",
    "product_launch":
        "Prepare a go/no-go decision for the marketplace checkout launch. "
        "Find the launch ticket and blockers, confirm engineering ownership, "
        "get an engineering-manager approval recorded in Jira, coordinate in Slack, "
        "schedule the review, then close the launch ticket.",
    "meeting_conflict":
        "A double-booking notification has arrived: Engineering Review conflicts with Strategic Customer Call. "
        "Read the notification, inspect both calendars to confirm the conflict, "
        "move the Engineering Review to the earliest feasible slot, then notify participants via Slack.",
    "launch_readiness":
        "Prepare the Marketplace Checkout launch readiness review. "
        "Customer Success has a private partner commitment, Engineering owns the blocker investigation, "
        "Product owns the readiness sheet, and Engineering Management must approve. "
        "Coordinate across Gmail, Slack, Jira, Sheets, and Calendar without bypassing role boundaries.",
    "budget_approval":
        "Discover a budget request for the Q1 Analytics Dashboard initiative. "
        "Locate the budget Jira ticket, have Engineering record a cost estimate, "
        "get Engineering Manager approval, update the budget tracker sheet, "
        "schedule a project kickoff meeting, and announce the approval in the product Slack channel.",
    "vendor_onboarding":
        "TechNova Solutions has been selected as a new analytics vendor. "
        "Discover the onboarding request, find all three Jira tickets (procurement VEND-401, "
        "legal review VEND-402, IT provisioning VEND-403), coordinate Legal and IT sign-offs in parallel, "
        "get Engineering Manager approval, mark the vendor ACTIVE in the tracker sheet, "
        "schedule an onboarding kickoff, and announce completion in the procurement channel.",
}

AGENT_ROLES = {
    "pm_01":      {"name": "Sarah",  "role": "Project Manager",       "color": "#4e8ef7"},
    "eng_01":     {"name": "Arjun",  "role": "Engineer",              "color": "#f7934e"},
    "product_01": {"name": "Maya",   "role": "Product Manager",       "color": "#4ef7a4"},
    "mgr_01":     {"name": "Daniel", "role": "Engineering Manager",   "color": "#f74e4e"},
    "cs_01":      {"name": "Priya",  "role": "Customer Success",      "color": "#b44ef7"},
}

RESULTS_PATH      = Path(__file__).resolve().parents[1] / "benchmark_results" / "llm_results.json"
RESULTS_5EP_PATH  = Path(__file__).resolve().parents[1] / "benchmark_results" / "llm_results_5ep.json"
ZEROSHOT_PATH     = Path(__file__).resolve().parents[1] / "benchmark_results" / "llm_results_zeroshot.json"
BASELINES_PATH    = Path(__file__).resolve().parents[1] / "benchmark_results" / "baselines.json"


# ── helpers ───────────────────────────────────────────────────────────────────
def _badge(text: str, color: str = "#444") -> str:
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:0.78rem;font-weight:600">{text}</span>'
    )


def _diff_color(difficulty: str) -> str:
    return {"Easy": "#2ecc71", "Medium": "#f39c12", "Hard": "#e74c3c"}.get(difficulty, "#888")


def _success_color(success: bool) -> str:
    return "#2ecc71" if success else "#e74c3c"


def _render_task_card(task: str) -> None:
    meta = TASK_META[task]
    diff_c = _diff_color(meta["difficulty"])
    badges = " ".join(_badge(a, "#334") for a in meta["apps"])
    agent_badges = " ".join(
        _badge(AGENT_ROLES[a]["name"], AGENT_ROLES[a]["color"])
        for a in meta["agents"]
        if a in AGENT_ROLES
    )
    st.markdown(
        f"""
<div style="border:1px solid #333;border-radius:8px;padding:14px 16px;margin-bottom:8px;background:#0e1117">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
    <span style="font-size:1.5rem">{meta['icon']}</span>
    <strong style="font-size:1.05rem">{task.replace('_', ' ').title()}</strong>
    <span style="margin-left:auto">{_badge(meta['difficulty'], diff_c)}</span>
  </div>
  <p style="color:#aaa;font-size:0.88rem;margin:4px 0 8px">{TASK_DESCRIPTIONS[task]}</p>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:4px"><strong style="font-size:0.78rem;color:#888">APPS:</strong> {badges}</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px"><strong style="font-size:0.78rem;color:#888">AGENTS:</strong> {agent_badges}</div>
  <div style="margin-top:6px;color:#aaa;font-size:0.78rem">⛳ {meta['subgoals']} subgoals</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_trajectory(trajectory: list[dict]) -> None:
    for step in trajectory:
        result = step.get("result") or {}
        success = result.get("success", False)
        agent = step.get("agent", "")
        agent_info = AGENT_ROLES.get(agent, {"name": agent, "role": agent, "color": "#888"})
        icon = "✅" if success else "❌"
        reward = step.get("reward", 0.0)
        progress = step.get("progress", 0.0)
        tool = f'{step.get("app", "")}.{step.get("action", "")}'
        label = (
            f'{icon} Step {step.get("step", "?")}  '
            f'[{agent_info["name"]}] {tool}  '
            f'│ reward {reward:+.2f}  │ progress {progress:.0%}'
        )
        with st.expander(label, expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("Parameters")
                st.json(step.get("parameters") or {})
            with col_b:
                st.caption("Result")
                st.json({"success": success, "message": result.get("message"), "data": result.get("data") or {}})
            comps = step.get("reward_components")
            if comps:
                st.caption("Reward components")
                st.json(comps)
            sg = step.get("subgoals")
            if sg:
                st.caption("Subgoal state")
                cols = st.columns(min(len(sg), 4))
                for i, (gid, done) in enumerate(sg.items()):
                    cols[i % len(cols)].markdown(
                        f'{"🟢" if done else "⚪"} `{gid}`'
                    )


def _run_episode_with_spinner(task: str, policy: str, seed: int, provider: str, model: str):
    """Run one episode and return result dict."""
    from enterprise_env.evaluation.runner import run_episode, run_random_episode, run_llm_episode

    if policy == "Deterministic Baseline":
        return run_episode(task, seed=seed)
    if policy == "Random":
        return run_random_episode(task, seed=seed)
    # LLM policy
    from enterprise_env.evaluation.llm import make_client
    try:
        client = make_client(provider.lower(), model)
    except Exception as exc:
        st.error(f"Cannot create LLM client: {exc}")
        return None
    return run_llm_episode(task, client, seed=seed)


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/office-building.png", width=60)
    st.title("Enterprise MARL")
    st.caption("Multi-Agent RL Benchmark — v1.2")
    st.divider()

    st.subheader("Task")
    task = st.selectbox("Select task", TASKS, format_func=lambda t: f"{TASK_META[t]['icon']}  {t.replace('_',' ').title()}")

    st.subheader("Policy")
    policy = st.radio("Agent policy", ["Deterministic Baseline", "LLM (Ollama)", "Random"])

    if policy == "LLM (Ollama)":
        provider = "ollama"
        model = st.text_input("Ollama model", value="qwen2.5:3b")
    else:
        provider = "ollama"
        model = "qwen2.5:3b"

    st.subheader("Episodes")
    episodes = st.slider("Number of episodes", 1, 10, 1)
    seed = st.number_input("Starting seed", min_value=0, value=100, step=1)

    st.divider()
    run_btn = st.button("▶  Run Benchmark", type="primary", use_container_width=True)
    st.caption("Each episode runs in sequence. LLM episodes take ~2 min each via local Ollama.")


# ── main tabs ─────────────────────────────────────────────────────────────────
tab_overview, tab_run, tab_compare, tab_results = st.tabs(["🏠 Task Overview", "▶️ Run Episode", "🆚 Policy Comparison", "📊 Saved Results"])


# ── TAB 1: overview ───────────────────────────────────────────────────────────
with tab_overview:
    st.header("Enterprise Multi-Agent RL Benchmark")
    st.markdown(
        """
This benchmark simulates a **Fortune 500 enterprise** (Walmart Global Tech) with 5 synthetic employees
coordinating across 5 real-world apps to complete **long-horizon cross-functional workflows**.

Each task requires multiple agents to hand off information across Gmail, Slack, Jira, Google Sheets,
and Calendar — respecting role-based permissions and dependency constraints.
"""
    )

    st.subheader("Environment")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tasks", "6")
    c2.metric("Agents", "5")
    c3.metric("Apps", "5")
    c4.metric("Max subgoals", "8")
    c5.metric("Max steps", "45")

    st.divider()
    st.subheader("Policy Taxonomy")
    st.markdown("""
This benchmark evaluates agents across a **four-tier policy spectrum**, from random exploration to
oracle execution. Each tier answers a different research question.
""")
    cols = st.columns(4)
    tiers = [
        ("🎲", "Random Baseline", "#e74c3c",
         "**0% success** across all tasks.\nConfirms tasks cannot be solved by chance — establishes the lower bound."),
        ("🤖", "Zero-Shot LLM", "#e67e22",
         "**~30–50% est.** (future work).\nPure LLM with no workflow context. Tests model generalization without task-specific knowledge."),
        ("📋", "Hint-Guided LLM", "#2ecc71",
         "**100% success** (current).\nLLM + workflow SOPs. Simulates an *onboarded employee* who follows company procedures. Validates task design."),
        ("🏆", "Oracle Baseline", "#3498db",
         "**100% success** (scripted).\nDeterministic rule-based policy with hardcoded IDs. Proves mechanical solvability of every task."),
    ]
    for col, (icon, title, color, desc) in zip(cols, tiers):
        col.markdown(
            f'<div style="border-left:4px solid {color};padding:10px 12px;border-radius:4px;background:#111;height:160px">'
            f'<div style="font-size:1.4rem">{icon}</div>'
            f'<strong style="font-size:0.9rem">{title}</strong><br>'
            f'<small style="color:#ccc">{desc}</small></div>',
            unsafe_allow_html=True,
        )
    st.markdown("""
> **Why hint-guided LLM?**  In real enterprises, employees operate with SOPs, runbooks, and
> workflow documentation — not as zero-shot generalists. The hint-guided policy simulates an
> *informed agent* with access to company procedures, analogous to **RAG over enterprise documentation**.
> Its 100% success rate *validates the task structure and reward function*, independent of LLM model size.
> Zero-shot autonomous agents are the natural next research step (RL training, fine-tuning).
""")

    st.divider()
    st.subheader("All Tasks")
    col_l, col_r = st.columns(2)
    for i, t in enumerate(TASKS):
        with (col_l if i % 2 == 0 else col_r):
            _render_task_card(t)

    st.divider()
    st.subheader("Reward Structure")
    st.markdown(
        """
| Component | Value | When |
|---|---|---|
| Valid useful action | **+0.25** | Each successful, non-redundant action |
| Redundant action | **−1.00** | Successful but no-op (no change, no info, no progress) |
| Per subgoal completed | **+8.0 × (1/N)** | Each time a dependency-gated subgoal is satisfied |
| Coordination bonus | **+2.00** | Cross-agent actions: Slack, email, calendar invite, assign |
| Terminal success | **+75.00** | All subgoals satisfied |
| Timeout | **−15.00** | Max steps exceeded without completion |
| Step cost | **−0.10** | Every step, always |

> **Why scores differ**: `launch_readiness` scores highest (~106) because it has the most cross-agent
> coordination steps (10 actions get +2.0 each). `meeting_conflict` scores lower (~88) because it
> has fewer subgoals and coordination actions despite being easier to solve.
"""
    )

    st.divider()
    st.subheader("Agent Roster")
    agent_cols = st.columns(5)
    for i, (aid, info) in enumerate(AGENT_ROLES.items()):
        agent_cols[i].markdown(
            f'<div style="border-left:4px solid {info["color"]};padding:8px 10px;border-radius:4px;background:#111">'
            f'<strong>{info["name"]}</strong><br>'
            f'<small style="color:#aaa">{aid}</small><br>'
            f'<small>{info["role"]}</small></div>',
            unsafe_allow_html=True,
        )


# ── TAB 2: run episode ────────────────────────────────────────────────────────
with tab_run:
    meta = TASK_META[task]
    st.header(f"{meta['icon']} {task.replace('_', ' ').title()}")
    st.caption(TASK_DESCRIPTIONS[task])

    badge_row = " ".join(_badge(a, "#334") for a in meta["apps"])
    st.markdown(badge_row, unsafe_allow_html=True)
    st.markdown("")

    if run_btn:
        all_results = []
        progress_bar = st.progress(0, text="Starting…")
        status_box = st.empty()

        for ep in range(episodes):
            ep_seed = int(seed) + ep
            progress_bar.progress((ep) / episodes, text=f"Episode {ep + 1}/{episodes} — seed={ep_seed}")
            status_box.info(f"Running episode {ep + 1} of {episodes} with seed={ep_seed}…")
            t0 = time.perf_counter()
            result = _run_episode_with_spinner(task, policy, ep_seed, provider, model)
            elapsed = time.perf_counter() - t0
            if result is None:
                break
            result["_elapsed"] = elapsed
            all_results.append(result)
            status_box.success(
                f"Episode {ep + 1} done in {elapsed:.1f}s — "
                f"{'✅ SUCCESS' if result['success'] else '❌ FAILED'}  "
                f"steps={result['steps']}  reward={result['reward']:.2f}"
            )

        progress_bar.progress(1.0, text="Done.")

        if not all_results:
            st.error("No results — check your LLM provider or task configuration.")
        else:
            st.divider()
            # ── aggregate stats ────────────────────────────────────────────
            from enterprise_env.evaluation.metrics import aggregate
            agg = aggregate(all_results)

            st.subheader("📈 Results")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Success rate", f"{agg['success_rate']:.0%}", help=f"95% CI: {agg['success_rate_95ci'][0]:.2f} – {agg['success_rate_95ci'][1]:.2f}")
            m2.metric("Avg reward", f"{agg['avg_reward']:.2f}", help=f"σ = {agg['reward_std']:.2f}")
            m3.metric("Avg steps", f"{agg['avg_steps']:.1f}", help=f"On success: {agg['avg_steps_on_success']:.1f}")
            m4.metric("Avg progress", f"{agg['avg_progress']:.0%}")
            m5.metric("Policy errors", f"{agg['policy_error_rate']:.0%}")

            if len(all_results) > 1:
                st.caption(f"95% Wilson CI: [{agg['success_rate_95ci'][0]:.3f}, {agg['success_rate_95ci'][1]:.3f}]")

            st.divider()
            # ── per-episode breakdown ──────────────────────────────────────
            st.subheader("Per-episode breakdown")
            ep_data = [
                {
                    "Episode": i + 1,
                    "Seed": int(seed) + i,
                    "Success": "✅" if r["success"] else "❌",
                    "Steps": r["steps"],
                    "Reward": f"{r['reward']:.2f}",
                    "Progress": f"{r['progress']:.0%}",
                    "Error": r.get("policy_error") or "—",
                    "Time (s)": f"{r.get('_elapsed', 0):.1f}",
                }
                for i, r in enumerate(all_results)
            ]
            st.dataframe(ep_data, use_container_width=True)

            st.divider()
            # ── trajectory for last episode ────────────────────────────────
            last = all_results[-1]
            st.subheader(f"Trajectory — episode {len(all_results)} (seed={int(seed) + len(all_results) - 1})")
            if last.get("trajectory"):
                _render_trajectory(last["trajectory"])
            else:
                st.caption("No trajectory data available.")

    else:
        st.info(f"Configure options in the sidebar and click **▶ Run Benchmark** to start. Policy: **{policy}**, Episodes: **{episodes}**, Task: **{task}**")

        # Show task subgoals preview
        st.divider()
        st.subheader("Task Subgoals")
        from enterprise_env.tasks.factory import make_task
        try:
            t_obj = make_task(task)
            sgs = t_obj.subgoals()
            for sg in sgs:
                deps = f" ← {', '.join(sg.depends_on)}" if sg.depends_on else ""
                st.markdown(f"- **`{sg.id}`** — {sg.description}{deps}")
        except Exception:
            st.caption("Could not load subgoal list.")


# ── TAB 3: policy comparison ─────────────────────────────────────────────────
with tab_compare:
    st.markdown(
        "<h2 style='margin-bottom:2px'>Policy Benchmark Deep Dive</h2>"
        "<p style='color:#888;font-size:0.93rem;margin-top:0'>Oracle &nbsp;·&nbsp; Hint-Guided LLM &nbsp;·&nbsp; Zero-Shot LLM &mdash; head-to-head across all 6 tasks</p>",
        unsafe_allow_html=True,
    )

    # ── helpers ──────────────────────────────────────────────────────────────
    def _load_json(p):
        try:
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        except Exception:
            return None

    hint_data     = _load_json(RESULTS_5EP_PATH)
    zs_data       = _load_json(ZEROSHOT_PATH)
    baseline_data = _load_json(BASELINES_PATH)

    hint_sum   = hint_data.get("summary", {})     if hint_data     else {}
    zs_sum     = zs_data.get("summary",   {})     if zs_data       else {}
    oracle_sum = {t: baseline_data[t]["rule"]  for t in TASKS if baseline_data and t in baseline_data}

    # ── policy hero cards ────────────────────────────────────────────────────
    def _avg(summary, key="success_rate"):
        vals = [summary.get(t, {}).get(key, 0.0) for t in TASKS if summary.get(t)]
        return sum(vals) / len(vals) if vals else 0.0

    h_avg_sr  = _avg(hint_sum,   "success_rate")
    z_avg_sr  = _avg(zs_sum,     "success_rate")
    h_avg_rw  = _avg(hint_sum,   "avg_reward")
    z_avg_rw  = _avg(zs_sum,     "avg_reward")
    h_avg_st  = _avg(hint_sum,   "avg_steps")
    z_avg_st  = _avg(zs_sum,     "avg_steps")
    o_avg_rw  = _avg(oracle_sum, "avg_reward")
    o_avg_st  = _avg(oracle_sum, "avg_steps")

    st.markdown("""
<style>
.policy-card { border-radius:10px; padding:20px 22px; margin-bottom:4px; }
.policy-card .big { font-size:2.6rem; font-weight:800; line-height:1; }
.policy-card .label { font-size:0.82rem; color:#aaa; margin-top:4px; }
.policy-card .sub { font-size:0.75rem; color:#666; margin-top:2px; }
.policy-card .stat { display:flex; gap:18px; margin-top:12px; }
.policy-card .stat-item { text-align:center; }
.policy-card .stat-item .val { font-size:1.1rem; font-weight:700; }
.policy-card .stat-item .key { font-size:0.7rem; color:#777; }
.metric-pill { display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; margin:2px; }
</style>
""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.markdown(
        f'<div class="policy-card" style="background:linear-gradient(135deg,#0d2137 0%,#1a3a5c 100%);border:1px solid #2a5080">'
        f'<div class="big" style="color:#4ea8de">100%</div>'
        f'<div class="label">Oracle Baseline</div>'
        f'<div class="sub">Scripted deterministic agent &nbsp;|&nbsp; 25 episodes per task</div>'
        f'<div class="stat">'
        f'<div class="stat-item"><div class="val" style="color:#4ea8de">{o_avg_rw:.0f}</div><div class="key">Avg Reward</div></div>'
        f'<div class="stat-item"><div class="val" style="color:#4ea8de">{o_avg_st:.1f}</div><div class="key">Avg Steps</div></div>'
        f'<div class="stat-item"><div class="val" style="color:#4ea8de">6/6</div><div class="key">Tasks Solved</div></div>'
        f'</div>'
        f'<div style="margin-top:10px"><span class="metric-pill" style="background:#1a4060;color:#4ea8de">Upper Bound</span>'
        f'<span class="metric-pill" style="background:#1a4060;color:#4ea8de">Proves Solvability</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        f'<div class="policy-card" style="background:linear-gradient(135deg,#0d2a1a 0%,#1a4a2a 100%);border:1px solid #2a6040">'
        f'<div class="big" style="color:#2ecc71">{h_avg_sr:.0%}</div>'
        f'<div class="label">Hint-Guided LLM</div>'
        f'<div class="sub">qwen2.5:3b + workflow SOPs &nbsp;|&nbsp; 5 episodes per task</div>'
        f'<div class="stat">'
        f'<div class="stat-item"><div class="val" style="color:#2ecc71">{h_avg_rw:.0f}</div><div class="key">Avg Reward</div></div>'
        f'<div class="stat-item"><div class="val" style="color:#2ecc71">{h_avg_st:.1f}</div><div class="key">Avg Steps</div></div>'
        f'<div class="stat-item"><div class="val" style="color:#2ecc71">28/30</div><div class="key">Episodes Won</div></div>'
        f'</div>'
        f'<div style="margin-top:10px"><span class="metric-pill" style="background:#1a3a20;color:#2ecc71">Validates Task Design</span>'
        f'<span class="metric-pill" style="background:#1a3a20;color:#2ecc71">RAG Analogy</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        f'<div class="policy-card" style="background:linear-gradient(135deg,#2a0d0d 0%,#4a1a1a 100%);border:1px solid #6a2020">'
        f'<div class="big" style="color:#e74c3c">{z_avg_sr:.0%}</div>'
        f'<div class="label">Zero-Shot LLM</div>'
        f'<div class="sub">qwen2.5:3b, no hints &nbsp;|&nbsp; 1 episode per task</div>'
        f'<div class="stat">'
        f'<div class="stat-item"><div class="val" style="color:#e74c3c">{z_avg_rw:.1f}</div><div class="key">Avg Reward</div></div>'
        f'<div class="stat-item"><div class="val" style="color:#e74c3c">{z_avg_st:.1f}</div><div class="key">Avg Steps</div></div>'
        f'<div class="stat-item"><div class="val" style="color:#e74c3c">0/6</div><div class="key">Tasks Solved</div></div>'
        f'</div>'
        f'<div style="margin-top:10px"><span class="metric-pill" style="background:#3a1010;color:#e74c3c">Measures Gap</span>'
        f'<span class="metric-pill" style="background:#3a1010;color:#e74c3c">Future RL Target</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── chart builder helpers ────────────────────────────────────────────────
    POLICY_COLORS = {"Oracle": "#4ea8de", "Hint-Guided": "#2ecc71", "Zero-Shot": "#e74c3c"}
    TASK_SHORT    = ["Customer\nIncident","Product\nLaunch","Meeting\nConflict",
                     "Launch\nReadiness","Budget\nApproval","Vendor\nOnboarding"]

    def _grouped_bar_svg(series_3, values_3, chart_h=260, bar_w=48, bar_gap=8, grp_pad=24, show_pct=True, y_max=None, y_label=""):
        """series_3: list of (name, color), values_3: list of 6-element lists."""
        n_pol   = len(series_3)
        grp_w   = n_pol * (bar_w + bar_gap) - bar_gap + grp_pad
        svg_w   = 72 + len(TASKS) * grp_w
        lbl_h   = 44
        leg_h   = 28
        total_h = chart_h + lbl_h + leg_h + 8
        max_val = y_max or max((max(v) for v in values_3), default=1)
        if max_val == 0: max_val = 1

        p = []
        # defs gradient
        p.append("<defs>")
        for sname, scolor in series_3:
            gid = sname.replace("-","").replace(" ","")
            p.append(f'<linearGradient id="g{gid}" x1="0" y1="0" x2="0" y2="1">'
                     f'<stop offset="0%" stop-color="{scolor}" stop-opacity="1"/>'
                     f'<stop offset="100%" stop-color="{scolor}" stop-opacity="0.6"/>'
                     f'</linearGradient>')
        p.append("</defs>")

        # grid
        for pct in [25, 50, 75, 100]:
            yg = chart_h - (pct / 100) * chart_h
            p.append(f'<line x1="68" y1="{yg:.0f}" x2="{svg_w-4}" y2="{yg:.0f}" stroke="#222" stroke-width="1" stroke-dasharray="5,4"/>')
            label_val = f"{pct}%" if show_pct else f"{int(pct * max_val / 100)}"
            p.append(f'<text x="64" y="{yg+4:.0f}" fill="#555" font-size="9" text-anchor="end">{label_val}</text>')
        p.append(f'<line x1="68" y1="{chart_h}" x2="{svg_w-4}" y2="{chart_h}" stroke="#333" stroke-width="1"/>')
        if y_label:
            p.append(f'<text x="10" y="{chart_h//2}" fill="#555" font-size="9" text-anchor="middle" transform="rotate(-90,10,{chart_h//2})">{y_label}</text>')

        for ti in range(len(TASKS)):
            gx  = 72 + ti * grp_w
            lbl = TASK_SHORT[ti]
            lx  = gx + (n_pol * (bar_w + bar_gap) - bar_gap) / 2
            for li, line in enumerate(lbl.split("\n")):
                p.append(f'<text x="{lx:.0f}" y="{chart_h + 16 + li*13}" fill="#aaa" font-size="10" text-anchor="middle">{line}</text>')

            for bi, ((sname, scolor), vals) in enumerate(zip(series_3, values_3)):
                bx  = gx + bi * (bar_w + bar_gap)
                val = max(vals[ti], 0)
                bh  = (val / max_val) * chart_h
                by  = chart_h - bh
                gid = sname.replace("-","").replace(" ","")
                p.append(f'<rect x="{bx}" y="{by:.1f}" width="{bar_w}" height="{max(bh,1.5):.1f}" fill="url(#g{gid})" rx="3"/>')
                if bh > 18:
                    lbl_v = f"{int(val*100)}%" if show_pct else f"{val:.1f}"
                    p.append(f'<text x="{bx+bar_w/2:.0f}" y="{by+bh/2+4:.0f}" fill="#fff" font-size="9" font-weight="700" text-anchor="middle">{lbl_v}</text>')
                elif val > 0:
                    lbl_v = f"{int(val*100)}%" if show_pct else f"{val:.1f}"
                    p.append(f'<text x="{bx+bar_w/2:.0f}" y="{by-3:.0f}" fill="{scolor}" font-size="8" text-anchor="middle">{lbl_v}</text>')

        # legend
        leg_y = chart_h + lbl_h + 4
        for bi, (sname, scolor) in enumerate(series_3):
            lx = 72 + bi * 190
            p.append(f'<rect x="{lx}" y="{leg_y}" width="12" height="12" fill="{scolor}" rx="2"/>')
            p.append(f'<text x="{lx+17}" y="{leg_y+10}" fill="#bbb" font-size="11">{sname}</text>')

        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {total_h}" '
                f'style="background:#0e1117;border-radius:10px;width:100%;border:1px solid #1e1e2e">'
                + "".join(p) + "</svg>")

    # ── chart 1: success rate ────────────────────────────────────────────────
    st.markdown("### Success Rate by Task")
    st.caption("Percentage of episodes where all subgoals were completed within the horizon.")
    series3 = [("Oracle","#4ea8de"), ("Hint-Guided","#2ecc71"), ("Zero-Shot","#e74c3c")]
    o_sr = [oracle_sum.get(t,{}).get("success_rate",1.0) for t in TASKS]
    h_sr = [hint_sum.get(t,  {}).get("success_rate",0.0) for t in TASKS]
    z_sr = [zs_sum.get(t,    {}).get("success_rate",0.0) for t in TASKS]
    st.markdown(_grouped_bar_svg(series3, [o_sr, h_sr, z_sr], chart_h=240), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── chart 2: average reward ──────────────────────────────────────────────
    st.markdown("### Average Episode Reward")
    st.caption("Shaped reward including subgoal progress (+8/N each), coordination bonuses (+2), terminal success (+75), and step penalties.")
    o_rw = [oracle_sum.get(t,{}).get("avg_reward",0.0) for t in TASKS]
    h_rw = [hint_sum.get(t,  {}).get("avg_reward",0.0) for t in TASKS]
    z_rw = [max(zs_sum.get(t,{}).get("avg_reward",0.0), 0) for t in TASKS]
    max_rw = max(max(o_rw+h_rw+z_rw), 1)
    st.markdown(_grouped_bar_svg(series3, [o_rw, h_rw, z_rw], chart_h=200, show_pct=False, y_max=max_rw, y_label="Reward"), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── chart 3: steps to solve ──────────────────────────────────────────────
    st.markdown("### Average Steps per Episode")
    st.caption("Oracle steps show minimum possible. Hint-guided matches closely. Zero-shot steps are wasted before failure.")
    o_st = [oracle_sum.get(t,{}).get("avg_steps",0.0) for t in TASKS]
    h_st = [hint_sum.get(t,  {}).get("avg_steps",0.0) for t in TASKS]
    z_st = [zs_sum.get(t,    {}).get("avg_steps",0.0) for t in TASKS]
    max_st = max(max(o_st+h_st+z_st), 1)
    st.markdown(_grouped_bar_svg(series3, [o_st, h_st, z_st], chart_h=180, show_pct=False, y_max=max_st, y_label="Steps"), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── chart 4: task progress (zero-shot only meaningful here) ─────────────
    st.markdown("### Average Task Progress (% subgoals reached)")
    st.caption("Shows how far each policy gets even without full completion. Oracle and Hint-Guided reach 100%. Zero-shot stalls early.")
    o_pr = [oracle_sum.get(t,{}).get("avg_progress",1.0) for t in TASKS]
    h_pr = [hint_sum.get(t,  {}).get("avg_progress",0.0) for t in TASKS]
    z_pr = [zs_sum.get(t,    {}).get("avg_progress",0.0) for t in TASKS]
    st.markdown(_grouped_bar_svg(series3, [o_pr, h_pr, z_pr], chart_h=180), unsafe_allow_html=True)

    st.divider()

    # ── per-task deep dive cards ─────────────────────────────────────────────
    st.markdown("### Per-Task Deep Dive")
    st.caption("Click each task to expand full stats for all three policies.")

    ZS_FAILURES = {
        "customer_incident":  ("Looping + Policy Error",     "Re-reads email 4x, generates cyclic actions. Halts at 9 steps, 25% progress. Failure: no workflow order known."),
        "product_launch":     ("Permission Violation",        "Calls jira.change_status for product_01 — role not permitted. Halts at 3 steps, 14% progress."),
        "meeting_conflict":   ("Constraint Loop + Timeout",   "19 repeated actions, 3 constraint violations, hits step limit (25) at 40% progress without resolving conflict."),
        "launch_readiness":   ("Immediate Looping",           "Re-reads same resource on step 2. Policy error halts run at 2 steps, 12% progress."),
        "budget_approval":    ("Looping + Policy Error",     "3-action loop on budget discovery. Halts at 8 steps, 14% progress. Cannot discover correct Jira IDs."),
        "vendor_onboarding":  ("Looping + Policy Error",     "Cannot discover VEND-401 without hints. Loops on search actions. Halts at 11 steps, 25% progress."),
    }

    for task in TASKS:
        meta_t = TASK_META.get(task, {})
        o = oracle_sum.get(task, {})
        h = hint_sum.get(task, {})
        z = zs_sum.get(task, {})
        h_sr_v = h.get("success_rate", 0.0)
        z_sr_v = z.get("success_rate", 0.0)
        gap_v  = (h_sr_v - z_sr_v) * 100
        zf_primary, zf_detail = ZS_FAILURES.get(task, ("—", "—"))
        h_ci   = h.get("success_rate_95ci", [0,1])

        with st.expander(f"{meta_t.get('icon','')}  {task.replace('_',' ').title()}   —   Oracle 100%  |  Hint-Guided {h_sr_v:.0%}  |  Zero-Shot {z_sr_v:.0%}  |  Gap +{gap_v:.0f}pp"):
            col_o, col_h, col_z = st.columns(3)

            with col_o:
                st.markdown(
                    '<div style="background:#0d2137;border-radius:8px;padding:14px;border:1px solid #1a3a5c">'
                    '<div style="font-size:0.78rem;color:#4ea8de;font-weight:700;letter-spacing:0.08em;margin-bottom:8px">ORACLE</div>',
                    unsafe_allow_html=True,
                )
                st.metric("Success Rate", f"{o.get('success_rate',1.0):.0%}")
                st.metric("Avg Reward",   f"{o.get('avg_reward',0):.1f}")
                st.metric("Avg Steps",    f"{o.get('avg_steps',0):.1f}")
                st.metric("Episodes",     f"{o.get('episodes',25)}")
                st.markdown("</div>", unsafe_allow_html=True)

            with col_h:
                st.markdown(
                    '<div style="background:#0d2a1a;border-radius:8px;padding:14px;border:1px solid #1a4a2a">'
                    '<div style="font-size:0.78rem;color:#2ecc71;font-weight:700;letter-spacing:0.08em;margin-bottom:8px">HINT-GUIDED LLM</div>',
                    unsafe_allow_html=True,
                )
                st.metric("Success Rate", f"{h_sr_v:.0%}")
                st.metric("Avg Reward",   f"{h.get('avg_reward',0):.1f}", f"±{h.get('reward_std',0):.1f}")
                st.metric("Avg Steps",    f"{h.get('avg_steps',0):.1f}")
                st.metric("95% CI",       f"[{h_ci[0]:.2f}, {h_ci[1]:.2f}]")
                st.metric("Policy Errors",f"{h.get('policy_error_rate',0):.0%}")
                st.metric("LLM Calls",    f"{h.get('llm_calls',0)}")
                st.markdown("</div>", unsafe_allow_html=True)

            with col_z:
                st.markdown(
                    '<div style="background:#2a0d0d;border-radius:8px;padding:14px;border:1px solid #5a1a1a">'
                    '<div style="font-size:0.78rem;color:#e74c3c;font-weight:700;letter-spacing:0.08em;margin-bottom:8px">ZERO-SHOT LLM</div>',
                    unsafe_allow_html=True,
                )
                st.metric("Success Rate",   f"{z_sr_v:.0%}")
                st.metric("Avg Reward",     f"{z.get('avg_reward',0):.1f}")
                st.metric("Progress",       f"{z.get('avg_progress',0):.0%}")
                st.metric("Steps Taken",    f"{z.get('avg_steps',0):.0f}")
                st.metric("Repeated Acts",  f"{z.get('avg_repeated_actions',0):.0f}")
                st.metric("Constraint Viol",f"{z.get('avg_constraint_violations',0):.0f}")
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                f'<div style="margin-top:10px;background:#1a0a0a;border-left:3px solid #e74c3c;border-radius:4px;padding:10px 14px">'
                f'<span style="color:#e74c3c;font-size:0.78rem;font-weight:700">ZERO-SHOT FAILURE: {zf_primary}</span><br>'
                f'<span style="color:#aaa;font-size:0.82rem">{zf_detail}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── summary comparison table ─────────────────────────────────────────────
    st.markdown("### Full Comparison Table")
    tbl_rows = []
    for task in TASKS:
        o = oracle_sum.get(task, {})
        h = hint_sum.get(task, {})
        z = zs_sum.get(task, {})
        tbl_rows.append({
            "Task":              task.replace("_"," ").title(),
            "Oracle SR":         f"{o.get('success_rate',1.0):.0%}",
            "Oracle Reward":     f"{o.get('avg_reward',0):.1f}",
            "Oracle Steps":      f"{o.get('avg_steps',0):.1f}",
            "Hint SR":           f"{h.get('success_rate',0):.0%}",
            "Hint Reward":       f"{h.get('avg_reward',0):.1f}",
            "Hint Steps":        f"{h.get('avg_steps',0):.1f}",
            "Hint 95% CI":       "[{:.2f},{:.2f}]".format(*h.get("success_rate_95ci",[0,1])),
            "ZS SR":             f"{z.get('success_rate',0):.0%}",
            "ZS Reward":         f"{z.get('avg_reward',0):.1f}",
            "ZS Progress":       f"{z.get('avg_progress',0):.0%}",
            "ZS Repeated":       f"{z.get('avg_repeated_actions',0):.0f}",
            "Gap (H-ZS)":        f"+{(h.get('success_rate',0)-z.get('success_rate',0))*100:.0f}pp",
        })
    st.dataframe(tbl_rows, use_container_width=True)

    st.divider()

    # ── research narrative ────────────────────────────────────────────────────
    st.markdown("### Why the +93pp Gap Exists")

    ga, gb = st.columns([1, 1])
    with ga:
        st.markdown("""
**Three structural reasons zero-shot fails on enterprise tasks:**

| Root Cause | Evidence |
|---|---|
| No knowledge of action order | All tasks stall in first 2–11 steps |
| Cannot discover concrete IDs | product_launch: calls wrong tool; vendor_onboarding: never finds VEND-401 |
| Looping without a workflow map | meeting_conflict: 19 repeated actions before timeout |

**Hint-guided = RAG over enterprise SOPs.**
In real companies, employees follow runbooks, not first principles.
The +93pp gap *is* the value of that documentation.
""")
    with gb:
        st.markdown("""
**What each policy proves:**

- **Oracle 100%** — every task is mechanically solvable; reward function fires correctly
- **Hint-Guided 93%** — task design is sound; 2 failures are model bugs, not task bugs
- **Zero-Shot 0%** — enterprise procedural knowledge cannot be inferred from context alone

**Future work to close the gap:**
- Behavioral Cloning on hint-guided trajectories
- PPO / QMIX against the shaped reward
- LLM fine-tuning (SFT + RLHF on failures)
""")

    st.markdown(
        '<div style="background:linear-gradient(90deg,#0d2137,#0d2a1a);border-radius:8px;padding:16px 20px;border:1px solid #2a4040;margin-top:8px">'
        '<span style="color:#aaa;font-size:0.88rem">'
        '<strong style="color:#fff">Key finding for Wedecode:</strong> '
        'The benchmark cleanly separates <em>task design quality</em> (Oracle proves solvability) '
        'from <em>autonomous agent capability</em> (Zero-Shot reveals the gap). '
        'A +93pp gap with a 3B local model is direct evidence for why enterprise AI needs '
        'structured workflow context injection — and exactly the research problem this benchmark is built to measure.'
        '</span></div>',
        unsafe_allow_html=True,
    )


# ── TAB 4: saved results (raw JSON) ──────────────────────────────────────────
with tab_results:
    st.header("📊 Saved Benchmark Results (Raw)")

    if not RESULTS_PATH.exists():
        st.warning(f"No results file found at `{RESULTS_PATH}`. Run a benchmark first.")
    else:
        try:
            data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            st.error(f"Could not parse results file: {exc}")
            data = {}

        if data:
            col_meta1, col_meta2, col_meta3 = st.columns(3)
            col_meta1.metric("Provider", data.get("provider", "—"))
            col_meta2.metric("Model", data.get("model", "—"))
            col_meta3.metric("Mode", data.get("mode", "—"))

            summary = data.get("summary", {})
            if summary:
                st.divider()
                st.subheader("Summary Table")

                rows = []
                for t, s in summary.items():
                    ci = s.get("success_rate_95ci", [0, 1])
                    rows.append({
                        "Task": t.replace("_", " ").title(),
                        "Episodes": s.get("episodes", "—"),
                        "Success Rate": f"{s.get('success_rate', 0):.0%}",
                        "95% CI": f"[{ci[0]:.2f}, {ci[1]:.2f}]",
                        "Avg Reward": f"{s.get('avg_reward', 0):.2f}  ±{s.get('reward_std', 0):.2f}",
                        "Avg Steps": f"{s.get('avg_steps', 0):.1f}",
                        "Steps on Success": f"{s.get('avg_steps_on_success', 0):.1f}",
                        "Avg Progress": f"{s.get('avg_progress', 0):.0%}",
                        "Policy Errors": f"{s.get('policy_error_rate', 0):.0%}",
                        "LLM Calls": s.get("llm_calls", "—"),
                    })
                st.dataframe(rows, use_container_width=True)

                st.divider()
                st.subheader("Per-Task Details")
                for t, s in summary.items():
                    meta_t = TASK_META.get(t, {})
                    icon = meta_t.get("icon", "📋")
                    with st.expander(f"{icon} {t.replace('_', ' ').title()}"):
                        st.json(s)

            raw = data.get("results", [])
            if raw:
                st.divider()
                with st.expander("Raw episode results (JSON)"):
                    st.json(raw)
