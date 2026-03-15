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
Create a clean architectural diagram visualization showing the three-stage dispatcher pattern as a horizontal flow. Left stage "FIND WORK": a canonical ready queue produced from task cards, claims, and dependency edges. Middle stage "BUILD CONTEXT": an assembly station where `.hive/` state, `AGENCY.md`, `PROGRAM.md`, and search hits are combined into a rich startup package. Right stage "DELIVER": multiple output channels branching out, including a GitHub issue, a Slack message, an API endpoint, and an email icon. Arrows flow left to right showing the transformation. Clean, technical illustration style, blueprint-like precision, clear visual hierarchy, professional and informative.

**Caption:** *The dispatcher pattern: find work from the canonical queue, build context from Hive, then deliver it in the agent's native format.*

---

## Image 3: Why Dispatchers Matter - Vendor Independence

**Prompt:**
Create an image showing the concept of vendor independence through a modular plug-and-play system. A central orchestration platform with a beehive motif has standardized docking ports where different agent modules can connect and disconnect easily. Currently plugged in: a Claude module, but floating nearby ready to swap are a GPT module, a Gemini module, and a self-hosted model module. The docking mechanism emphasizes easy switching without changing the core infrastructure. The Hive workspace structure, with `.hive/`, `AGENCY.md`, and `PROGRAM.md`, remains stable regardless of which module is plugged in. Modular technology illustration, hardware-inspired aesthetic, clean swap-in swap-out visual metaphor, empowering and flexible.

**Caption:** *Vendor independence: Switch agents without changing project structure. Today Claude, tomorrow GPT-4—the orchestration remains stable.*

---

## Image 4: Best-of-Breed Routing

**Prompt:**
Create an image showing intelligent task routing as a smart sorting conveyor system. Tasks (represented as distinct packages with labels) enter from the top and a routing mechanism directs them to specialized agents based on their characteristics. A "Research" package routes to a GPT-4 agent with web browsing (globe icon), a "Complex Code" package routes to a Claude agent (sophisticated robot), a "Documentation" package routes to a Haiku agent (feather/quill icon for fast writing), a "Review" package routes to a Gemini agent (multi-eye inspection bot). Each agent station shows its specialty icons. The system demonstrates that different agents excel at different tasks. Smart factory sorting illustration, colorful but organized, efficient and intelligent aesthetic.

**Caption:** *Best-of-breed routing: Research to GPT-4, complex code to Claude, docs to Haiku, review to Gemini. Each task goes to the agent that excels at it.*

---

## Image 5: The Claude Code Dispatcher Deep Dive

**Prompt:**
Create an illustrated code-flow diagram showing the Claude Code dispatcher's internal mechanics as a cross-section machine view. Four chambers in sequence: Chamber 1 "hive task ready" shows the canonical queue being queried. Chamber 2 "select_work" shows a priority sorting funnel. Chamber 3 "hive context startup" shows task state, `AGENCY.md`, `PROGRAM.md`, and file context being wrapped into a rich issue package. Chamber 4 "deliver" shows the package transforming into a GitHub issue with an `@claude` mention that triggers the Claude robot. A final output shows the task being claimed in canonical state rather than flipping project ownership. Technical cutaway illustration, machine internals aesthetic, step-by-step process visualization, detailed but clear.

**Caption:** *Inside the Claude Code dispatcher: find ready work, select by priority, build context, create the issue, then claim the canonical task.*

---

## Image 6: Multi-Agent Router Architecture

**Prompt:**
Create an image showing a sophisticated multi-agent routing system as an intelligent traffic control center. A central routing hub (hexagonal control room) receives incoming projects and examines their tags and attributes. Based on routing rules displayed on screens (condition → agent mappings), projects are directed to different dispatcher queues. The queues lead to distinct agent terminals: Claude Code (for default coding), GPT-4 Researcher (with research/web tags), Gemini Reviewer (with review tags), Haiku Writer (with documentation tags). A fallback arrow shows unmatched projects going to Claude Code as default. Air traffic control or railway switching aesthetic, organized complexity, intelligent decision-making visualization.

**Caption:** *Multi-agent routing: Rules examine project tags and route to specialized agents. Research tasks to GPT-4, reviews to Gemini, everything else to Claude.*

---

## Image 7: Completion Callbacks Pattern

**Prompt:**
Create an image showing three different completion callback patterns as three parallel tracks or lanes. Lane 1 "DIRECT UPDATE": an agent robot directly calling the Hive CLI to update a task or accept a run. Lane 2 "WEBHOOK CALLBACK": an agent sending a completion signal to a webhook endpoint which then updates canonical task state. Lane 3 "POLLING": a monitoring eye periodically checking agent status, then updating the task when complete. All three lanes converge at the same destination: refreshed task state, run artifacts, and synchronized human-facing projections. Comparative process illustration, three parallel approaches, clear visual distinction, all valid paths to the same goal.

**Caption:** *Completion patterns: direct task or run updates, webhook callbacks, or status polling. All feed back into the same canonical state.*

---

## Image 8: Production Architecture

**Prompt:**
Create a comprehensive production architecture diagram as a layered system visualization. Top layer "Scheduled Automation": a ready-queue job and a projection-sync job feeding multiple dispatcher boxes for Claude Code, Slack, and API-based agents. Middle layer "Agent Execution": each dispatcher's output shows the agent working in its native environment. Bottom layer "Canonical Hive State": a central glowing `.hive/` substrate with task updates, run artifacts, memory, and projections flowing outward to `AGENCY.md` and `GLOBAL.md`. Arrows show the full cycle: ready queue → dispatchers → agents → canonical state → synced projections. Production system diagram style, comprehensive but not cluttered, professional DevOps aesthetic, full-cycle visualization.

**Caption:** *Production architecture: Hive exposes the queue, dispatchers route work, agents execute, and canonical state flows back into synced projections.*

---

## Generation Notes

**Style consistency:** Professional technical illustrations with a focus on clarity and architecture. Use the beehive/Agent Hive visual motifs (hexagons, honey-gold accents) as connecting elements. Show dispatchers as bridges between the Hive and diverse agent ecosystems.

**Color palette:**
- Agent Hive: Honey gold, warm amber
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
