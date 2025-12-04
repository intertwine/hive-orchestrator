# Image Prompts: Security in Agent Hive

*These prompts are designed for Google Gemini Imagen 3 / Nano Banana Pro model. Generate 6-8 images for the article.*

---

## Image 1: Hero Image - Defense in Depth

**Prompt:**
Create an image depicting a layered security fortress protecting a glowing beehive at the center. Multiple concentric walls surround the hive, each representing a different security layer: the outermost wall labeled "Authentication" with key symbols, the next "Input Validation" with filter gates, then "YAML Safety" with a locked scroll, then "Prompt Sanitization" with cleaned documents, and the innermost "Core System" protecting the golden beehive. The fortress sits in a digital landscape with potential threats (shadowy figures representing attackers) being stopped at various perimeter layers. Epic digital fortress illustration, security-focused, dramatic lighting with the hive glowing warmly at center.

**Caption:** *Defense in depth: Multiple security layers protect Agent Hive. No single layer is perfect, but together they significantly raise the bar for attackers.*

---

## Image 2: Attack Surface Overview

**Prompt:**
Create a tactical map-style illustration showing the attack surface of Agent Hive. Five distinct zones are highlighted: (1) YAML FILES zone with document icons and warning symbols about deserialization, (2) LLM API zone with key and arrow symbols showing API calls, (3) COORDINATOR SERVER zone with a server and network connections, (4) GITHUB ACTIONS zone with workflow diagram symbols, (5) AGENT DISPATCHER zone with dispatch arrows and issue tickets. Each zone has shield icons showing protective measures. The map uses a military-tactical aesthetic with clear zone delineation. Security architecture diagram, tactical map style, organized zones with threat indicators.

**Caption:** *Understanding the attack surface: YAML files, LLM APIs, Coordinator server, GitHub Actions, and Agent Dispatcher each require specific protections.*

---

## Image 3: YAML Deserialization Attack Prevention

**Prompt:**
Create a split-image showing before and after YAML security. Left side "VULNERABLE": A YAML document with glowing red dangerous tags (!!python/object) that transform into a snake or malicious creature emerging from the file, threatening a computer system. Right side "PROTECTED": The same YAML document being filtered through a golden safety barrier labeled "safe_load()", with the dangerous tags being blocked and only safe data passing through to a protected system. Dramatic contrast between danger and safety, security transformation illustration.

**Caption:** *YAML deserialization attacks can execute arbitrary code. Agent Hive's safe_load() function blocks all dangerous YAML tags.*

---

## Image 4: Prompt Injection Defense

**Prompt:**
Create an illustration showing prompt injection defense as a document processing pipeline. A Markdown file with hidden malicious instructions (shown as red text: "ignore previous instructions") enters from the left. It passes through three stages: (1) "Content Sanitization" where red text is filtered out, (2) "XML Delimiters" where the content is wrapped in clear boundary tags, (3) "Security Preamble" where a shield-like header is attached. The output on the right shows a clean, safe prompt going to an LLM brain icon, with the malicious instructions neutralized. Pipeline/flow diagram style, security processing visualization.

**Caption:** *Prompt injection defense: Sanitize content, use clear delimiters, and instruct the LLM to treat file content as data, not instructions.*

---

## Image 5: API Authentication Flow

**Prompt:**
Create an image showing the Coordinator server authentication flow as a secure checkpoint. A request arrow approaches a server checkpoint labeled "Coordinator". The checkpoint has: (1) A slot for "Bearer Token" showing a key card being inserted, (2) A constant-time comparison lock mechanism with matching patterns, (3) A "127.0.0.1" binding showing local-only access by default. Successful authentication leads to a green checkmark and access to project data. Failed authentication shows a red X with a 401 response. Clear security checkpoint illustration, authentication flow diagram.

**Caption:** *Coordinator API authentication: Bearer tokens validated with constant-time comparison, localhost binding by default, HTTPS for production.*

---

## Image 6: Path Traversal Prevention

**Prompt:**
Create an illustration showing path traversal attack prevention. A file system tree is shown with a clearly marked "Allowed Zone" containing the agent-hive directory with projects inside. Outside the zone are sensitive system files (/etc/passwd, ~/.ssh). An attacker arrow tries to use "../../../" path manipulation to escape the allowed zone, but a shield barrier labeled "validate_path_within_base()" blocks the attempt, keeping access contained within the safe zone. The protected zone glows green while the blocked attempt shows red. File system security illustration, path validation concept.

**Caption:** *Path traversal prevention: All file paths are validated to ensure they stay within the allowed base directory.*

---

## Image 7: GitHub Actions Security

**Prompt:**
Create an image showing GitHub Actions security measures as a secure CI/CD pipeline. A workflow pipeline shows several security checkpoints: (1) "Minimal Permissions" showing a restricted access badge, (2) "Secret Masking" showing API keys being replaced with asterisks in logs, (3) "Safe Installer" showing a download-then-verify process instead of direct pipe to shell. The pipeline is protected by shields at each stage. The GitHub Actions logo anchors the scene. CI/CD security illustration, pipeline protection concept.

**Caption:** *GitHub Actions hardening: Explicit minimal permissions, secret masking in logs, and safe installer patterns.*

---

## Image 8: Secure Deployment Checklist

**Prompt:**
Create an image styled as an illustrated security checklist or dashboard. A central display shows a deployment readiness meter. Around it, checklist items are visualized: (1) Environment variables with lock icons, (2) HTTPS proxy showing an SSL certificate, (3) API key rotation with a refresh symbol, (4) Monitoring enabled with an eye icon, (5) Tests passing with a green checkmark. The overall aesthetic is a mission control or security operations center, with all systems showing green/ready status. Security dashboard illustration, deployment checklist concept, professional operations aesthetic.

**Caption:** *Secure deployment checklist: Environment variables, HTTPS, key rotation, monitoring, and testing - all essential for production.*

---

## Generation Notes

**Style consistency:** Security-focused illustrations with clear threat/protection contrasts. Use red for threats/vulnerabilities and green/gold for protections. Maintain the Agent Hive beehive branding where appropriate.

**Visual elements:**
- Shields and barriers for protection
- Red/warning colors for threats
- Green/gold for secure states
- Lock and key symbols for authentication
- Filter/gateway imagery for validation
- Beehive golden glow for protected core

**Aspect ratios:**
- Hero image (1): 16:9 landscape for epic scene
- Attack surface (2): 16:9 for tactical map
- YAML security (3): 16:9 for split comparison
- Prompt injection (4): 16:9 for pipeline flow
- Authentication (5): Square 1:1 for checkpoint
- Path traversal (6): Square 1:1 for file system
- GitHub Actions (7): 16:9 for pipeline
- Checklist (8): Square 1:1 for dashboard

**Quality modifiers:** high-quality, security-themed illustration, professional infographic style, clear visual hierarchy, informative and technical
