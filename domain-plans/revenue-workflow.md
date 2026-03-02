# Domain Plan: Revenue Workflow

## Purpose
Automate revenue tracking, invoicing, royalty reporting, and financial visibility across Lingua Ink's three revenue streams. Reduce manual effort in tracking what's owed, what's been paid, and what the business health looks like at any given time.

## Inputs
- knowledge/clients.md — Client profiles, contract terms, rate structures
- knowledge/rhythms.md — Reporting cadences (royalty reports quarterly, invoicing per-project)
- data/client-registry.yaml — Contract types, rates, royalty splits, retainer amounts
- data/clickup-fields.yaml — Revenue custom field for task-level income tracking
- YNAB API — Transaction categorization and financial visibility (personal and business finances)

## System Overview
Maya currently manages three revenue streams manually:

**1. Consulting revenue (LIM):** Rate varies by client ($166.66–$195/hr). Some clients pay retainers (Nicole: $5K). Invoicing is manual. Time tracked in ClickUp. Invoice format visible in invoice-example.png.

**2. Publishing revenue (LIB):** Amazon KDP royalties (monthly), IngramSpark, direct sales (in-person, consignment). Royalty reporting done in a custom spreadsheet with per-author sheets and a dashboard. Two contract models coexist: fee-based (Martin: $400 + 50/50) and revenue-share (Morescalchi: $0 + 60/40). Sulima has no contract (informal, 0% split). Pat Schoof proposal offers 60–70% to author.

**3. Products/courses:** Writing with Maya templates ($12 each / $39 bundle via WooCommerce). Gentle Guide and Self-Pub Cheat Sheet (two products, same project, not yet launched, $29–59 range). Paid cohort in development ($300–500 for 6 weeks).

**Additional channels:** Book consignment at Broadway Books, Second Shapes, NIWA. In-person book fair sales. BuyMeACoffee donations (tracked for Sulima).

**Financial reality:** 2024 net loss ~$5,829. 2025 operated at a loss. Recurring costs ~$200–250/month (software) + $12/month hosting + $10/month virtual mailbox. Goal: $15K/month gross. Both business plans are aspirational; SEA version is more realistic baseline.

## Automation Requirements

### Revenue Tracking Dashboard
- Aggregate revenue by stream: Consulting (LIM), Publishing (LIB), Products/Courses
- Aggregate by client: Nicole, Devon, TDA, Sulima (royalties only), Carolyn, etc.
- Aggregate by month, quarter, year-to-date
- Surface key metrics: revenue vs. target ($15K/month goal), revenue by hour worked, paid vs. volunteer time ratio
- Include recurring costs (software ~$200-250/mo, hosting $12/mo, virtual mailbox $10/mo) for net visibility

### Consulting Revenue (LIM)
- Pull time tracked from ClickUp tasks tagged with Revenue = "Direct, High" or "Direct, Low"
- Calculate billable hours by client using per-client rates:
  - Devon Ervin: $195/hr, project ceiling $1,950
  - Nicole Dalton: $166.66/hr, $5K retainer
  - TDA: $1,000 board-approved budget (total owed: $1,223.39)
- Generate invoice data: client, hours, rate, total, retainer balance
- Track retainer drawdown (Nicole: $5K - hours billed)
- Flag when approaching project ceiling (Devon: $975/phase)

### Publishing Revenue (LIB)
- Import KDP royalty data (monthly CSV exports from KDP dashboard)
- Parse and categorize: by title, by format (ebook, paperback, KENP), by author
- Apply royalty splits per author contract:
  - Sulima Malzin: 0% to author (Maya retains all)
  - Carolyn Martin: 50/50 on Amazon royalties, 100% to author on own-channel
  - Daniela Morescalchi: 60/40 author/publisher (when published)
- Generate quarterly royalty reports per author (due 1st of Jan, Apr, Jul, Oct)
- Track consignment inventory and sales (manual input, low volume)
- Track WooCommerce product sales (Writing with Maya templates)

### Quarterly Royalty Report Generation
- Auto-generate from accumulated KDP/IngramSpark data
- Per-author format: title, format, units sold, royalty rate, gross royalty, split, amount owed
- Include summary dashboard: total catalog sales, per-author totals, trend vs. prior quarter
- Output format: Maya's existing Excel template structure (for continuity), or upgrade to PDF if preferred

### Invoice Generation
- Extend or replace the existing Node.js + docx pipeline
- Pull data from ClickUp (hours by client) and rate schedule
- Apply invoice template matching existing format (visible in invoice-example.png)
- Output: .docx and/or PDF
- Track invoice status: generated, sent, paid, overdue

## Edge Cases & Constraints
- **Rate varies by client.** There is no single standard rate. Each client engagement has its own rate, and new clients may negotiate different rates. The system must store per-client rates.
- **Sulima's arrangement is entirely informal.** No contract, 0% royalty split. This should not be "normalized" or flagged as an error. It's intentional.
- **Multiple royalty split models coexist.** Fee-based (upfront fee + royalty split), revenue-share (no fee + different split), and informal (no contract). Automation must handle per-author terms from client-registry.yaml.
- **Consignment is physical.** Broadway Books, Second Shapes, NIWA. Small volume, tracked manually. May not be worth automating beyond a simple log.
- **Resume revenue claims are forward-looking.** "4 authors, 8 published titles" rounds up anticipating near-completion titles. Actual current: 3 authors, 6 published titles. The dashboard should show actual numbers.
- **KDP data format.** KDP exports as CSV with specific column structure. Parser must handle Amazon's format, which has changed in the past.
- **IngramSpark data.** Separate reporting system from KDP. May require different parser.
- **BuyMeACoffee.** Tracked for Sulima. Small amounts, irregular. Include in revenue tracking but don't over-engineer.

## Implementation Notes

### ClickUp Revenue Field
- Field ID: `44470f88-d8e2-4e14-9f39-c63b30e6aede`
- Options: None (`7ab3a7e0`), Indirect (`fd4654d4`), Passive (`9267bc99`), Direct Low (`4e797c63`), Direct High (`73b3ec47`)
- Query tasks with Revenue = Direct High or Direct Low to find billable work

### Per-Client Rate Reference
From client-registry.yaml:
- Nicole Dalton (Dalton Law): $166.66/hr, $5K retainer
- Devon Ervin: $195/hr, $975/phase ceiling, $1,950 total ceiling
- TDA: $1,000 budget, $1,223.39 total owed (includes hosting + plugin costs)

### Royalty Split Reference
From client-registry.yaml:
- Sulima Malzin: 0% (all retained by Maya)
- Carolyn Martin: 50/50 Amazon, 100% to author own-channel
- Daniela Morescalchi: 60/40 author/publisher, 10-year term per work
- (Prospective) Pat Schoof: 60-70% to author

### Published Titles (current)
- Sulima: *Arms Filled with Bittersweet*, *All in the Soup Together*, *Words That Dance*, *Tributaries*
- Maya: *Painting Celia* (all-time sales: $507.20)
- Carolyn: *Metrophobia* (sales Aug-Nov 2025: $55.19)
- Total: 3 authors, 6 published titles

### YNAB Integration
- **Purpose:** Transaction categorization and financial visibility. Maya uses YNAB for both personal and business finances. YNAB auto-imports transactions from bank accounts — SL does not need to create entries.
- **API base URL:** `https://api.ynab.com/v1`
- **Auth:** Bearer token from YNAB Account Settings (to be provided during SL setup)
- **Official SDKs:** JavaScript (`ynab-sdk-js`), Python (`ynab-sdk-python`)
- **Key capabilities for SL:** Read transactions, update/categorize transactions, read budgets and categories, read account balances.
- **Primary use case:** Categorize imported transactions that YNAB can't auto-categorize. Example: a PayPal outflow arrives in YNAB — SL determines whether it's an LIB printing cost, an electric bill, or a software subscription, and updates the YNAB category accordingly.
- **Secondary use case:** Read categorized transactions for revenue dashboard and financial reporting.
- **Category names use emojis** (e.g., "Lingua Ink: 💵 Income: Production"). SL must handle emoji in category matching and API calls.
- **Stripe/PayPal/Venmo APIs needed for categorization context.** YNAB's bank feed imports transactions but only shows the processor name (e.g., "PayPal"), not what the payment was for. SL cross-references with payment processor APIs to get item-level detail (printing order vs. software subscription vs. client payment), then uses that detail to set the correct YNAB category.
  - **PayPal:** Transaction Search API provides item descriptions, counterparty, invoice IDs
  - **Stripe:** Charges/Payment Intents API provides product/description metadata (WooCommerce sales)
  - **Venmo:** Limited API (business accounts only). If unavailable, Venmo transactions may need manual categorization or Maya's input
  - **Credentials:** All to be provided during SL setup

### Existing Invoice Pipeline
- Node.js + docx library generates .docx invoices
- LibreOffice converts to PDF
- DXA measurements required (percentages break in Google Docs)
- validate.py for QC checks

### Quarterly Cadence
- Royalty reports due: 1st of January, April, July, October
- Calendar event exists on linguainkmedia calendar
- Report covers prior quarter's sales data

## Resolved Questions
- **Revenue dashboard format:** Web dashboard with exportable data.
- **Royalty report generation:** Semi-automated. SL generates the report, Maya reviews before sending to authors.
- **Invoice generation:** SL's choice — whatever works best. No preference on pipeline (extend Node.js + docx or build new).
- **Consignment tracking:** Simple web page or dashboard section recording: number of books out, location (Broadway Books, Second Shapes, NIWA), date placed, when to retrieve unsold copies.
- **WooCommerce sales data:** Pull from PayPal/Stripe transaction records for simplicity (already integrated for YNAB categorization).
- **COBRA and job search:** Not included in financial visibility. Maya is aware of deadlines; no tracking value in the dashboard.
