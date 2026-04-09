# A06 — Multi-Tenant SaaS Database Schema

## Task

Design a PostgreSQL database schema for a multi-tenant project management SaaS
(think Linear or Jira, but simpler). 

**Domain model:**
- Organizations (tenants) each have multiple Projects
- Projects have Issues; Issues can have parent Issues (subtasks)
- Issues have Labels, Assignees (Users), Comments, and Status history
- Users belong to Organizations; can have different roles per Organization
- Organizations are on subscription plans (free/pro/enterprise) with feature flags

**Requirements:**
1. **Full schema** — all tables with columns, types, constraints, foreign keys
2. **Indexing strategy** — which indexes, and why (explain query patterns they serve)
3. **Multi-tenancy isolation** — row-level security or schema-per-tenant? Justify your choice.
4. **Soft deletes** — handle deleted issues/projects without breaking history
5. **Audit log** — design for capturing who changed what and when
6. **Scale consideration** — how would this schema hold up at 10M issues per tenant?

## Scoring Rubric (embedded)
- Correctness (40%): Is the schema valid PostgreSQL? Are constraints correct? Is isolation sound?
- Depth (30%): Are all 6 requirements addressed with real SQL (not pseudocode)?
- Clarity (20%): Can a backend engineer implement this directly from your design?
- Structure (10%): Organized sections, properly formatted SQL blocks.
