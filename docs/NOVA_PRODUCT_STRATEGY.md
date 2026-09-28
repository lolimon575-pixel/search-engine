# NOVA Product Strategy

## Product promise

**NOVA is trust-first web search.** The core job is not to become another generic list of links or another AI chat wrapper. NOVA should help a person answer three questions quickly:

1. Is this result relevant?
2. Is this really the organization/site I think it is?
3. What evidence does NOVA have for that status?

NOVA Rank and NOVA Profiles are deliberately separate systems.

## Ranking firewall

Organic ranking must never consume any of these fields:

- profile tier
- billing/payment state
- company subscription state
- profile design/accent
- paid links or CTA configuration

A payment can unlock richer presentation and profile management. It cannot buy a higher organic result.

## Trust ladder

### Curated registry

NOVA has manually curated a domain-to-organization relationship. This is useful evidence, but it is not proof that the current user claiming the profile controls the domain.

### Domain-control verified

The organization publishes a one-time NOVA token at:

`https://example.com/.well-known/nova-verification.txt`

NOVA verifies the file directly over HTTPS. This proves technical control of the domain at that moment.

### Future identity verified

For a commercial Premium profile, domain control should be followed by an independent business/identity check. Billing is one signal, not proof by itself.

### Future Premium profile

Premium changes the company card, analytics and profile tools only. It never changes NOVA Rank.

## Competitive lessons (September 2026)

- Google/Bing: users expect instant answers, rich cards, suggestions, media and filters.
- Brave: provenance, privacy and user-visible AI sources are differentiators.
- DuckDuckGo: shortcuts such as !bang dramatically reduce navigation friction.
- Kagi: per-domain controls and search lenses give the user agency over ranking.
- NOVA: combine those usability expectations with a stronger identity/trust layer.

## Stage 1 — Trust product (implemented in 1.8)

- Rich major-company registry
- Curated vs domain-control verified trust states
- Self-service domain-control challenge
- Premium-ready profile metadata
- Company knowledge cards
- Ranking firewall
- Automated tests

## Stage 2 — Search utility (mostly implemented in 1.8)

- Web / Verified / Exact modes
- Freshness filters
- Live query suggestions
- !bang navigation
- Local domain boost/block controls
- Reversible personalization stored in the browser
- Transparent ranking signals

Next additions:
- News/images/video verticals
- Better query intent classification
- Related searches and topic refinement
- Result-quality feedback loop
- Independent second search source for resilience

## Stage 3 — Commercial self-service

Requires authentication and a payment/identity provider.

Planned flow:

1. Company creates account.
2. Company selects an existing NOVA Profile.
3. Domain-control challenge succeeds.
4. Business/identity verification succeeds.
5. Billing succeeds.
6. Premium editor unlocks.
7. Company can manage logo, description, official links, support links and CTA.
8. NOVA labels the card as a paid enhanced profile without altering organic rank.
9. Company gets profile analytics, not user-level search histories.

## Monetizable Premium features

- Custom verified company card
- Managed official links and support destinations
- Brand assets and visual theme
- Product/service shortcuts
- Status/incidents/support links
- Profile analytics
- Change history and verification audit trail
- Multiple verified regional domains

Never monetize:
- organic rank position
- verification result itself
- removal of legitimate negative technical signals
- suppression of competing organic results
