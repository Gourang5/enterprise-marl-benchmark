from __future__ import annotations
from typing import Any

SCHEMAS: dict[str, dict[str, tuple[type | tuple[type, ...], bool]]] = {
    "gmail.search_emails": {"query": (str, True)},
    "gmail.read_email": {"email_id": (str, True)},
    "gmail.send_email": {"recipient_id": (str, True), "subject": (str, True), "body": (str, True), "email_id": (str, False)},
    "slack.search_messages": {"query": (str, True)},
    "slack.read_channel": {"channel_id": (str, True)},
    "slack.send_message": {"channel_id": (str, True), "text": (str, True), "mentions": (list, False), "message_id": (str, False)},
    "jira.search_issues": {"query": (str, True)},
    "jira.read_issue": {"issue_id": (str, True)},
    "jira.assign_issue": {"issue_id": (str, True), "assignee_id": (str, True)},
    "jira.add_comment": {"issue_id": (str, True), "comment": (str, True), "mentions": (list, False)},
    "jira.change_status": {"issue_id": (str, True), "status": (str, True)},
    "calendar.read_calendar": {},
    "calendar.create_event": {"title": (str, True), "participants": (list, True), "start_time": (int, True), "end_time": (int, True), "event_id": (str, False)},
    "calendar.reschedule_event": {"event_id": (str, True), "start_time": (int, True), "end_time": (int, True)},
    "sheets.list_sheets": {},
    "sheets.read_sheet": {"sheet_id": (str, True)},
    "sheets.update_cell": {"sheet_id": (str, True), "cell": (str, True), "value": ((str, int, float, bool), True)},
    "sheets.append_row": {"sheet_id": (str, True), "values": (list, True)},
}


def validate_parameters(tool: str, params: dict[str, Any]) -> str | None:
    if tool not in SCHEMAS:
        return f"Unknown tool {tool}"
    if not isinstance(params, dict):
        return "parameters must be an object"
    schema = SCHEMAS[tool]
    for name, (typ, required) in schema.items():
        if required and name not in params:
            return f"Missing required parameter: {name}"
        if name in params and not isinstance(params[name], typ):
            return f"Parameter {name} has wrong type"
    unknown = sorted(set(params) - set(schema))
    if unknown:
        return f"Unknown parameter(s): {', '.join(unknown)}"
    if tool == "calendar.create_event" or tool == "calendar.reschedule_event":
        if params.get("end_time", 1) <= params.get("start_time", 0):
            return "end_time must be greater than start_time"
    if tool == "slack.send_message" and "mentions" in params:
        if not all(isinstance(x, str) for x in params["mentions"]):
            return "mentions must contain employee IDs"
    if tool == "sheets.append_row" and not all(isinstance(x, (str, int, float, bool)) for x in params.get("values", [])):
        return "values must contain scalar values"
    if tool == "calendar.create_event" and not all(isinstance(x, str) for x in params.get("participants", [])):
        return "participants must contain employee IDs"
    return None
