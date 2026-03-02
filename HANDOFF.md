# HANDOFF — Seamless Bootstrap → Seamless

## What SB Produced

Seamless Bootstrap (SB) extracted and organized Maya Bairey's institutional knowledge into structured deliverables for the Seamless (SL) automation project. The work ran across 5 phases from February to March 2026.

### Source Material
26 handoff documents, system snapshots (ClickUp fields JSON, Gmail XML, Google Calendar ICS, n8n workflow JSON, Google Drive ID matrix JSON), website exports, contracts, invoices, business plans, brand style guides, blog style guides, and direct operator notes from Maya.

### What Was Produced
SB produced three layers of output:

**Knowledge layer** (human-readable reference):
- `output/knowledge/tools.md` — Complete tool inventory with configurations
- `output/knowledge/conventions.md` — Naming rules, formatting preferences, design principles
- `output/knowledge/clients.md` — Client profiles, relationships, contracts
- `output/knowledge/identities.md` — Seven voice profiles, identity routing table, AI tells blacklist
- `output/knowledge/rhythms.md` — Weekly/monthly/quarterly cadences, time allocation

**Data layer** (machine-readable configuration):
- `output/data/clickup-fields.yaml` — 6 custom fields with all option UUIDs, workspace/space/list IDs
- `output/data/email-identities.yaml` — 17 Send-As identities, SMTP configs, 27 labels
- `output/data/calendar-map.yaml` — 3 calendars, recurring events, integration status
- `output/data/file-routing.yaml` — Tag vocabulary, n8n workflows, all Google Drive folder IDs
- `output/data/client-registry.yaml` — Client profiles with ClickUp option IDs, rates, royalty splits

**Domain plans** (automation instructions):
- `output/domain-plans/clickup-automation.md` — Task CRUD, field population, reporting
- `output/domain-plans/email-triage.md` — Classification, labeling, identity-aware drafting
- `output/domain-plans/calendar-sync.md` — Unified view, meeting prep, cadence tracking
- `output/domain-plans/file-management.md` — Scalable file routing to replace n8n matrices
- `output/domain-plans/revenue-workflow.md` — Revenue tracking, invoicing, royalty reports
- `output/domain-plans/brand-codification.md` — Voice selection, em dash enforcement, AI tells filter
- `output/domain-plans/content-distribution.md` — Cross-platform distribution, PRG newsletter, social

**Synthesis deliverables:**
- `output/seamless-claude-md-draft.md` — Draft CLAUDE.md for SL
- `output/agent-designs/` — 4 prototype agent designs (email triage, PRG newsletter, content distribution, ClickUp task)
- `output/gaps.md` — Everything unresolved
- `extraction/fact-index.md` — Global fact index with source references

## File Mapping: SB → SL

| SB File | SL Purpose |
|---------|------------|
| `output/seamless-claude-md-draft.md` | Starting point for SL's `.claude/CLAUDE.md` |
| `output/data/*.yaml` | Load directly as SL configuration data |
| `output/knowledge/*.md` | Reference documents for SL context |
| `output/domain-plans/*.md` | Implementation guides for each automation domain |
| `output/agent-designs/*.md` | Starting point for SL subagent definitions |
| `output/gaps.md` | SL setup checklist — items to resolve first |
| `extraction/fact-index.md` | Source-linked reference for verifying any fact |

## SL Setup Steps

### 1. Credentials & API Access
Before anything else, resolve these (documented in `gaps.md`):
- [ ] ClickUp API token
- [ ] Gmail API OAuth (stephbairey@gmail.com)
- [ ] Google Calendar API (separate auth per calendar, all 3)
- [ ] Google Drive API
- [ ] YNAB API token
- [ ] PayPal API credentials
- [ ] Stripe API key
- [ ] Venmo access token (business account, if available)
- [ ] Social media platform APIs (as needed)
- [ ] WordPress application passwords (linguaink.com, bairey.com, sulimamalzin.net)
- [ ] WooCommerce API keys (bairey.com)

**Secrets management:** Copy `output/secrets.env.example` to `secrets.env` and fill in real values. `secrets.env` is gitignored and must never be committed. All domain plans reference credentials as "to be provided during SL setup" — this is where they go.

### 2. Install CLAUDE.md
Copy `output/seamless-claude-md-draft.md` to SL's `.claude/CLAUDE.md`. Customize:
- Add SL-specific repo structure
- Add SL-specific rules (commit conventions, testing, etc.)
- Review and adjust the identity routing table if anything has changed
- Add API credential references (don't store secrets in CLAUDE.md)

### 3. Load Data Files
Copy `output/data/*.yaml` into SL's data directory. These are the configuration files that SL reads:
- Validate YAML syntax
- Verify ClickUp option IDs against live API (sanity check after Phase 5 cross-validation fix)
- Verify email identities against current Gmail Send-As settings

### 4. Set Up Agent Designs
Use `output/agent-designs/*.md` as starting points for SL subagents. These are prototypes — refine during implementation:
- Adjust model selection based on task complexity and cost
- Add actual tool bindings (Gmail MCP, ClickUp API, etc.)
- Test against real data before deploying

### 5. Work Through Gaps
`output/gaps.md` contains remaining unresolved items. Most design questions were resolved during Phase 5 review. Remaining priority items:
- Missing credentials (blocking — see Step 1)
- Email signatures (need export from Gmail)
- SPF/DKIM/DMARC records (check during setup)
- Volatile items to re-check (Story Lounge ending, Pat Schoof decision, LLC formation)

### 6. Domain-by-Domain Implementation
Implement in this suggested order (dependencies flow downward):
1. **Brand Codification** — Identity routing and voice system. Everything else depends on getting the name right.
2. **ClickUp Automation** — Task management. Foundation for tracking all other work.
3. **Email Triage** — Daily operational value. Depends on identity routing.
4. **Calendar Sync** — Scheduling awareness. Cross-references ClickUp tasks.
5. **File Management** — Replace n8n. Can run independently.
6. **Revenue Workflow** — Financial visibility. Depends on ClickUp data.
7. **Content Distribution** — Promotion pipeline. Depends on brand codification. Last because "product first, marketing second."

## Cross-Cutting Concern: Unified Dashboard

Multiple domains converge on a web-based dashboard. SL should treat this as a shared infrastructure decision rather than building separate UIs per domain.

**Dashboard surfaces identified during SB:**
- **Revenue:** Dashboard with exportable data (revenue by stream/client/period, costs, targets)
- **Email digest:** Daily morning summary grouped by label with priority flags
- **Consignment tracking:** Books out, location, dates, retrieval schedule
- **Calendar:** Could benefit from a unified view for SL purposes
- **ClickUp reporting:** Weekly summaries, emotional load distribution, overdue tasks

**What SB does NOT prescribe:**
- Technology stack or auth model
- Whether it's one app or a lightweight portal linking to purpose-built views

**Infrastructure note:** SL services should run on Maya's office computer (primary workstation, upstairs office) or cloud as needed. The household local dashboard (passive display on a mini-PC downstairs — like an airport arrival/departure monitor) is a separate system and NOT part of SL. The Media Server (mini-PC, upstairs office, runs Jellyfin and other self-hosting) is also separate from SL scope except for n8n which runs on the office computer.

**Recommendation:** Make the dashboard architecture an early SL decision (before domain-by-domain implementation), since multiple domains will feed into it.

## Known Limitations

### What SB Did Not Produce
- **No code.** SB produces documents and data files, not automation logic.
- **No API testing.** Data files contain IDs and configurations but were not validated against live APIs (except where sourced from system snapshots).

### Data Currency
- Source material is current as of March 2026.
- System snapshots (ClickUp, Gmail, Calendar) were not re-exported at Phase 5 start (Maya confirmed no changes).
- If SL implementation extends into Q2 2026 or later, re-export critical snapshots before building against them.

### Maya Corrections
`maya-corrections.md` contains 11 corrections to source material errors discovered during review. These have been incorporated into all output files, but SL should check this file when source documents are referenced — the original sources still contain the errors.

## Contact
- **Maya Bairey** — stephbairey@gmail.com
- **GitHub:** stephbairey/seamless-bootstrap (private repo)
