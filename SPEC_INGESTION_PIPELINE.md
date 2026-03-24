# Open Brain — SPEC_INGESTION_PIPELINE.md

> **Spec:** Ingestion Pipeline — Metadata Extraction, Embedding Generation, Dual-Write Orchestration
> **Version:** 1.0
> **Last Updated:** March 3, 2026
> **Depends On:** SPEC_POSTGRES_SCHEMA.md, SPEC_NEO4J_SCHEMA.md, SPEC_MCP_SERVER.md
> **Depended On By:** SPEC_GITHUB_SYNC.md, SPEC_LOCAL_DIRECTORY_WATCHER.md, SPEC_DATA_MIGRATION.md, SPEC_AI_COACH.md
> **Read First:** IDEAL_STATE.md, NORTHSTAR.md

---

## Purpose

The Ingestion Pipeline is the engine behind every write operation in Open Brain. When the MCP server receives a `capture_thought`, `update_thought`, or `bulk_import` call, it delegates to this pipeline. The pipeline transforms raw text into a fully indexed, relationship-aware knowledge graph entry.

No raw thought goes directly into the database. Every thought passes through this pipeline, which: validates input, checks privacy rules, extracts structured metadata via LLM, generates a vector embedding, writes to Postgres, creates Neo4j nodes and edges, detects auto-relationships to existing thoughts, extracts action items, and logs the audit trail.

This spec defines two deployment modes: **Edge Function** (Supabase-hosted, production) and **Inline** (same process as MCP server, local development). The logic is identical — only the transport differs.

---

## Platform Constraints

- **Edge Function Runtime:** Deno (Supabase Edge Functions)
- **Edge Function Limits (Free Tier):**
  - 500,000 invocations/month
  - 2MB request body limit
  - 150-second execution timeout (wall clock)
  - 256MB memory limit
  - No persistent state between invocations
- **External API Calls from Edge Functions:**
  - OpenAI API (embedding generation)
  - LLM API (metadata extraction — Claude Haiku or GPT-4o-mini)
  - Neo4j Bolt protocol (graph writes)
- **Supabase Service Key:** Edge Functions use `SUPABASE_SERVICE_KEY` to bypass RLS for internal writes. This key is NEVER exposed to MCP clients.

---

## Architecture

```
MCP Server (capture_thought / update_thought / bulk_import)
    │
    │  HTTP POST (with JWT auth header)
    ▼
Ingestion Pipeline (Edge Function or Inline)
    │
    ├── Step 1: Validate + Privacy Check
    │     ├── Check tracking_state
    │     └── Check exclusion_rules
    │
    ├── Step 2: Metadata Extraction (LLM)       ──── parallel ────┐
    │     └── topics, people, projects,                           │
    │         summary, action_items, thought_type                 │
    │                                                             │
    ├── Step 3: Embedding Generation (OpenAI)    ─────────────────┘
    │     └── text-embedding-3-small → 1536d vector
    │
    ├── Step 4: Postgres Write
    │     ├── INSERT thoughts
    │     └── INSERT thought_embeddings
    │
    ├── Step 5: Neo4j Write
    │     ├── CREATE Thought node
    │     ├── MERGE Topic/Person/Project nodes
    │     ├── CREATE entity edges (TAGGED_WITH, MENTIONS, BELONGS_TO, CAPTURED_BY)
    │     └── Auto-relationship detection → CREATE RELATES_TO edges
    │
    ├── Step 6: Action Item Extraction
    │     └── INSERT action_items (if any found)
    │
    └── Step 7: Audit Log
          └── INSERT audit_log entry
```

**Steps 2 and 3 run in parallel** — metadata extraction and embedding generation are independent API calls. This is the primary latency optimization. Combined wall clock time: ~2-3 seconds instead of ~4-5 seconds sequential.

---

## Pipeline Modes

### Mode 1: Edge Function (Production)

The MCP server calls the Edge Function via HTTP POST. The Edge Function has access to `SUPABASE_SERVICE_KEY` and handles all database writes.

```
MCP Server → HTTP POST https://[project-ref].supabase.co/functions/v1/ingest
  Headers:
    Authorization: Bearer [user-jwt]
    Content-Type: application/json
  Body:
    { "content": "...", "source": "claude", "thought_type": "insight", ... }
```

**When to use:** Production deployments, when you want separation of concerns and service-key isolation.

### Mode 2: Inline (Local Development)

The MCP server runs the pipeline logic directly in-process. The MCP server uses the anon key for Postgres (RLS-enforced) and the Neo4j driver directly.

**When to use:** Local development with stdio transport. Simpler to debug. Acceptable for single-user deployment.

**Implementation note:** Extract all pipeline logic into a shared module. The Edge Function imports it, and the MCP server can also import it for inline mode. The difference is only in authentication and transport.

---

## Step 1: Validate + Privacy Check

### 1.1 Input Validation

```typescript
interface IngestInput {
  content: string;           // Required. Min 10 chars, max 50,000 chars.
  source: SourceType;        // Required. Must match source_type enum.
  thought_type?: ThoughtType; // Optional. Defaults to 'insight'.
  energy_level?: number;     // Optional. 1-5.
  tags?: string[];           // Optional. User-supplied tags.
  source_url?: string;       // Optional. URL of original conversation.
  source_date?: string;      // Optional. ISO 8601 datetime for migrated data.
  user_id: string;           // Required. From JWT auth token.
}
```

**Validation rules:**
- `content` must be between 10 and 50,000 characters. Reject shorter (too vague for metadata extraction). Reject longer (chunk it first — see SPEC_DATA_MIGRATION.md).
- `source` must be a valid `source_type` enum value.
- `thought_type` must be a valid `thought_type` enum value if provided.
- `energy_level` must be integer 1-5 if provided.
- `tags` must be array of strings, max 20 tags, max 50 chars each. Normalize: lowercase, trim whitespace.
- `source_url` must be valid URL format if provided.
- `source_date` must be valid ISO 8601 if provided.

**Validation error response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Content must be between 10 and 50,000 characters.",
    "details": { "field": "content", "received_length": 5 }
  }
}
```

### 1.2 Tracking State Check

Query `tracking_state` table for the authenticated user:

```sql
SELECT mode FROM tracking_state WHERE user_id = $user_id;
```

- If `mode` is `paused` or `session_exclude`, reject immediately:
```json
{
  "error": {
    "code": "TRACKING_PAUSED",
    "message": "Tracking is currently paused. Set tracking mode to 'active' to capture thoughts."
  }
}
```

- If no row exists for the user, treat as `active` (first-time user) and INSERT a default row.

### 1.3 Exclusion Rules Check

Load all active exclusion rules for the user:

```sql
SELECT rule_type, pattern, description FROM exclusion_rules
WHERE user_id = $user_id AND is_active = TRUE;
```

Check content against each rule:

| Rule Type | Check Logic |
|-----------|-------------|
| `keyword` | Case-insensitive substring match: `content.toLowerCase().includes(pattern.toLowerCase())` |
| `topic` | Checked AFTER metadata extraction (Step 2) — if any extracted topic matches the pattern |
| `source` | Exact match: `input.source === pattern` |
| `regex` | `new RegExp(pattern, 'i').test(content)` — wrap in try/catch for invalid regex |

**For `keyword`, `source`, and `regex` rules:** Check BEFORE Step 2 (skip expensive LLM calls).
**For `topic` rules:** Check AFTER Step 2 metadata extraction (need extracted topics first).

If any rule matches:
```json
{
  "error": {
    "code": "EXCLUDED_CONTENT",
    "message": "Content matched exclusion rule: [rule description]",
    "details": { "rule_type": "keyword", "pattern": "salary" }
  }
}
```

**Caching:** Load exclusion rules once per pipeline invocation. For bulk_import, load once and apply to all items in the batch.

---

## Step 2: Metadata Extraction (LLM)

### LLM Choice

**Primary:** Claude Haiku (claude-3-5-haiku-latest) via Anthropic API
**Fallback:** GPT-4o-mini via OpenAI API

Both are cheap (~$0.25/M input tokens, ~$1.25/M output tokens for Haiku). At 500 words/thought average, each extraction costs ~$0.0003. Budget allows ~300-500 extractions/month.

**Fallback logic:** If primary LLM returns error or times out (>10 seconds), retry once. If still failing, try fallback LLM. If both fail, proceed with empty metadata (content still gets stored with embedding, just without extracted entities). Log the failure.

### Extraction Prompt Template

```
You are a metadata extraction engine for a personal knowledge graph. Given a thought, extract structured metadata.

Rules:
- topics: 1-5 topic strings, normalized to lowercase. These are subject areas, not keywords. Prefer established terms over novel phrases. Examples: "agent security", "graph databases", "interview prep", "open brain architecture".
- people: Names of people mentioned. Use the name as written. If uncertain whether something is a person's name, omit it.
- projects: Named projects, products, or initiatives. Examples: "ClawGuard", "Open Brain", "Kaizen Emerge". Do not invent project names — only extract explicitly mentioned ones.
- summary: One sentence (max 120 chars) capturing the core insight. Write in third person. Example: "Decided to use dual-database architecture for separate storage and graph concerns."
- action_items: Concrete commitments or tasks the person said they would do. Must be actionable. "I should think about X" is NOT an action item. "I need to deploy the staging server by Friday" IS.
- suggested_type: Best classification of this thought from the list below. Only suggest a type if the input didn't already specify one.

Thought types: insight, decision, action_item, question, reflection, architecture, lesson, person_note, meeting_note, research

Respond with ONLY valid JSON. No markdown fencing. No explanation.

{
  "topics": [],
  "people": [],
  "projects": [],
  "summary": "",
  "action_items": [],
  "suggested_type": ""
}

Thought:
"""
{content}
"""
```

### LLM Call Configuration

```typescript
// Anthropic API call
const response = await anthropic.messages.create({
  model: "claude-3-5-haiku-latest",
  max_tokens: 500,
  temperature: 0,  // Deterministic extraction
  messages: [{ role: "user", content: promptWithContent }]
});
```

**Temperature 0** — metadata extraction is deterministic, not creative.
**Max tokens 500** — metadata payloads are small. Prevents runaway responses.

### Response Parsing

```typescript
interface ExtractionResult {
  topics: string[];
  people: string[];
  projects: string[];
  summary: string;
  action_items: string[];
  suggested_type: string;
}
```

**Parsing rules:**
1. Strip any markdown code fencing (```json ... ```) if present despite instructions.
2. `JSON.parse()` the response. If parsing fails, log warning and use empty defaults.
3. Normalize `topics`: lowercase, trim whitespace, deduplicate.
4. Normalize `people`: trim whitespace, deduplicate. Preserve casing.
5. Normalize `projects`: trim whitespace, deduplicate. Preserve casing.
6. Truncate `summary` to 200 chars if longer.
7. Filter `action_items`: remove empty strings and items under 10 chars.
8. `suggested_type`: only apply if the MCP caller didn't provide a `thought_type`. Validate against enum.

### Post-Extraction Exclusion Check

After extraction, check `topic` exclusion rules:

```typescript
const topicRules = exclusionRules.filter(r => r.rule_type === 'topic');
for (const rule of topicRules) {
  if (extractedTopics.some(t => t.toLowerCase() === rule.pattern.toLowerCase())) {
    return { error: { code: 'EXCLUDED_CONTENT', message: `...` } };
  }
}
```

---

## Step 3: Embedding Generation (OpenAI)

**Runs in PARALLEL with Step 2.**

### API Call

```typescript
const embeddingResponse = await openai.embeddings.create({
  model: "text-embedding-3-small",
  input: content,  // Raw thought content, not the summary
  encoding_format: "float"
});

const embedding: number[] = embeddingResponse.data[0].embedding;
// Result: 1536-dimension float array
```

**Input:** The full `content` field, not the summary. The embedding should capture the full semantic meaning.

**Content length handling:**
- text-embedding-3-small supports up to 8,191 tokens (~6,000 words).
- If content exceeds 8,000 tokens (rare — we cap at 50,000 chars), truncate to first 8,000 tokens. Log a warning.

### Cost

~$0.02 per 1M tokens. At 500 words (~670 tokens) per thought:
- 1,000 thoughts = ~670,000 tokens = ~$0.013
- Monthly budget for embeddings: effectively unlimited within the $0.10-0.30 range.

### Error Handling

If OpenAI API fails:
1. Retry once after 2-second delay.
2. If still failing, this is a **blocking error** — cannot store a thought without its embedding.
3. Return error to MCP server:
```json
{
  "error": {
    "code": "EMBEDDING_ERROR",
    "message": "Failed to generate embedding. OpenAI API returned: [error message]. Try again in a moment."
  }
}
```

---

## Step 4: Postgres Write

Both Steps 2 and 3 must complete before this step. Await the parallel Promise.all().

### 4.1 Insert into `thoughts` table

```sql
INSERT INTO thoughts (
  content, source, thought_type, energy_level, tags,
  topics, people, projects, summary,
  source_url, source_date, user_id
) VALUES (
  $content, $source, $thought_type, $energy_level, $tags,
  $topics, $people, $projects, $summary,
  $source_url, $source_date, $user_id
)
RETURNING id, created_at;
```

**Field mapping:**
- `thought_type`: Use caller-provided value, or `suggested_type` from extraction, or default `'insight'`.
- `topics`, `people`, `projects`: From extraction result (normalized arrays).
- `summary`: From extraction result.
- `tags`: From caller input (user-supplied), NOT from extraction.
- `source_date`: Only populated for migrated/imported data. `created_at` is always NOW().

### 4.2 Insert into `thought_embeddings` table

```sql
INSERT INTO thought_embeddings (
  thought_id, embedding, model, user_id
) VALUES (
  $thought_id, $embedding, 'text-embedding-3-small', $user_id
);
```

**Transaction handling:** Steps 4.1 and 4.2 should be wrapped in a single Postgres transaction. If the embedding insert fails, roll back the thought insert.

```typescript
const { data: thought, error } = await supabase.rpc('ingest_thought', {
  p_content: content,
  p_source: source,
  // ... all fields
  p_embedding: embedding
});
```

**Alternative: Postgres function** — Create an `ingest_thought()` function that handles both inserts atomically. This is the recommended approach for production.

### Postgres Function: `ingest_thought()`

```sql
CREATE OR REPLACE FUNCTION ingest_thought(
  p_content TEXT,
  p_source source_type,
  p_thought_type thought_type,
  p_energy_level SMALLINT DEFAULT NULL,
  p_tags TEXT[] DEFAULT '{}',
  p_topics TEXT[] DEFAULT '{}',
  p_people TEXT[] DEFAULT '{}',
  p_projects TEXT[] DEFAULT '{}',
  p_summary TEXT DEFAULT NULL,
  p_source_url TEXT DEFAULT NULL,
  p_source_date TIMESTAMPTZ DEFAULT NULL,
  p_embedding vector(1536),
  p_user_id UUID
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_thought_id UUID;
BEGIN
  -- Insert thought
  INSERT INTO thoughts (
    content, source, thought_type, energy_level, tags,
    topics, people, projects, summary,
    source_url, source_date, user_id
  ) VALUES (
    p_content, p_source, p_thought_type, p_energy_level, p_tags,
    p_topics, p_people, p_projects, p_summary,
    p_source_url, p_source_date, p_user_id
  ) RETURNING id INTO v_thought_id;

  -- Insert embedding
  INSERT INTO thought_embeddings (thought_id, embedding, model, user_id)
  VALUES (v_thought_id, p_embedding, 'text-embedding-3-small', p_user_id);

  -- Audit log
  INSERT INTO audit_log (event_type, entity_id, entity_type, details, source, user_id)
  VALUES (
    'thought_created', v_thought_id, 'thought',
    jsonb_build_object(
      'topics', p_topics,
      'people', p_people,
      'projects', p_projects,
      'source', p_source::TEXT,
      'thought_type', p_thought_type::TEXT
    ),
    p_source, p_user_id
  );

  RETURN v_thought_id;
END;
$$;
```

---

## Step 5: Neo4j Write

After Postgres write succeeds (thought ID is now known), write to Neo4j.

### 5.1 Create Thought Node

```cypher
CREATE (t:Thought {
  id: $thought_id,
  summary: $summary,
  thought_type: $thought_type,
  source: $source,
  created_at: datetime($created_at),
  energy_level: $energy_level
})
RETURN t.id
```

### 5.2 Create Entity Edges

**TAGGED_WITH → Topics** (MERGE to avoid duplicates):

```cypher
UNWIND $topics AS topic_name
MERGE (topic:Topic {name: topic_name})
  ON CREATE SET topic.first_seen = datetime(), topic.last_seen = datetime(), topic.thought_count = 1
  ON MATCH SET topic.last_seen = datetime(), topic.thought_count = topic.thought_count + 1
WITH topic
MATCH (t:Thought {id: $thought_id})
CREATE (t)-[:TAGGED_WITH {auto: true}]->(topic)
```

**MENTIONS → People** (MERGE):

```cypher
UNWIND $people AS person_name
MERGE (p:Person {name: person_name})
  ON CREATE SET p.first_mentioned = datetime(), p.last_mentioned = datetime(), p.mention_count = 1
  ON MATCH SET p.last_mentioned = datetime(), p.mention_count = p.mention_count + 1
WITH p
MATCH (t:Thought {id: $thought_id})
CREATE (t)-[:MENTIONS {context: ''}]->(p)
```

**BELONGS_TO → Projects** (MERGE):

```cypher
UNWIND $projects AS project_name
MERGE (p:Project {name: project_name})
  ON CREATE SET p.status = 'active', p.created_at = datetime()
WITH p
MATCH (t:Thought {id: $thought_id})
CREATE (t)-[:BELONGS_TO]->(p)
```

**CAPTURED_BY → Source** (MATCH existing seeded node):

```cypher
MATCH (t:Thought {id: $thought_id})
MATCH (s:Source {name: $source})
CREATE (t)-[:CAPTURED_BY]->(s)
SET s.thought_count = s.thought_count + 1
```

**Optimization:** Combine these into a single Cypher transaction to minimize round trips. Neo4j driver supports transaction functions:

```typescript
await neo4jSession.executeWrite(async (tx) => {
  await tx.run(createThoughtQuery, params);
  await tx.run(createTopicEdgesQuery, params);
  await tx.run(createPeopleEdgesQuery, params);
  await tx.run(createProjectEdgesQuery, params);
  await tx.run(createSourceEdgeQuery, params);
});
```

### 5.3 Auto-Relationship Detection

After the thought is in Postgres with its embedding, find semantically similar existing thoughts:

```sql
-- Find top-3 most similar existing thoughts (excluding the one just created)
SELECT t.id, t.summary, 1 - (te.embedding <=> $new_embedding) AS similarity
FROM thoughts t
JOIN thought_embeddings te ON t.id = te.thought_id
WHERE t.user_id = $user_id
  AND t.is_deleted = FALSE
  AND t.id != $new_thought_id
  AND 1 - (te.embedding <=> $new_embedding) > 0.85
ORDER BY te.embedding <=> $new_embedding ASC
LIMIT 3;
```

For each result above the 0.85 threshold, create a RELATES_TO edge in Neo4j:

```cypher
MATCH (a:Thought {id: $new_thought_id})
MATCH (b:Thought {id: $related_id})
CREATE (a)-[:RELATES_TO {
  auto: true,
  similarity: $similarity,
  created_at: datetime()
}]->(b)
```

**Threshold rationale:** 0.85 cosine similarity is high enough to avoid noisy connections but permissive enough to catch meaningful thematic overlap. Tune after observing real data — if generating too many spurious connections, raise to 0.88. If missing obvious connections, lower to 0.80.

### 5.4 Neo4j Failure Handling

If Neo4j write fails AFTER Postgres succeeds:
1. **Do NOT roll back Postgres.** The thought is stored and searchable — the graph linkage is secondary.
2. Log the failure to `audit_log` with event details:
```sql
INSERT INTO audit_log (event_type, entity_id, entity_type, details, source, user_id)
VALUES ('thought_created', $thought_id, 'thought',
  '{"neo4j_sync_failed": true, "error": "[error message]"}'::jsonb,
  $source, $user_id);
```
3. The `brain_status` tool detects this mismatch by comparing Postgres thought count to Neo4j Thought node count.
4. **Recovery strategy:** A separate repair function (run manually or on schedule) queries for thoughts in Postgres not in Neo4j and re-runs Step 5 for them:
```sql
-- Find unsynced thoughts
SELECT t.id FROM thoughts t
WHERE t.is_deleted = FALSE
  AND NOT EXISTS (
    -- Check if thought exists in Neo4j by querying Neo4j
    -- Implementation: query Neo4j for each thought ID, or batch query
  );
```

---

## Step 6: Action Item Extraction

If the LLM extracted any `action_items` in Step 2, insert them into Postgres:

```sql
INSERT INTO action_items (thought_id, content, status, project, user_id)
VALUES ($thought_id, $action_item_content, 'open', $project, $user_id)
RETURNING id;
```

**Field mapping:**
- `thought_id`: The newly created thought's UUID.
- `content`: The action item text from extraction.
- `project`: If the thought has exactly one extracted project, use it. Otherwise NULL.
- `status`: Always `'open'` for newly extracted action items.

**Audit log:** Each action item gets its own audit entry:
```sql
INSERT INTO audit_log (event_type, entity_id, entity_type, details, source, user_id)
VALUES ('action_item_created', $action_item_id, 'action_item',
  jsonb_build_object('content', $content, 'from_thought', $thought_id),
  $source, $user_id);
```

---

## Step 7: Audit Log

If not already handled by the `ingest_thought()` Postgres function, write a final audit entry:

```sql
INSERT INTO audit_log (event_type, entity_id, entity_type, details, source, user_id)
VALUES (
  'thought_created',
  $thought_id,
  'thought',
  jsonb_build_object(
    'topics', $topics,
    'people', $people,
    'projects', $projects,
    'action_items_count', $action_items_count,
    'auto_relationships', $auto_relationship_ids,
    'neo4j_synced', $neo4j_success
  ),
  $source,
  $user_id
);
```

---

## Pipeline Response

After all steps complete, return the full result to the MCP server:

```typescript
interface IngestResult {
  id: string;                    // UUID of created thought
  content: string;
  source: string;
  thought_type: string;
  summary: string;               // LLM-extracted
  topics: string[];              // LLM-extracted
  people: string[];              // LLM-extracted
  projects: string[];            // LLM-extracted
  tags: string[];                // User-supplied
  energy_level: number | null;
  auto_relationships: Array<{
    related_id: string;
    type: "RELATES_TO";
    similarity: number;
  }>;
  action_items_extracted: Array<{
    id: string;
    content: string;
  }>;
  created_at: string;            // ISO 8601
  processing_time_ms: number;    // For monitoring
}
```

---

## Update Pipeline (for `update_thought`)

When `update_thought` is called with changed `content`:

1. Re-run Step 2 (metadata extraction) with new content.
2. Re-run Step 3 (embedding generation) with new content.
3. UPDATE Postgres `thoughts` row with new metadata.
4. UPDATE `thought_embeddings` row with new embedding:
   ```sql
   UPDATE thought_embeddings
   SET embedding = $new_embedding, model = 'text-embedding-3-small', created_at = NOW()
   WHERE thought_id = $thought_id;
   ```
5. UPDATE Neo4j Thought node properties:
   ```cypher
   MATCH (t:Thought {id: $thought_id})
   SET t.summary = $new_summary, t.thought_type = $new_type
   ```
6. Remove old TAGGED_WITH, MENTIONS, BELONGS_TO edges and create new ones based on re-extracted metadata:
   ```cypher
   // Remove old entity edges
   MATCH (t:Thought {id: $thought_id})-[r:TAGGED_WITH|MENTIONS|BELONGS_TO]->()
   DELETE r
   ```
   Then re-run Step 5.2 for new entities.
7. Remove old auto-detected RELATES_TO edges and re-run auto-relationship detection:
   ```cypher
   MATCH (t:Thought {id: $thought_id})-[r:RELATES_TO {auto: true}]-()
   DELETE r
   ```
   Then re-run Step 5.3.
8. Audit log: `thought_updated` with before/after diff.

**When only `tags` or `thought_type` change (content unchanged):**
- Skip Steps 2 and 3 (no re-extraction or re-embedding needed).
- Update Postgres `thoughts` row.
- Update Neo4j node properties if `thought_type` changed.
- Audit log.

---

## Bulk Import Pipeline (for `bulk_import`)

The `bulk_import` MCP tool processes up to 100 thoughts per call. The pipeline handles batching and cross-batch relationship detection.

### Batch Processing Flow

```
1. Audit log: bulk_import_started
2. Load exclusion rules (once for entire batch)
3. For each thought (rate limited to 10/sec):
   a. Validate input
   b. Check exclusion rules (keyword, source, regex)
   c. Call LLM for metadata extraction  ──── parallel ────┐
   d. Generate embedding               ─────────────────┘
   e. Check topic exclusion rules (post-extraction)
   f. Postgres insert (thoughts + embeddings)
   g. Neo4j node + entity edge creation
   h. Track for cross-batch relationship detection
4. Cross-batch relationship detection:
   a. For each imported thought, find top-3 similar thoughts
      (from BOTH existing thoughts AND other thoughts in this batch)
   b. Create RELATES_TO edges for pairs above 0.85 threshold
   c. Deduplicate: don't create A→B and B→A
5. Audit log: bulk_import_completed with stats
6. Return summary
```

### Rate Limiting

**Target: 10 thoughts/second** to stay within free tier Edge Function limits.

Implementation: Use a semaphore or token bucket. Process thoughts in batches of 10 with 1-second intervals.

```typescript
const BATCH_SIZE = 10;
const BATCH_DELAY_MS = 1000;

for (let i = 0; i < thoughts.length; i += BATCH_SIZE) {
  const batch = thoughts.slice(i, i + BATCH_SIZE);
  await Promise.all(batch.map(t => processSingleThought(t)));
  if (i + BATCH_SIZE < thoughts.length) {
    await sleep(BATCH_DELAY_MS);
  }
}
```

### LLM Batching Optimization

For bulk import, metadata extraction can be batched to reduce API round trips:

**Option A (Recommended):** Send individual LLM calls in parallel (up to 10 concurrent). Simpler, more reliable.

**Option B:** Batch multiple thoughts into a single LLM call with indexed output. Riskier (one parsing failure loses entire batch), but fewer API calls.

Recommendation: Start with Option A. Switch to Option B only if API rate limits become an issue.

### Deduplication

Before inserting, check for duplicate content:

```sql
-- Check if a thought with very similar content already exists
SELECT id, content FROM thoughts
WHERE user_id = $user_id
  AND is_deleted = FALSE
  AND content = $content;  -- Exact match
```

For fuzzy deduplication (same idea, different wording), check embedding similarity:
```sql
SELECT id FROM thought_embeddings
WHERE user_id = $user_id
  AND 1 - (embedding <=> $new_embedding) > 0.95;  -- Very high similarity = likely duplicate
```

Threshold 0.95 for deduplication is deliberately higher than 0.85 for auto-relationships. We want to avoid storing near-identical content but still link related-but-different ideas.

### Cross-Batch Relationship Detection

After all thoughts in the batch are stored:

```sql
-- For each newly imported thought, find top-3 most similar thoughts
-- (including others in this batch)
SELECT a.id AS from_id, b.id AS to_id,
       1 - (ae.embedding <=> be.embedding) AS similarity
FROM thought_embeddings ae
JOIN thought_embeddings be ON ae.thought_id != be.thought_id
JOIN thoughts a ON ae.thought_id = a.id
JOIN thoughts b ON be.thought_id = b.id
WHERE ae.thought_id = ANY($new_thought_ids)
  AND a.user_id = $user_id
  AND b.user_id = $user_id
  AND a.is_deleted = FALSE
  AND b.is_deleted = FALSE
  AND 1 - (ae.embedding <=> be.embedding) > 0.85
ORDER BY similarity DESC;
```

Deduplicate pairs (if A→B found, skip B→A) before creating Neo4j edges.

---

## Edge Function Deployment

### Function Structure

```
supabase/functions/ingest/
├── index.ts          # Entry point — HTTP handler
├── pipeline.ts       # Core pipeline logic (shared with inline mode)
├── extraction.ts     # LLM metadata extraction
├── embedding.ts      # OpenAI embedding generation
├── neo4j-writer.ts   # Neo4j node/edge creation
└── validation.ts     # Input validation + exclusion rule checking
```

### Entry Point (index.ts)

```typescript
// Pseudocode for Edge Function entry point
import { serve } from "https://deno.land/std/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js";
import { runPipeline } from "./pipeline.ts";

serve(async (req: Request) => {
  // Verify JWT from Authorization header
  const authHeader = req.headers.get("Authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return new Response(JSON.stringify({ error: { code: "AUTH_ERROR", message: "Missing auth token" } }), { status: 401 });
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_KEY")!  // Service key — Edge Function only
  );

  // Verify token and get user
  const { data: { user }, error: authError } = await supabase.auth.getUser(authHeader.split(" ")[1]);
  if (authError || !user) {
    return new Response(JSON.stringify({ error: { code: "AUTH_ERROR", message: "Invalid auth token" } }), { status: 401 });
  }

  const input = await req.json();
  input.user_id = user.id;

  const result = await runPipeline(input, supabase);
  return new Response(JSON.stringify(result), {
    status: result.error ? 400 : 200,
    headers: { "Content-Type": "application/json" }
  });
});
```

### Environment Variables (Edge Function Secrets)

Set via Supabase CLI or dashboard:

```bash
supabase secrets set OPENAI_API_KEY=[key]
supabase secrets set ANTHROPIC_API_KEY=[key]
supabase secrets set NEO4J_URI=[bolt+s://...]
supabase secrets set NEO4J_USER=neo4j
supabase secrets set NEO4J_PASSWORD=[password]
```

`SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are automatically available in Edge Functions.

---

## Performance Targets

| Metric | Target | Bottleneck |
|--------|--------|-----------|
| Single thought ingestion (wall clock) | < 5 seconds | LLM extraction + embedding in parallel |
| LLM metadata extraction | < 3 seconds | Haiku/4o-mini response time |
| Embedding generation | < 1 second | OpenAI API response time |
| Postgres write (thought + embedding) | < 200ms | Local to Supabase |
| Neo4j write (node + edges) | < 500ms | Network to AuraDB |
| Auto-relationship detection | < 1 second | pgvector HNSW query |
| Bulk import (100 thoughts) | < 60 seconds | Rate limited to 10/sec |

**Total budget per single capture: < 5 seconds** (IDEAL_STATE.md target).

---

## Error Handling Summary

| Step | Failure Mode | Recovery |
|------|-------------|----------|
| Step 1: Validation | Invalid input | Return VALIDATION_ERROR. No write. |
| Step 1: Tracking | Paused mode | Return TRACKING_PAUSED. No write. |
| Step 1: Exclusion | Rule match | Return EXCLUDED_CONTENT. No write. |
| Step 2: LLM | API timeout/error | Retry once → fallback LLM → proceed with empty metadata |
| Step 3: Embedding | API timeout/error | Retry once → BLOCKING ERROR. Cannot store without embedding. |
| Step 4: Postgres | Insert failure | Return DATABASE_ERROR. No partial write. |
| Step 5: Neo4j | Write failure | Log warning. Thought exists in Postgres but not in graph. brain_status detects mismatch. |
| Step 5.3: Auto-rel | Query timeout | Skip auto-relationships. Not blocking. |
| Step 6: Action items | Insert failure | Log warning. Thought stored, action items lost. Non-blocking. |

**Principle:** Postgres write is the critical path. Neo4j, action items, and auto-relationships are secondary. A thought stored in Postgres without Neo4j linkage is degraded but functional. A thought not stored at all is a pipeline failure.

---

## Verification Steps

After implementation, verify the pipeline with these tests:

1. **Happy path:** Call `capture_thought` with rich content → verify thought appears in Postgres with extracted metadata → verify Neo4j node + entity edges exist → verify auto-relationships created if similar thoughts exist → verify audit log entry.

2. **Tracking paused:** Set tracking mode to `paused` → call `capture_thought` → verify TRACKING_PAUSED error → verify no database writes.

3. **Exclusion rule match:** Create a keyword exclusion rule → call `capture_thought` with matching content → verify EXCLUDED_CONTENT error.

4. **Neo4j failure resilience:** Temporarily disconnect Neo4j → call `capture_thought` → verify thought stored in Postgres → verify brain_status reports sync mismatch.

5. **Bulk import:** Call `bulk_import` with 20 diverse thoughts → verify all stored → verify cross-batch relationships created → verify deduplication works on second import of same content.

6. **Update with content change:** Call `update_thought` with new content → verify re-extracted metadata → verify new embedding → verify old RELATES_TO edges removed and new ones created.

7. **Performance:** Measure single-thought ingestion wall clock time → must be < 5 seconds.

---

## ClawGuard Generalization Notes

When forking the ingestion pipeline for ClawGuard:

| Open Brain | ClawGuard | Change |
|-----------|-----------|--------|
| Metadata extraction prompt | Action classification prompt | Extract: capability_tags, targets, risk_indicators, tool_chain |
| `topics` extraction | `capability_tags` extraction | wallet, search, execute, file_write, api_call |
| `people` extraction | `targets` extraction | Files, URLs, APIs, users affected by the action |
| `action_items` extraction | `alert_triggers` extraction | Actions exceeding policy thresholds |
| Auto-relationship (RELATES_TO) | Sequential detection (FOLLOWS) | Chain actions by timestamp + agent session |
| Exclusion rules | Redaction rules | PII detection and stripping BEFORE storage |
| Energy level passthrough | Confidence score capture | Extract model's reported confidence |

**New ClawGuard pipeline step:** Between Steps 1 and 2, add a **Redaction Step** that scans content for PII patterns (email addresses, phone numbers, API keys, etc.) and replaces them with `[REDACTED]` tokens before storage. This step does NOT exist in Open Brain (personal data is the user's own).

---

*This spec is complete and ready for implementation. Next: SPEC_GITHUB_SYNC.md*
