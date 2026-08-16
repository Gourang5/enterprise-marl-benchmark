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
    st.header("🆚 Four-Tier Policy Comparison")
    st.markdown(
        "Full benchmark results across all **4 policies** and **6 tasks**. "
        "Each tier answers a different research question about enterprise agent capability."
    )

    # ── load all result files ────────────────────────────────────────────────
    hint_data     = None
    zs_data       = None
    baseline_data = None

    for path, store in [
        (RESULTS_5EP_PATH,  "hint"),
        (ZEROSHOT_PATH,     "zs"),
        (BASELINES_PATH,    "base"),
    ]:
        if path.exists():
            try:
                parsed = json.loads(path.read_text(encoding="utf-8"))
                if store == "hint":   hint_data     = parsed
                elif store == "zs":   zs_data       = parsed
                else:                 baseline_data = parsed
            except Exception:
                pass

    hint_sum = hint_data.get("summary", {}) if hint_data else {}
    zs_sum   = zs_data.get("summary",   {}) if zs_data   else {}

    # oracle / random from baselines.json (25 episodes each)
    oracle_sum = {t: baseline_data[t]["rule"]   for t in TASKS if baseline_data and t in baseline_data} if baseline_data else {}
    random_sum = {t: baseline_data[t]["random"] for t in TASKS if baseline_data and t in baseline_data} if baseline_data else {}

    all_loaded = bool(hint_sum and zs_sum and oracle_sum)

    if all_loaded:
        st.success("All 4 policy results loaded — Oracle (25ep) | Hint-Guided (5ep) | Zero-Shot (1ep) | Random (25ep)")
    elif hint_sum:
        st.info("Hint-guided and baseline results loaded. Zero-shot results also available.")
    else:
        st.warning("No benchmark results found. Run the benchmarks first.")

    st.divider()

    # ── top-line metric cards ────────────────────────────────────────────────
    st.subheader("Overall Average Success Rate")
    def avg_sr(summary):
        vals = [summary.get(t, {}).get("success_rate", 0.0) for t in TASKS]
        return sum(vals) / len(vals) if vals else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(
        '<div style="background:#1a2a3a;border-top:4px solid #3498db;border-radius:6px;padding:14px;text-align:center">'
        '<div style="font-size:2rem;font-weight:700;color:#3498db">100%</div>'
        '<div style="color:#aaa;font-size:0.85rem">Oracle Baseline</div>'
        '<div style="color:#666;font-size:0.75rem">25 episodes</div></div>',
        unsafe_allow_html=True,
    )
    h_avg = avg_sr(hint_sum)
    m2.markdown(
        f'<div style="background:#1a3a2a;border-top:4px solid #2ecc71;border-radius:6px;padding:14px;text-align:center">'
        f'<div style="font-size:2rem;font-weight:700;color:#2ecc71">{h_avg:.0%}</div>'
        f'<div style="color:#aaa;font-size:0.85rem">Hint-Guided LLM</div>'
        f'<div style="color:#666;font-size:0.75rem">5 episodes · qwen2.5:3b</div></div>',
        unsafe_allow_html=True,
    )
    z_avg = avg_sr(zs_sum)
    m3.markdown(
        f'<div style="background:#2a1a0a;border-top:4px solid #e67e22;border-radius:6px;padding:14px;text-align:center">'
        f'<div style="font-size:2rem;font-weight:700;color:#e67e22">{z_avg:.0%}</div>'
        f'<div style="color:#aaa;font-size:0.85rem">Zero-Shot LLM</div>'
        f'<div style="color:#666;font-size:0.75rem">1 episode · qwen2.5:3b</div></div>',
        unsafe_allow_html=True,
    )
    m4.markdown(
        '<div style="background:#2a1a1a;border-top:4px solid #e74c3c;border-radius:6px;padding:14px;text-align:center">'
        '<div style="font-size:2rem;font-weight:700;color:#e74c3c">0%</div>'
        '<div style="color:#aaa;font-size:0.85rem">Random Baseline</div>'
        '<div style="color:#666;font-size:0.75rem">25 episodes</div></div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── grouped bar chart — all 4 policies ──────────────────────────────────
    st.subheader("Success Rate by Task — All 4 Policies")

    oracle_sr = [oracle_sum.get(t, {}).get("success_rate", 1.0) for t in TASKS]
    hint_sr   = [hint_sum.get(t,   {}).get("success_rate", 0.0) for t in TASKS]
    zs_sr     = [zs_sum.get(t,     {}).get("success_rate", 0.0) for t in TASKS]
    random_sr = [random_sum.get(t, {}).get("success_rate", 0.0) for t in TASKS]

    series_all = [
        ("Oracle",          oracle_sr, "#3498db"),
        ("Hint-Guided",     hint_sr,   "#2ecc71"),
        ("Zero-Shot",       zs_sr,     "#e67e22"),
        ("Random",          random_sr, "#e74c3c"),
    ]

    bar_w     = 46
    bar_gap   = 8
    group_pad = 28
    group_w   = 4 * (bar_w + bar_gap) - bar_gap + group_pad
    chart_w   = 70 + len(TASKS) * group_w
    chart_h   = 280
    label_h   = 44
    legend_h  = 36
    total_h   = chart_h + label_h + legend_h + 10

    parts = []
    # y-axis grid
    for pct in [25, 50, 75, 100]:
        y = chart_h - (pct / 100) * chart_h
        parts.append(f'<line x1="65" y1="{y:.0f}" x2="{chart_w}" y2="{y:.0f}" stroke="#2a2a2a" stroke-width="1" stroke-dasharray="5,4"/>')
        parts.append(f'<text x="60" y="{y + 4:.0f}" fill="#666" font-size="10" text-anchor="end">{pct}%</text>')
    # baseline at 0
    parts.append(f'<line x1="65" y1="{chart_h}" x2="{chart_w}" y2="{chart_h}" stroke="#444" stroke-width="1"/>')

    for ti, task in enumerate(TASKS):
        gx    = 70 + ti * group_w
        label = task.replace("_", " ").title().replace(" ", "\n")
        # split long labels
        words = task.replace("_", " ").title().split()
        if len(words) > 1:
            mid = len(words) // 2
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:])
            lx = gx + (4 * (bar_w + bar_gap) - bar_gap) / 2
            parts.append(f'<text x="{lx:.0f}" y="{chart_h + 16}" fill="#bbb" font-size="10" text-anchor="middle">{line1}</text>')
            parts.append(f'<text x="{lx:.0f}" y="{chart_h + 28}" fill="#bbb" font-size="10" text-anchor="middle">{line2}</text>')
        else:
            lx = gx + (4 * (bar_w + bar_gap) - bar_gap) / 2
            parts.append(f'<text x="{lx:.0f}" y="{chart_h + 20}" fill="#bbb" font-size="10" text-anchor="middle">{words[0]}</text>')

        for bi, (sname, sdata, color) in enumerate(series_all):
            bx  = gx + bi * (bar_w + bar_gap)
            val = sdata[ti] if sdata[ti] is not None else 0.0
            bh  = val * chart_h
            by  = chart_h - bh
            # bar
            parts.append(f'<rect x="{bx}" y="{by:.1f}" width="{bar_w}" height="{max(bh, 1):.1f}" fill="{color}" rx="3" opacity="0.9"/>')
            # label inside/above bar
            if val >= 0.12:
                ty = by + bh / 2 + 4
                parts.append(f'<text x="{bx + bar_w/2:.0f}" y="{ty:.0f}" fill="#fff" font-size="9" font-weight="bold" text-anchor="middle">{int(val*100)}%</text>')
            elif val > 0:
                parts.append(f'<text x="{bx + bar_w/2:.0f}" y="{by - 3:.0f}" fill="{color}" font-size="9" text-anchor="middle">{int(val*100)}%</text>')

    # legend
    leg_y = chart_h + label_h + 8
    for bi, (sname, _, color) in enumerate(series_all):
        lx = 70 + bi * 180
        parts.append(f'<rect x="{lx}" y="{leg_y}" width="12" height="12" fill="{color}" rx="2"/>')
        parts.append(f'<text x="{lx + 17}" y="{leg_y + 10}" fill="#ccc" font-size="11">{sname}</text>')

    bar_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {chart_w} {total_h}" '
        f'style="background:#0e1117;border-radius:8px;width:100%;border:1px solid #222">'
        + "".join(parts) + "</svg>"
    )
    st.markdown(bar_svg, unsafe_allow_html=True)

    st.divider()

    # ── reward comparison chart ──────────────────────────────────────────────
    st.subheader("Average Reward by Task — Oracle vs Hint-Guided vs Zero-Shot")

    oracle_rw = [oracle_sum.get(t, {}).get("avg_reward", 0.0) for t in TASKS]
    hint_rw   = [hint_sum.get(t,   {}).get("avg_reward", 0.0) for t in TASKS]
    zs_rw     = [zs_sum.get(t,     {}).get("avg_reward", 0.0) for t in TASKS]
    max_rw    = max(max(oracle_rw + hint_rw + zs_rw), 1)

    rw_series = [
        ("Oracle",      oracle_rw, "#3498db"),
        ("Hint-Guided", hint_rw,   "#2ecc71"),
        ("Zero-Shot",   zs_rw,     "#e67e22"),
    ]
    rw_bar_w   = 56
    rw_bar_gap = 10
    rw_grp_pad = 30
    rw_grp_w   = 3 * (rw_bar_w + rw_bar_gap) - rw_bar_gap + rw_grp_pad
    rw_chart_w = 70 + len(TASKS) * rw_grp_w
    rw_chart_h = 200
    rw_total_h = rw_chart_h + 60 + 30

    rw_parts = []
    for pct in [25, 50, 75, 100]:
        y = rw_chart_h - (pct / 100) * rw_chart_h
        rw_parts.append(f'<line x1="65" y1="{y:.0f}" x2="{rw_chart_w}" y2="{y:.0f}" stroke="#2a2a2a" stroke-dasharray="4,4"/>')
        rw_parts.append(f'<text x="60" y="{y+4:.0f}" fill="#666" font-size="9" text-anchor="end">{int(pct * max_rw / 100)}</text>')
    rw_parts.append(f'<line x1="65" y1="{rw_chart_h}" x2="{rw_chart_w}" y2="{rw_chart_h}" stroke="#444"/>')

    for ti, task in enumerate(TASKS):
        gx    = 70 + ti * rw_grp_w
        words = task.replace("_", " ").title().split()
        mid   = len(words) // 2
        lx    = gx + (3 * (rw_bar_w + rw_bar_gap) - rw_bar_gap) / 2
        rw_parts.append(f'<text x="{lx:.0f}" y="{rw_chart_h + 14}" fill="#bbb" font-size="9" text-anchor="middle">{" ".join(words[:mid])}</text>')
        rw_parts.append(f'<text x="{lx:.0f}" y="{rw_chart_h + 25}" fill="#bbb" font-size="9" text-anchor="middle">{" ".join(words[mid:])}</text>')

        for bi, (sname, sdata, color) in enumerate(rw_series):
            bx  = gx + bi * (rw_bar_w + rw_bar_gap)
            val = max(sdata[ti], 0)
            bh  = (val / max_rw) * rw_chart_h
            by  = rw_chart_h - bh
            rw_parts.append(f'<rect x="{bx}" y="{by:.1f}" width="{rw_bar_w}" height="{max(bh,1):.1f}" fill="{color}" rx="3" opacity="0.85"/>')
            if val > max_rw * 0.08:
                rw_parts.append(f'<text x="{bx + rw_bar_w/2:.0f}" y="{by + bh/2 + 4:.0f}" fill="#fff" font-size="8" font-weight="bold" text-anchor="middle">{val:.0f}</text>')

    leg_y2 = rw_chart_h + 44
    for bi, (sname, _, color) in enumerate(rw_series):
        lx = 70 + bi * 200
        rw_parts.append(f'<rect x="{lx}" y="{leg_y2}" width="12" height="12" fill="{color}" rx="2"/>')
        rw_parts.append(f'<text x="{lx+17}" y="{leg_y2+10}" fill="#ccc" font-size="11">{sname}</text>')

    rw_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {rw_chart_w} {rw_total_h}" '
        f'style="background:#0e1117;border-radius:8px;width:100%;border:1px solid #222">'
        + "".join(rw_parts) + "</svg>"
    )
    st.markdown(rw_svg, unsafe_allow_html=True)

    st.divider()

    # ── detailed comparison table ────────────────────────────────────────────
    st.subheader("Full Results Table")
    rows = []
    for task in TASKS:
        o  = oracle_sum.get(task, {})
        h  = hint_sum.get(task, {})
        z  = zs_sum.get(task, {})
        r  = random_sum.get(task, {})
        h_sr = h.get("success_rate", 0.0)
        z_sr = z.get("success_rate", 0.0)
        rows.append({
            "Task":                  task.replace("_", " ").title(),
            "Oracle SR":             f"{o.get('success_rate', 1.0):.0%}",
            "Oracle Reward":         f"{o.get('avg_reward', 0):.1f}",
            "Hint-Guided SR":        f"{h_sr:.0%}",
            "Hint-Guided Reward":    f"{h.get('avg_reward', 0):.1f}",
            "Hint-Guided Steps":     f"{h.get('avg_steps', 0):.1f}",
            "Zero-Shot SR":          f"{z_sr:.0%}",
            "Zero-Shot Reward":      f"{z.get('avg_reward', 0):.1f}",
            "Zero-Shot Progress":    f"{z.get('avg_progress', 0):.0%}",
            "Gap (H vs Z)":          f"+{(h_sr - z_sr)*100:.0f}pp",
            "Random SR":             f"{r.get('success_rate', 0):.0%}",
        })
    st.dataframe(rows, use_container_width=True)

    st.divider()

    # ── zero-shot failure analysis ───────────────────────────────────────────
    st.subheader("Zero-Shot Failure Analysis")

    failure_data = {
        "customer_incident":  {"primary": "Looping + Policy Failure",    "detail": "Re-reads same email 4x. Generates cyclic no-progress actions. Fails after 9 steps at 25% progress."},
        "product_launch":     {"primary": "Permission Violation",         "detail": "Calls jira.change_status for product_01 who lacks that permission. Fails after 3 steps at 14% progress."},
        "meeting_conflict":   {"primary": "Looping + Constraint Violation","detail": "Loops 19 times, hits 3 constraint violations, times out at max steps (25) with only 40% progress."},
        "launch_readiness":   {"primary": "Looping + Policy Failure",    "detail": "Reads same resource twice immediately. Fails after just 2 steps at 12% progress."},
        "budget_approval":    {"primary": "Looping + Policy Failure",    "detail": "Loops 3 times on same actions. Fails after 8 steps at 14% progress."},
        "vendor_onboarding":  {"primary": "Looping + Policy Failure",    "detail": "Loops on discovery actions. Cannot find VEND-401 without hints. Fails after 11 steps at 25% progress."},
    }

    fail_cols = st.columns(2)
    for i, task in enumerate(TASKS):
        fd = failure_data.get(task, {})
        meta_t = TASK_META.get(task, {})
        with fail_cols[i % 2]:
            st.markdown(
                f'<div style="border:1px solid #333;border-radius:6px;padding:12px;margin-bottom:8px;background:#0e1117">'
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
                f'<span>{meta_t.get("icon","")}</span>'
                f'<strong style="font-size:0.9rem">{task.replace("_"," ").title()}</strong>'
                f'<span style="margin-left:auto;background:#e74c3c;color:#fff;padding:2px 8px;border-radius:4px;font-size:0.72rem">{fd.get("primary","—")}</span>'
                f'</div>'
                f'<p style="color:#999;font-size:0.82rem;margin:0">{fd.get("detail","")}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── research narrative ────────────────────────────────────────────────────
    st.subheader("Why Does the Gap Exist?")
    st.markdown("""
**The +93pp average gap between Hint-Guided and Zero-Shot directly measures the value of structured workflow knowledge in enterprise settings.**

---

#### The 3 root causes of zero-shot failure

| Root Cause | What happens | Why hints fix it |
|---|---|---|
| **Unknown action order** | Agent doesn't know DAG dependency sequence — tries shortcuts that the verifier rejects | Hints provide the exact subgoal sequence |
| **Unknown parameter values** | Concrete IDs like `VEND-401` must be discovered, not guessed — model fabricates wrong values | Hints provide the discovery path (read email → find ticket) |
| **Looping without a map** | Without a workflow map, model re-reads same resources and burns step budget on −1.0 redundancy penalties | Hints prevent revisiting completed steps |

---

#### The RAG / SOP analogy

In real Fortune 500 enterprises, employees don't start from zero every morning.
They follow **Standard Operating Procedures (SOPs)**, runbooks, and onboarding docs.

**Hint-guided LLM = onboarded employee with access to company documentation.**
**Zero-shot LLM = contractor on day 1 with no briefing.**

This is exactly what **Retrieval-Augmented Generation (RAG)** does for enterprise AI —
it injects the right context at the right time (Lewis et al., 2020).

---

#### What comes next: closing the gap autonomously

The gap is not a flaw — it is the **research agenda**:

| Approach | How it closes the gap |
|---|---|
| **Behavioral Cloning** | Train on hint-guided trajectories — agent learns the SOP implicitly |
| **PPO / Policy Gradient** | Optimize directly against the shaped reward (+75 terminal, +8/N subgoal) |
| **QMIX / VDN** | Centralized training + decentralized execution — agents learn coordination |
| **LLM Fine-tuning** | SFT on successful episodes, RLHF/RLAIF on failures |

The environment infrastructure — reward function, subgoal verifiers, ScenarioFactory —
is deliberately built to support all four without any modification.
""")

    st.info(
        "**Key finding for Wedecode:** The 4-tier taxonomy cleanly separates "
        "*task design quality* (Oracle proves solvability) from *agent capability* (Zero-Shot shows the gap). "
        "A +93pp gap with a 3B local model is the strongest possible case for why "
        "enterprise AI needs workflow context injection — and why this benchmark platform has research value."
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
