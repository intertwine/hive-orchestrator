import { useMemo } from "react";

import { createConsoleClient } from "../api/client";
import { AttentionBoard } from "../components/AttentionBoard";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function InboxPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = useMemo(
    () => createConsoleClient(apiBase, workspacePath),
    [apiBase, workspacePath],
  );
  const { data, loading, error } = useConsoleQuery(
    `inbox:${apiBase}:${workspacePath}`,
    () => client.getInbox(),
    3000,
  );
  const items = useMemo(
    () => (Array.isArray(data?.items) ? data.items : []),
    [data?.items],
  );
  return (
    <AttentionBoard
      eyebrow="Operator attention"
      title="Inbox"
      loading={loading}
      error={error}
      items={items}
      mode="inbox"
      emptyMessage="The inbox is clear."
    />
  );
}
