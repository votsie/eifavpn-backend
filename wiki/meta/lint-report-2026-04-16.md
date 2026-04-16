---
type: meta
title: "Lint Report 2026-04-16"
created: 2026-04-16
updated: 2026-04-16
tags: [meta, lint]
status: developing
---

# Lint Report: 2026-04-16

## Summary
- Pages scanned: 33
- Issues found: 24
- Auto-fixed: 20
- Needs review: 4

## Orphan Pages
- None found. All pages have inbound links from index.md or other pages.

## Dead Links
- None found. All wikilinks resolve to existing files.

## Missing Pages
- "Security Review" (`concepts/security-review.md`): security hardening was performed (P0-P2 fixes), no wiki page existed. **Created.**

## Frontmatter Gaps
All 33 pages were missing `status`, `created`, and `tags`. **Auto-fixed on all pages.**

| Page | Missing Before Fix |
|------|--------------------|
| All 33 pages | status, created, tags |
| 17 pages (index files, hot, log, overview, domains) | type |

## Cross-Reference Gaps
Major unlinked mentions fixed:
- [[hot]]: added wikilinks to [[Remnawave]], [[CryptoPay]], [[Wata H2H]], [[Telegram Stars]], [[User Model]], [[Subscription Model]]
- [[overview]]: added wikilinks for [[Telegram Stars]], [[CryptoPay]], [[Wata H2H]], [[JWT Authentication]], [[Telegram Bot Integration]]
- [[concepts/payment-processing]]: added wikilinks to [[Remnawave Integration]], [[Subscriptions App]]
- [[concepts/authentication-flows]]: added wikilinks to [[User Model]], [[EmailVerification Model]], [[Telegram Bot Integration]]
- [[concepts/subscription-lifecycle]]: added wikilinks to [[User Model]], [[Telegram Bot Integration]]
- [[concepts/referral-system]]: added wikilinks to [[Telegram Bot Integration]], [[Subscription Model]]
- [[concepts/proxy-system]]: added wikilinks to [[JWT Authentication]], [[User Model]]
- [[entities/wata-h2h]]: updated security note — verification now implemented
- New page [[Security Review]] linked from [[overview]], [[Subscription Lifecycle]], [[Payment Processing]]

## Stale Claims
- [[entities/wata-h2h]]: claim "Security gap (no signature verification)" is now stale — Wata webhook verification was implemented. **Fixed.**
- [[concepts/payment-processing]]: claim "Security gap: Wata webhook lacks signature verification" is now stale. **Fixed.**

## Writing Style
- No major violations found. Pages use declarative present tense consistently.
- Sources are cited via file paths where applicable.

## Needs Review (not auto-fixed)
1. [[PromoCode Model]] — model is referenced but not yet defined in code (try/except ImportError). Keep page or mark as `status: planned`?
2. [[hot]] — hot cache has many plain-text mentions that could be wikilinked, but hot cache is meant for fast loading, not navigation. Keep minimal?
3. Dashboard dataview queries — requires Obsidian Dataview plugin. Created stub.
4. Canvas map — requires Obsidian Canvas. Created stub.
