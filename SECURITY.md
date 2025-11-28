# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in Agent Hive, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of these methods:

1. **GitHub Security Advisories** (Preferred): Use [GitHub's private vulnerability reporting](https://github.com/intertwine/hive-orchestrator/security/advisories/new)

2. **Email**: Contact the maintainers directly (see repository for contact information)

### What to Include

Please include as much of the following information as possible:

- Type of vulnerability (e.g., injection, authentication bypass, etc.)
- Full paths of source files related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact assessment of the vulnerability

### Response Timeline

- **Initial Response**: Within 48 hours of report
- **Status Update**: Within 7 days
- **Resolution Target**: Within 30 days for critical issues

### What to Expect

1. **Acknowledgment**: We'll confirm receipt of your report
2. **Assessment**: We'll investigate and determine the severity
3. **Updates**: We'll keep you informed of our progress
4. **Resolution**: We'll develop and test a fix
5. **Disclosure**: We'll coordinate public disclosure with you

## Security Best Practices

When using Agent Hive:

### API Keys

- **Never commit API keys** to the repository
- Use the `.env` file for local development (it's git-ignored)
- Use GitHub Secrets for CI/CD workflows
- Rotate keys if you suspect exposure

### GitHub Actions

- The Cortex workflow only modifies `GLOBAL.md` and `projects/**/AGENCY.md` files
- All file modifications are validated before commit
- Fork PRs do not have access to repository secrets

### Self-Hosting

If deploying your own instance:

- Run the Coordinator Server behind a reverse proxy with HTTPS
- Restrict network access to trusted agents
- Monitor logs for unusual activity
- Keep dependencies updated

## Known Security Considerations

### By Design

- **Cortex modifies files automatically**: The orchestration engine updates Markdown files. This is intentional but should be understood.
- **LLM API calls**: Cortex sends project state to configured LLM providers. Be mindful of sensitive information in AGENCY.md files.

### Mitigations in Place

- File modification whitelist (only AGENCY.md and GLOBAL.md)
- No code execution from LLM responses
- Git-based audit trail for all changes
- Secrets stored in environment variables

## Scope

This security policy applies to:

- The Agent Hive codebase in this repository
- The official GitHub Actions workflows
- Documentation and examples

It does not cover:

- Third-party integrations or forks
- User-deployed instances (your responsibility)
- External services (OpenRouter, GitHub, etc.)

## Attribution

We appreciate responsible disclosure and will acknowledge security researchers who report valid vulnerabilities (unless they prefer to remain anonymous).

Thank you for helping keep Agent Hive secure!
