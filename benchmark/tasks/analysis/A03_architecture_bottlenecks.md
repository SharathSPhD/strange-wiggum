# A03 — Architecture Bottleneck Audit

## Task

Audit the following architecture description for bottlenecks, single points of failure,
and scalability issues. Provide concrete, actionable recommendations.

### System Description

A food delivery platform with the following architecture:
- **Single PostgreSQL database** (1 primary, 1 replica) handling all reads and writes
  - Tables: users, restaurants, orders, menu_items, drivers, reviews (~50M rows combined)
  - All services query this DB directly via connection pool (max 200 connections)
- **Monolithic Python/Django app** deployed on 3 EC2 instances behind an ALB
  - Handles: user auth, order placement, real-time driver tracking, payment processing, notifications
  - Synchronous request handling (no async workers)
- **Real-time driver location**: drivers ping location every 5 seconds via REST API → written to PostgreSQL
  - 2,000 active drivers during peak → 24,000 writes/minute to location table
- **Payment processing**: synchronous call to Stripe in the order request handler (p99 = 800ms)
- **Notifications**: emails and SMS sent synchronously during order placement
- **No caching layer** — all data fetched from DB on every request
- **Peak load**: 50,000 concurrent users, 5,000 orders/minute

Identify at least **5 specific bottlenecks**, explain why each is a problem (with numbers),
and provide a concrete fix for each.

## Scoring Rubric (embedded)
- Correctness (40%): Are the identified bottlenecks real problems? Are the numbers right?
- Depth (30%): Are fixes specific and implementable (not just "add caching")?
- Clarity (20%): Can an engineer action this immediately?
- Structure (10%): Organized by bottleneck with problem/impact/fix format.
