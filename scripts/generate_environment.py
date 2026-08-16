#!/usr/bin/env python3
"""Factory v2 demo command.

Usage:
    python scripts/generate_environment.py --seed 42 --scenario vendor_onboarding
    python scripts/generate_environment.py --seed 43 --scenario vendor_onboarding

Does NOT require Ollama. Shows deterministic entity generation and validation.

Existing / static environment and evaluation commands are unaffected.
"""
from __future__ import annotations
import argparse
import json
import sys

from enterprise_env.factory_v2 import (
    CompanySpec,
    generate_world,
    run_generated_episode,
    build_manifest,
)
from enterprise_env.factory_v2.validator import ValidationError


def main() -> None:
    ap = argparse.ArgumentParser(
        description="factory_v2: generate a deterministic enterprise world from a seed"
    )
    ap.add_argument("--seed",     type=int, default=42,
                    help="Integer seed (default: 42)")
    ap.add_argument("--scenario", default="vendor_onboarding",
                    choices=["vendor_onboarding"],
                    help="Task scenario to generate")
    ap.add_argument("--difficulty", default="medium",
                    choices=["easy", "medium", "hard", "adversarial"],
                    help="Distractor density preset (default: medium)")
    ap.add_argument("--company", default="GlobalTech Corp",
                    help="Host company display name")
    ap.add_argument("--json",   action="store_true",
                    help="Output full manifest as JSON instead of summary")
    ap.add_argument("--run-oracle", action="store_true",
                    help="Also run oracle baseline to verify solvability")
    args = ap.parse_args()

    spec = CompanySpec(
        seed=args.seed,
        company_name=args.company,
        scenario=args.scenario,
        difficulty=args.difficulty,
    )

    try:
        world = generate_world(spec, validate=True)
    except ValidationError as e:
        print(f"VALIDATION FAILED:\n{e}", file=sys.stderr)
        sys.exit(1)

    manifest = build_manifest(world)

    if args.json:
        print(json.dumps(manifest, indent=2))
        return

    # --- Human-readable summary ---
    v  = world.vendor
    pm   = world.employee_by_role("project_manager")
    eng  = world.employee_by_role("engineer")
    prod = world.employee_by_role("product_manager")
    mgr  = world.employee_by_role("engineering_manager")
    cs   = world.employee_by_role("customer_success")

    print(f"")
    print(f"Factory mode : generated (factory_v2)")
    print(f"Seed         : {world.spec.seed}")
    print(f"Company      : {world.spec.company_name}")
    print(f"Scenario     : {world.spec.scenario}")
    print(f"Difficulty   : {world.spec.difficulty}")
    print(f"")
    print(f"Employees")
    print(f"  {pm.agent_id:<12} {pm.role:<22} {pm.display_name}  <{pm.email}>")
    print(f"  {eng.agent_id:<12} {eng.role:<22} {eng.display_name}  <{eng.email}>")
    print(f"  {prod.agent_id:<12} {prod.role:<22} {prod.display_name}  <{prod.email}>")
    print(f"  {mgr.agent_id:<12} {mgr.role:<22} {mgr.display_name}  <{mgr.email}>")
    print(f"  {cs.agent_id:<12} {cs.role:<22} {cs.display_name}  <{cs.email}>")
    print(f"")
    print(f"Vendor       : {v.name}")
    print(f"Tickets      : {v.main_ticket}  {v.legal_ticket}  {v.it_ticket}")
    print(f"Sheet ID     : {v.sheet_id}")
    print(f"Channel ID   : {v.channel_id}")
    print(f"")
    print(f"DAG          : discover->find_ticket->(legal_review||it_provisioning)->"
          f"manager_approval->update_sheet->schedule_kickoff->announce")
    print(f"")
    print(f"Validation   : {world.validation_status}")
    print(f"Fingerprint  : {world.fingerprint}")
    print(f"")

    if args.run_oracle:
        print("Running oracle baseline to verify solvability...")
        result = run_generated_episode(world)
        sr = "PASS" if result["success"] else "FAIL"
        print(f"Oracle result: {sr}  |  steps={result['steps']}"
              f"  reward={result['reward']:.2f}  progress={result['progress']:.0%}")
        if not result["success"]:
            print(f"  policy_error: {result['policy_error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
