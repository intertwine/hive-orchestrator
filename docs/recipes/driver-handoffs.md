# Driver Handoffs

Different drivers are good at different parts of the job. Hive keeps the run record, context pack, worktree, and audit trail stable while the driver changes.

## Pick the driver for the task

- `local`: best for straightforward work inside one repo.
- `codex`: good when you want a strong coding agent with run artifacts and a prepared worktree.
- `claude-code`: good when broad repo search or synthesis matters more than fast local iteration.
- `manual`: good when a human or unsupported harness needs to take over.

## Before you reroute

- Check the current run detail and timeline.
- Make sure the current state is captured in the worktree and transcript.
- Add a short typed note explaining why the reroute is happening.

## After you reroute

- Confirm the new driver can see the same run brief and context manifest.
- Keep the same run ID and task lineage whenever possible.
- Leave the old driver’s transcript and handles in place for auditability.

## The rule of thumb

Reroute when the new driver has a clear advantage. Do not reroute just because a run feels slow for a minute.
