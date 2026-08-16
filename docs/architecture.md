# Architecture

Shared database -> repository -> app simulators -> semantic actions -> environment -> role-filtered observations.

SQLite is used for the MVP because the assignment has a 2–3 day timeline. Foreign keys are enabled so employee/project/team/app relationships remain internally consistent.

The environment uses sequential agent turns because enterprise workflows are naturally causal: one employee's action changes what the next employee can observe.

Optional PettingZoo/Gymnasium integration can be added via the `rl` extra once the semantic environment is stable.
