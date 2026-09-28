# NOVA Product Direction

## What NOVA is

NOVA is an identity-first web search product.

A normal search result answers: **what page matched my query?**

NOVA should additionally answer:

1. **Who is behind this domain?**
2. **How was that identity established?**
3. **What did NOVA technically verify?**
4. **Why is this result ranked here?**
5. **Can I choose a different search lens without being profiled?**

The product is useful when it reduces the work needed to decide whether a result is relevant and whether the source is really who it claims to be.

## Trust model

Trust must never be represented as one binary badge.

NOVA separates:

- `OWNER_VERIFIED` — control of the domain was proven with a domain challenge.
- `EXTERNAL_CONFIRMED` — an independent external source maps the organization to the domain.
- `CURATED` — NOVA's editorial registry maps the organization to the domain.
- `SIGNALS` — the website contains self-declared organization signals.
- `UNKNOWN` — no meaningful identity evidence is available.

Technical health (DNS / HTTPS / HTTP / redirects) is separate from identity.

## Ranking constitution

NOVA Rank may use relevance, source diversity, query/domain/title matching, technical quality and identity evidence when it is relevant to the user's intent.

NOVA Rank must **never** use:

- payment status;
- subscription plan;
- Profile Plus status;
- sales relationship;
- amount paid.

A paid company must be able to look better, not rank better.

## Company product

### Owner Verified — trust layer

Domain owners can prove control by publishing a one-time NOVA challenge at:

`/.well-known/nova-site-verification.txt`

This status is about domain control and is not sold.

### Profile Plus — monetization layer

A future paid company profile may unlock:

- richer description and structured company data;
- selected official links;
- support / careers / investor / status links;
- richer visual identity;
- product/service shortcuts;
- verified contact and help destinations;
- analytics about how the profile is viewed;
- change review tools.

Profile Plus never changes organic ranking.

## Search conveniences

NOVA should provide familiar search affordances while keeping the interface calm:

- query correction;
- suggestions and history;
- Web / Official / Discussions lenses;
- quick bangs for external engines/sites;
- source-grounded quick briefs;
- dark mode;
- local browser-only domain personalization;
- transparent rank signals;
- visible identity and technical verification.

## Next milestones

1. **NOVA 1.8 — Identity Search**
   Trust Passports, Owner Verified flow, expanded entity registry, lenses, bangs, local domain personalization and NOVA Brief.

2. **NOVA 1.9 — Search Quality**
   Better provider redundancy, richer snippets, related queries, freshness handling, language/region controls, caching and latency work.

3. **NOVA 2.0 — Company Platform**
   Authentication, Stripe billing, Profile Plus editor, moderation/review workflow, owner analytics, profile change history and abuse controls.
