# Long-Horizon Task Design

A task is long-horizon when final success requires dependent subgoals, information gathering, multiple applications, coordination and delayed consequences. Raw step count alone is not sufficient.

MVP target:
- 5–8 subgoals
- 8–20 meaningful tool calls
- 2–3 agents
- 3–4 applications
- dependency depth 3–6
- 20–40 step cap
- deterministic verifier
- distractors
- multiple valid plans

Example dependency chain:
Customer report -> incident identified -> engineer assigned -> engineer notified -> meeting scheduled -> issue resolved -> customer notified.
