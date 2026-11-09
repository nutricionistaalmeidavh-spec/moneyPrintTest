CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,status TEXT NOT NULL,request_path TEXT,github_sha TEXT,workflow TEXT,details TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS jobs_latest ON jobs(created_at DESC);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,encrypted_value TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,action TEXT NOT NULL,detail TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS login_attempts(key TEXT PRIMARY KEY,failures INTEGER NOT NULL DEFAULT 0,locked_until INTEGER NOT NULL DEFAULT 0);

CREATE TABLE IF NOT EXISTS video_flows (
 id TEXT PRIMARY KEY,
 name TEXT NOT NULL,
 graph TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS video_flows_latest ON video_flows(updated_at DESC);

-- Additive Studio V3 tables; existing jobs, sessions and secrets remain unchanged.
CREATE TABLE IF NOT EXISTS studio_projects(id TEXT PRIMARY KEY,topic TEXT NOT NULL,revision INTEGER NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS studio_projects_recent ON studio_projects(updated_at DESC);
CREATE TABLE IF NOT EXISTS studio_revisions(project_id TEXT NOT NULL,revision INTEGER NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(project_id,revision));
