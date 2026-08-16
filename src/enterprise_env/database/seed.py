from .repository import CompanyRepository

# Synthetic employees in a fictionalized Walmart Global Tech setting. No real employee data is used.
EMPLOYEES=[
("pm_01","Sarah","project_manager","team_pm","sarah@walmart-sim.test"),
("eng_01","Arjun","engineer","team_platform","arjun@walmart-sim.test"),
("product_01","Maya","product_manager","team_product","maya@walmart-sim.test"),
("mgr_01","Daniel","engineering_manager","team_platform","daniel@walmart-sim.test"),
("cs_01","Priya","customer_success","team_cs","priya@walmart-sim.test")]
PERMISSIONS={
"project_manager":{"gmail.read_email","gmail.search_emails","gmail.send_email","slack.read_channel","slack.search_messages","slack.send_message","jira.search_issues","jira.read_issue","jira.assign_issue","jira.add_comment","jira.change_status","calendar.read_calendar","calendar.create_event","calendar.reschedule_event","sheets.list_sheets","sheets.read_sheet","sheets.update_cell","sheets.append_row"},
"engineer":{"gmail.read_email","gmail.search_emails","gmail.send_email","slack.read_channel","slack.search_messages","slack.send_message","jira.search_issues","jira.read_issue","jira.add_comment","jira.change_status","calendar.read_calendar","calendar.create_event","sheets.list_sheets","sheets.read_sheet","sheets.update_cell"},
"product_manager":{"gmail.read_email","gmail.search_emails","gmail.send_email","slack.read_channel","slack.search_messages","slack.send_message","jira.search_issues","jira.read_issue","jira.assign_issue","jira.add_comment","calendar.read_calendar","calendar.create_event","calendar.reschedule_event","sheets.list_sheets","sheets.read_sheet","sheets.update_cell","sheets.append_row"},
"engineering_manager":{"gmail.read_email","gmail.search_emails","gmail.send_email","slack.read_channel","slack.search_messages","slack.send_message","jira.search_issues","jira.read_issue","jira.assign_issue","jira.add_comment","jira.change_status","calendar.read_calendar","calendar.create_event","calendar.reschedule_event","sheets.list_sheets","sheets.read_sheet","sheets.update_cell","sheets.append_row"},
"customer_success":{"gmail.read_email","gmail.search_emails","gmail.send_email","slack.read_channel","slack.search_messages","slack.send_message","jira.search_issues","jira.read_issue","jira.add_comment","calendar.read_calendar","calendar.create_event","sheets.list_sheets","sheets.read_sheet","sheets.update_cell"}}

def seed_company(repo):
    from pathlib import Path
    repo.executescript(Path(__file__).with_name("schema.sql").read_text())
    for x in [("team_pm","Program Management"),("team_platform","Global Platform Engineering"),("team_product","Product"),("team_cs","Enterprise Customer Success")]: repo.add("INSERT INTO teams VALUES(?,?)",x)
    for x in EMPLOYEES: repo.add("INSERT INTO employees VALUES(?,?,?,?,?)",x)
    for x in [("PROJ-ALPHA","Identity & API Reliability","mgr_01"),("PROJ-LAUNCH","Marketplace Checkout Launch","product_01")]: repo.add("INSERT INTO projects VALUES(?,?,?)",x)
    repo.add("INSERT INTO customers VALUES(?,?,?)",("CUST-ACME","Acme Retail Partner","customer@example.com"))
    channels=[("CH-PROJECT","#identity-platform"),("CH-INCIDENTS","#incidents"),("CH-PRODUCT","#checkout-launch"),("CH-RANDOM","#watercooler")]
    for x in channels: repo.add("INSERT INTO channels VALUES(?,?)",x)
    for cid,_ in channels:
        for eid,*_ in EMPLOYEES: repo.add("INSERT INTO channel_members VALUES(?,?)",(cid,eid))
    for eid,_,role,_,_ in EMPLOYEES:
        for p in PERMISSIONS[role]: repo.add("INSERT INTO permissions VALUES(?,?)",(eid,p))
    repo.add("INSERT INTO spreadsheets VALUES(?,?,?)",("SHEET-OPS","Enterprise Operating Tracker","pm_01"))
    for eid in ("pm_01","eng_01","product_01","mgr_01","cs_01"):
        role="owner" if eid=="pm_01" else ("editor" if eid in {"eng_01","product_01"} else "viewer")
        repo.add("INSERT INTO sheet_members VALUES(?,?,?)",("SHEET-OPS",eid,role))
    return repo
