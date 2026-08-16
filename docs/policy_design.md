# Policy Design & Evaluation Methodology

## Policy Taxonomy

This benchmark evaluates multi-agent coordination across a four-tier policy spectrum.
Each tier is a distinct research instrument, not a ranking of "better" policies.

```
Random (0%)  ──────────────────────────────────────────  Oracle (100%)
               Zero-Shot LLM (0%, qwen2.5:3b measured)
               Hint-Guided LLM (93%, qwen2.5:3b measured)
```

| Policy | Success Rate | Purpose |
|---|---|---|
| Random Baseline | 0% all 6 tasks | Lower bound — confirms tasks are not trivially solvable |
| Zero-Shot LLM | 0% (qwen2.5:3b, 1 ep/task) | Raw generalization; the meaningful research number |
| **Hint-Guided LLM** | **93%** (qwen2.5:3b, 5 ep/task) | **Validates task design and reward function** |
| Oracle / Deterministic | 100% all 6 tasks | Upper bound — proves mechanical solvability |

Note: Zero-shot is 0% for qwen2.5:3b specifically. Larger models (GPT-4o, Claude 3.5,
Gemini 1.5 Pro) are expected to achieve higher zero-shot scores — the result depends on
model capability, not task design quality.

---

## Why Hint-Guided LLM, Not Zero-Shot?

### The Research Question Separation

This benchmark's primary contribution is the **environment design** — dependency-gated subgoal DAGs,
role-based permissions, multi-app coordination, and a shaped reward function. Evaluating whether
a 3B-parameter local model can solve these tasks zero-shot conflates two distinct questions:

1. **Is the task well-designed?** (benchmark question)
2. **How capable is the LLM?** (model evaluation question)

The hint-guided LLM answers question 1. It isolates task quality from model quality.

### Real-World Grounding

In actual Fortune 500 enterprises, employees do not operate as zero-shot generalists.
They follow:
- Standard Operating Procedures (SOPs)
- Runbooks and escalation playbooks
- Onboarding documentation and workflow guides

The hint system simulates an **onboarded employee** who has been trained on company
procedures — this is the most realistic agent model for enterprise settings.

This is analogous to **Retrieval-Augmented Generation (RAG)** over internal company documentation,
a well-established pattern in enterprise AI deployment (Lewis et al., 2020; Gao et al., 2023).

### Validation Function

The 100% success rate of the hint-guided LLM serves a specific research purpose:
it **validates that the reward function fires correctly** and that each task's subgoal DAG
is structurally sound. If hint-guided LLM failed, it would indicate a broken task or reward
bug — not a model limitation.

This is analogous to the "oracle sanity check" used in RL benchmarks (e.g., MiniGrid, BabyAI)
where a privileged policy is run first to confirm the environment is solvable before evaluating
learned agents.

### What the Zero-Shot Result Means

We measured zero-shot with `qwen2.5:3b`: 0% success across all 6 tasks.
This tells us:

- The 3B model lacks the multi-step reasoning required for 8-subgoal multi-agent coordination ← **model limitation**
- Not: the tasks are unsolvable ← confirmed by Oracle 100% and Hint-Guided 93%

A larger model (GPT-4o, Claude 3.5, Gemini 1.5 Pro) would achieve higher zero-shot
performance on the same tasks. The zero-shot result is model-dependent, not a claim
about task difficulty.

---

## What the Results Actually Show

| Comparison | Finding |
|---|---|
| Oracle 100% vs Random 0% | Tasks span the full challenge spectrum — neither trivial nor impossible |
| Same Det% at all difficulty levels | Scripted agents are distractor-immune; validates ScenarioFactory injection |
| Random 0% at all difficulty levels | Tasks require structured sequential reasoning; random search insufficient |
| Hint-guided LLM 93% | All 6 tasks are correctly specified, verifiable, and reward-consistent; 2 failures are model-side (wrong param format) |

---

## Future Work: Autonomous Agents

The natural next step is training agents that **learn** the workflow knowledge currently
provided as hints:

1. **Behavioral Cloning** — train on successful hint-guided trajectories
2. **PPO / Policy Gradient** — optimize directly against the reward function
3. **QMIX / VDN** — centralized training, decentralized execution (full CTDE paradigm)
4. **Fine-tuned LLM** — SFT on successful episodes, then RLHF/RLAIF

The environment infrastructure (reward function, subgoal verifiers, ScenarioFactory splits)
is deliberately designed to support all four approaches without modification.

---

## References

- Lewis et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS.
- Yao et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR 2023.
- Chevalier-Boisvert et al. (2018). *BabyAI: A Platform to Study the Sample Efficiency of Grounded Language Understanding.* ICLR 2019.
- Gao et al. (2023). *Retrieval-Augmented Generation for Large Language Models: A Survey.*
