export type JsonRecord = Record<string, unknown>;

export interface ConsoleHomePayload {
  ok: boolean;
  home: JsonRecord;
}

export interface ConsoleInboxPayload {
  ok: boolean;
  items: JsonRecord[];
}

export interface ConsoleRunsPayload {
  ok: boolean;
  runs: JsonRecord[];
}

export interface ConsoleRunDetailPayload {
  ok: boolean;
  detail: JsonRecord;
}

export interface ConsoleProjectsPayload {
  ok: boolean;
  projects: JsonRecord[];
}

export interface ConsoleProjectContextPayload {
  ok: boolean;
  project: JsonRecord;
  rendered: string;
  context: JsonRecord;
}

export interface ConsoleProgramDoctorPayload {
  ok: boolean;
  doctor: JsonRecord;
}

export interface ConsoleCampaignsPayload {
  ok: boolean;
  campaigns: JsonRecord[];
}

export interface ConsoleCampaignDetailPayload {
  ok: boolean;
  campaign: JsonRecord;
  active_runs: JsonRecord[];
  accepted_runs: JsonRecord[];
  project_status: JsonRecord[];
}

export interface ConsoleSearchPayload {
  ok: boolean;
  results: JsonRecord[];
}

function withPath(url: URL, workspacePath: string) {
  if (workspacePath.trim()) {
    url.searchParams.set("path", workspacePath.trim());
  }
  return url;
}

async function fetchJson<T>(input: URL): Promise<T> {
  const response = await fetch(input);
  if (!response.ok) {
    throw new Error(`Console request failed: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function createConsoleClient(apiBase: string, workspacePath: string) {
  const root = apiBase.replace(/\/+$/, "") || window.location.origin;

  return {
    getHome() {
      return fetchJson<ConsoleHomePayload>(withPath(new URL(`${root}/home`), workspacePath));
    },

    getInbox() {
      return fetchJson<ConsoleInboxPayload>(withPath(new URL(`${root}/inbox`), workspacePath));
    },

    getRuns(filters?: {
      projectId?: string;
      driver?: string;
      health?: string;
      campaignId?: string;
    }) {
      const url = withPath(new URL(`${root}/runs`), workspacePath);
      if (filters?.projectId) {
        url.searchParams.set("project_id", filters.projectId);
      }
      if (filters?.driver) {
        url.searchParams.set("driver", filters.driver);
      }
      if (filters?.health) {
        url.searchParams.set("health", filters.health);
      }
      if (filters?.campaignId) {
        url.searchParams.set("campaign_id", filters.campaignId);
      }
      return fetchJson<ConsoleRunsPayload>(url);
    },

    getRunDetail(runId: string) {
      return fetchJson<ConsoleRunDetailPayload>(
        withPath(new URL(`${root}/runs/${runId}`), workspacePath),
      );
    },

    steerRun(
      runId: string,
      payload: {
        action: string;
        reason?: string;
        target?: JsonRecord;
        budget_delta?: JsonRecord;
        note?: string;
        actor?: string;
      },
    ) {
      const url = withPath(new URL(`${root}/runs/${runId}/steer`), workspacePath);
      return fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then(async (response) => {
        if (!response.ok) {
          throw new Error(`Console request failed: ${response.status} ${response.statusText}`);
        }
        return (await response.json()) as JsonRecord;
      });
    },

    getProjects() {
      return fetchJson<ConsoleProjectsPayload>(withPath(new URL(`${root}/projects`), workspacePath));
    },

    getProjectContext(projectRef: string) {
      return fetchJson<ConsoleProjectContextPayload>(
        withPath(new URL(`${root}/projects/${projectRef}/context`), workspacePath),
      );
    },

    getProjectDoctor(projectRef: string) {
      return fetchJson<ConsoleProgramDoctorPayload>(
        withPath(new URL(`${root}/projects/${projectRef}/doctor`), workspacePath),
      );
    },

    getCampaigns() {
      return fetchJson<ConsoleCampaignsPayload>(
        withPath(new URL(`${root}/campaigns`), workspacePath),
      );
    },

    getCampaign(campaignId: string) {
      return fetchJson<ConsoleCampaignDetailPayload>(
        withPath(new URL(`${root}/campaigns/${campaignId}`), workspacePath),
      );
    },

    search(query: string, scopes?: string[]) {
      const url = withPath(new URL(`${root}/search`), workspacePath);
      url.searchParams.set("query", query);
      for (const scope of scopes ?? []) {
        url.searchParams.append("scope", scope);
      }
      return fetchJson<ConsoleSearchPayload>(url);
    },
  };
}
