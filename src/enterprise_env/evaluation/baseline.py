from ..core.actions import Action

class ScriptedPolicy:
    def __init__(self,actions): self.actions=list(actions); self.i=0
    def action(self,env):
        if self.i>=len(self.actions):
            return Action(env.agent_selection,"calendar","read_calendar",{})
        a=self.actions[self.i];self.i+=1;return a

class CustomerIncidentBaseline(ScriptedPolicy):
    def __init__(self):
        super().__init__([
            Action("pm_01","gmail","search_emails",{"query":"authentication outage"}),
            Action("pm_01","gmail","read_email",{"email_id":"seed-email-001"}),
            Action("pm_01","jira","search_issues",{"query":"authentication failures"}),
            Action("pm_01","jira","read_issue",{"issue_id":"INC-421"}),
            Action("pm_01","jira","assign_issue",{"issue_id":"INC-421","assignee_id":"eng_01"}),
            Action("pm_01","slack","send_message",{"channel_id":"CH-INCIDENTS","text":"INC-421 assigned to Arjun. Please investigate the auth gateway regression.","mentions":["eng_01"]}),
            Action("eng_01","jira","add_comment",{"issue_id":"INC-421","comment":"Investigating auth gateway rollout regression and token validation path."}),
            Action("eng_01","jira","change_status",{"issue_id":"INC-421","status":"in_progress"}),
            Action("pm_01","calendar","create_event",{"event_id":"INC-EVENT","title":"INC-421 Incident Review","participants":["eng_01"],"start_time":780,"end_time":810}),
            Action("eng_01","jira","change_status",{"issue_id":"INC-421","status":"resolved"}),
            Action("pm_01","gmail","send_email",{"email_id":"resolution-email","recipient_id":"cs_01","subject":"INC-421 resolved","body":"INC-421 is resolved after investigation of the authentication gateway regression."}),
        ])

class ProductLaunchBaseline(ScriptedPolicy):
    def __init__(self):
        super().__init__([
            Action("product_01","jira","search_issues",{"query":"launch readiness"}),
            Action("product_01","jira","read_issue",{"issue_id":"LAUNCH-101"}),
            Action("product_01","jira","assign_issue",{"issue_id":"LAUNCH-101","assignee_id":"eng_01"}),
            Action("eng_01","jira","add_comment",{"issue_id":"LAUNCH-101","comment":"Validated payment retry telemetry; metrics and alerts are healthy."}),
            Action("mgr_01","jira","add_comment",{"issue_id":"LAUNCH-101","comment":"Approved — engineering validation and management sign-off are confirmed for the launch review."}),
            Action("product_01","slack","send_message",{"channel_id":"CH-PRODUCT","text":"LAUNCH-101 go/no-go: validation complete and manager approval recorded.","mentions":["eng_01","mgr_01"]}),
            Action("product_01","calendar","create_event",{"event_id":"LAUNCH-REVIEW","title":"Marketplace Checkout Go/No-Go","participants":["eng_01","mgr_01"],"start_time":840,"end_time":900}),
            Action("mgr_01","jira","change_status",{"issue_id":"LAUNCH-101","status":"resolved"}),
        ])

class MeetingConflictBaseline(ScriptedPolicy):
    def __init__(self):
        super().__init__([
            Action("pm_01","gmail","read_email",{"email_id":"conflict-email-001"}),
            Action("pm_01","calendar","read_calendar",{}),
            Action("eng_01","calendar","read_calendar",{}),
            Action("pm_01","calendar","reschedule_event",{"event_id":"EV-2","start_time":720,"end_time":780}),
            Action("pm_01","slack","send_message",{"channel_id":"CH-PROJECT","text":"EV-2 Engineering Review rescheduled to 12:00-13:00 to avoid the customer call and platform standup.","mentions":["eng_01"]}),
        ])

class LaunchReadinessBaseline(ScriptedPolicy):
    def __init__(self):
        super().__init__([
            Action("cs_01","gmail","search_emails",{"query":"partner checkout commitment"}),
            Action("cs_01","gmail","read_email",{"email_id":"lr-email-001"}),
            Action("cs_01","slack","send_message",{"channel_id":"CH-PRODUCT","text":"Partner commitment is launch-blocking and requires readiness before the 16:00 review.","mentions":["product_01"]}),
            Action("eng_01","jira","search_issues",{"query":"checkout retry readiness"}),
            Action("eng_01","jira","read_issue",{"issue_id":"READY-301"}),
            Action("eng_01","jira","add_comment",{"issue_id":"READY-301","comment":"Investigated payment retry telemetry and production alerts; telemetry is healthy and evidence is ready."}),
            Action("eng_01","jira","change_status",{"issue_id":"READY-301","status":"in_progress"}),
            Action("product_01","sheets","read_sheet",{"sheet_id":"SHEET-LAUNCH"}),
            Action("product_01","sheets","update_cell",{"sheet_id":"SHEET-LAUNCH","cell":"B2","value":"READY"}),
            Action("product_01","sheets","update_cell",{"sheet_id":"SHEET-LAUNCH","cell":"C2","value":"Partner requires readiness before 16:00 review"}),
            Action("product_01","sheets","update_cell",{"sheet_id":"SHEET-LAUNCH","cell":"B3","value":"READY"}),
            Action("product_01","sheets","update_cell",{"sheet_id":"SHEET-LAUNCH","cell":"C3","value":"READY-301 telemetry validated"}),
            Action("mgr_01","jira","add_comment",{"issue_id":"READY-301","comment":"Approved for launch readiness review based on recorded evidence."}),
            Action("product_01","sheets","update_cell",{"sheet_id":"SHEET-LAUNCH","cell":"B4","value":"APPROVED"}),
            Action("product_01","sheets","update_cell",{"sheet_id":"SHEET-LAUNCH","cell":"C4","value":"Daniel approved in READY-301"}),
            Action("product_01","calendar","create_event",{"event_id":"LR-REVIEW","title":"Marketplace Launch Readiness Review","participants":["eng_01","mgr_01","cs_01"],"start_time":960,"end_time":990}),
            Action("product_01","slack","send_message",{"channel_id":"CH-PRODUCT","text":"Launch is ready for review: READY-301 evidence captured in SHEET-LAUNCH.","mentions":["eng_01","mgr_01","cs_01"]}),
        ])

class BudgetApprovalBaseline(ScriptedPolicy):
    def __init__(self):
        super().__init__([
            Action("product_01","gmail","read_email",{"email_id":"budget-email-001"}),
            Action("product_01","jira","search_issues",{"query":"BUDGET analytics"}),
            Action("product_01","jira","read_issue",{"issue_id":"BUDGET-201"}),
            Action("eng_01","jira","add_comment",{"issue_id":"BUDGET-201","comment":"Engineering estimate: 8 sprint-days for the analytics dashboard. Validated against current team capacity."}),
            Action("mgr_01","jira","add_comment",{"issue_id":"BUDGET-201","comment":"Budget approved. Engineering can proceed with the Q1 Analytics Dashboard initiative."}),
            Action("product_01","sheets","read_sheet",{"sheet_id":"SHEET-BUDGET"}),
            Action("product_01","sheets","update_cell",{"sheet_id":"SHEET-BUDGET","cell":"C2","value":"APPROVED"}),
            Action("product_01","calendar","create_event",{"title":"Q1 Analytics Dashboard Kickoff","participants":["product_01","eng_01","mgr_01"],"start_time":720,"end_time":780}),
            Action("product_01","slack","send_message",{"channel_id":"CH-PRODUCT","text":"BUDGET-201 approved. Q1 Analytics Dashboard initiative is go. Kickoff scheduled for 12:00.","mentions":["eng_01","mgr_01"]}),
        ])

class VendorOnboardingBaseline(ScriptedPolicy):
    def __init__(self):
        super().__init__([
            Action("pm_01","gmail","read_email",{"email_id":"vendor-request-001"}),
            Action("pm_01","jira","search_issues",{"query":"VEND onboarding TechNova"}),
            Action("pm_01","jira","read_issue",{"issue_id":"VEND-401"}),
            Action("product_01","jira","add_comment",{"issue_id":"VEND-402","comment":"Legal review complete. TechNova Solutions vendor agreement is compliant with procurement and data handling policies."}),
            Action("eng_01","jira","add_comment",{"issue_id":"VEND-403","comment":"IT setup complete. Access credentials and API keys provisioned. Sandbox environment configured for TechNova integration."}),
            Action("mgr_01","jira","add_comment",{"issue_id":"VEND-401","comment":"Vendor onboarding approved. Legal and IT have both confirmed readiness. Proceed with kickoff."}),
            Action("pm_01","sheets","read_sheet",{"sheet_id":"SHEET-VENDOR"}),
            Action("pm_01","sheets","update_cell",{"sheet_id":"SHEET-VENDOR","cell":"B2","value":"ACTIVE"}),
            Action("pm_01","calendar","create_event",{"title":"TechNova Solutions Onboarding Kickoff","participants":["product_01","eng_01","mgr_01"],"start_time":720,"end_time":780}),
            Action("pm_01","slack","send_message",{"channel_id":"CH-PROCUREMENT","text":"VEND-401 approved. TechNova Solutions onboarding is complete. Legal cleared, IT provisioned, kickoff scheduled.","mentions":["product_01","eng_01","mgr_01"]}),
        ])

BASELINES={
    "customer_incident":CustomerIncidentBaseline,
    "product_launch":ProductLaunchBaseline,
    "meeting_conflict":MeetingConflictBaseline,
    "launch_readiness":LaunchReadinessBaseline,
    "budget_approval":BudgetApprovalBaseline,
    "vendor_onboarding":VendorOnboardingBaseline,
}

def make_baseline(task_name):
    return BASELINES[task_name]()
