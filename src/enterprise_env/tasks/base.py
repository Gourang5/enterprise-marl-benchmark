from __future__ import annotations
import re
from dataclasses import dataclass

# Matches negation words that can precede a keyword and invert its meaning.
# Window: we scan the 60 characters immediately before the keyword.
_NEG_RE = re.compile(
    r"\b(not|no|never|cannot|can't|isn't|wasn't|don't|doesn't|won't|"
    r"failed|rejected|declined|denied|unable|refuse|refusal|disagree|"
    r"disapprove|withhold|blocking|blocked|pending|missing|absent)\b",
    re.I,
)


def _affirms(text: str, keyword: str, window: int = 60) -> bool:
    """Return True iff *text* contains *keyword* without a negation in the preceding window.

    Prevents trivial verifier exploits such as ``"NOT approved"`` satisfying an
    ``"approved"`` check or ``"has NOT been validated"`` satisfying ``"validated"``.
    """
    lo = text.lower()
    klo = keyword.lower()
    idx = lo.find(klo)
    if idx == -1:
        return False
    prefix = lo[max(0, idx - window): idx]
    return not bool(_NEG_RE.search(prefix))


@dataclass(frozen=True)
class Subgoal:
    id: str
    description: str
    depends_on: tuple[str, ...] = ()


class BaseTask:
    task_id = ""
    name = ""
    instruction = ""
    max_steps = 30
    start_agent = "pm_01"

    def setup(self, repo, seed):
        raise NotImplementedError

    def subgoals(self):
        raise NotImplementedError

    def verify_subgoal(self, repo, g):
        raise NotImplementedError

    def achieved(self, repo, gid):
        sg = next(x for x in self.subgoals() if x.id == gid)
        if any(not self.achieved(repo, d) for d in sg.depends_on):
            return False
        return bool(self.verify_subgoal(repo, gid))

    def progress(self, repo):
        gs = self.subgoals()
        return sum(self.achieved(repo, x.id) for x in gs) / len(gs)

    def complete(self, repo):
        return all(self.achieved(repo, x.id) for x in self.subgoals())
