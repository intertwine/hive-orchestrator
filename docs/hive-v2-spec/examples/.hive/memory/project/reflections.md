# Reflections — Long-Term Project Memory

_Last updated: 2026-03-14 15:30 UTC_  
_Last reflected: 2026-03-14_

## Core Identity

- **Project:** Hive 2.0
- **Working style:** CLI-first, file-based, evaluator-gated
- **Primary interfaces:** `GLOBAL.md`, `AGENCY.md`, `PROGRAM.md`, `.hive/tasks/*.md`, `hive` CLI

## Durable architectural calls

- Canonical machine state is structured text in the repo.
- SQLite is local cache only.
- MCP is optional and should stay thin.
- Observational memory is part of the core design, not an afterthought.
- Autonomous work must produce run artifacts and evaluator results.

## Current roadmap

1. task files and parser
2. CLI JSON surface
3. `PROGRAM.md` and run engine
4. project-local memory
5. migration
6. optional Code Mode adapter
