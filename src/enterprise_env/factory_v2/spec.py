"""CompanySpec — declarative configuration for generated worlds.

This is the entry point for factory_v2 generated mode. Legacy / static
environments do not use this class and are not affected by it.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class CompanySpec:
    """Declarative spec for a deterministically generated enterprise world.

    Same seed + same spec → identical generated world, always.
    Different seed → different employees, vendor, and IDs.

    Args:
        seed: Integer seed for all entity generation.
        company_name: Display name of the host company.
        scenario: Task scenario to generate for. Currently "vendor_onboarding".
        difficulty: Distractor density preset ("easy"/"medium"/"hard"/"adversarial").
    """
    seed: int
    company_name: str = "GlobalTech Corp"
    scenario: str = "vendor_onboarding"
    difficulty: str = "medium"
    schema_version: int = 2
