PRAGMA foreign_keys = ON;
CREATE TABLE teams(team_id TEXT PRIMARY KEY,name TEXT NOT NULL);
CREATE TABLE employees(employee_id TEXT PRIMARY KEY,name TEXT NOT NULL,role TEXT NOT NULL,team_id TEXT NOT NULL REFERENCES teams(team_id),email TEXT NOT NULL UNIQUE);
CREATE TABLE projects(project_id TEXT PRIMARY KEY,name TEXT NOT NULL,owner_id TEXT NOT NULL REFERENCES employees(employee_id));
CREATE TABLE customers(customer_id TEXT PRIMARY KEY,name TEXT NOT NULL,contact_email TEXT NOT NULL);
CREATE TABLE channels(channel_id TEXT PRIMARY KEY,name TEXT NOT NULL UNIQUE);
CREATE TABLE channel_members(channel_id TEXT REFERENCES channels(channel_id),employee_id TEXT REFERENCES employees(employee_id),PRIMARY KEY(channel_id,employee_id));
CREATE TABLE emails(email_id TEXT PRIMARY KEY,sender_id TEXT NOT NULL REFERENCES employees(employee_id),recipient_id TEXT NOT NULL REFERENCES employees(employee_id),subject TEXT NOT NULL,body TEXT NOT NULL,timestamp INTEGER NOT NULL,read INTEGER NOT NULL DEFAULT 0);
CREATE TABLE slack_messages(message_id TEXT PRIMARY KEY,channel_id TEXT NOT NULL REFERENCES channels(channel_id),sender_id TEXT NOT NULL REFERENCES employees(employee_id),text TEXT NOT NULL,timestamp INTEGER NOT NULL);
CREATE TABLE jira_issues(issue_id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(project_id),title TEXT NOT NULL,description TEXT NOT NULL,status TEXT NOT NULL,priority TEXT NOT NULL,assignee_id TEXT REFERENCES employees(employee_id),reporter_id TEXT NOT NULL REFERENCES employees(employee_id));
CREATE TABLE jira_comments(comment_id INTEGER PRIMARY KEY AUTOINCREMENT,issue_id TEXT NOT NULL REFERENCES jira_issues(issue_id),author_id TEXT NOT NULL REFERENCES employees(employee_id),comment TEXT NOT NULL,timestamp INTEGER NOT NULL);
CREATE TABLE calendar_events(event_id TEXT PRIMARY KEY,title TEXT NOT NULL,organizer_id TEXT NOT NULL REFERENCES employees(employee_id),start_time INTEGER NOT NULL,end_time INTEGER NOT NULL);
CREATE TABLE event_participants(event_id TEXT REFERENCES calendar_events(event_id),employee_id TEXT REFERENCES employees(employee_id),PRIMARY KEY(event_id,employee_id));
CREATE TABLE permissions(employee_id TEXT NOT NULL REFERENCES employees(employee_id),permission TEXT NOT NULL,PRIMARY KEY(employee_id,permission));
CREATE TABLE audit_log(
  log_id INTEGER PRIMARY KEY AUTOINCREMENT,
  step INTEGER,
  agent_id TEXT,
  app TEXT,
  action_type TEXT,
  resource_id TEXT,
  success INTEGER,
  changed INTEGER
);
CREATE TABLE spreadsheets(sheet_id TEXT PRIMARY KEY,name TEXT NOT NULL,owner_id TEXT NOT NULL REFERENCES employees(employee_id));
CREATE TABLE sheet_members(sheet_id TEXT REFERENCES spreadsheets(sheet_id),employee_id TEXT REFERENCES employees(employee_id),role TEXT NOT NULL,PRIMARY KEY(sheet_id,employee_id));
CREATE TABLE sheet_cells(sheet_id TEXT REFERENCES spreadsheets(sheet_id),cell TEXT NOT NULL,value TEXT NOT NULL,updated_by TEXT REFERENCES employees(employee_id),updated_at INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(sheet_id,cell));
