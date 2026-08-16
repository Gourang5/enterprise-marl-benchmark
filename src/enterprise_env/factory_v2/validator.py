"""Standalone validator for factory_v2 GeneratedWorld instances.

Validates without needing a running environment or Ollama.
Fails loudly with descriptive errors — no silent repair.
"""
from __future__ import annotations
from .world import GeneratedWorld

# Permissions by role — mirrors database/seed.py PERMISSIONS dict.
# Kept here so the validator is self-contained (no DB required).
_PERMISSIONS: dict[str, set[str]] = {
    "project_manager": {
        "gmail.read_email", "gmail.search_emails", "gmail.send_email",
        "slack.read_channel", "slack.search_messages", "slack.send_message",
        "jira.search_issues", "jira.read_issue", "jira.assign_issue",
        "jira.add_comment", "jira.change_status",
        "calendar.read_calendar", "calendar.create_event", "calendar.reschedule_event",
        "sheets.list_sheets", "sheets.read_sheet", "sheets.update_cell", "sheets.append_row",
    },
    "engineer": {
        "gmail.read_email", "gmail.search_emails", "gmail.send_email",
        "slack.read_channel", "slack.search_messages", "slack.send_message",
        "jira.search_issues", "jira.read_issue", "jira.add_comment", "jira.change_status",
        "calendar.read_calendar", "calendar.create_event",
        "sheets.list_sheets", "sheets.read_sheet", "sheets.update_cell",
    },
    "product_manager": {
        "gmail.read_email", "gmail.search_emails", "gmail.send_email",
        "slack.read_channel", "slack.search_messages", "slack.send_message",
        "jira.search_issues", "jira.read_issue", "jira.assign_issue", "jira.add_comment",
        "calendar.read_calendar", "calendar.create_event", "calendar.reschedule_event",
        "sheets.list_sheets", "sheets.read_sheet", "sheets.update_cell", "sheets.append_row",
    },
    "engineering_manager": {
        "gmail.read_email", "gmail.search_emails", "gmail.send_email",
        "slack.read_channel", "slack.search_messages", "slack.send_message",
        "jira.search_issues", "jira.read_issue", "jira.assign_issue",
        "jira.add_comment", "jira.change_status",
        "calendar.read_calendar", "calendar.create_event", "calendar.reschedule_event",
        "sheets.list_sheets", "sheets.read_sheet", "sheets.update_cell", "sheets.append_row",
    },
    "customer_success": {
        "gmail.read_email", "gmail.search_emails", "gmail.send_email",
        "slack.read_channel", "slack.search_messages", "slack.send_message",
        "jira.search_issues", "jira.read_issue", "jira.add_comment",
        "calendar.read_calendar", "calendar.create_event",
        "sheets.list_sheets", "sheets.read_sheet", "sheets.update_cell",
    },
}

# Minimum roles required per scenario.
_REQUIRED_ROLES: dict[str, list[str]] = {
    "vendor_onboarding": [
        "project_manager",
        "engineer",
        "product_manager",
        "engineering_manager",
        "customer_success",
    ],
}

# Permissions each role must have to complete the scenario.
_SCENARIO_PERMISSIONS: dict[str, dict[str, list[str]]] = {
    "vendor_onboarding": {
        "project_manager":    ["gmail.read_email", "jira.read_issue",
                               "sheets.update_cell", "slack.send_message",
                               "calendar.create_event"],
        "product_manager":    ["jira.add_comment"],
        "engineer":           ["jira.add_comment"],
        "engineering_manager":["jira.add_comment"],
    },
}


class ValidationError(Exception):
    pass


class WorldValidator:
    """Validates a GeneratedWorld without instantiating a live environment."""

    def validate(self, world: GeneratedWorld) -> list[str]:
        """Return list of error strings. Empty list means validation passed."""
        errors: list[str] = []
        errors.extend(self._check_employees(world))
        errors.extend(self._check_vendor(world))
        errors.extend(self._check_scenario_roles(world))
        errors.extend(self._check_permissions(world))
        errors.extend(self._check_dag(world))
        return errors

    def validate_or_raise(self, world: GeneratedWorld) -> None:
        """Validate and raise ValidationError on first failure."""
        errors = self.validate(world)
        if errors:
            raise ValidationError(
                f"Generated world (seed={world.spec.seed}) has {len(errors)} error(s):\n"
                + "\n".join(f"  [{i+1}] {e}" for i, e in enumerate(errors))
            )

    # ------------------------------------------------------------------
    # Check methods
    # ------------------------------------------------------------------

    def _check_employees(self, world: GeneratedWorld) -> list[str]:
        errors = []
        seen_ids: set[str] = set()
        seen_names: set[str] = set()
        for e in world.employees:
            if e.agent_id in seen_ids:
                errors.append(f"Duplicate agent_id: {e.agent_id!r}")
            seen_ids.add(e.agent_id)
            if not e.first_name or not e.last_name:
                errors.append(f"Employee {e.agent_id!r} has empty name fields")
            if e.display_name in seen_names:
                errors.append(f"Duplicate display name: {e.display_name!r}")
            seen_names.add(e.display_name)
            if "@" not in e.email or "." not in e.email:
                errors.append(f"Employee {e.agent_id!r} has malformed email: {e.email!r}")
            if not e.role:
                errors.append(f"Employee {e.agent_id!r} has no role")
        return errors

    def _check_vendor(self, world: GeneratedWorld) -> list[str]:
        errors = []
        v = world.vendor
        if not v.name or len(v.name.split()) < 2:
            errors.append(f"Vendor name {v.name!r} must have at least 2 words")
        if len(v.ticket_prefix) < 2:
            errors.append(f"Ticket prefix {v.ticket_prefix!r} too short (min 2 chars)")
        tickets = [v.main_ticket, v.legal_ticket, v.it_ticket]
        if len(set(tickets)) != 3:
            errors.append(f"Vendor tickets are not unique: {tickets}")
        for t in tickets:
            if not t or "-" not in t:
                errors.append(f"Ticket ID {t!r} must contain a dash (e.g. SYNC-401)")
        if str(world.spec.seed) not in v.email_id:
            errors.append(f"Vendor email_id {v.email_id!r} does not embed seed {world.spec.seed}")
        if not v.sheet_id:
            errors.append("Vendor sheet_id is empty")
        if not v.channel_id:
            errors.append("Vendor channel_id is empty")
        return errors

    def _check_scenario_roles(self, world: GeneratedWorld) -> list[str]:
        errors = []
        scenario = world.spec.scenario
        required = _REQUIRED_ROLES.get(scenario)
        if required is None:
            errors.append(f"Unknown scenario: {scenario!r}")
            return errors
        present_roles = {e.role for e in world.employees}
        for role in required:
            if role not in present_roles:
                errors.append(f"No agent with role {role!r} for scenario {scenario!r}")
        return errors

    def _check_permissions(self, world: GeneratedWorld) -> list[str]:
        errors = []
        scenario = world.spec.scenario
        needed = _SCENARIO_PERMISSIONS.get(scenario, {})
        role_map = {e.role: e for e in world.employees}
        for role, required_perms in needed.items():
            emp = role_map.get(role)
            if emp is None:
                continue  # already reported in _check_scenario_roles
            role_perms = _PERMISSIONS.get(role, set())
            for perm in required_perms:
                if perm not in role_perms:
                    errors.append(
                        f"{emp.agent_id!r} (role={role!r}) lacks required permission {perm!r}"
                    )
        return errors

    def _check_dag(self, world: GeneratedWorld) -> list[str]:
        """Verify the vendor_onboarding DAG structure matches the world's entities."""
        errors = []
        if world.spec.scenario != "vendor_onboarding":
            return errors
        # Ensure all required agent roles exist
        needed = {"project_manager", "engineer", "product_manager", "engineering_manager"}
        present = {e.role for e in world.employees}
        for role in needed:
            if role not in present:
                errors.append(f"DAG requires role {role!r} but none found")
        # Ensure vendor entity IDs are non-empty
        v = world.vendor
        for field_name, val in [
            ("main_ticket",  v.main_ticket),
            ("legal_ticket", v.legal_ticket),
            ("it_ticket",    v.it_ticket),
            ("email_id",     v.email_id),
            ("sheet_id",     v.sheet_id),
            ("channel_id",   v.channel_id),
        ]:
            if not val:
                errors.append(f"Vendor {field_name} is empty — DAG cannot reference it")
        return errors
