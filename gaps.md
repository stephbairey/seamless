# Gaps — Unresolved Items
# Phase 5 output — Seamless Bootstrap
# Everything SL needs that SB couldn't provide or confirm

## Data Layer Issues (Found During Cross-Validation)

### Fixed: ClickUp Option ID Mismatch
- **Issue:** 15 of 16 ClickUp Project option IDs in `client-registry.yaml` did not match the authoritative IDs in `clickup-fields.yaml` (sourced from system snapshot). Only "Raging Grannies" matched.
- **Resolution:** All 15 IDs corrected in client-registry.yaml to match clickup-fields.yaml (the system snapshot is authoritative).
- **Root cause:** Phase 2 enrichment assigned incorrect option IDs. Unknown source of the wrong IDs.
- **Status:** FIXED.

## Missing Credentials & API Access

### ClickUp API Token
- **Needed for:** All ClickUp automation (task creation, querying, updates)
- **Action:** Maya must provide during SL setup
- **Domain plan:** clickup-automation.md

### Gmail API OAuth Credentials
- **Needed for:** Email triage, PRG newsletter automation, identity-aware drafting
- **Action:** Configure OAuth2 for stephbairey@gmail.com during SL setup
- **Domain plan:** email-triage.md

### Google Calendar API Credentials
- **Needed for:** Calendar sync, meeting prep, cadence tracking
- **Action:** Separate auth per calendar (confirmed — one token will NOT cover all 3)
- **Domain plan:** calendar-sync.md

### Google Drive API Credentials
- **Needed for:** File routing automation
- **Action:** OAuth2 or service account with Drive access
- **Domain plan:** file-management.md

### Social Media API Access
- **Needed for:** Content distribution
- **Platforms:** Facebook Graph API (3 pages), Instagram API (2 accounts), YouTube Data API (2 channels), LinkedIn API (2 profiles), TikTok API (restricted access)
- **Action:** Configure per platform during SL setup
- **Domain plan:** content-distribution.md

## Missing Configuration Details

### ClickUp Time Tracking
- **Resolved:** Maya rarely uses ClickUp's built-in timer. Time is estimated and added manually after a task is complete.
- **Impact:** Revenue workflow cannot pull live hours from API. SL should work with manually-entered time values on completed tasks.
- **Domain plans:** revenue-workflow.md, clickup-automation.md

### ClickUp Saved Views
- **Resolved:** Maya uses extensive saved views and filters. Multiple dashboards (Executive, Overview), list/table/calendar views, saved dashboards per client, and a saved calendar view per client.
- **Impact:** SL must not create conflicting views. SL should be aware of and work alongside existing views.
- **Domain plan:** clickup-automation.md

### Gmail Filter Export
- **Resolved:** Already available at `sources/system-snapshots/GmailFilters.xml`.
- **Domain plan:** email-triage.md

### Email Signatures
- **What's missing:** Per-identity email signature content. Maya has formatted signatures but needs a way to provide them (they contain HTML formatting).
- **Action:** Maya to export signature HTML from Gmail settings (Settings → General → Signature) or screenshot them for SL to replicate.
- **Domain plan:** email-triage.md

### SPF/DKIM/DMARC Records
- **What's missing:** DNS authentication records for the 6 email domains
- **Impact:** Deliverability of SL-generated emails
- **Domain plan:** email-triage.md

### Docker / Self-Hosting Infrastructure
- **Resolved:** Maya runs n8n and Stirling PDF in Docker on her office computer. n8n is the free Docker version (NOT n8n.io cloud at $20/mo). All other self-hosting is on a separate Media Server computer.
- **Impact:** SL automation that depends on n8n runs locally, not in the cloud. This affects availability (office computer must be on), deployment, and how SL triggers n8n workflows.
- **Scope:** SL manages n8n (on office computer) only. Media Server and other self-hosting are out of SL scope.

### Hosting Provider
- **Resolved:** Nixihost confirmed as hosting provider.
- **WordPress installs:**
  - bairey.com — Maya Bairey (personal/author)
  - sulimamalzin.net — Sulima Malzin, herSelf
  - staging.bairey.com — currently undedicated, available for client work that needs non-local access by clients
  - jaimebairey.com — Jaime Bairey Photography (Maya's niece; hosted as a familial gift, not actively used)
  - linguaink.com — Lingua Ink Books
  - linguainkmedia.com — Lingua Ink Media
  - lynnahaller.com — Lynn A. Haller
- **Email addresses hosted at Nixihost (by domain):**
  - **bairey.com:** maya@, steph@, webgranny@ (legacy — should be removed)
  - **linguaink.com:** maya@, steph@, info@
  - **linguainkmedia.com:** maya@, steph@, connect@ (public-facing), info@
  - **lynnahaller.com:** lynn@, connect@, doorknobs@ (distribution list to both Lynn and Maya)
  - **jaimebairey.com:** jaime@, info@
  - **sulimamalzin.net:** sulima@

## Resolved Design Questions
- **Revenue dashboard:** Web dashboard with exportable data.
- **Daily email digest:** Dashboard (part of emerging unified dashboard system).
- **File routing config:** Database table (queryable, dashboard-friendly).
- **Voice profile storage:** YAML config files.
- **WwM video pipeline:** As automated as possible.
- **First product to launch:** Writing with Maya (PDF templates + video pipeline).

## Volatile Items (May Change During SL)

### Story Lounge Status
- **Current:** Legacy — approximately 2 weeks remaining (as of March 2026). Treat as legacy; no automation needed.
- **Impact:** Will need removal from recurring calendar events after it ends.

### Genre Cohort Model
- **Current:** Conceptual — genre-specific cohorts under Maya's branding at 50/50 split
- **Impact:** May create new distribution, ClickUp, and branding needs

### Pat Schoof Decision
- **Current:** Proposal sent, engaged, no commitment
- **Impact:** If signed, adds new publishing client across multiple systems

### LLC Formation
- **Current:** Planned but not done. Still sole proprietorship.
- **Impact:** May affect invoicing format, business identity

### COBRA Expiration (July 2026)
- **Current:** Critical financial deadline
- **Impact:** May accelerate revenue priorities and job search intensity

## Structural Limitations

### Phase 0 Manifest
- **Resolved:** `extraction/manifest.md` built retroactively from existing source files. Catalogs ~60 unique documents across 6 source directories.

### Policies Document
- **Resolved:** `output/knowledge/policies.md` built. Consolidates 15 policy areas from domain plans, identities.md, and conventions.md. Covers: no auto-send, identity routing, AI tells, em dashes, Peterday, sacred sign-offs, Approach field, secrets management, client confidentiality, existing systems protection, graceful degradation, cognitive load, and infrastructure scope.

### KDP Export Format
- **Resolved:** Documented from sample file `sources/system-snapshots/KDP_Prior_Month_Royalties-2025-12-01[Lingua-Ink Admin].xlsx`.
- **Format:** Excel workbook with 5 sheets:
  - **eBook Royalty:** Title, Author, ASIN, Marketplace, Units Sold, Units Refunded, Net Units Sold, Royalty Type, Transaction Type, Currency, Avg. List Price without tax, Avg. Offer Price without tax, Avg. File Size (MB), Avg. Delivery Cost, Royalty
  - **KENP Read:** Title, Author, ASIN, Marketplace, Kindle Edition Normalized Page (KENP) Read
  - **Paperback Royalty:** Title, Author, ISBN, Marketplace, Units Sold, Units Refunded, Royalty Type, Avg. List Price without tax, Avg. Offer Price without tax, Avg. Manufacturing Cost, Royalty, Currency, ASIN
  - **Hardcover Royalty:** Same columns as Paperback
  - **Total Earnings:** Title, Author, ASIN/ISBN, Marketplace, Units Sold, Units Refunded, Net Units Sold or KENP Read, Royalty Type, Payout Plan, Currency, Avg. List Price without tax, Avg. Offer Price without tax, Avg. File Size (MB), Avg. Delivery/Manufacturing cost, Earnings
- **Note:** Each sheet has a "Sales Period" header row before the column headers. Parser must skip row 1.
- **Domain plan:** revenue-workflow.md

### GA4 Property for linguainkmedia.com
- **What's missing:** GA4 property ID for linguainkmedia.com (probably doesn't have one)
- **Impact:** Analytics coverage gap for the LIM consulting site
- **Severity:** Low — Maya noted it likely doesn't have GA4
