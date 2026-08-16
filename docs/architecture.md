# Architecture

## Overview

```
              Agent / Policy
                    |
                    v
              EnterpriseEnv
              reset / step
                    |
        -------------------------
        |                       |
        v                       v
  App Simulators           Task / Verifier
        |
        v
 Gmail | Slack | Jira | Calendar | Sheets
        |
        v
       CompanyRepository
        |
        v
     SQLite Database
     Shared Company State
```

## Layer-by-layer

### SQLite Shared Company State

At the bottom of the stack is a shared SQLite database that represents the entire company world.
Every table, row, and relationship lives here: employees, emails, Jira tickets, calendar events, Slack channels, spreadsheet cells.

This was a deliberate early design decision. The alternative was five disconnected in-memory mock objects, one per application. That approach breaks cross-application causality: if one agent approves a ticket in Jira, another agent cannot observe the consequence through Gmail or Sheets, because there is no shared ground truth connecting them.

With SQLite as the single source of truth, cross-application state propagation happens naturally. One agent changes state; the next agent who queries any application reads the updated world.

SQLite also enables realistic query patterns. Agents cannot do direct dictionary lookups by ID. They must issue search queries with keywords, the same way a real employee would search their inbox or Jira board. This makes retrieval a genuine research challenge rather than a solved lookup problem.

### CompanyRepository

Directly above SQLite is the repository layer. This provides typed access methods for all entity types: employees, emails, issues, calendar events, channels, and sheet cells. The repository is also where role-based access control is enforced at the data level. Queries are filtered by `agent_id` and `role` before results are returned, so an engineer who calls `sheets_for("eng_01")` only receives sheets where that agent has membership.

### App Simulators

The five application simulators (Gmail, Slack, Jira, Calendar, Sheets) sit on top of the repository. Each simulator exposes a domain-specific interface: `search_emails`, `send_message`, `change_issue_status`, `create_event`, `update_cell`, and similar. Internally each call is a thin wrapper over repository reads and writes. The simulators are stateless; all state lives in SQLite.

This thinness is intentional. The goal was not to build SaaS clones. The goal was enough surface area to make realistic enterprise actions possible while keeping the implementation auditable.

Permission enforcement happens at two levels. The repository layer checks data-level membership (does this agent have access to this sheet?). The app simulator layer checks action-level permission (does this agent role allow this action type?). Both must pass for an action to succeed.

### EnterpriseEnv

The environment is the main integration layer. It implements a Gymnasium-compatible interface with `reset(seed)`, `step(action)`, and `close()`.

`reset` initialises a fresh SQLite database, seeds the company state from a deterministic integer seed, and returns the first observation for each agent.

`step` receives a structured action (`agent_id`, `app`, `action_type`, `parameters`), validates it against the agent's permission set, dispatches it to the relevant app simulator, evaluates the resulting database state against the task verifier, computes reward, and assembles the next observation.

Observations are role-filtered. Each agent's observation contains only the information their role permits: their own inbox headers (not bodies), only the Slack channels they belong to, only their own calendar events, and only sheets where they have membership. The full company state is never directly visible to any single agent.

### Task / Verifier

The task layer defines the workflow: the ordered set of subgoals, their dependency relationships, and the database predicates that constitute success for each subgoal.

Subgoals are dependency-gated. A subgoal can only be credited once all its declared prerequisites are satisfied. This creates genuine temporal structure: later actions in the workflow are mechanically blocked until earlier state exists, not just encouraged by reward shaping.

Verification is deterministic and state-based. Success is not determined by whether an agent posted a particular string in Slack or used a particular phrase. It is determined by whether the underlying database contains the correct state. The verifier checks things like: does the Jira ticket have status `approved`? Was the sheet cell updated by `pm_01` specifically, not by any agent? Does the calendar event exist with the right attendees?

Negation-aware affirmation logic is used where natural language is involved (for example, Slack announcement verification). A message saying "vendor is not approved" contains the word "approved" but should not trigger success. The verifier uses clause-boundary negation detection to handle this correctly.

### Evaluator State Separation

The verifier has access to rich internal state: subgoal progress, reward component breakdown, step count. This information is useful for debugging, analysis, and centralised training critics. However, it should not be part of the normal agent observation, as it would allow a policy to read benchmark internals rather than learn from the environment.

This is handled by separating evaluator information into `info["eval"]`. The top-level `info` dict returned from `step` contains only what an agent would normally observe: `success`, `message`, and `step`. The full evaluator state is nested under `info["eval"]` and is accessible for training infrastructure but not automatically part of the agent's input.

In a CTDE (Centralised Training, Decentralised Execution) setup, the training critic can condition on `info["eval"]["subgoals"]` for dense supervision signal, while execution policies operate only on per-agent observations.

## Design Decisions

### Why sequential turn-based execution

Enterprise workflows are naturally causal. One employee's action changes what the next employee can observe and do. Sequential turn-based execution models this correctly without requiring a parallel action encoder. True simultaneous multi-agent execution is possible with the experimental PettingZoo AEC adapter, but sequential execution is the default because it keeps the environment behaviour deterministic and inspectable.

### Why role-filtered observations

Global observability would reduce the environment to a single-agent coordination problem with cosmetic agent labels. Role-filtered observations force agents to communicate and hand off information explicitly, which is the actual research challenge. An engineer should not automatically know what the PM found in their Gmail inbox. The PM should have to relay that information through Slack or Jira for the engineer to act on it.

### Why shaped reward over sparse terminal reward

Tasks can require 8 to 17 subgoals and 25 to 45 steps. Sparse terminal reward makes credit assignment extremely difficult in this regime. Shaped reward fires at each subgoal unlock, giving the learning signal closer to the action that caused it. Anti-redundancy penalties prevent reward farming from repeated reads with no state change.

## Source Layout

```
src/enterprise_env/
    env.py                      # EnterpriseEnv (Gymnasium interface)
    repo.py                     # CompanyRepository (role-filtered DB access)
    apps/
        gmail.py
        slack.py
        jira.py
        calendar.py
        sheets.py
    tasks/
        base.py                 # BaseTask, subgoal dependency logic
        vendor_onboarding.py
        customer_incident.py
        product_launch.py
        meeting_conflict.py
        launch_readiness.py
        budget_approval.py
    rewards/
        reward.py               # Shaped reward + anti-hacking logic
    evaluation/
        runner.py               # Episode runner for oracle and scripted policies
        llm.py                  # LLM harness with retry, schema validation, failure taxonomy
    generation.py               # ScenarioFactory V1 (all 6 tasks)
    factory_v2/
        spec.py                 # CompanySpec dataclass
        world.py                # WorldGenerator (isolated seeded RNG)
        validator.py            # WorldValidator
        tasks/
            vendor_onboarding.py  # GeneratedVendorOnboardingTask
```
