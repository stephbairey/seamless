# Revenue Module Briefing: How the Royalty Spreadsheet Actually Works

This document explains the structure of Maya's existing royalty tracking spreadsheet (Lingua_Ink_Royalty_Reports.xlsx) so the Seamless revenue module can ingest KDP data and export tables formatted to paste into it.

---

## The Goal

Maya uploads KDP CSV exports into Seamless. Seamless parses them and outputs rows formatted to paste directly into the **Transactions** sheet of the royalty spreadsheet. The spreadsheet remains the source of truth for now; Seamless is the ingestion and transformation layer.

This is NOT about replacing the spreadsheet. It's about eliminating the manual work of reformatting KDP data into the spreadsheet's column structure.

---

## Spreadsheet Structure (9 sheets)

### Transactions (the target)

This is the master ledger. Every sale, payment, refund, and cost entry for all authors lives here. When Seamless exports data, it needs to match this schema exactly.

**Columns (in order):**

| Column | Name | Type | Notes |
|--------|------|------|-------|
| A | Date | Date (YYYY-MM-DD) | First of month for monthly KDP data, exact date for in-person/one-off |
| B | Title | Text | Book title, or "(multiple)" for payment rows |
| C | Author | Text | "Maya Bairey", "Sulima Malzin", or "Carolyn Martin" |
| D | Format | Text | "Ebook", "Paperback", "Vella", "Cards", "Support", "(multiple)", "NIWA Mt. Angel" |
| E | Type | Text | "Purchase", "KENP", "Free promo", "Pre-order", "Goodreads", "Free price match", "Payment", "Receipt", "Refund", "Printing cost (50)", "Printing cost (250)", "Printing repayment" |
| F | Marketplace | Text | "Amazon.com", "Amazon.ca", "Amazon.co.uk", "Amazon.de", "Amazon.fr", etc. Also: "In person", "Vistaprint", "Buymeacoffee", "NIWA", "(multiple)" |
| G | Units Sold | Integer | Blank/NaN for payment rows |
| H | Units Refunded | Integer | Usually 0 |
| I | Net Units Sold | Integer | For KENP rows: this is page count, not unit count. 0 for monthly KENP, actual count for daily KENP. |
| J | Payout | Decimal | Amazon royalty rate (0.35, 0.60, 0.70, 1.00) OR blank for payments. For recent rows (May 2025+), this is 1.00 across the board. |
| K | Earnings | Decimal | Net royalty amount in the sale's native currency (but stored as a number, not tagged with currency) |
| L | KEEP% | Decimal or blank | Publisher's share: 1.0 for Maya's books, 0.0 for Sulima's, 0.5 for Carolyn's. Blank for some rows (especially newer ones from May 2025+). |
| M | (unnamed) | Text or blank | Occasional notes like "fees?" |

**Critical details:**

- Rows are sorted by date, then roughly by author within the same date.
- Payment rows (where Maya pays Sulima) have negative Earnings, "(multiple)" for Title/Format, and "(multiple)" for Marketplace.
- Non-book entries exist: Buymeacoffee receipts/payments (Sulima's support income), business card printing costs, NIWA consignment fees, Tributaries printing/repayment cycle.
- KENP (Kindle Edition Normalized Pages) rows have page counts in Units Sold but 0 in Net Units Sold for monthly aggregated data. Daily KENP data (like April 2025 entries) has page counts in both columns.
- The Payout column changed meaning over time. Earlier data has Amazon's royalty rate (0.35 for ebooks, 0.60 for paperbacks). Newer data (May 2025+) shows 1.00, possibly because Maya switched to recording the full amount and handling splits via KEEP%.

### DASHBOARD

Summary view. Shows per-author totals: Total Paid, Royalties Owed, and Profit. This is calculated from the other sheets (likely formula-driven), not a data entry point.

### Royalty Report

Formatted report with Lingua Ink Media letterhead (address, phone, email). Covers a specific date range (currently Jan 1 - Dec 31, 2025). Shows one author at a time with their royalty rate, itemized transactions, total earnings, total due to author, and last balance. This is the sheet that gets exported/printed for author payment records.

### Maya, Sulima, Carolyn (per-author sheets)

Each has a summary block at top (Total Sales broken into Ebook/Print/KENP) followed by the full transaction history for that author. Column structure matches Transactions but without the KEEP% column. These are filtered views of the Transactions data.

### Transform

A working/staging sheet where KDP data gets reformatted before going into Transactions. Contains partially processed data with ASINs visible. This is essentially what Seamless will replace.

### Paste

Raw KDP CSV paste area. Two sections: the main Combined Sales report (with all KDP columns including Royalty Type, Payout Plan, Currency, Avg. List Price, Avg. Offer Price, Avg. File Size, Avg. Manufacturing Cost) and a separate KENP section at the bottom with daily page-read data.

KDP Combined Sales columns (as pasted):
MONTH, Title, Author, ASIN/ISBN, Marketplace, Units Sold, Units Refunded, Net Units Sold or Combined KENP, Royalty Type, Payout Plan, Currency, Avg. List Price without tax, Avg. Offer Price without tax, Avg. File Size (MB), Avg. Delivery/Manufacturing cost, Earnings

KENP section columns:
Date, Title, Author Name, eBook ASIN, Audiobook ASIN, Audible ASIN, Marketplace, KENP, Returns, Royalty, KENP PAID

### Lists

Reference/lookup sheet. Contains:
- ASIN/ISBN for each book with Type (Ebook/Paperback/Hard cover), Last Price, and Keep% per title
- Purchase type mapping (Standard → Purchase, KENP → KENP, Free - Promotion → Free promo, etc.)
- Author name list
- Date range list (monthly periods going back to Oct 2022)

---

## What Seamless Needs to Do

### Input: KDP CSV Export

KDP provides a "Combined Sales" CSV. The columns match what's in the Paste sheet. Seamless should parse this CSV and transform each row into the Transactions schema.

### Transformation Rules

1. **Date**: KDP uses "YYYY-MM" format. Convert to first-of-month date (YYYY-MM-01).

2. **Title**: Pass through as-is from KDP.

3. **Author**: Pass through. KDP uses "Maya Bairey", "Sulima Malzin", etc.

4. **Format**: Map from KDP's "Payout Plan" field:
   - "Standard - Paperback" → "Paperback"
   - "Standard - Hardcover" → "Paperback" (or "Hard cover" — check with Maya)
   - "Standard" (ebook) → "Ebook"
   - "Kindle Edition Normalized Pages (KENP)" → "Ebook" (with Type = "KENP")

5. **Type**: Map from KDP's "Royalty Type" and "Payout Plan":
   - KENP rows → "KENP"
   - Royalty Type "35%" or "70%" with units > 0 → "Purchase"
   - Net units but $0 earnings → "Free promo"
   - Look at the Purchase type mappings in the Lists sheet for the full set

6. **Marketplace**: Pass through from KDP (Amazon.com, Amazon.ca, etc.)

7. **Units Sold / Units Refunded / Net Units Sold**: 
   - For regular sales: pass through from KDP
   - For KENP: Units Sold = KENP page count, Net Units Sold = 0 (for monthly data)

8. **Payout**: This is the Amazon royalty rate. Map from KDP's "Royalty Type":
   - "35%" → 0.35
   - "60%" → 0.60
   - "70%" → 0.70
   - KENP → 0.00
   - Or use 1.00 if following the newer convention (check with Maya which she prefers going forward)

9. **Earnings**: The royalty amount from KDP. Pass through.

10. **KEEP%**: Look up from the Lists sheet data (stored in Seamless config):
    - Maya Bairey → 1.0
    - Sulima Malzin → 0.0
    - Carolyn Martin → 0.5

### KENP Daily Data

KDP also provides a separate daily KENP report. This has individual dates (not monthly) and per-day page reads with the actual KENP payment calculated. These need to be transformed into Transactions rows too, with:
- Date: the actual date from the report
- Format: "Ebook"
- Type: "KENP"
- Units Sold: KENP page count
- Net Units Sold: KENP page count (daily data keeps the count in both fields)
- Payout: 0.00
- Earnings: the KENP PAID value

### Output Format

Seamless should export a table (CSV or display in the UI) with columns in exact Transactions order:
Date, Title, Author, Format, Type, Marketplace, Units Sold, Units Refunded, Net Units Sold, Payout, Earnings, KEEP%

Maya copies these rows and pastes them into the Transactions sheet. The per-author sheets and Dashboard presumably pull from Transactions via formulas or manual copy.

---

## Duplicate Detection

The plan mentions checking for existing records with same (royalty_date, title, asin_isbn, marketplace, transaction_type). That's good, but note:

- The Transactions sheet does NOT store ASIN/ISBN. Duplicates need to be caught by (Date, Title, Author, Format, Type, Marketplace, Units Sold, Earnings) — the full row signature.
- KDP sometimes reports the same book twice in the same month on the same marketplace with different royalty rates (35% vs 70% for ebooks depending on price). These are NOT duplicates.
- Free promo rows with 0 earnings are easy to accidentally duplicate since many look identical. The Units Sold count is the differentiator.

---

## Edge Cases from the Real Data

1. **Sulima's non-book entries**: Buymeacoffee, business cards, NIWA consignment, and printing costs are manually entered, not from KDP. Seamless should NOT try to generate these from CSV imports. They're manual revenue entries.

2. **Payment rows**: Negative earnings rows where Maya pays authors. These are manual entries too.

3. **In-person sales**: Marketplace = "In person", Payout = 1.00 (full cover price kept). Not from KDP.

4. **Hardcover**: Painting Celia has a hardcover edition (B0D33MQ4F5 / 979-8-9906749-0-5). KDP reports it as "Standard - Hardcover". The spreadsheet currently shows these as Paperback with the hardcover ISBN in the Lists sheet. Clarify with Maya how she wants hardcovers labeled.

5. **Currency mixing**: KDP reports in local currency (USD, CAD, GBP, EUR, AUD, BRL). The Earnings column in Transactions stores the raw amount without currency tagging. All values appear to be in their original currency, not converted to USD.

6. **The Payout column shift**: Pre-2025 data uses Amazon's royalty percentage (0.35, 0.60). Post-May-2025 data uses 1.00. The revenue module should ask Maya which convention to use for new imports, or detect it from the KDP data.

---

## What This Means for the Plan

The plan's Phase B (KDP Import + Royalty Reports) is the right starting point, but the implementation should be adjusted:

1. **Primary output is paste-ready rows**, not just internal storage. The export-to-Transactions format is the critical deliverable.

2. **The KDP parser needs to handle two report types**: Combined Sales (monthly) and KENP daily reads. They have different column structures.

3. **The royalty calculation can be simpler than planned** — KEEP% is per-author, not per-title. Maya=1.0, Sulima=0.0, Carolyn=0.5. The plan's split parsing ("50/50 Amazon", "60/40 author/publisher") is more complex than what the real data shows.

4. **ASIN/ISBN lookup lives in the Lists sheet**, not in the transaction data. Seamless should store this mapping (from the Lists sheet data) but doesn't need it in the export rows.

5. **The Transform and Paste sheets are what Seamless replaces.** The workflow today is: paste raw KDP into Paste → manually reformat in Transform → copy into Transactions. Seamless automates that middle step.
