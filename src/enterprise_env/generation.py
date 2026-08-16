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
    "easy": Difficulty("easy", None, 2),
    "medium": Difficulty("medium", None, 6),
    "hard": Difficulty("hard", None, 15),
    "adversarial": Difficulty("adversarial", None, 30),
}


@dataclass(frozen=True)
class ScenarioSpec:
    task_name: str
    seed: int
    difficulty: str
    split: str = "custom"


class ScenarioFactory:
    """Parameterized scenario factory for reproducible train/dev/test generation.

    Task families provide the core dependency DAG and verifier. The factory varies seed,
    distractor density, step budget, and split membership while preserving deterministic
    replay and exact solvability checks.
    """

    def resolve_difficulty(self, difficulty="medium"):
        if isinstance(difficulty, Difficulty):
            return difficulty
        if difficulty not in PRESETS:
            raise ValueError(f"Unknown difficulty {difficulty}; choices={sorted(PRESETS)}")
        return PRESETS[difficulty]

    def build(self, task_name="customer_incident", seed=42, difficulty="medium"):
        diff = self.resolve_difficulty(difficulty)
        env = make_env(task_name, diff.max_steps)
        obs, info = env.reset(seed)
        self._inject_distractors(env, seed, diff.distractors or 0)
        self.validate(env)
        info = dict(info)
        info.update({"difficulty": diff.name, "distractors": diff.distractors or 0})
        return env, obs, info

    def blueprint(self, task_name="customer_incident", seed=42, difficulty="medium", split="custom"):
        diff = self.resolve_difficulty(difficulty)
        task = TASKS[task_name]()
        return {
            "task_name": task_name,
            "task_id": task.task_id,
            "seed": int(seed),
            "difficulty": diff.name,
            "split": split,
            "max_steps": diff.max_steps or task.max_steps,
            "distractors": diff.distractors,
            "apps": self._task_apps(task_name),
            "subgoal_count": len(task.subgoals()),
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

    def _inject_distractors(self, env, seed, count):
        rng = random.Random((seed + 1) * 7919)
        subjects = [
            "Routine access review", "Sandbox credential rotation", "Copy review follow-up",
            "Dashboard cleanup", "Travel planning", "Invoice formatting", "Non-prod latency note",
        ]
        for i in range(count):
            sender = rng.choice(["product_01", "mgr_01", "cs_01", "eng_01"])
            recipient = rng.choice(["pm_01", "product_01", "cs_01"])
            if sender == recipient:
                sender = "mgr_01"
            subject = rng.choice(subjects)
            env.repo.add(
                "INSERT INTO emails VALUES(?,?,?,?,?,?,0)",
                (f"factory-noise-{seed}-{i}", sender, recipient, f"{subject} #{i}", "Routine synthetic distractor; not relevant to the active task.", 100 + i),
            )
        # Jira noise: low-priority tickets that look plausible but are not related to the task
        jira_noise = [
            ("Routine access review", "Standard quarterly access review cycle."),
            ("Non-prod credential rotation", "Sandbox environment credential rotation."),
            ("Dashboard latency note", "Analytics dashboard occasional slowness; not production-blocking."),
            ("Copy review follow-up", "Marketing copy review; post-launch task."),
            ("Metrics naming cleanup", "Observability housekeeping; no launch dependency."),
        ]
        for i in range(min(count // 2 + 1, 3)):
            title, desc = rng.choice(jira_noise)
            env.repo.add(
                "INSERT INTO jira_issues VALUES(?,?,?,?,?,?,?,?)",
                (f"factory-noise-jira-{seed}-{i}", "PROJ-ALPHA", f"{title} #{i}", desc, "open", "P3", None, "product_01"),
            )
        # Slack noise: benign messages in random channels
        slack_noise = [
            "Team lunch at noon, anyone interested?",
            "Reminder: weekly standup in 15 minutes.",
            "Coffee machine on floor 3 is fixed.",
            "Off-site planning doc shared in Drive.",
        ]
        for i in range(min(count // 3 + 1, 2)):
            sender = rng.choice(["product_01", "mgr_01", "cs_01", "eng_01"])
            channel = rng.choice(["CH-RANDOM", "CH-PROJECT"])
            env.repo.add(
                "INSERT INTO slack_messages VALUES(?,?,?,?,?)",
                (f"factory-noise-msg-{seed}-{i}", channel, sender, rng.choice(slack_noise), 50 + i),
            )

    @staticmethod
    def _task_apps(task_name):
        if task_name == "meeting_conflict":
            return ["gmail", "calendar", "slack"]
        if task_name in ("launch_readiness", "budget_approval", "vendor_onboarding"):
            return ["gmail", "slack", "jira", "sheets", "calendar"]
        return ["gmail", "slack", "jira", "calendar"]
