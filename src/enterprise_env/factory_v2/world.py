"""WorldGenerator and GeneratedWorld for factory_v2.

Generates deterministic entity sets from a CompanySpec seed.
Same seed → same world. Different seed → different employees, vendor, IDs.

Legacy / static environments are not touched.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from .spec import CompanySpec
from .names import FIRST_NAMES, LAST_NAMES, VENDOR_ADJECTIVES, VENDOR_NOUNS

# Static role list — same 5 roles as legacy, agent IDs stay fixed.
# Changing agent IDs would break verifiers and Ollama prompts.
ROLE_AGENTS = [
    ("pm_01",      "project_manager"),
    ("eng_01",     "engineer"),
    ("product_01", "product_manager"),
    ("mgr_01",     "engineering_manager"),
    ("cs_01",      "customer_success"),
]

ROLE_TEAM = {
    "project_manager":    "team_pm",
    "engineer":           "team_platform",
    "product_manager":    "team_product",
    "engineering_manager":"team_platform",
    "customer_success":   "team_cs",
}


@dataclass
class EmployeeRecord:
    agent_id:   str
    role:       str
    first_name: str
    last_name:  str
    email:      str
    team_id:    str

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class VendorRecord:
    name:          str
    ticket_prefix: str   # 3-4 uppercase letters
    main_ticket:   str   # e.g. "SYNC-401"
    legal_ticket:  str   # e.g. "SYNC-402"
    it_ticket:     str   # e.g. "SYNC-403"
    email_id:      str   # e.g. "vendor-req-42-001"
    sheet_id:      str   # e.g. "SHEET-VENDOR-42"
    channel_id:    str   # e.g. "CH-PROC-42"


@dataclass
class GeneratedWorld:
    spec:              CompanySpec
    employees:         list[EmployeeRecord]
    vendor:            VendorRecord
    fingerprint:       str = ""
    validation_status: str = "pending"

    def employee_by_id(self, agent_id: str) -> EmployeeRecord | None:
        return next((e for e in self.employees if e.agent_id == agent_id), None)

    def employee_by_role(self, role: str) -> EmployeeRecord | None:
        return next((e for e in self.employees if e.role == role), None)


class WorldGenerator:
    """Deterministically generates a GeneratedWorld from a CompanySpec.

    Uses an isolated seeded RNG — does not affect global random state.
    """

    def __init__(self, spec: CompanySpec):
        self.spec = spec
        self.rng = random.Random(spec.seed)

    def generate(self) -> GeneratedWorld:
        employees = self._gen_employees()
        vendor = self._gen_vendor()
        return GeneratedWorld(spec=self.spec, employees=employees, vendor=vendor)

    # ------------------------------------------------------------------
    # Internal generators
    # ------------------------------------------------------------------

    def _gen_employees(self) -> list[EmployeeRecord]:
        domain = self._company_domain()
        used_first: set[str] = set()
        result = []
        for agent_id, role in ROLE_AGENTS:
            first = self._pick_unique(FIRST_NAMES, used_first)
            used_first.add(first)
            last = self.rng.choice(LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}@{domain}"
            result.append(EmployeeRecord(
                agent_id=agent_id,
                role=role,
                first_name=first,
                last_name=last,
                email=email,
                team_id=ROLE_TEAM[role],
            ))
        return result

    def _gen_vendor(self) -> VendorRecord:
        adj  = self.rng.choice(VENDOR_ADJECTIVES)
        noun = self.rng.choice(VENDOR_NOUNS)
        name = f"{adj} {noun}"
        # Ticket prefix: first 4 letters of noun, uppercase.
        # Guaranteed >= 4 chars since shortest noun is "Labs" (4).
        prefix = noun[:4].upper()
        seed   = self.spec.seed
        return VendorRecord(
            name=name,
            ticket_prefix=prefix,
            main_ticket=f"{prefix}-401",
            legal_ticket=f"{prefix}-402",
            it_ticket=f"{prefix}-403",
            email_id=f"vendor-req-{seed}-001",
            sheet_id=f"SHEET-VENDOR-{seed}",
            channel_id=f"CH-PROC-{seed}",
        )

    def _company_domain(self) -> str:
        slug = self.spec.company_name.lower().replace(" ", "")
        return f"{slug}-sim.test"

    def _pick_unique(self, pool: list[str], used: set[str]) -> str:
        candidates = [x for x in pool if x not in used]
        if not candidates:
            candidates = pool  # fallback if pool exhausted
        return self.rng.choice(candidates)
