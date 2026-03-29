# Pi Harness Guide

Use Pi when you want the deepest native v2.4 path: governed `open` for Hive-managed work or advisory `attach` for continuing a live Pi session.

## Five-minute path

Install Hive and the Pi companion:

```bash
uv tool install 'mellona-hive[console]'
npm install -g @mellona/pi-hive
```

Verify what this machine can really support:

```bash
hive integrate doctor pi --json
hive integrate pi
```

Then stay inside Pi for first value:

```bash
pi-hive connect
pi-hive next --project-id <project-id>
pi-hive open <task-id> --json
```

If you already have a live Pi session, attach it instead of relaunching:

```bash
pi-hive attach <native-session-ref> --task-id <task-id> --json
```

## Truth

- `pi-hive open ...` creates a governed Hive-managed run
- `pi-hive attach ...` binds an existing Pi session as advisory
- both modes persist normalized `trajectory.jsonl` and steering artifacts

## If something fails

Run:

```bash
hive integrate doctor pi --json
```

That will tell you whether Node, the companion package, and the managed runner are all available.
