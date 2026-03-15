-- Hive 2.0 derived cache schema
-- Canonical state lives in markdown/jsonl files. This SQLite DB is a local cache.
-- Safe to delete and rebuild with `hive cache rebuild`.

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  path TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  priority INTEGER NOT NULL DEFAULT 3,
  owner TEXT,
  target_repo_url TEXT,
  target_repo_branch TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('epic','task','bug','spike','chore','review','experiment')),
  status TEXT NOT NULL CHECK(status IN ('proposed','ready','claimed','in_progress','blocked','review','done','archived')),
  priority INTEGER NOT NULL DEFAULT 3,
  parent_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
  owner TEXT,
  claimed_until TEXT,
  display_order INTEGER NOT NULL DEFAULT 0,
  display_path TEXT,
  labels_json TEXT NOT NULL DEFAULT '[]',
  relevant_files_json TEXT NOT NULL DEFAULT '[]',
  acceptance_json TEXT NOT NULL DEFAULT '[]',
  summary_md TEXT NOT NULL DEFAULT '',
  notes_md TEXT NOT NULL DEFAULT '',
  source_json TEXT NOT NULL DEFAULT '{}',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_edges (
  id TEXT PRIMARY KEY,
  src_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  edge_type TEXT NOT NULL CHECK(edge_type IN ('blocks','parent_of','relates_to','duplicates','supersedes')),
  dst_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(src_task_id, edge_type, dst_task_id)
);

CREATE TABLE IF NOT EXISTS claims (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  owner TEXT NOT NULL,
  acquired_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  released_at TEXT,
  status TEXT NOT NULL CHECK(status IN ('active','released','expired','superseded')),
  release_reason TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  mode TEXT NOT NULL CHECK(mode IN ('workflow','experiment','review')),
  status TEXT NOT NULL CHECK(status IN ('planned','running','evaluating','accepted','rejected','escalated','aborted')),
  executor TEXT NOT NULL DEFAULT 'local',
  branch_name TEXT,
  worktree_path TEXT,
  program_path TEXT,
  program_sha256 TEXT,
  plan_path TEXT,
  summary_path TEXT,
  review_path TEXT,
  patch_path TEXT,
  command_log_path TEXT,
  logs_dir TEXT,
  tokens_in INTEGER,
  tokens_out INTEGER,
  cost_usd REAL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  exit_reason TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS run_steps (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL,
  step_type TEXT NOT NULL CHECK(step_type IN ('plan','edit','command','test','eval','review','memory','note')),
  status TEXT NOT NULL CHECK(status IN ('started','succeeded','failed','skipped')),
  summary TEXT NOT NULL DEFAULT '',
  artifact_path TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(run_id, seq)
);

CREATE TABLE IF NOT EXISTS evaluations (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  evaluator_id TEXT NOT NULL,
  command TEXT NOT NULL,
  required INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL CHECK(status IN ('pass','fail','skipped')),
  metric_name TEXT,
  metric_value REAL,
  stdout_path TEXT,
  stderr_path TEXT,
  created_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(run_id, evaluator_id)
);

CREATE TABLE IF NOT EXISTS memory_docs (
  id TEXT PRIMARY KEY,
  scope TEXT NOT NULL CHECK(scope IN ('project','global','run','agent')),
  scope_key TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('observations','reflections','profile','active','summary')),
  path TEXT NOT NULL UNIQUE,
  updated_at TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS search_docs (
  id TEXT PRIMARY KEY,
  doc_type TEXT NOT NULL CHECK(doc_type IN ('task','run_summary','memory','program','agency','global')),
  path TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS search_docs_fts USING fts5(
  id UNINDEXED,
  title,
  body,
  content='search_docs',
  content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS search_docs_ai AFTER INSERT ON search_docs BEGIN
  INSERT INTO search_docs_fts(rowid, id, title, body)
  VALUES (new.rowid, new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS search_docs_ad AFTER DELETE ON search_docs BEGIN
  INSERT INTO search_docs_fts(search_docs_fts, rowid, id, title, body)
  VALUES('delete', old.rowid, old.id, old.title, old.body);
END;

CREATE TRIGGER IF NOT EXISTS search_docs_au AFTER UPDATE ON search_docs BEGIN
  INSERT INTO search_docs_fts(search_docs_fts, rowid, id, title, body)
  VALUES('delete', old.rowid, old.id, old.title, old.body);
  INSERT INTO search_docs_fts(rowid, id, title, body)
  VALUES (new.rowid, new.id, new.title, new.body);
END;

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  occurred_at TEXT NOT NULL,
  actor TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  source TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects(slug);
CREATE INDEX IF NOT EXISTS idx_tasks_project_status_priority ON tasks(project_id, status, priority, updated_at);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id);
CREATE INDEX IF NOT EXISTS idx_task_edges_src ON task_edges(src_task_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_task_edges_dst ON task_edges(dst_task_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_claims_task_status_expiry ON claims(task_id, status, expires_at);
CREATE INDEX IF NOT EXISTS idx_runs_task_status ON runs(task_id, status, started_at);
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_type, entity_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_memory_docs_scope ON memory_docs(scope, scope_key, kind);

-- A materialized convenience view for ready work.
CREATE VIEW IF NOT EXISTS ready_tasks AS
SELECT
  t.*
FROM tasks t
WHERE t.status IN ('proposed','ready')
  AND NOT EXISTS (
    SELECT 1
    FROM claims c
    WHERE c.task_id = t.id
      AND c.status = 'active'
      AND c.expires_at > datetime('now')
  )
  AND NOT EXISTS (
    SELECT 1
    FROM task_edges e
    JOIN tasks blocker ON blocker.id = e.src_task_id
    WHERE e.edge_type = 'blocks'
      AND e.dst_task_id = t.id
      AND blocker.status NOT IN ('done','archived')
  );

-- A convenience view for latest active claims by task.
CREATE VIEW IF NOT EXISTS active_claims AS
SELECT c.*
FROM claims c
WHERE c.status = 'active'
  AND c.expires_at > datetime('now');

-- Suggested rebuild contract:
-- 1. parse GLOBAL.md / AGENCY.md / PROGRAM.md / task files / run artifacts / memory docs
-- 2. repopulate tables
-- 3. index search targets
-- 4. replay events as telemetry only (not as current-state authority)
