from .customer_incident import CustomerIncidentTask
from .product_launch import ProductLaunchTask
from .meeting_conflict import MeetingConflictTask
from .launch_readiness import LaunchReadinessTask
from .budget_approval import BudgetApprovalTask
from .vendor_onboarding import VendorOnboardingTask

TASKS = {
    "customer_incident": CustomerIncidentTask,
    "product_launch": ProductLaunchTask,
    "meeting_conflict": MeetingConflictTask,
    "launch_readiness": LaunchReadinessTask,
    "budget_approval": BudgetApprovalTask,
    "vendor_onboarding": VendorOnboardingTask,
}


def make_task(name):
    if name not in TASKS:
        raise ValueError(f"Unknown task {name}; choices={sorted(TASKS)}")
    return TASKS[name]()
