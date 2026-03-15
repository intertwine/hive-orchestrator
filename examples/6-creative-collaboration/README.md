# Creative Collaboration

Use this pattern when the work is iterative, style-sensitive, and benefits from shared memory.

Typical task stack:

1. define brief and tone
2. draft outline
3. draft main piece
4. edit and polish

## Hive v2 Flow

```bash
hive task create --project-id creative-demo --title "Define tone and brief" --json
hive task create --project-id creative-demo --title "Draft outline" --json
hive task create --project-id creative-demo --title "Write first draft" --json
```

Use memory to preserve the shared voice:

```bash
hive memory observe --note "Keep the tone spare, warm, and lightly funny" --scope project --json
hive memory reflect --scope project --json
```

## Why This Pattern Works

- the task graph captures the sequence
- memory captures taste, constraints, and lessons learned
- `AGENCY.md` stays readable for humans reviewing the creative direction

Useful commands:

```bash
hive context startup --project creative-demo --json
hive memory search "tone" --project creative-demo --json
```
