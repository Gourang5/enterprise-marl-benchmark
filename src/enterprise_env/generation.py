from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import random
from pathlib import Path
from .factory import make_env
from .tasks.factory import TASKS


@dataclass(frozen=True)
class Difficulty:
    name: str = "medium"
    max_steps: int | None = None
    distractors: int | None = None


PRESETS = {
    "easy":        Difficulty("easy",        None, 2),
    "medium":      Difficulty("medium",      None, 6),
    "hard":        Difficulty("hard",        None, 15),
    "adversarial": Difficulty("adversarial", None, 30),
}

# Realistic near-miss email subjects: same domain, different specifics
_DISTRACTOR_SUBJECTS = [
    "Quarterly VPN certificate renewal",
    "Sandbox API token expiry — dev cluster",
    "Analytics dashboard p95 latency note",
    "Mobile sign-in UX feedback — partner review",
    "Catalog webhook retry backlog cleared",
    "Conference travel request — Q3 summit",
    "Intern onboarding checklist reminder",
    "Non-prod load test scheduling window",
    "Post-launch retrospective date poll",
    "Docs site deployment rollback notice",
]

# Bodies look like real enterprise messages, just about the wrong thing
_DISTRACTOR_BODIES = [
    "Non-production certificate rotation — no action needed from platform team this week.",
    "The sandbox API token expired during last night's deployment; staging environments unaffected.",
    "P95 latency on the analytics dashboard increased by 120ms. Reads are available; write path unaffected.",
    "Partner shared UX notes on the mobile sign-in screen. No auth or API changes required.",
    "Webhook retry queue peaked at 4,200 items overnight; self-cleared by 06:00. No data loss.",
    "Approved travel to Q3 industry summit. Expense report due within 14 days of return.",
    "New intern joining the platform team next Monday. Laptop and access requests sent to IT.",
    "Load test window reserved for non-prod environment Saturday 22:00–02:00. Production unaffected.",
    "Retrospective date poll for the last sprint — please fill in your availability by EOD.",
    "Docs site was rolled back to the previous build after a broken anchor link was detected.",
]

# Jira noise titles/descriptions: plausible tickets, wrong project or already resolved
_JIRA_NOISE = [
    ("Quarterly access review — contractor accounts",
     "Standard contractor access review cycle. No changes expected for permanent employees."),
    ("Non-prod credential rotation",
     "Sandbox environment credential rotation per security policy; production unaffected."),
    ("Dashboard latency investigation",
     "Analytics dashboard occasional slowness. No production blocking; investigation ongoing."),
    ("Post-launch copy review follow-up",
     "Marketing copy review scheduled after launch week. No engineering dependency."),
    ("Observability metrics naming alignment",
     "Renaming internal histogram labels to match naming convention. No external impact."),
    ("Stale A/B experiment cleanup",
     "Experiment from three quarters ago needs archival; feature flags already disabled."),
    ("Release branch tag verification",
     "Verify release tag checksum after automated CI tagging step. Routine post-release check."),
]

# Slack noise: plausible channel messages, clearly off-topic
_SLACK_NOISE = [
    "Team lunch at noon — conference room 4B reserved.",
    "Reminder: weekly platform standup in 15 minutes.",
    "The espresso machine on floor 3 is back in service.",
    "Off-site planning doc has been shared in the team Drive folder.",
    "Friday wrap-up notes posted in the wiki. See you Monday!",
    "Heads up: building fire drill at 14:30 today, non-disruptive.",
]


@dataclass(frozen=True)
class ScenarioSpec:
    task_name: str
    seed: int
    difficulty: str
    split: str = "custom"


class ScenarioFactory:
    """Parameterized scenario factory for reproducible train/dev/test generation.

    Task families provide the core dependency DAG and verifier. The factory varies:
    - seed (determines distractor content and entity name suffixes)
    - distractor density (easy→adversarial)
    - step budget

    Architecture is designed to extend into org-topology variation, permission
    configuration, workflow-DAG swapping, and OOD entity splits — the factory
    plumbing is intentionally parameterized for those future axes.
    """

    def resolve_difficulty(self, difficulty="medium"):
        if isinstance(difficulty, Difficulty):
            return difficulty
        if difficulty not in PRESETS:
            raise ValueError(f"Unknown difficulty {difficulty}; choices={sorted(PRESETS)}")
        return PRESETS[difficulty]

    # Five fixed agent IDs present in every task family.
    AGENTS = ["pm_01", "eng_01", "product_01", "mgr_01", "cs_01"]

    def build(self, task_name="customer_incident", seed=42, difficulty="medium"):
        diff = self.resolve_difficulty(difficulty)
        env = make_env(task_name, diff.max_steps)
        obs, info = env.reset(seed)
        self._inject_distractors(env, seed, diff.distractors or 0)
        self.validate(env)
        info = dict(info)
        info.update({
            "difficulty":       diff.name,
            "distractors":      diff.distractors or 0,
            "validator_status": "passed",
        })
        return env, obs, info

    def blueprint(self, task_name="customer_incident", seed=42, difficulty="medium", split="custom"):
        diff = self.resolve_difficulty(difficulty)
        task = TASKS[task_name]()
        return {
            "scenario_id":      f"{task_name}_{int(seed)}_{diff.name}",
            "task_name":        task_name,
            "task_id":          task.task_id,
            "seed":             int(seed),
            "difficulty":       diff.name,
            "split":            split,
            "max_steps":        diff.max_steps or task.max_steps,
            "distractors":      diff.distractors,
            "apps":             self._task_apps(task_name),
            "agents":           self.AGENTS,
            "subgoal_count":    len(task.subgoals()),
            "validator_status": "pending",  # set to "passed" after build()+validate()
        }

    def generate_split(self, task_names=None, n=100, split="train", difficulty="medium", seed=0):
        names = list(task_names or sorted(TASKS))
        rng = random.Random(seed)
        specs = []
        # Disjoint seed ranges reduce accidental train/test overlap.
        split_offset = {"train": 0, "dev": 1_000_000, "test": 2_000_000}.get(split, 3_000_000)
        for i in range(n):
            task_name = names[i % len(names)]
            scenario_seed = split_offset + rng.randrange(1_000_000) + i
            specs.append(self.blueprint(task_name, scenario_seed, difficulty, split))
        return specs

    def export_dataset(self, output_dir, train=100, dev=20, test=50, difficulty="medium", seed=0):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        manifest = {
            "version": 1,
            "factory_seed": seed,
            "difficulty": self.resolve_difficulty(difficulty).name,
            "splits": {},
        }
        for split, n in (("train", train), ("dev", dev), ("test", test)):
            rows = self.generate_split(n=n, split=split, difficulty=difficulty, seed=seed)
            path = out / f"{split}.jsonl"
            path.write_text("\n".join(json.dumps(x, sort_keys=True) for x in rows) + ("\n" if rows else ""))
            manifest["splits"][split] = {"episodes": n, "file": path.name}
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return manifest

    def validate(self, env):
        if env.verifier.progress(env.repo) != 0.0:
            raise ValueError("Invalid scenario: task has free initial progress")
        goals = {x.id: x for x in env.task.subgoals()}
        for g in goals.values():
            for dep in g.depends_on:
                if dep not in goals:
                    raise ValueError(f"Unknown dependency {dep} for {g.id}")
        visiting, done = set(), set()

        def visit(gid):
            if gid in visiting:
                raise ValueError("Subgoal graph contains a cycle")
            if gid in done:
                return
            visiting.add(gid)
            for dep in goals[gid].depends_on:
                visit(dep)
            visiting.remove(gid)
            done.add(gid)

        for gid in goals:
            visit(gid)
        return True

    def _inject_distractors(self, env, seed: int, count: int):
        """Inject realistic near-miss distractors — same enterprise domain, wrong task."""
        rng = random.Random((seed + 1) * 7919)
        for i in range(count):
            sender    = rng.choice(["product_01", "mgr_01", "cs_01", "eng_01"])
            recipient = rng.choice(["pm_01", "product_01", "cs_01"])
            if sender == recipient:
                sender = "mgr_01"
            subject = rng.choice(_DISTRACTOR_SUBJECTS)
            body    = rng.choice(_DISTRACTOR_BODIES)
            # Vary subject with a seed-specific suffix so distractors differ across episodes
            suffix = f" (ref #{seed % 900 + 100 + i})"
            env.repo.add(
                "INSERT INTO emails VALUES(?,?,?,?,?,?,0)",
                (f"factory-noise-{seed}-{i}", sender, recipient, subject + suffix, body, 100 + i),
            )

        for i in range(min(count // 2 + 1, 3)):
            title, desc = rng.choice(_JIRA_NOISE)
            env.repo.add(
                "INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)",
                (
                    f"factory-noise-jira-{seed}-{i}", "PROJ-ALPHA",
                    f"{title} #{seed % 50 + i}", desc,
                    "open", "P3", None, "product_01",
                ),
            )

        for i in range(min(count // 3 + 1, 2)):
            sender  = rng.choice(["product_01", "mgr_01", "cs_01", "eng_01"])
            channel = rng.choice(["CH-RANDOM", "CH-PROJECT"])
            env.repo.add(
                "INSERT INTO slack_messages VALUES(?,?,?,?,?)",
                (
                    f"factory-noise-msg-{seed}-{i}", channel, sender,
                    rng.choice(_SLACK_NOISE), 50 + i,
                ),
            )

    @staticmethod
    def _task_apps(task_name):
        if task_name == "meeting_conflict":
            return ["gmail", "calendar", "slack"]
        if task_name in ("launch_readiness", "budget_approval", "vendor_onboarding"):
            return ["gmail", "slack", "jira", "sheets", "calendar"]
        return ["gmail", "slack", "jira", "calendar"]
