# Domain Plan: File Management

## Purpose
Automate file routing from Google Drive intake folders to destination folders based on TagSpaces filename tags. Replace the current n8n matrix-based system with something that scales beyond 3 clients without requiring manually encoded Excel matrices.

## Inputs
- knowledge/conventions.md — TagSpaces format, symmetry rule, client tag behavior
- knowledge/tools.md — n8n workflow details, TagSpaces description, Google Drive structure
- data/file-routing.yaml — Tag vocabulary, 3 active workflows with IDs, routing pipeline description, all folder IDs
- data/client-registry.yaml — Clients with file routing (Lynn, Maya, Sulima) and those without

## System Overview
**Pipeline:** TagSpaces → Google Drive intake folder → n8n hourly trigger → tag-pair matrix lookup → destination folder (or Unsorted).

**Tagging:** Files are tagged in TagSpaces with up to 2 bracketed tags appended to the filename (e.g., `document[Cover Painting-Celia].pdf`). Tags are visible everywhere — Drive, search, n8n string parsing. No metadata storage.

**Routing logic:** n8n parses the filename, extracts tag pairs, alphabetically sorts them (symmetry rule — `[Cover Painting-Celia]` and `[Painting-Celia Cover]` route identically), then looks up the sorted pair in a hardcoded matrix to find the destination folder ID. Client tags (Lynn, Maya, Sulima) are stripped from the routing key because the intake folder already encodes client identity.

**Current state:** 3 active file sort workflows (Lynn, Maya, Sulima), running hourly. The routing matrices are manually encoded into n8n workflow code from Excel source-of-truth spreadsheets. No automated sync between Excel and n8n.

**Graceful degradation:** Files with unrecognized tag pairs route to a client-specific Unsorted folder. This folder also serves a psychological function — it's reassurance that nothing is lost.

**Scaling barrier:** Adding a new client requires building a new matrix in Excel, manually encoding it into a new n8n workflow, and maintaining both. Maya wants a system where adding a client doesn't require this manual matrix work. All clients already have Google Drive folders.

**Tag vocabulary:** 31 total tags across 3 clients — 3 client tags, 17 universal content tags, 1 partial tag (B-Roll, present in Lynn/Maya but not Sulima), and project-specific tags per client (3 for Lynn, 3 for Maya, 4 for Sulima).

## Automation Requirements

### Core: Scalable File Routing
- Replace the hardcoded n8n matrices with a data-driven routing system
- Routing configuration stored in a single editable file (YAML, JSON, or database) — not embedded in workflow code
- Adding a new client requires only: (1) create Google Drive folder structure, (2) add routing entries to the config file. No code changes.
- Maintain the existing tag-pair → folder mapping logic. Every existing route must produce the same result as the current system.
- Preserve the symmetry rule: alphabetically sort tag pairs before lookup
- Preserve the client tag stripping: intake folder encodes client, client tag is searchable redundancy

### Graceful Degradation
- Unrecognized tag pairs → client-specific Unsorted folder (maintain current behavior)
- Files with 0 tags → Unsorted (can't route without tags)
- Files with 1 tag → attempt routing with single-tag key, fall back to Unsorted
- Log all Unsorted routings for periodic review

### TagSpaces Compatibility
- Continue parsing bracketed tags from filenames
- Support up to 2 tags per file
- Do not modify the filename tagging convention — TagSpaces is the source of truth for tag assignment

### New Client Onboarding
- Template for new client folder structure: Admin, Marketing, Source files, Website (Assets/Copy/Design), Unsorted, plus book-specific folders as needed
- Auto-generate routing config entries from the folder structure
- Support both universal content tags and client-specific project tags

### Monitoring
- Dashboard or report: files routed per client per week, Unsorted file count, routing errors
- Alert if Unsorted folder grows beyond a threshold (configurable)

## Edge Cases & Constraints
- **Unsorted folder is emotional infrastructure.** It provides reassurance that nothing is lost. Never remove it, never skip it, never treat it as an error state.
- **Tag order doesn't matter.** `[Cover Painting-Celia]` and `[Painting-Celia Cover]` must route identically. Alphabetical sort before lookup.
- **Client tag stripping.** If a file is tagged `[Maya Cover]` in the /MAYA intake folder, the routing key is `Cover` (single tag), not `Cover Maya`. The client tag is redundant with the intake folder.
- **B-Roll tag is partial.** Present for Lynn and Maya, absent for Sulima. The routing config must handle per-client tag availability.
- **Lingua Ink routing is placeholder.** A matrix exists in google_drive_id_matrix.json but only 4 of 484 cells route (project self-pairs). Not wired to n8n. May be activated later.
- **Google Drive folder IDs are stable.** All folder IDs documented in file-routing.yaml. Use these directly — don't search for folders by name.
- **n8n still runs.** The existing n8n workflows will continue running until SL replaces them. Migration must be coordinated to avoid duplicate routing.

## Implementation Notes

### Current n8n Workflows (to be replaced)
From `data/file-routing.yaml`:
- Sort LYNN files: workflow `sB5xfJmIuOMT9kmb`
- Sort MAYA files: workflow `nU8lKfEFO4DxTyex`
- Sort SULIMA files: workflow `MIK98RtLqhWtfJH4`
- All run on hourly triggers

### Routing Matrix Source
- Complete matrices: `sources/system-snapshots/google_drive_id_matrix.json`
- Each matrix is 22x22 (tag-pair to folder-ID lookup)
- Matrix keys: `MAYA_routing_matrix`, `LYNN_routing_matrix`, `SULIMA_routing_matrix`, `LINGUA INK_routing_matrix`

### Google Drive API
- Authentication: OAuth2 or service account with Drive access
- Key operations: list files in intake folder, move file to destination folder, create folders
- Rate limits: Google Drive API default quotas

### Intake Folder Paths
- Lynn: `/LYNN` (Unsorted: `1tp5aFpswfMYtgc_L4jUzXybzxgwJf2_t`)
- Maya: `/MAYA` (Unsorted: `1ykOtB1Lzao_-YY5kILRep2J-yduW-yvd`)
- Sulima: `/SULIMA` (Unsorted: `1R0aAzfFYL8pB08eBBG09IYcExjLDE6S1`)

### Complete Folder IDs
All destination folder IDs documented in `data/file-routing.yaml` under `folder_ids`. Example (Maya):
- Admin: `1Uzt32vdzpwWtCvlMdeebxtAKYtcWjuqg`
- Book - Painting Celia: `1HYgKE8KHG3aHa5yssRP5QkYSCkixs6Iv`
- Marketing: `1liZVn5ML72uIAoAhHkp-gcvV2PUbMxIC`
- (Full list: 20+ folders per client)

### Tag Vocabulary Reference
From `data/file-routing.yaml`:
- **Universal (17):** Source, Asset, Copy, Design, Marketing, Newsletter, Inspo, Admin, Cover, Info, Backup, Headshot, Interior, OLD, Video, PSD, Featured-image, Social-image
- **Partial (1):** B-Roll (Lynn, Maya only)
- **Client tags (3):** Lynn, Maya, Sulima
- **Project tags:** Lynn (Hallway-of-Doorknobs, Untitled-Libby, Workbook), Maya (Painting-Celia, Sailor's-Code, Untitled-Kelsey), Sulima (All-in-the-Soup, Arms-Filled-with-Bittersweet, Tributaries, Words-That-Dance)

### Migration Strategy
1. Build new routing system alongside existing n8n workflows
2. Test with a small batch of files per client to verify routing matches
3. Disable n8n workflows only after confirming SL routing produces identical results
4. Keep n8n workflows as rollback option during transition period

## Resolved Questions
- **Google Drive API credentials:** Will be provided during SL setup.
- **Routing config storage:** Database table (queryable, dashboard-friendly) — better fit for this volume of data.
- **Lingua Ink routing:** Yes, activate. Create folder structure following the client template.
- **Devon Ervin, Daniela Morescalchi, and all other clients:** Yes — ALL clients should have automated routing once the final process is decided.
- **Tag vocabulary expansion:** Auto-detect. When Maya adds a new tag, the routing system should pick it up without manual config.
- **Folder destination inference:** Ideally SL should figure out which folder a file belongs in with minimal input from Maya.
- **Google Drive folder IDs:** SL should retrieve folder IDs via the Google Drive API rather than requiring Maya to gather them manually. Fallback: Maya has an n8n workflow that can export IDs per client.

## Open Questions
- **TagSpaces replacement:** Maya is open to replacing TagSpaces entirely with a new tagging/routing system if SL can provide one. The current bracket-in-filename convention works but is friction. No replacement has been identified yet — SL should consider whether a better approach exists (e.g., Drive metadata, a tagging layer within SL, or another method) as long as tag visibility and searchability are preserved.
