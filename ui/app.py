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

RESULTS_PATH = Path(__file__).resolve().parents[1] / "benchmark_results" / "llm_results.json"


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
tab_overview, tab_run, tab_results = st.tabs(["🏠 Task Overview", "▶️ Run Episode", "📊 Saved Results"])


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


# ── TAB 3: saved results ──────────────────────────────────────────────────────
with tab_results:
    st.header("📊 Saved Benchmark Results")

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
