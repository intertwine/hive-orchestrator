import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { createConsoleClient } from "../api/client";
import { ConsoleLink } from "../components/ConsoleLink";
import { KeyValueGrid } from "../components/KeyValueGrid";
import { Panel } from "../components/Panel";
import { StateNotice } from "../components/StateNotice";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

type SearchResultRecord = Record<string, unknown>;

interface SearchDraftState {
  harness: string;
  projectId: string;
  query: string;
  source: string;
  timeWindow: string;
}

function readString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function submittedStateFromParams(searchParams: URLSearchParams): SearchDraftState {
  return {
    harness: searchParams.get("harness") ?? "",
    projectId: searchParams.get("project") ?? "",
    query: searchParams.get("query") ?? "program doctor",
    source: searchParams.get("source") ?? "",
    timeWindow: searchParams.get("time") ?? "",
  };
}

function resultId(result: SearchResultRecord): string {
  return (
    readString(result.id)
    || readString(result.path)
    || `${readString(result.kind, "result")}:${readString(result.title, "Result")}`
  );
}

function openLabel(result: SearchResultRecord): string {
  return readString(result.open_label, "Open in context");
}

export function SearchPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const [searchParams, setSearchParams] = useSearchParams();
  const submitted = useMemo(() => submittedStateFromParams(searchParams), [searchParams]);
  const [draft, setDraft] = useState<SearchDraftState>(submitted);
  const [selectedResultId, setSelectedResultId] = useState("");
  const pendingPreviewFocusId = useRef<string | null>(null);
  const previewRef = useRef<HTMLDivElement | null>(null);
  const client = useMemo(
    () => createConsoleClient(apiBase, workspacePath),
    [apiBase, workspacePath],
  );
  const searchRequestKey = useMemo(
    () =>
      JSON.stringify({
        apiBase,
        workspacePath,
        query: submitted.query,
        projectId: submitted.projectId,
        source: submitted.source,
        harness: submitted.harness,
        timeWindow: submitted.timeWindow,
      }),
    [
      apiBase,
      workspacePath,
      submitted.harness,
      submitted.projectId,
      submitted.query,
      submitted.source,
      submitted.timeWindow,
    ],
  );
  const { data, loading, error } = useConsoleQuery(
    `search:${searchRequestKey}`,
    () =>
      client.search(submitted.query, {
        harness: submitted.harness || undefined,
        projectId: submitted.projectId || undefined,
        source: submitted.source || undefined,
        timeWindow: submitted.timeWindow || undefined,
      }),
    0,
  );
  const results = useMemo(
    () => (Array.isArray(data?.results) ? (data.results as SearchResultRecord[]) : []),
    [data?.results],
  );
  const selectedResult = results.find((result) => resultId(result) === selectedResultId) ?? results[0] ?? null;

  useEffect(() => {
    setDraft(submitted);
  }, [submitted]);

  useEffect(() => {
    if (!results.length) {
      setSelectedResultId("");
      return;
    }
    setSelectedResultId((current) => {
      return results.some((result) => resultId(result) === current)
        ? current
        : resultId(results[0] as SearchResultRecord);
    });
  }, [results]);

  useEffect(() => {
    if (!selectedResult || pendingPreviewFocusId.current !== selectedResultId) {
      return;
    }
    pendingPreviewFocusId.current = null;
    if (window.innerWidth > 1024) {
      return;
    }
    window.requestAnimationFrame(() => {
      previewRef.current?.focus();
      previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [selectedResult, selectedResultId]);

  function focusPreviewOnNarrowScreens() {
    if (window.innerWidth > 1024) {
      return;
    }
    window.requestAnimationFrame(() => {
      previewRef.current?.focus();
      previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function selectResult(identifier: string) {
    if (identifier === selectedResultId) {
      focusPreviewOnNarrowScreens();
      return;
    }
    pendingPreviewFocusId.current = identifier;
    setSelectedResultId(identifier);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = new URLSearchParams();
    next.set("query", draft.query.trim() || "program doctor");
    if (draft.projectId.trim()) {
      next.set("project", draft.projectId.trim());
    }
    if (draft.source) {
      next.set("source", draft.source);
    }
    if (draft.harness) {
      next.set("harness", draft.harness);
    }
    if (draft.timeWindow) {
      next.set("time", draft.timeWindow);
    }
    setSearchParams(next);
  }

  return (
    <div className="page-grid page-grid--detail">
      <Panel eyebrow="Unified provenance" title="Search">
        <div className="stack">
          <form className="filters" onSubmit={handleSubmit}>
            <label className="console-field">
              <span>Query</span>
              <input
                value={draft.query}
                onChange={(event) => setDraft((current) => ({ ...current, query: event.target.value }))}
              />
            </label>
            <label className="console-field">
              <span>Project</span>
              <input
                placeholder="demo"
                value={draft.projectId}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, projectId: event.target.value }))
                }
              />
            </label>
            <label className="console-field">
              <span>Source</span>
              <select
                aria-label="Source"
                value={draft.source}
                onChange={(event) => setDraft((current) => ({ ...current, source: event.target.value }))}
              >
                <option value="">All sources</option>
                <option value="task">Tasks</option>
                <option value="run">Runs</option>
                <option value="memory">Memory</option>
                <option value="docs">Docs</option>
                <option value="command">Commands</option>
                <option value="recipe">Recipes</option>
                <option value="project">Projects</option>
                <option value="campaign">Campaigns</option>
                <option value="delegate">Delegates</option>
              </select>
            </label>
            <label className="console-field">
              <span>Harness</span>
              <select
                aria-label="Harness"
                value={draft.harness}
                onChange={(event) => setDraft((current) => ({ ...current, harness: event.target.value }))}
              >
                <option value="">Any harness</option>
                <option value="local">local</option>
                <option value="manual">manual</option>
                <option value="pi">pi</option>
                <option value="codex">codex</option>
                <option value="claude">claude</option>
                <option value="openclaw">openclaw</option>
                <option value="hermes">hermes</option>
              </select>
            </label>
            <label className="console-field">
              <span>Time</span>
              <select
                aria-label="Time"
                value={draft.timeWindow}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, timeWindow: event.target.value }))
                }
              >
                <option value="">Any time</option>
                <option value="24h">Last 24 hours</option>
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
              </select>
            </label>
            <div className="filters__actions">
              <button className="primary-button" type="submit">
                Search
              </button>
            </div>
          </form>

          <p className="console-settings__note">
            Search spans tasks, runs, docs, memory, recipes, campaigns, and attached delegate
            sessions. Match reasons stay visible so operators can trust why a result surfaced.
          </p>

          {loading ? (
            <StateNotice
              detail="Hive is searching tasks, runs, docs, memory, and delegate traces for the submitted query."
              title="Searching"
            />
          ) : error ? (
            <StateNotice
              detail={`Verify the API base and workspace path in Settings, then retry once search is reachable again. (${error})`}
              title="Unable to search"
              tone="error"
            />
          ) : (
            <div className="stack">
              {results.length ? (
                results.map((result) => {
                  const identifier = resultId(result);
                  const summary = readString(
                    result.summary,
                    readString(result.snippet, "No preview available."),
                  );
                  const reasonList = Array.isArray(result.why) ? (result.why as string[]) : [];
                  const occurredAt = readString(result.occurred_at);
                  const harness = readString(result.harness);
                  const projectLabel = readString(result.project_label);
                  const dedupeNote = readString(result.dedupe_note);
                  return (
                    <button
                      aria-controls="search-preview-panel"
                      aria-pressed={selectedResultId === identifier}
                      className={`list-card list-card--button${selectedResultId === identifier ? " list-card--selected" : ""}`}
                      key={identifier}
                      type="button"
                      onClick={() => selectResult(identifier)}
                    >
                      <div className="list-card__header">
                        <div>
                          <p className="hero-card__eyebrow">
                            {readString(result.source_label, readString(result.kind, "Result"))}
                          </p>
                          <h3>{readString(result.title, "Result")}</h3>
                        </div>
                        <StatusPill tone={readString(result.status, readString(result.kind, "info"))}>
                          {readString(result.source_label, readString(result.kind, "result"))}
                        </StatusPill>
                      </div>
                      <p>{summary}</p>
                      <p className="list-card__meta">
                        {[projectLabel, harness, occurredAt].filter((value) => value).join(" • ") || "Preview available in the side rail."}
                      </p>
                      {reasonList.length ? (
                        <ul className="reason-list">
                          {reasonList.slice(0, 2).map((reason) => (
                            <li key={`${identifier}:${reason}`}>{reason}</li>
                          ))}
                        </ul>
                      ) : null}
                      {dedupeNote ? <p className="list-card__meta">{dedupeNote}</p> : null}
                    </button>
                  );
                })
              ) : (
                <StateNotice
                  detail="Refine the query or broaden the filters if you expected a result from another source, harness, or time window."
                  title="No search results yet"
                />
              )}
            </div>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Preview and provenance" title="Result context">
        {loading ? (
          <StateNotice
            detail="The preview rail will fill in as soon as the search results arrive."
            title="Waiting for search results"
          />
        ) : error ? (
          <StateNotice
            detail="Result preview is unavailable until the search request succeeds."
            title="Preview unavailable"
            tone="error"
          />
        ) : selectedResult ? (
          <div className="stack search-preview" id="search-preview-panel" ref={previewRef} tabIndex={-1}>
            <article className="hero-card">
              <p className="hero-card__eyebrow">
                {readString(selectedResult.source_label, readString(selectedResult.kind, "Result"))}
              </p>
              <h3>{readString(selectedResult.title, "Result")}</h3>
              <p className="hero-card__subtle">
                {readString(
                  selectedResult.summary,
                  readString(selectedResult.snippet, "No preview available."),
                )}
              </p>
              {readString(selectedResult.deep_link) ? (
                <div className="hero-command-actions">
                  <ConsoleLink className="primary-button" to={readString(selectedResult.deep_link)}>
                    {openLabel(selectedResult)}
                  </ConsoleLink>
                </div>
              ) : (
                <p className="list-card__meta">
                  This result is already in its richest context here in Search.
                </p>
              )}
            </article>

            <KeyValueGrid
              values={[
                { label: "Source", value: readString(selectedResult.source_label, "Result") },
                {
                  label: "Project",
                  value: readString(selectedResult.project_label, "Workspace"),
                },
                { label: "Harness", value: readString(selectedResult.harness, "—") },
                { label: "Occurred", value: readString(selectedResult.occurred_at, "—") },
                { label: "Path", value: readString(selectedResult.path, "—") },
              ]}
            />

            <article className="list-card">
              <div className="list-card__header">
                <h3>Why this matched</h3>
              </div>
              <ul className="reason-list">
                {(Array.isArray(selectedResult.why) ? (selectedResult.why as string[]) : []).map((reason) => (
                  <li key={`why:${reason}`}>{reason}</li>
                ))}
              </ul>
              {readString(selectedResult.dedupe_note) ? (
                <p className="list-card__meta">{readString(selectedResult.dedupe_note)}</p>
              ) : null}
            </article>

            <article className="list-card">
              <div className="list-card__header">
                <h3>Preview</h3>
              </div>
              <pre className="inline-json">
                {readString(
                  selectedResult.preview,
                  readString(selectedResult.snippet, "No preview available."),
                )}
              </pre>
            </article>
          </div>
        ) : results.length ? (
          <StateNotice
            detail="Pick a result from the left-hand column to inspect its preview, provenance, and deep link."
            title="Select a result to inspect"
          />
        ) : (
          <StateNotice
            detail="Run a search or broaden the filters to produce a preview with provenance here."
            title="No preview results yet"
          />
        )}
      </Panel>
    </div>
  );
}
