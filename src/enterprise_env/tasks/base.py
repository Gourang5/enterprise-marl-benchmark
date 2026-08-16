from __future__ import annotations
import re
from dataclasses import dataclass

# Full negation list — used for prefix checks within the keyword's sentence
# and for the yes/no-question answer check.
_NEG_RE = re.compile(
    r"\b(not|no|never|cannot|can't|isn't|wasn't|don't|doesn't|won't|"
    r"failed|rejected|declined|denied|unable|refuse|refusal|disagree|"
    r"disapprove|withhold|blocking|blocked|pending|missing|absent)\b",
    re.I,
)

# Suffix-only negation — excludes bare "no" because enterprise phrases like
# "no issues found", "no further action required", "no blockers" appear in the
# suffix of affirmative statements and must not block a valid match.
_STRONG_POST_NEG_RE = re.compile(
    r"\b(not|never|cannot|can't|isn't|wasn't|won't|"
    r"rejected|declined|denied|refused|disapproved)\b",
    re.I,
)

# Characters that mark a sentence / clause boundary.
_SENT_SEP = frozenset('.!?;')


def _affirms(text: str, keyword: str, window: int = 60) -> bool:
    """Return True iff *text* affirmatively contains *keyword*.

    Uses clause-boundary–aware negation scoping rather than a fixed character
    window, so cross-sentence negation does not block a valid affirmation:

    - ``"Not approved"``                          → False  (pre-keyword negation)
    - ``"Approved? No, rejected."``               → False  (question-answer)
    - ``"Approved. No further action required."`` → True   (different sentence)
    - ``"Validated, no issues found."``           → True   (bare "no" ≠ negation)
    - ``"Previous rejected. This one approved."`` → True   (negation in prior sentence)

    *window* is retained for API compatibility but is not used; sentence
    boundaries replace the fixed-width scan.
    """
    lo = text.lower()
    klo = keyword.lower()
    idx = lo.find(klo)
    if idx == -1:
        return False
    end = idx + len(klo)

    # Find the sentence that contains the keyword.
    sent_start = 0
    for ci in range(idx - 1, -1, -1):
        if lo[ci] in _SENT_SEP:
            sent_start = ci + 1
            break

    sent_end = len(lo)
    for ci in range(idx, len(lo)):
        if lo[ci] in _SENT_SEP:
            sent_end = ci
            break

    # 1. Negation anywhere in the sentence before the keyword.
    if _NEG_RE.search(lo[sent_start:idx]):
        return False

    # 2. Yes/no-question pattern: keyword immediately followed by '?'
    #    The next clause may be a direct "No" answer — treat that as negation.
    trail = lo[end: end + 5].lstrip()
    if trail.startswith('?'):
        q_pos = lo.index('?', end)
        next_clause = lo[q_pos + 1: q_pos + 20].lstrip()
        if next_clause and _NEG_RE.search(next_clause[:15]):
            return False

    # 3. Strong negation within the same sentence after the keyword.
    if _STRONG_POST_NEG_RE.search(lo[end:sent_end]):
        return False

    return True


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
