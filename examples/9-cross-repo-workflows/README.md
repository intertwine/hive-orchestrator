# Example 9: Cross-Repository Workflows

This example demonstrates how to use Agent Hive to coordinate work across external GitHub repositories using the file-based hive protocol.

## Overview

Agent Hive can manage projects that target external repositories. By adding a `target_repo` field to your AGENCY.md metadata, the Dispatcher automatically:

1. Clones the external repository
2. Generates a file tree
3. Reads key files for context
4. Includes this information in the GitHub issue

The agent then works on the external repo while using AGENCY.md as shared memory.

## Use Cases

- **Open Source Contributions**: Coordinate improvements to open source projects
- **Multi-Repo Organizations**: Manage work across multiple repositories
- **Vendor Integrations**: Implement integrations with third-party systems
- **Documentation Projects**: Update docs across different repositories

## Project Structure

```
projects/external/
└── target-project/
    └── AGENCY.md          # Contains target_repo metadata
```

## Key Metadata Fields

```yaml
target_repo:
  url: https://github.com/org/repo    # Required: Repository URL
  branch: main                         # Optional: Branch (default: main)
```

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                        AGENCY.md                             │
│  target_repo:                                                │
│    url: https://github.com/example/repo                     │
│    branch: main                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Context Assembler                        │
│  1. Clone external repo (shallow, depth=1)                  │
│  2. Generate file tree (4 levels, excludes noise)           │
│  3. Read key files (package.json, README.md, src/index.*)   │
│  4. Include in issue body                                    │
│  5. Clean up temp directory                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Issue                            │
│  - AGENCY.md content                                         │
│  - Project file structure                                    │
│  - Target repo structure                                     │
│  - Target repo key files                                     │
│  - External repo-specific instructions                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Agent Work                            │
│  1. Claims project via AGENCY.md                            │
│  2. Forks target repo if needed                             │
│  3. Implements changes                                       │
│  4. Writes output to Phase sections in AGENCY.md            │
│  5. Creates PR to target repository                          │
│  6. Releases ownership                                       │
└─────────────────────────────────────────────────────────────┘
```

## Multi-Phase Pattern

For complex improvements, use phases within a single AGENCY.md:

```markdown
## Tasks
- [ ] Analyze repository structure and patterns
- [ ] Identify improvement opportunity
- [ ] Implement and submit PR

## Phase 1: Analysis
*Agent writes analysis here*

## Phase 2: Strategy
*Agent writes improvement plan here*

## Phase 3: Implementation
*Agent writes code changes and PR details here*
```

Each task can be handled by the same or different agents. The AGENCY.md captures the full history of work.

## Running This Example

1. **Create your external project**:
   ```bash
   mkdir -p projects/external/my-target-repo
   cp examples/9-cross-repo-workflows/AGENCY.md projects/external/my-target-repo/
   # Edit AGENCY.md to point to your target repo
   ```

2. **Check ready work**:
   ```bash
   make ready
   ```

3. **The Dispatcher will**:
   - Detect the project is ready
   - Clone the target repo for context
   - Create an issue with full context
   - Agent claims and works on it

## Example AGENCY.md

See the [AGENCY.md](./AGENCY.md) file in this directory for a complete example targeting a real repository.

## Best Practices

1. **Keep tasks atomic**: Each task should be completable in one work session
2. **Use phase sections**: Document analysis, strategy, and implementation separately
3. **Specify key files**: Use `relevant_files` to highlight important files in the target repo
4. **Write clear objectives**: The agent needs to understand what improvement to make
5. **Review before PR**: Always review agent output before submitting PRs to external repos

## Security Considerations

- External repos are cloned with `--depth 1` (shallow clone)
- Temporary directories are cleaned up immediately after context extraction
- Only public repositories can be cloned without authentication
- Review all generated code before submitting to external repositories

## Related Documentation

- [Article 11: Cross-Repository Multi-Agent Workflows](../../articles/11-cross-repo-multi-agent-workflows.md)
- [Context Assembler Source](../../src/context_assembler.py)
- [Dispatcher Source](../../src/agent_dispatcher.py)
