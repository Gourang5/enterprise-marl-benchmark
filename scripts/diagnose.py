#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from enterprise_env.evaluation.llm import make_client, OLLAMA_DEFAULT_MODEL
from enterprise_env.factory import make_env


def main():
    p=argparse.ArgumentParser(description="Check benchmark fixtures, search semantics, and Ollama readiness.")
    p.add_argument("--model", default=OLLAMA_DEFAULT_MODEL)
    p.add_argument("--base-url", default=None)
    p.add_argument("--skip-ollama", action="store_true")
    args=p.parse_args()
    checks=[]

    env=make_env("customer_incident")
    env.reset(seed=100)
    email_hits=env.repo.search_emails("pm_01","authentication outage")
    jira_hits=env.repo.search_issues("production authentication outage")
    checks.append(("email_search", bool(email_hits) and email_hits[0]["email_id"]=="seed-email-001", email_hits[:3]))
    checks.append(("jira_search", bool(jira_hits) and jira_hits[0]["issue_id"]=="INC-421", jira_hits[:3]))
    env.close()

    if not args.skip_ollama:
        try:
            status=make_client("ollama",args.model,base_url=args.base_url).preflight()
            checks.append(("ollama",True,status))
        except Exception as exc:
            checks.append(("ollama",False,str(exc)))

    ok=True
    for name,passed,detail in checks:
        ok &= passed
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {json.dumps(detail, default=str)}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
