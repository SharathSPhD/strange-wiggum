# A07 — Production Incident Post-Mortem

## Task

Write a complete post-mortem for the following production incident.

### Incident Summary

**Date:** 2024-03-15  
**Duration:** 4 hours 23 minutes (14:07 UTC – 18:30 UTC)  
**Impact:** 78% of checkout requests failed; ~$2.1M in lost GMV  
**Service:** E-commerce checkout service  

### Timeline of Events

- **13:45** — Routine deployment of checkout-service v2.4.1 (added new promo code logic)
- **14:07** — Spike in checkout error rate: 5% → 78% within 3 minutes
- **14:09** — PagerDuty alert fires; on-call engineer acknowledges
- **14:22** — Engineer suspects database; runs `EXPLAIN ANALYZE` on slow queries
- **14:35** — Database CPU at 99%; queries timing out after 30s
- **14:51** — Team attempts rollback but deployment pipeline is locked (another deploy in progress)
- **15:03** — Pipeline unlocked; rollback initiated
- **15:19** — Rollback completes; error rate drops to 12% (residual DB load)
- **15:45** — DB CPU normalizes; error rate returns to baseline 0.3%
- **Root cause identified (post-incident):** New promo code query ran a full table scan on the `orders` table (50M rows) for every checkout — missing index on `promo_code_id` column added in v2.4.1 migration

Your post-mortem must include:
1. **Executive summary** (3 sentences max)
2. **Root cause analysis** (5 Whys or fault tree)
3. **Timeline** (annotated with what engineers knew/thought at each step)
4. **Contributing factors** (process/tooling gaps that allowed this)
5. **Action items** (minimum 5, each with owner role, priority, and due date format)
6. **Metrics** (define the SLI/SLO that was violated and what it should be)

## Scoring Rubric (embedded)
- Correctness (40%): Is the root cause analysis technically accurate and complete?
- Depth (30%): Are action items specific and actionable? Is the 5-Whys rigorous?
- Clarity (20%): Blameless tone, clear timeline, accessible to non-engineers?
- Structure (10%): Standard post-mortem format with all 6 sections present.
