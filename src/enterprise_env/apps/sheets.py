from .base import BaseApp
from ..core.models import ToolResult


class SheetsApp(BaseApp):
    name = "sheets"

    def _access(self, agent, sheet_id, write=False):
        member = self.repo.get("SELECT role FROM sheet_members WHERE sheet_id=? AND employee_id=?", (sheet_id, agent))
        if not member:
            return ToolResult(False, "Sheet not accessible", {})
        if write and member["role"] not in {"editor", "owner"}:
            return ToolResult(False, "Sheet is read-only for this agent", {})
        return None

    def execute(self, agent, action, p):
        denied = self.authorize(agent, action)
        if denied:
            return denied
        if action == "list_sheets":
            return ToolResult(True, "Sheets listed", {"sheets": self.repo.sheets_for(agent)}, False, False, True)
        if action == "read_sheet":
            access = self._access(agent, p["sheet_id"])
            if access:
                return access
            return ToolResult(True, "Sheet read", {"sheet_id": p["sheet_id"], "cells": self.repo.sheet_cells(p["sheet_id"])}, False, False, True)
        if action == "update_cell":
            access = self._access(agent, p["sheet_id"], write=True)
            if access:
                return access
            self.repo.upsert_sheet_cell(p["sheet_id"], p["cell"], str(p["value"]), agent, self.env.time)
            return ToolResult(True, "Cell updated", {"sheet_id": p["sheet_id"], "cell": p["cell"], "value": str(p["value"])}, True, True)
        if action == "append_row":
            access = self._access(agent, p["sheet_id"], write=True)
            if access:
                return access
            row = self.repo.next_sheet_row(p["sheet_id"])
            for idx, value in enumerate(p["values"], start=1):
                self.repo.upsert_sheet_cell(p["sheet_id"], f"{self._col(idx)}{row}", str(value), agent, self.env.time)
            return ToolResult(True, "Row appended", {"sheet_id": p["sheet_id"], "row": row}, True, True)
        return ToolResult(False, "Unknown Sheets action", {})

    @staticmethod
    def _col(n):
        out = ""
        while n:
            n, r = divmod(n - 1, 26)
            out = chr(65 + r) + out
        return out
