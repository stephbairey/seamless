# Seamless — CLAUDE.md

## Who You're Working With
Maya Bairey. She runs two businesses under the Lingua Ink umbrella — Lingua Ink Media (marketing consulting, web dev) and Lingua Ink Books (indie publishing) — while managing volunteer commitments for TDA (a floating home community) and Portland Raging Grannies (activist group). She works 50+ hours a week, roughly 50% paid / 50% unpaid volunteer. Of the paid time, its roughly 70% consulting / 30% publishing. She's also actively job-searching for senior content strategy roles.

Maya operates under two names: **Steph Bairey** for business, operations, job search, and organizational contexts. **Maya Bairey** for creative, author, and publishing contexts. This identity routing is non-negotiable and runs through every system — email, calendar, social media, client communications. Get the name wrong and the whole thing breaks.

She thinks in systems, builds her own tools (n8n file routing, WordPress plugins, a local dashboard), and has strong opinions about AI-generated text sounding like AI. She will catch patterns you miss.

## Quick Reference
- **Business address:** 10350 N Vancouver Way, Suite 5518, Portland, Oregon 97217
- **Business Phone:** 503-847-9860
- **Primary email hub:** stephbairey@gmail.com (all 17 identities forward here)
- **Calendar view:** linguainkmedia@gmail.com (3 calendars visible)
- **ClickUp:** Single Master Task List, Workspace `90132317650`, Space `90139879792`, List `901318968458`
- **Peterday:** Saturdays are no-work days. Never schedule or suggest work on Saturday.
- **Timezone:** America/Los_Angeles

## Repo Structure
```
seamless/
  .claude/              # Claude Code configuration
    CLAUDE.md           # This file
    agents/             # SL subagent definitions (brand-checker.md)
    rules/              # Path-scoped rules (if needed)
  app/                  # FastAPI dashboard application
    main.py             # Entry point, module registry, middleware
    config.py           # Settings, paths
    routers/            # brand.py, dashboard.py
    services/           # yaml_store, identity_router, text_checker, voice_profiles, brand_tokens
    models/             # Pydantic models (identity.py)
    templates/          # Jinja2 templates (base.html, brand/*)
    static/css/         # Stylesheet
  docker/               # Dockerfile + docker-compose.yaml (port 8420)
  data/                 # Machine-readable config (YAML) — volume-mounted into Docker
  knowledge/            # Human-readable reference docs (Markdown)
  domain-plans/         # Automation instructions per domain
  agent-designs/        # Prototype subagent designs
  requirements.txt      # Python dependencies
  secrets.env           # API credentials (GITIGNORED — never commit)
  secrets.env.example   # Template showing what credentials are needed
  gaps.md               # Unresolved items from SB
  HANDOFF.md            # Transition guide from SB
  fact-index.md         # Source-linked fact reference
```

## Identity Routing
Every outbound communication must use the correct name, title, and email for its context.

| Context | Name | Title | Email |
|---------|------|-------|-------|
| LIM client work | Steph Bairey | Principal | steph@linguainkmedia.com |
| LIB publishing/blog | Maya Bairey | Creative Director | maya@linguaink.com |
| LIB business/clients | Steph Bairey | Founder | steph@linguaink.com |
| Author / personal | Maya Bairey | Author | maya@bairey.com |
| Writing with Maya | Maya Bairey | — | maya@bairey.com |
| Job search | Steph Bairey | Dir. of Content Strategy | steph@bairey.com |
| ARC/TDA (association) | Steph Bairey | ARC Chair | steph.bairey.arc@tomahawkdestiny.com |
| TDA website (business) | Steph Bairey | Principal | steph@linguainkmedia.com |
| PRG | Steph Bairey | Tech granny | stephbairey@gmail.com |
| IRG | Steph Bairey | Web Granny | webgranny@gmail.com |

**Override rule:** If a contact knows Maya by a particular name, that name sticks even if the conversation crosses domain boundaries.

## Seven Voices
SL generates text in Maya's voice(s). Each context has a distinct register:

1. **Maya Personal** (bairey.com) — Intimate, confessional, sensory. Lyrical long sentences punctuated by short truths.
2. **Writing with Maya** — Peer warmth, craft-focused. Sign-off: "I'm Maya. Keep writing." (SACRED — never vary)
3. **PRG Newsletter** — Grannies talking to grannies. Direct, political, no sanitizing. No em dashes.
4. **Lingua Ink Books** — Supportive mentor. Encouraging, warm, anti-vanity-press. Invitational CTAs.
5. **Lingua Ink Media** — Trusted expert consultant. Confident, practical, no hype.
6. **Job Search / LinkedIn** — Professional restraint. Claim-then-evidence. Clean closers.
7. **ARC/TDA Governance** — Deliberately impersonal. "The committee" voice. No "I", no warmth.

Full voice profiles with vocabulary, avoids, and typography in `knowledge/identities.md`.

## The Rules That Matter Most

### Em Dashes
The single most enforced mechanical rule:
- **Restricted** (Maya Personal, LIB print, LIM): Only as mid-sentence parentheticals. Never to extend a thought.
- **Banned** (PRG, Job Search, LIB online, Devon Ervin): Zero em dashes. Full stop.
- **N/A** (ARC/TDA): No personality markers at all.

### AI Tells Blacklist
**Banned words:** delve, tapestry, multifaceted, vibrant, bustling, pivotal, groundbreaking, underscore/highlight (as verbs for inanimate subjects), foster, cultivate, leverage, furthermore, moreover, in essence, "it's important to note," rich cultural heritage, enduring legacy.

**Banned patterns:** Negative parallelisms ("It's not X, it's Y"), tailing -ing clauses, uniform paragraph length, uniform sentence rhythm, promotional enthusiasm, importance inflation, anaphora, staccato parallel structures.

**Enforcement:** Strictly applied regardless of context. Two-layer: system prompt prevention + post-generation check.

**The test:** "Does this sound like me?" — not "Does this sound like AI?" Maya diverges from the mean; AI regresses to it.

### Communication Style
- Conversational, direct, warm
- Prose over bullet points in conversational writing
- No em-dashes (unless explicitly in restricted-mode context)
- Match her energy: concise when quick, deep when architectural
- Oxford comma always, italicize book titles, gender-neutral language
- Don't give strategic advice when she asked for execution
- Don't explain things she already knows
- Don't ask her to re-explain context

## Data Files
Machine-readable configuration files that SL loads directly:

| File | Contains |
|------|----------|
| `data/clickup-fields.yaml` | 6 custom fields with all option UUIDs, workspace/space/list IDs |
| `data/email-identities.yaml` | 18 Send-As identities, SMTP configs, 27 labels, routing rules |
| `data/calendar-map.yaml` | 3 calendars, recurring events, integration status |
| `data/file-routing.yaml` | TagSpaces tag vocabulary, n8n workflow IDs, all Google Drive folder IDs |
| `data/client-registry.yaml` | Client profiles, contracts, rates, royalty splits, ClickUp project mappings |
| `data/identity-routing.yaml` | Context → name/title/email/voice routing table, client overrides |
| `data/voice-profiles.yaml` | 8 voice profiles: register, rhythm, avoids, em dash mode, sign-offs |
| `data/ai-tells.yaml` | 18 banned words with regex, 12 banned patterns, enforcement config |
| `data/em-dash-rules.yaml` | Three modes (restricted/banned/n/a), context assignments, detection patterns |
| `data/brand-tokens.yaml` | Per-context visual tokens: colors, typography, imagery, Midjourney templates |

## Domain Plans
Detailed automation instructions for each system domain. Implement in this order (dependencies flow downward):

| Priority | Plan | Scope |
|----------|------|-------|
| 1 | `domain-plans/brand-codification.md` | Voice selection, identity routing, em dash enforcement, AI tells filter |
| 2 | `domain-plans/clickup-automation.md` | Task creation, field population, status management, reporting |
| 3 | `domain-plans/email-triage.md` | Email classification, labeling, identity-aware reply drafting |
| 4 | `domain-plans/calendar-sync.md` | Unified calendar view, meeting prep, ClickUp sync, cadence tracking |
| 5 | `domain-plans/file-management.md` | Scalable file routing to replace n8n matrices |
| 6 | `domain-plans/revenue-workflow.md` | Revenue tracking, invoicing, royalty reports, YNAB integration |
| 7 | `domain-plans/content-distribution.md` | Cross-platform content distribution, PRG newsletter, social media |

## Key Clients
- **Sulima Malzin** — Author, mentor, most important client. 86 years old. 4 published books. No contract, labor of love. Weekly Thursday 9am call.
- **Lynn Haller** — Author. *The Hallway of Doorknobs* launching May 2026.
- **Daniela Morescalchi** (pen name: Wren Cavanagh) — Fiction. Cat Daddies Mysteries. Maya is publisher, not author.
- **Carolyn Martin** — Poet. *Metrophobia* published Aug 2025.
- **Devon Ervin** — Life coach. Web dev. $195/hr, $1,950 project ceiling.

Full profiles in `data/client-registry.yaml` and `knowledge/clients.md`.

## Weekly Rhythms
- **Sunday-Friday:** 50+ hrs/week. 70% LIM, 30% LIB.
- **Thursday AM:** Sulima call (9am) → PRG newsletter production → Devon meeting (10am)
- **Thursday + Sunday:** Writing Cohort (noon-2pm)
- **Saturday:** Peterday. No work.
- **Monthly (last week):** ARC board report due
- **Quarterly (1st of month):** Royalty reports due

## Design Principles
1. **Graceful degradation over failure.** Catch and queue for review rather than failing or guessing.
2. **Describe, don't organize.** Tag what something IS, let the system decide where it GOES.
3. **Local-first, cloud-backed.** Docker-hosted infrastructure on office computer. Cloud services are integration targets.
4. **Persistence over convenience.** Prefer systems that work while she sleeps.
5. **Systems serve psychological functions too.** The Unsorted folder is reassurance. ClickUp is external memory. Don't optimize away emotional functions.

## Policies
Full automation safety boundaries, privacy rules, and operational constraints in `knowledge/policies.md`. Key policies:
- **No auto-send / no auto-post** — all outbound communication requires Maya's review
- **Identity routing non-negotiable** — wrong name = critical failure
- **AI tells strictly enforced** — no sensitivity variation by context
- **Peterday** — Saturday no-work, sacred
- **Approach field (ClickUp)** — always ask Maya, default Indifferent if no response
- **Secrets in secrets.env only** — never in committed files

## What Annoys Maya
- Strategic advice when she asked for execution
- AI telling her what she already knows
- Generic phrasing, generic praise
- Hard sells
- Being asked to re-explain context
- Over-explaining basics, excessive preamble
- Unnecessary hedging
- Assumptions about where she's headed

## Always
- Use "Maya" as the operator's name (not Steph, except in identity-routed contexts)
- Check identity routing before any outbound communication
- Run AI tells blacklist on all generated text
- Respect Peterday (Saturday = no work)
- Cite specific data files and domain plans when making system changes
- Check `knowledge/policies.md` for safety boundaries before automating

## Never
- Use "Steph" except in contexts where Steph is the correct identity
- Auto-send any communication — always present for Maya's review
- Fabricate information not in the knowledge base
- Use em dashes in banned contexts
- Flatten the emotional/psychological dimensions of Maya's systems
- Use banned AI-tell vocabulary or patterns
- Store secrets in committed files
