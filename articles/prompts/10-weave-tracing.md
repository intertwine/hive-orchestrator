# Image Prompts: Observability with Weave Tracing

*These prompts are designed for Google Gemini Imagen 3 / Nano Banana Pro model. Generate 6-8 images for the article.*

---

## Image 1: Hero Image - The Observability Dashboard

**Prompt:**
Create an image of a futuristic monitoring dashboard for AI agents. A large curved display shows real-time traces of LLM calls flowing through a beehive-shaped system. Individual call traces appear as golden light trails connecting nodes. Metrics panels show latency histograms, token usage graphs, and success/failure indicators. The Weights & Biases (W&B) logo appears subtly integrated. An operator (human or robot) observes the dashboard, gaining insight into the system's behavior. The atmosphere is professional and high-tech, like a mission control center for AI orchestration. Epic monitoring dashboard illustration, observability theme, data visualization aesthetic.

**Caption:** *Complete visibility: Weave tracing shows every LLM call, its latency, token usage, and success status. No more black-box AI operations.*

---

## Image 2: Tracing Architecture Flow

**Prompt:**
Create an architectural diagram showing how Weave tracing integrates with Agent Hive. On the left, three components (Cortex, Dashboard, Dispatcher) send requests through a central "traced_llm_call()" function. The function captures metadata (latency, tokens, success) while the request flows to an OpenRouter API on the right. Below the traced_llm_call, a Weave collector gathers the trace data and sends it to a W&B cloud icon at the bottom. Arrows show the flow of data and traces. Clean architecture diagram style, data flow visualization, integration concept.

**Caption:** *Tracing architecture: All LLM calls flow through traced_llm_call(), which captures metrics and sends them to Weave for analysis.*

---

## Image 3: LLMCallMetadata Visualization

**Prompt:**
Create an illustration of the LLMCallMetadata object as a detailed information card or data panel. The card shows fields displayed beautifully: "model: claude-haiku-4.5" with a brain icon, "latency_ms: 847" with a stopwatch, "prompt_tokens: 1,234" with input arrows, "completion_tokens: 567" with output arrows, "total_tokens: 1,801" with a sum symbol, "success: true" with a green checkmark, "timestamp" with a clock. The card floats in a digital space, representing structured metadata from an LLM call. Data card illustration, clean information design, metadata visualization.

**Caption:** *Rich metadata for every call: Model, latency, token counts, success status, and timestamps - all captured automatically.*

---

## Image 4: Automatic Header Sanitization

**Prompt:**
Create a before/after comparison showing API key sanitization. Left side shows raw headers with a visible API key: "Authorization: Bearer sk-or-v1-actual-key-here" highlighted in red with warning symbols. Right side shows the same headers after sanitization, with the key replaced by "***REDACTED***" in green/safe color. An arrow between them shows the sanitization process. The message is clear: sensitive data never reaches the logs. Split comparison illustration, security-focused, privacy protection concept.

**Caption:** *Security by default: API keys and sensitive headers are automatically redacted before being sent to Weave traces.*

---

## Image 5: Graceful Degradation

**Prompt:**
Create an illustration showing graceful degradation as a highway with alternate routes. The main highway is labeled "Weave Tracing Enabled" with monitoring towers along the route. Three exit ramps show fallback scenarios: (1) "Weave Not Installed" - the road continues smoothly without monitoring, (2) "No API Key" - local-only operation, (3) "Initialization Failed" - a warning sign but the road continues. The destination "Application Works" is reached regardless of which path is taken. The message: tracing is optional and never breaks the application. Highway/route illustration, fallback concept, reliability theme.

**Caption:** *Graceful degradation: If Weave isn't available, isn't configured, or fails to initialize, Agent Hive continues working normally.*

---

## Image 6: Trace Inspection View

**Prompt:**
Create a detailed illustration of inspecting a single trace in the W&B interface. A expanded trace card shows: a timeline bar with start and end markers, request payload section (with redacted auth header), response section with completion text, token breakdown chart (prompt vs completion), latency measurement with milliseconds display, and error details section (empty for successful call). The interface looks modern and data-rich, like a premium debugging tool. Interface mockup illustration, trace inspection concept, detailed data view.

**Caption:** *Drilling into traces: See the full request, response, token breakdown, and timing for any LLM call.*

---

## Image 7: Custom Operation Tracing

**Prompt:**
Create an illustration showing the @trace_op decorator in action. A Python function definition is shown with @trace_op("process_project") decorating it. From the function, a trace record extends like a filing card, capturing: function name, input arguments, return value, duration, and success status. Multiple decorated functions are shown creating a hierarchy of nested trace records. The concept of wrapping any function in observability is clear. Code-meets-visualization illustration, decorator concept, function tracing aesthetic.

**Caption:** *Trace any operation: Use @trace_op to add observability to your own functions, creating hierarchical trace records.*

---

## Image 8: Debugging with Traces

**Prompt:**
Create an illustration showing a detective or analyst using traces to debug issues. Three investigation scenarios are shown: (1) "Slow Calls" - a magnifying glass on latency spikes in a timeline, (2) "Failed Calls" - filtering to show only red/failed entries with error messages visible, (3) "Token Analysis" - grouping calls by model to analyze token consumption. The overall scene suggests using data to solve problems, with traces as the evidence. Detective/investigation illustration, debugging concept, data-driven problem solving aesthetic.

**Caption:** *Debug with data: Filter by latency, success status, or model to identify issues. Traces provide the evidence you need.*

---

## Generation Notes

**Style consistency:** Data-rich, observability-focused illustrations. Clean, modern aesthetic like a SaaS monitoring platform. Use the Weights & Biases orange/coral accent color where appropriate alongside Agent Hive's gold/honey tones.

**Visual elements:**
- Timelines and trace flows
- Metrics charts and graphs
- Data cards and panels
- Golden light trails for traces
- Beehive motifs integrated with monitoring
- W&B brand colors (coral/orange) as accent

**Aspect ratios:**
- Hero image (1): 16:9 landscape for dashboard scene
- Architecture (2): 16:9 for flow diagram
- Metadata card (3): Square 1:1 for data card
- Sanitization (4): 16:9 for before/after
- Degradation (5): 16:9 for highway metaphor
- Trace view (6): 16:9 for interface mockup
- Decorator (7): Square 1:1 for code concept
- Debugging (8): 16:9 for investigation scene

**Quality modifiers:** high-quality, data visualization style, modern SaaS aesthetic, professional monitoring theme, clean and informative
