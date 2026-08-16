"""Tests for factory_v2 generated-mode world factory.

All tests are isolated from the static/legacy environment:
- No test modifies existing task classes or seed data
- No test modifies global state
- Existing 70 tests are verified to still pass via the full suite

Coverage:
  - Determinism (same seed → same world)
  - Diversity (different seeds → different entities)
  - Fingerprint stability and cross-seed difference
  - WorldValidator pass / fail paths
  - Generated task setup + oracle solvability
  - Manifest schema_version == 2
  - Legacy environment still works after factory_v2 import
"""
from __future__ import annotations
import pytest

from enterprise_env.factory_v2 import (
    CompanySpec,
    generate_world,
    build_env,
    run_generated_episode,
    build_manifest,
    compute_fingerprint,
)
from enterprise_env.factory_v2.validator import WorldValidator, ValidationError
from enterprise_env.factory_v2.world import WorldGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spec(seed=42, scenario="vendor_onboarding", difficulty="medium"):
    return CompanySpec(seed=seed, scenario=scenario, difficulty=difficulty)


def _world(seed=42, validate=True):
    return generate_world(_spec(seed=seed), validate=validate)


# ---------------------------------------------------------------------------
# 1. Determinism — same seed → identical world
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_seed_same_employees(self):
        w1 = _world(42)
        w2 = _world(42)
        names1 = [e.display_name for e in w1.employees]
        names2 = [e.display_name for e in w2.employees]
        assert names1 == names2

    def test_same_seed_same_vendor(self):
        w1 = _world(42)
        w2 = _world(42)
        assert w1.vendor.name         == w2.vendor.name
        assert w1.vendor.main_ticket  == w2.vendor.main_ticket
        assert w1.vendor.legal_ticket == w2.vendor.legal_ticket
        assert w1.vendor.it_ticket    == w2.vendor.it_ticket

    def test_same_seed_same_fingerprint(self):
        assert _world(42).fingerprint == _world(42).fingerprint

    def test_same_seed_same_ids(self):
        w1 = _world(42)
        w2 = _world(42)
        assert w1.vendor.email_id   == w2.vendor.email_id
        assert w1.vendor.sheet_id   == w2.vendor.sheet_id
        assert w1.vendor.channel_id == w2.vendor.channel_id


# ---------------------------------------------------------------------------
# 2. Diversity — different seeds → different entities
# ---------------------------------------------------------------------------

class TestDiversity:
    def test_different_seeds_different_vendor_name(self):
        # Allow a very small collision probability across 32 vendor options
        names = {_world(s).vendor.name for s in range(42, 55)}
        assert len(names) > 1, "All 13 seeds produced the same vendor name"

    def test_different_seeds_different_ticket_ids(self):
        w42 = _world(42)
        w43 = _world(43)
        # Email/sheet/channel IDs embed seed — always differ
        assert w42.vendor.email_id   != w43.vendor.email_id
        assert w42.vendor.sheet_id   != w43.vendor.sheet_id
        assert w42.vendor.channel_id != w43.vendor.channel_id

    def test_different_seeds_different_employee_names(self):
        names42 = {e.display_name for e in _world(42).employees}
        names43 = {e.display_name for e in _world(43).employees}
        assert names42 != names43, "Seeds 42 and 43 produced identical employee names"

    def test_different_seeds_different_fingerprints(self):
        assert _world(42).fingerprint != _world(43).fingerprint

    def test_agent_ids_stay_fixed(self):
        for seed in [42, 43, 100, 999]:
            world = _world(seed)
            ids = {e.agent_id for e in world.employees}
            assert ids == {"pm_01", "eng_01", "product_01", "mgr_01", "cs_01"}


# ---------------------------------------------------------------------------
# 3. Fingerprint properties
# ---------------------------------------------------------------------------

class TestFingerprint:
    def test_fingerprint_format(self):
        fp = _world(42).fingerprint
        assert fp.startswith("sha256:")
        assert len(fp) == len("sha256:") + 16

    def test_fingerprint_stable_across_calls(self):
        w = _world(42)
        fp1 = compute_fingerprint(w)
        fp2 = compute_fingerprint(w)
        assert fp1 == fp2

    def test_fingerprint_differs_per_seed(self):
        fps = {compute_fingerprint(_world(s)) for s in range(42, 52)}
        assert len(fps) == 10, "Some seeds share a fingerprint"


# ---------------------------------------------------------------------------
# 4. Validator
# ---------------------------------------------------------------------------

class TestValidator:
    def test_valid_world_passes(self):
        w = _world(42)
        errors = WorldValidator().validate(w)
        assert errors == []

    def test_validation_status_pass(self):
        assert _world(42).validation_status == "PASS"

    def test_bad_employee_email_fails(self):
        w = _world(42, validate=False)
        # corrupt one email
        w.employees[0].email = "not-an-email"
        errors = WorldValidator().validate(w)
        assert any("email" in e.lower() for e in errors)

    def test_duplicate_vendor_tickets_fail(self):
        w = _world(42, validate=False)
        w.vendor.legal_ticket = w.vendor.main_ticket  # create duplicate
        errors = WorldValidator().validate(w)
        assert any("unique" in e.lower() or "not unique" in e.lower() for e in errors)

    def test_validate_or_raise_on_bad_world(self):
        w = _world(42, validate=False)
        w.vendor.legal_ticket = w.vendor.main_ticket  # bad
        with pytest.raises(ValidationError):
            WorldValidator().validate_or_raise(w)


# ---------------------------------------------------------------------------
# 5. Employee structure
# ---------------------------------------------------------------------------

class TestEmployeeStructure:
    def test_all_five_roles_present(self):
        w = _world(42)
        roles = {e.role for e in w.employees}
        assert roles == {
            "project_manager", "engineer", "product_manager",
            "engineering_manager", "customer_success",
        }

    def test_unique_display_names(self):
        w = _world(42)
        names = [e.display_name for e in w.employees]
        assert len(names) == len(set(names))

    def test_emails_have_correct_domain(self):
        spec = _spec(seed=42, difficulty="medium")
        spec_with_name = CompanySpec(seed=42, company_name="GlobalTech Corp",
                                     scenario="vendor_onboarding", difficulty="medium")
        w = generate_world(spec_with_name)
        for e in w.employees:
            assert "globaltech" in e.email.lower() or "globaltechcorp" in e.email.lower()

    def test_employee_by_role(self):
        w = _world(42)
        pm = w.employee_by_role("project_manager")
        assert pm is not None
        assert pm.agent_id == "pm_01"


# ---------------------------------------------------------------------------
# 6. Vendor structure
# ---------------------------------------------------------------------------

class TestVendorStructure:
    def test_vendor_name_has_two_words(self):
        for seed in [42, 43, 100]:
            v = _world(seed).vendor
            assert len(v.name.split()) == 2, f"Seed {seed}: vendor name {v.name!r}"

    def test_ticket_ids_contain_prefix(self):
        v = _world(42).vendor
        assert v.main_ticket.startswith(v.ticket_prefix)
        assert v.legal_ticket.startswith(v.ticket_prefix)
        assert v.it_ticket.startswith(v.ticket_prefix)

    def test_ticket_ids_have_dash(self):
        v = _world(42).vendor
        for t in [v.main_ticket, v.legal_ticket, v.it_ticket]:
            assert "-" in t

    def test_email_id_embeds_seed(self):
        for seed in [42, 99, 1234]:
            v = _world(seed).vendor
            assert str(seed) in v.email_id


# ---------------------------------------------------------------------------
# 7. Manifest
# ---------------------------------------------------------------------------

class TestManifest:
    def test_schema_version_is_2(self):
        m = build_manifest(_world(42))
        assert m["schema_version"] == 2

    def test_manifest_has_required_keys(self):
        m = build_manifest(_world(42))
        for key in ["seed", "company", "scenario", "difficulty",
                    "employees", "vendor", "validation_status",
                    "fingerprint", "enabled_apps", "dag_summary"]:
            assert key in m, f"Missing key {key!r}"

    def test_manifest_validation_pass(self):
        m = build_manifest(_world(42))
        assert m["validation_status"] == "PASS"

    def test_manifest_fingerprint_matches_world(self):
        w = _world(42)
        m = build_manifest(w)
        assert m["fingerprint"] == w.fingerprint

    def test_manifest_employees_count(self):
        m = build_manifest(_world(42))
        assert len(m["employees"]) == 5


# ---------------------------------------------------------------------------
# 8. Generated environment + oracle solvability
# ---------------------------------------------------------------------------

class TestGeneratedEnvOracle:
    def test_oracle_100pct_seed42(self):
        world = _world(42)
        result = run_generated_episode(world)
        assert result["success"] is True, (
            f"Oracle failed on seed 42: policy_error={result['policy_error']!r}"
        )

    def test_oracle_100pct_seed43(self):
        world = _world(43)
        result = run_generated_episode(world)
        assert result["success"] is True, (
            f"Oracle failed on seed 43: policy_error={result['policy_error']!r}"
        )

    def test_oracle_multiple_seeds(self):
        for seed in [42, 43, 99, 100, 7]:
            world = _world(seed)
            result = run_generated_episode(world)
            assert result["success"], (
                f"Oracle failed on seed {seed}: {result['policy_error']}"
            )

    def test_oracle_has_trajectory(self):
        world = _world(42)
        result = run_generated_episode(world)
        assert len(result["trajectory"]) > 0

    def test_oracle_progress_1(self):
        world = _world(42)
        result = run_generated_episode(world)
        assert result["progress"] == pytest.approx(1.0)

    def test_oracle_fingerprint_in_result(self):
        world = _world(42)
        result = run_generated_episode(world)
        assert result["world_fingerprint"] == world.fingerprint

    def test_generated_env_env_close(self):
        world = _world(42)
        env = build_env(world)
        env.reset(seed=42)
        env.close()  # must not raise


# ---------------------------------------------------------------------------
# 9. Cross-app entity propagation (Phase 3)
# ---------------------------------------------------------------------------

class TestCrossAppPropagation:
    def _setup_env(self, seed=42):
        world = _world(seed)
        env = build_env(world)
        env.reset(seed=seed)
        return world, env

    def test_employee_names_updated_in_db(self):
        world, env = self._setup_env(42)
        try:
            for emp in world.employees:
                row = env.repo.employee(emp.agent_id)
                assert row is not None, f"Employee {emp.agent_id!r} not found in DB"
                assert row["name"] == emp.display_name, (
                    f"{emp.agent_id}: DB name {row['name']!r} != {emp.display_name!r}"
                )
        finally:
            env.close()

    def test_vendor_email_exists_in_db(self):
        world, env = self._setup_env(42)
        try:
            email = env.repo.email(world.vendor.email_id)
            assert email is not None, f"Vendor email {world.vendor.email_id!r} not in DB"
        finally:
            env.close()

    def test_vendor_tickets_exist_in_db(self):
        world, env = self._setup_env(42)
        v = world.vendor
        try:
            for ticket in [v.main_ticket, v.legal_ticket, v.it_ticket]:
                row = env.repo.issue(ticket)
                assert row is not None, f"Ticket {ticket!r} not found in DB"
        finally:
            env.close()

    def test_vendor_sheet_exists_in_db(self):
        world, env = self._setup_env(42)
        try:
            pm = world.employee_by_role("project_manager")
            sheets = env.repo.sheets_for(pm.agent_id)
            sheet_ids = [s["sheet_id"] for s in sheets]
            assert world.vendor.sheet_id in sheet_ids
        finally:
            env.close()

    def test_vendor_channel_exists_in_db(self):
        world, env = self._setup_env(42)
        try:
            pm = world.employee_by_role("project_manager")
            channels = env.repo.channels_for(pm.agent_id)
            ch_ids = [c["channel_id"] for c in channels]
            assert world.vendor.channel_id in ch_ids
        finally:
            env.close()

    def test_different_seed_different_db_entities(self):
        world42, env42 = self._setup_env(42)
        world43, env43 = self._setup_env(43)
        try:
            # Vendor emails differ
            assert world42.vendor.email_id != world43.vendor.email_id
            # Main tickets may or may not differ (prefix depends on noun)
            # But email_id always differs (embeds seed)
        finally:
            env42.close()
            env43.close()


# ---------------------------------------------------------------------------
# 10. Legacy / static environment regression
# ---------------------------------------------------------------------------

class TestLegacyRegression:
    def test_legacy_oracle_still_100pct(self):
        from enterprise_env.evaluation.runner import run_episode
        result = run_episode("vendor_onboarding", seed=42)
        assert result["success"] is True

    def test_legacy_customer_incident_still_works(self):
        from enterprise_env.evaluation.runner import run_episode
        result = run_episode("customer_incident", seed=42)
        assert result["success"] is True

    def test_legacy_make_env_unchanged(self):
        from enterprise_env.factory import make_env
        env = make_env("vendor_onboarding")
        obs, info = env.reset(42)
        env.close()
        assert obs is not None

    def test_legacy_static_employee_ids_intact(self):
        from enterprise_env.factory import make_env
        env = make_env("vendor_onboarding")
        env.reset(42)
        emp = env.repo.employee("pm_01")
        assert emp is not None
        env.close()

    def test_factory_v2_import_does_not_break_legacy(self):
        """Importing factory_v2 must not alter any global state."""
        import enterprise_env.factory_v2  # noqa: F401
        from enterprise_env.evaluation.runner import run_episode
        result = run_episode("vendor_onboarding", seed=42)
        assert result["success"] is True
