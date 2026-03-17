import { type FormEvent, useState } from "react";

import { createConsoleClient } from "../api/client";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";

export function SearchPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = createConsoleClient(apiBase, workspacePath);
  const [query, setQuery] = useState("program doctor");
  const [results, setResults] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = await client.search(query);
      setResults((payload.results as Array<Record<string, unknown>> | undefined) ?? []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Panel eyebrow="Unified corpus" title="Search">
      <form className="filters" onSubmit={handleSubmit}>
        <label className="console-field">
          <span>Query</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <div className="filters__actions">
          <button className="primary-button" type="submit">
            Search
          </button>
        </div>
      </form>

      {loading ? <p>Searching…</p> : null}
      {error ? <p className="error-copy">{error}</p> : null}
      <div className="stack">
        {results.length ? (
          results.map((result) => (
            <article className="list-card" key={String(result.id ?? result.path)}>
              <div className="list-card__header">
                <h3>{String(result.title ?? result.path ?? "Result")}</h3>
                <StatusPill tone={String(result.kind ?? "info")}>
                  {String(result.kind ?? "result")}
                </StatusPill>
              </div>
              <p>{String(result.summary ?? result.snippet ?? "No summary available.")}</p>
              <ul className="reason-list">
                {(((result.why as string[] | undefined) ?? (result.matches as string[] | undefined)) ?? []).map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </article>
          ))
        ) : (
          <p>No search results yet.</p>
        )}
      </div>
    </Panel>
  );
}
