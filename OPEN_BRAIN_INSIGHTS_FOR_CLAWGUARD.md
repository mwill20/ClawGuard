# Open Brain Insights → ClawGuard

> **Source:** Open Brain architecture session (March 3, 2026)
> **Purpose:** Capture cross-project insights before they evaporate. Add this to the ClawGuard project folder.

---

## Why This Matters for ClawGuard

Open Brain and ClawGuard share the same DNA. Open Brain monitors a human's cognitive behavior. ClawGuard monitors an AI agent's operational behavior. The architectural patterns, schema designs, and detection mechanisms transfer directly. What we designed for one strengthens the other.

---

## 1. The Schema Pattern Is Identical

**Open Brain's core schema:** thought + vector embedding + metadata + typed relationships + audit trail

**ClawGuard's equivalent:** agent_action + vector embedding + metadata + typed relationships + audit trail

The swap is clean:

| Open Brain | ClawGuard |
|-----------|-----------|
| `thought` (raw text capture) | `agent_action` (tool call, API request, output) |
| `source_ai` (Claude, ChatGPT, etc.) | `agent_id` (which agent performed the action) |
| `thought_type` (decision, insight, action item) | `action_type` (tool_use, api_call, file_write, shell_exec) |
| `people` (extracted entities) | `targets` (files, URLs, APIs, users affected) |
| `topics` (extracted categories) | `capability_tags` (wallet, search, execute, skill) |
| `link_type` (builds_on, contradicts, led_to) | `action_chain` (triggered_by, escalated_to, resulted_in) |
| `energy_level` (optional user state) | `confidence_score` (model's own certainty) |
| Embedding (text-embedding-3-small, 1536d) | Embedding (same model, same dimensions) |
| Neo4j relationships | Neo4j relationships (same traversal queries) |

**What this means for ClawGuard:**

- Do NOT design ClawGuard's persistence layer from scratch. Fork Open Brain's schema and rename fields.
- The Postgres + pgvector + Neo4j dual-database pattern works identically: Postgres handles storage and vector search, Neo4j handles action chain traversal and pattern detection.
- Supabase Edge Functions as ingestion pipeline: receives agent telemetry → extracts metadata → generates embedding → stores in Postgres → creates Neo4j nodes/edges. Same pipeline, different data.
- RLS policies, audit logging, and service role key isolation transfer directly.

---

## 2. Detection Features Map to Monitoring Features

Open Brain's dashboard features are ClawGuard detection rules with different labels:

| Open Brain Feature | ClawGuard Equivalent | Detection Purpose |
|-------------------|---------------------|-------------------|
| **Orphan Detector** | **Orphan Action Detector** | Agent actions with no relationship to any known workflow = potentially unauthorized activity |
| **Convergence Radar** | **Behavior Convergence Alert** | Multiple agents producing semantically similar actions = coordinated behavior (benign or malicious) |
| **Bridge Nodes** | **Lateral Movement Detector** | Actions connecting otherwise disconnected system clusters = agent pivoting across domains |
| **Decay Alert** | **Dormant Agent Wake-Up Alert** | Agent that was inactive suddenly becomes active = potential compromise or unauthorized reactivation |
| **Goal Drift Detection** | **Policy Drift Detection** | Agent behavior deviating from defined policy boundaries = drift from intended operation |
| **Skill Decay Detection** | **Capability Creep Detection** | Agent gaining new capabilities over time that weren't in original specification = scope expansion |
| **Decision Tree Visualization** | **Action Chain Visualization** | Trace full decision path from trigger to outcome = forensic investigation tool |
| **Source Distribution** | **Agent Activity Heatmap** | Which agents are most active, doing what = operational visibility |
| **suggest_connections** | **Anomaly Correlation Engine** | Find semantically similar actions not yet linked = discover attack patterns spanning multiple agents |

**What this means for ClawGuard:**

- The dashboard visualization work done for Open Brain directly transfers. Same React components, same D3/recharts visualizations, different data labels.
- The `get_graph_view` MCP tool returns the same structured payload (nodes + edges) for both systems.
- You don't need separate visualization libraries. Build once for Open Brain, theme-swap for ClawGuard.

---

## 3. The "5 Attack Surface Primitives" Connect to Open Brain Source Types

**From the "Web is Forking" analysis (Feb 22):** ClawGuard monitors 5 attack surface primitives from the agent infrastructure layer:

1. **Agentic Wallets** (X402, Stripe ACS) — financial transactions
2. **Machine-Readable Content** (Cloudflare Markdown) — prompt injection surface
3. **Shell Execution** (OpenAI Skills) — arbitrary code execution
4. **Versioned Skills** — supply chain attack surface
5. **Agent Search** (Exa.ai) — adversarial content redirection

**Open Brain equivalent:** These are just `source_types` in the ingestion pipeline. Each primitive maps to a telemetry channel:

| Attack Primitive | Telemetry Channel | ClawGuard Ingestion |
|-----------------|-------------------|---------------------|
| Agentic Wallet | Transaction logs | Edge Function receives payment events → extracts amount, recipient, context → embeds → checks against spending policy → Neo4j links to triggering action |
| Machine-Readable Content | Content ingestion logs | Edge Function receives markdown fetch events → embeds content → checks for injection patterns → Neo4j links to requesting agent |
| Shell Execution | Container activity logs | Edge Function receives command logs → extracts commands, files touched, network calls → embeds → checks against allowlist → Neo4j links to skill that triggered |
| Versioned Skills | Skill registry events | Edge Function receives skill install/update events → embeds skill description → checks provenance → Neo4j links to agent using it |
| Agent Search | Search query/result logs | Edge Function receives search events → embeds queries and results → checks for adversarial content patterns → Neo4j links to downstream actions |

**What this means for ClawGuard:**

- The ingestion pipeline is the same Supabase Edge Function pattern. One function per primitive, all writing to the same Postgres + Neo4j backend.
- Each primitive gets its own `action_type` enum value, enabling filtered queries ("show me all wallet transactions for Agent-7 in the last 24 hours").
- The MCP tool surface for ClawGuard follows the same 12-tool pattern as Open Brain, with security-specific additions (e.g., `check_policy_compliance`, `quarantine_agent`, `get_risk_score`).

---

## 4. The AI Coach Pattern Becomes the Policy Engine

**Open Brain's AI Coach:** Runs analytical queries across Postgres and Neo4j to produce coaching reports — skill decay detection, goal drift, connection surfacing, weekly digest.

**ClawGuard's Policy Engine:** Same pattern, different purpose. Runs analytical queries across the agent telemetry database to produce security reports:

| Coach Feature | Policy Engine Feature | Query Pattern |
|--------------|----------------------|---------------|
| Skill Decay Detection | **Behavioral Baseline Drift** | Compare current agent action embeddings to historical baseline. Cosine distance exceeding threshold = behavior change. |
| Goal Drift Detection | **Policy Violation Detection** | Compare agent actions to declared policy boundaries. Semantic distance from policy intent exceeding threshold = violation. |
| Connection Surfacing | **Attack Pattern Discovery** | Find semantically similar actions across different agents not yet linked. Potential coordinated behavior. |
| Weekly Digest | **Security Posture Report** | Aggregate: total actions, policy violations, anomalies detected, risk score trend, agents requiring review. |
| Progress Rhythm Detector | **Activity Pattern Analyzer** | Detect unusual temporal patterns: burst activity, off-hours operations, periodic exfiltration-like behavior. |
| Ideal State Scoreboard | **Security Posture Score** | Computed from: % compliant actions, anomaly rate, mean time to detection, coverage across primitives. |

**What this means for ClawGuard:**

- The `run_coach_analysis` tool becomes `run_security_analysis` with identical internal architecture
- Scheduled runs (every hour, every day) produce automated security reports
- The same LLM-synthesis pattern works: feed structured data to an LLM, get a human-readable security brief
- Human confirmation requirements transfer: `capture_thought` runs freely → `capture_action` logs freely (low risk); `update_thought` needs confirmation → `quarantine_agent` definitely needs confirmation

---

## 5. Privacy Controls Become Access Controls

**Open Brain's privacy design:**

- Source-level tracking controls (which AI tools write to the database)
- In-conversation toggle (`@openbrain pause` / `@openbrain stop tracking`)
- Retroactive hard delete (remove from Postgres AND Neo4j)
- Auto-exclusion rules (categories that never get stored)

**ClawGuard's access control equivalent:**

| Open Brain Privacy | ClawGuard Access Control |
|-------------------|-------------------------|
| Source-level controls | **Agent enrollment** — which agents are monitored, with what permissions |
| Tracking toggle | **Monitoring modes** — active (full logging), passive (metadata only), exempt (no logging) |
| Hard delete | **Data retention policies** — automatic purge after N days, manual purge for sensitive operations |
| Auto-exclusion rules | **Redaction rules** — PII, credentials, and sensitive data stripped before storage |

**What this means for ClawGuard:**

- RLS policies from Open Brain extend with role-based access: security analysts see everything, developers see their agents only, executives see aggregate dashboards
- The audit trail design (source + timestamp on every write) is the SAME — ClawGuard just adds `reviewer` and `disposition` fields for human-in-the-loop decisions
- Redaction at ingestion (strip PII before embedding) is critical for ClawGuard and not needed for Open Brain — this is the one divergence point in the pipeline

---

## 6. The Portfolio Narrative — One Architecture, Two Applications

**The interview story:**

"I built Open Brain to apply the same monitoring principles to my own learning that ClawGuard applies to AI agent behavior. The architecture is identical: semantic search over vector embeddings, graph-based relationship tracking, anomaly detection via behavioral baseline drift, and a policy engine that flags when reality diverges from intent. Open Brain monitors ME. ClawGuard monitors AI agents. Same infrastructure, same patterns, different subjects."

**Why this matters:**

- Demonstrates you understand monitoring as a domain-agnostic discipline
- Shows you can abstract patterns from personal tools to enterprise systems
- Proves the architecture works because you use it yourself daily
- ClawGuard isn't theoretical — it's a generalization of a system you actually run

**What this means for ClawGuard:**

- The README should explicitly reference Open Brain as the companion project
- Architecture diagrams should show the shared infrastructure layer with domain-specific overlays
- The "Why this design?" section can reference "battle-tested on my personal knowledge system before applying to agent monitoring"

---

## 7. Specific Technical Transfers

**Directly reusable from Open Brain → ClawGuard:**

- Postgres schema with pgvector (rename tables, keep structure)
- Neo4j node/relationship schema (rename types, keep traversal patterns)
- Supabase Edge Function ingestion pipeline (add redaction step)
- MCP server skeleton (same tool registration pattern, different tool names)
- HNSW index configuration (cosine distance, 1536 dimensions)
- RLS policy templates (add role-based access)
- Dashboard React components (same visualizations, different themes)
- `brain_status` → `system_status` (same health check pattern)
- `bulk_import` → `bulk_ingest` (same batch processing for historical telemetry)

**ClawGuard-specific additions (not in Open Brain):**

- Real-time alerting (Open Brain is query-on-demand; ClawGuard needs push notifications)
- Policy-as-code engine (declarative rules that define acceptable agent behavior)
- Agent quarantine mechanism (block agent actions pending review)
- Risk scoring model (weighted combination of anomaly signals)
- Integration with existing SIEM/SOAR tools (Open Brain is standalone)
- Multi-tenant architecture (Open Brain is single-user; ClawGuard serves enterprise teams)

---

## Summary: What to Add to ClawGuard

| Transfer | Type | Priority |
|----------|------|----------|
| Fork Open Brain's Postgres+pgvector schema | Schema | High — don't redesign what works |
| Fork Neo4j node/relationship schema | Schema | High — same graph patterns |
| Map 5 attack primitives to ingestion channels | Architecture | High — core detection surface |
| Policy Engine = AI Coach with security queries | Feature | High — core value prop |
| Dashboard visualizations (shared components) | UI | Medium — build once, theme twice |
| Privacy controls → Access controls mapping | Security | High — enterprise requirement |
| Portfolio narrative (shared architecture story) | Documentation | Medium — interview/pitch prep |
| Redaction pipeline (ClawGuard-specific) | Feature | High — not in Open Brain |
| Real-time alerting (ClawGuard-specific) | Feature | High — not in Open Brain |
| Multi-tenant architecture (ClawGuard-specific) | Architecture | Medium — Phase 2+ |

---

*Added to ClawGuard project: March 3, 2026*
*Source session: Open Brain MCP Architecture Design*
