# Domain Plan: Email Triage

## Purpose
Automate email classification, labeling, and routing in Maya's Gmail hub. Build on the existing 48-filter foundation to handle messages that currently require manual sorting, and support identity-aware reply drafting.

## Inputs
- knowledge/conventions.md — Identity routing (two-axis model), email label hierarchy, communication style
- knowledge/tools.md — Gmail hub architecture, Send-As configuration, filter system
- knowledge/identities.md — Seven voice profiles, identity routing table, AI tells blacklist
- data/email-identities.yaml — 17 Send-As identities with routing rules, 27 labels, hub account details
- data/client-registry.yaml — Client names mapped to email contexts

## System Overview
**Hub model:** stephbairey@gmail.com is the single inbox of truth. All domain email (bairey.com, linguaink.com, linguainkmedia.com, tomahawkdestiny.com, lynnahaller.com) forwards at the hosting level. One inbox, 17 Send-As identities, 27 labels, 48 filters.

**Identity routing (two-axis model):**
- **Name axis:** Steph = business, operations, technical, government-name contexts. Maya = creative, author, writing community.
- **Domain axis:** Which organization. bairey.com (personal), linguaink.com (publishing), linguainkmedia.com (marketing/coding), tomahawkdestiny.com (moorage), lynnahaller.com (client), raginggrannies (PRG/IRG).

**Reply behavior:** Gmail auto-sends from whichever address received the inbound message. No manual switching for replies. For new compositions, the decision is "what hat am I wearing?" — but relationship history can override strict role logic.

**Existing filter system:** 48 filters organized across 9 categories handle automatic labeling, archiving, and noise management. These are the current automated triage layer.

**Manual triage:** Messages that don't match existing filters require Maya to label and potentially route them. Client emails often need identity-aware context (which name does this person know Maya by?).

**Label structure:** 27 labels organized by function — Client/relationship (Authors, Carolyn, Cohort, Daniela, Devon, Lynn, Nicole, Sulima), Organizational (ARC, PRG with sub-labels Newsletter/PRG Bumpf/PRG To Do/Webgranny, Tomahawk), Business (Amazon, Business with sub-labels SEO/Tools, Jobs, Lingua Ink, Taxes), Content/reference (Articles with sub-labels Business/SEO/Tools, Substack), Personal (KEEPERS, My Travel, Snoozed).

**Communication style constraints:** Warm but not sycophantic, professional but not corporate. No em-dashes. No AI-tell markers. Match Maya's energy — concise when quick, deep when architectural. Any draft must sound like a specific human, not a generic AI.

## Automation Requirements

### Smart Classification (beyond existing 48 filters)
- **Check labels before acting:** Before applying any label, check whether Google filters have already labeled the message. Only apply labels to unlabeled messages. Two systems must not compete.
- Classify unfiltered inbound email by:
  - **Client/contact:** Match sender to known contacts in client-registry.yaml. Apply appropriate Gmail label if not already applied by Google filters.
  - **Context:** Infer topic (publishing, consulting, organizational, personal, job search) from content and sender.
  - **Priority:** Flag urgent items — client deadlines, meeting requests, invoice questions, time-sensitive organizational communications.
  - **Newsletter collection:** Auto-label PRG-relevant emails as "PRG/Newsletter" when they arrive at stephbairey@gmail.com from known granny senders (members frequently bypass grannynewsletter@gaggle.email) — only if not already labeled.
- Do NOT replace, duplicate, or override existing 48 Google filters. SL operates only on messages they miss.

### Identity-Aware Reply Drafting
- Determine correct Send-As identity for reply based on:
  1. Which address received the inbound (auto-selects for replies)
  2. For new compositions: match recipient to known contacts and select identity per the routing table in identities.md
  3. Relationship override: if a contact historically receives email from a specific identity, maintain that consistency
- Select correct voice profile from identities.md for the reply context
- Apply the AI tells blacklist and em dash rules for the selected voice
- Present draft for Maya's review — never auto-send

### PRG Newsletter Support
- Throughout the week: identify emails from PRG members containing newsletter-worthy content
- Label with "PRG/Newsletter" for Maya's Thursday compilation
- Handle the known technical issue: multipart/related emails (embedded images) return empty bodies through Gmail API. Flag these for Maya to paste content manually.

### Daily Digest
- Morning summary of overnight email: grouped by label, flagging priority items
- Highlight: client emails needing response, upcoming meeting-related messages, newsletter items collected

## Edge Cases & Constraints
- **Identity override is relationship-based, not rule-based.** Some contacts know Maya by a name that doesn't match strict role logic. Automation must learn from reply history, not just apply the routing table.
- **PRG bypass pattern.** Grannies frequently email stephbairey@gmail.com directly instead of using grannynewsletter@gaggle.email. Automation must accommodate this.
- **No auto-send.** All drafted replies must be reviewed by Maya before sending. No exceptions.
- **Em dash rules vary by identity.** PRG (banned), job search (banned), LIB online (banned). Other contexts: permitted only as mid-sentence parentheticals.
- **Legacy addresses.** scb.zombie@gmail.com and webgranny@bairey.com are legacy but still receive forwarded mail. Don't treat them as errors.
- **gaggle.email moderation.** PRG newsletter goes through moderation (magic link login at gaggle.email). Automation cannot bypass this — it's a mailing list feature.

## Implementation Notes

### Gmail API
- **Hub account:** stephbairey@gmail.com
- **Scope required:** `gmail.modify` (read, label, draft), `gmail.send` (for Send-As functionality)
- **OAuth:** Must authenticate as stephbairey@gmail.com
- **Rate limits:** Gmail API default quotas (250 units/user/second)

### Send-As Identity Configuration
All 17 identities documented in `data/email-identities.yaml` with:
- Address, display name, reply-to
- SMTP server, port, TLS/SSL setting
- Identity context (steph-bairey, maya-bairey, lingua-ink, prg, arc-tda)
- Status (active vs. legacy)

### Label IDs
Gmail labels need to be resolved by name → internal ID at runtime. The 27 label names are in `data/email-identities.yaml`. Some have sub-labels using `/` notation (e.g., `PRG/Newsletter`, `Business/SEO`).

### Voice Profile Selection
Map identity_context to voice profile:
- `steph-bairey` → Job Search / LinkedIn voice (formal) or default Steph voice
- `maya-bairey` → Maya Personal voice
- `lingua-ink` → LIB or LIM voice depending on domain (linguaink.com = LIB, linguainkmedia.com = LIM)
- `prg` → PRG Newsletter voice
- `arc-tda` → ARC/TDA Governance voice

### Key Contact → Label Mapping
From client-registry.yaml and email-identities.yaml:
- Sulima Malzin → "Sulima" label
- Lynn Haller → "Lynn" label
- Nicole Dalton → "Nicole" label
- Devon Ervin → "Devon" label
- Daniela Morescalchi → "Daniela" label
- Carolyn Martin → "Carolyn" label
- PRG members → "PRG" or sub-labels
- ARC/TDA → "ARC" or "Tomahawk" labels

## Resolved Questions
- **Gmail API OAuth credentials:** Will be provided during SL setup.
- **Daily digest format:** Dashboard. (Note: a unified dashboard system is emerging across multiple domains — email digest, revenue, consignment tracking. SL should consider a shared dashboard infrastructure.)
- **Contact history for identity learning:** Scan by number of recent replies (not date range), since some contacts are emailed frequently and others rarely. This ensures both high- and low-frequency contacts get adequate history.
- **Filter export:** Yes. Export and document the existing 48 filters as part of SL configuration.
