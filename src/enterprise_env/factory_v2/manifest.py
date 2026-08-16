"""Manifest builder and fingerprint for factory_v2 generated worlds.

Generated manifests use schema_version: 2 to distinguish them from
legacy version-1 manifests in generated_scenarios/. Old manifests
are not touched.
"""
from __future__ import annotations
import hashlib
import json
from .world import GeneratedWorld


def compute_fingerprint(world: GeneratedWorld) -> str:
    """SHA-256 fingerprint of the world's stable configuration.

    Depends only on seed + generated entities — not on timestamps or
    runtime noise. Same seed → same fingerprint. Different seed → different.
    """
    stable = {
        "seed":       world.spec.seed,
        "company":    world.spec.company_name,
        "scenario":   world.spec.scenario,
        "difficulty": world.spec.difficulty,
        "employees": sorted(
            [
                {
                    "agent_id": e.agent_id,
                    "role":     e.role,
                    "name":     e.display_name,
                    "email":    e.email,
                }
                for e in world.employees
            ],
            key=lambda x: x["agent_id"],
        ),
        "vendor": {
            "name":          world.vendor.name,
            "ticket_prefix": world.vendor.ticket_prefix,
            "main_ticket":   world.vendor.main_ticket,
            "legal_ticket":  world.vendor.legal_ticket,
            "it_ticket":     world.vendor.it_ticket,
        },
    }
    canonical = json.dumps(stable, sort_keys=True, ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


def build_manifest(world: GeneratedWorld) -> dict:
    """Return a dict suitable for JSON serialization as the world manifest."""
    return {
        "schema_version":    2,
        "factory_version":   "1.0",
        "seed":              world.spec.seed,
        "company":           world.spec.company_name,
        "scenario":          world.spec.scenario,
        "difficulty":        world.spec.difficulty,
        "employees": [
            {
                "agent_id": e.agent_id,
                "role":     e.role,
                "name":     e.display_name,
                "email":    e.email,
                "team_id":  e.team_id,
            }
            for e in world.employees
        ],
        "vendor": {
            "name":          world.vendor.name,
            "ticket_prefix": world.vendor.ticket_prefix,
            "main_ticket":   world.vendor.main_ticket,
            "legal_ticket":  world.vendor.legal_ticket,
            "it_ticket":     world.vendor.it_ticket,
            "email_id":      world.vendor.email_id,
            "sheet_id":      world.vendor.sheet_id,
            "channel_id":    world.vendor.channel_id,
        },
        "enabled_apps":      ["gmail", "slack", "jira", "calendar", "sheets"],
        "dag_summary":       "discover->find_ticket->(legal_review||it_provisioning)->manager_approval->update_sheet->schedule_kickoff->announce",
        "validation_status": world.validation_status,
        "fingerprint":       world.fingerprint,
    }
