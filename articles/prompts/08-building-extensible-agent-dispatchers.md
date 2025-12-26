# Image Prompts: Building Extensible Agent Dispatchers

*These prompts are designed for Google Gemini Imagen 3 / Nano Banana Pro model. Generate 8 images for the article.*

---

## Image 1: Hero Image - One Hive, Many Agents

**Prompt:**
Create an image depicting a grand central beehive control tower with multiple glowing pathways leading outward to different destinations. From the central hive, illuminated dispatch tubes or light-rails extend to various agent platforms represented as distinct stations: a GitHub-branded terminal with the Claude robot waiting, a Slack-styled communication hub with team silhouettes, an OpenAI-branded workshop with an assistant robot, and a generic webhook antenna tower. Work requests (depicted as glowing hexagonal task packages) travel along these pathways to the appropriate destinations. The scene conveys the idea of a single orchestration center routing work to diverse agents. Epic architectural illustration, futuristic logistics center aesthetic, warm honey-gold highlights against cool technology blue, sense of organized flow and optionality.

**Caption:** *The dispatcher vision: One central hive, many agent destinations. Work flows automatically to the best agent for each task—Claude, GPT-4, Gemini, or human teams.*

---

## Image 2: The Dispatcher Pattern Architecture

**Prompt:**
Create a clean architectural diagram visualization showing the three-stage dispatcher pattern as a horizontal flow. Left stage "FIND WORK": A Cortex engine cylinder with gears, outputting a list of ready projects as document icons. Middle stage "BUILD CONTEXT": An assembly station where AGENCY.md documents, file trees, and code snippets are combined into a rich context package. Right stage "DELIVER": Multiple output channels branching out—a GitHub issue, a Slack message, an API endpoint, an email icon. Arrows flow left to right showing the transformation. Clean, technical illustration style, blueprint-like precision, clear visual hierarchy, professional and informative.

**Caption:** *The dispatcher pattern: Find work (query Cortex), Build context (assemble what agents need), Deliver (hand off in the agent's native format).*

---

## Image 3: Why Dispatchers Matter - Vendor Independence

**Prompt:**
Create an image showing the concept of vendor independence through a modular plug-and-play system. A central orchestration platform (beehive motif) has standardized docking ports where different agent modules can connect and disconnect easily. Currently plugged in: a Claude module (anthropic style), but floating nearby ready to swap: a GPT-4 module (OpenAI green), a Gemini module (Google colors), a self-hosted model module (custom gear icon). The docking mechanism emphasizes easy switching without changing the core infrastructure. The project structure (AGENCY.md files) remains unchanged regardless of which module is plugged in. Modular technology illustration, hardware-inspired aesthetic, clean swap-in swap-out visual metaphor, empowering and flexible.

**Caption:** *Vendor independence: Switch agents without changing project structure. Today Claude, tomorrow GPT-4—the orchestration remains stable.*

---

## Image 4: Best-of-Breed Routing

**Prompt:**
Create an image showing intelligent task routing as a smart sorting conveyor system. Tasks (represented as distinct packages with labels) enter from the top and a routing mechanism directs them to specialized agents based on their characteristics. A "Research" package routes to a GPT-4 agent with web browsing (globe icon), a "Complex Code" package routes to a Claude agent (sophisticated robot), a "Documentation" package routes to a Haiku agent (feather/quill icon for fast writing), a "Review" package routes to a Gemini agent (multi-eye inspection bot). Each agent station shows its specialty icons. The system demonstrates that different agents excel at different tasks. Smart factory sorting illustration, colorful but organized, efficient and intelligent aesthetic.

**Caption:** *Best-of-breed routing: Research to GPT-4, complex code to Claude, docs to Haiku, review to Gemini. Each task goes to the agent that excels at it.*

---

## Image 5: The Claude Code Dispatcher Deep Dive

**Prompt:**
Create an illustrated code-flow diagram showing the Claude Code dispatcher's internal mechanics as a cross-section machine view. Four chambers in sequence: Chamber 1 "ready_work()" shows the Cortex brain scanning project files. Chamber 2 "select_work" shows a priority sorting funnel (critical at top, low at bottom). Chamber 3 "build_context" shows AGENCY.md content being wrapped with file trees and instructions into a rich issue package. Chamber 4 "deliver" shows the package transforming into a GitHub issue with @claude mention that triggers the Claude robot. A final output shows the AGENCY.md being updated with "owner: claude-code". Technical cutaway illustration, machine internals aesthetic, step-by-step process visualization, detailed but clear.

**Caption:** *Inside the Claude Code dispatcher: Find ready work, select by priority, build rich context, create GitHub issue with @claude mention, claim ownership.*

---

## Image 6: Multi-Agent Router Architecture

**Prompt:**
Create an image showing a sophisticated multi-agent routing system as an intelligent traffic control center. A central routing hub (hexagonal control room) receives incoming projects and examines their tags and attributes. Based on routing rules displayed on screens (condition → agent mappings), projects are directed to different dispatcher queues. The queues lead to distinct agent terminals: Claude Code (for default coding), GPT-4 Researcher (with research/web tags), Gemini Reviewer (with review tags), Haiku Writer (with documentation tags). A fallback arrow shows unmatched projects going to Claude Code as default. Air traffic control or railway switching aesthetic, organized complexity, intelligent decision-making visualization.

**Caption:** *Multi-agent routing: Rules examine project tags and route to specialized agents. Research tasks to GPT-4, reviews to Gemini, everything else to Claude.*

---

## Image 7: Completion Callbacks Pattern

**Prompt:**
Create an image showing three different completion callback patterns as three parallel tracks or lanes. Lane 1 "DIRECT UPDATE": An agent robot directly editing an AGENCY.md file, creating a PR, setting owner to null—the cleanest loop. Lane 2 "WEBHOOK CALLBACK": An agent sending a completion signal to a webhook endpoint which then updates the AGENCY.md file. Lane 3 "POLLING": A monitoring eye periodically checking agent status, then updating AGENCY.md when complete. All three lanes converge at the same destination: an updated AGENCY.md with tasks marked complete and ownership released. Comparative process illustration, three parallel approaches, clear visual distinction, all valid paths to the same goal.

**Caption:** *Completion patterns: Direct AGENCY.md updates (cleanest), webhook callbacks, or status polling. All ensure the Hive knows when work is done.*

---

## Image 8: Production Architecture

**Prompt:**
Create a comprehensive production architecture diagram as a layered system visualization. Top layer "GitHub Actions (Scheduled)": Cortex engine running at :00, Router running at :15, connecting to multiple dispatcher boxes (Claude Code, Slack, OpenAI). Middle layer "Agent Execution": Each dispatcher's output showing the agent working (Claude sees @claude, human claims Slack work, OpenAI runs thread). Bottom layer "AGENCY.md (Source of Truth)": A central glowing document showing updates flowing back—tasks complete, notes added, ownership released, downstream work unlocked. Arrows show the full cycle: Cortex → Router → Dispatchers → Agents → AGENCY.md → (cycle repeats). Production system diagram style, comprehensive but not cluttered, professional DevOps aesthetic, full-cycle visualization.

**Caption:** *Production architecture: Cortex analyzes, Router dispatches, Agents execute, AGENCY.md captures state. A complete automation cycle with human oversight.*

---

## Generation Notes

**Style consistency:** Professional technical illustrations with a focus on clarity and architecture. Use the beehive/Agent Hive visual motifs (hexagons, honey-gold accents) as connecting elements. Show dispatchers as bridges between the Hive and diverse agent ecosystems.

**Color palette:**
- Agent Hive/Cortex: Honey gold, warm amber
- Claude/Anthropic: Warm coral/terracotta
- OpenAI/GPT: Green tones
- Google/Gemini: Google colors (blue, red, yellow, green)
- Slack: Purple/Slack brand colors
- Generic/neutral: Cool blues and grays

**Aspect ratios:**
- Hero image (1): 16:9 landscape for epic architectural scene
- Dispatcher pattern (2): 16:9 for horizontal flow diagram
- Vendor independence (3): 4:3 for modular visualization
- Best-of-breed (4): 16:9 for conveyor/routing layout
- Claude dispatcher (5): 4:3 for detailed cutaway
- Multi-agent router (6): 16:9 for traffic control scene
- Completion callbacks (7): 4:3 for parallel lanes comparison
- Production architecture (8): 16:9 for comprehensive system diagram

**Quality modifiers:** high-quality, detailed illustration, professional technical aesthetic, clear information hierarchy, modern DevOps/infrastructure style
