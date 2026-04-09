# A02 — Technical Design Doc: URL Shortener

## Task

Write a technical design document for a production URL shortener service (think bit.ly scale).

Requirements for the document:
1. **Requirements** — functional + non-functional (scale: 100M URLs, 10B redirects/month)
2. **High-level architecture** — components, data flow diagram (ASCII), key tech choices
3. **Database schema** — table(s), indexes, justification for SQL vs NoSQL choice
4. **Encoding scheme** — how to generate short codes (collision handling, length)
5. **Scalability** — how does the system handle 10x traffic spike? What are the bottlenecks?
6. **Caching strategy** — what to cache, where, TTL reasoning
7. **Failure modes** — 3 failure scenarios and mitigations

The document should be concrete — specific numbers, specific technologies (not just "a cache").

## Scoring Rubric (embedded)
- Correctness (40%): Are technical claims correct? Are tradeoffs well-reasoned?
- Depth (30%): Are all 7 sections addressed with specifics (not hand-waving)?
- Clarity (20%): Is it readable by a senior engineer unfamiliar with this system?
- Structure (10%): Proper headers, code/schema blocks, ASCII diagram.
