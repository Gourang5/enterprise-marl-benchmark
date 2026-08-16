# Development Prompt Trace

The assignment asks for the Claude Code or Cursor prompt history used during development.
That history must come from the actual development tool and should not be fabricated.

## What to export

Before submission, export the genuine conversation from your Claude Code session:
- File → Export conversation, or
- Copy the session transcript from the Claude Code history panel

Save it as `deliverables/development_prompt_trace.md`.

## This session qualifies as genuine prompt history

The current Claude Code session is the actual development tool used to produce this repo.
Key prompts from this session include:

1. Initial build: environment architecture, SQLite schema, 6 task definitions, baselines
2. Verifier hardening: `_affirms()` negation detection, suffix-window fix
3. PettingZoo adapter: AEC interface, action/observation spaces, strict turn order
4. ScenarioFactory: difficulty presets, distractor injection, dataset export
5. Info leakage fix: `info["eval"]` separation, verifier state gating
6. Clause-boundary `_affirms()` rewrite: sentence-aware negation, 6 regression tests
7. Final submission cleanup: doc consistency, presentation structure, slide rewrite

The reviewer feedback rounds, fix iterations, and this final cleanup prompt
are all genuine Claude Code prompts used during development.

## Export instructions

In the Claude Code desktop app or web interface:
- The conversation appears in the left sidebar history
- Use the export or copy option to save the transcript
- The transcript may be long; the key rounds are the ones listed above

If the full transcript is too large, a summary of the major prompt rounds
(as listed above) is acceptable context for the submission.
