# Automation Policies
# Consolidated safety boundaries, privacy rules, and operational constraints for SL
# Sources: domain plans, identities.md, conventions.md, agent designs

## 1. No Auto-Send / No Auto-Post

All outbound communication requires Maya's explicit review and approval before sending.

- **Email:** Never auto-send. All drafted replies presented for review. No exceptions.
- **Social media:** Never auto-post. All generated content presented for approval.
- **PRG newsletter:** Maya pastes final HTML into Gmail and sends manually. gaggle.email moderation (magic link) cannot be bypassed.
- **Royalty reports:** Semi-automated. SL generates, Maya reviews before sending to authors.
- **Comment automation:** Human-in-the-loop.

**Why:** Maya's reputation depends on every message sounding like her, not like AI. One wrong-name email or off-voice post could damage client trust.

## 2. Identity Routing Is Non-Negotiable

Wrong name in wrong context is a critical failure.

- **Steph Bairey:** LIM client work, job search, PRG, ARC, LinkedIn.
- **Maya Bairey:** LIB publishing, bairey.com, author work, Writing with Maya, creative contexts.
- **Ghost-writing:** Complete identity suppression. Nicole Dalton content uses Nicole's name, voice, and brand. Maya does not exist in that context.
- **Relationship override:** If a contact knows Maya by a particular name, that name sticks even if the conversation crosses domain boundaries. Learned from history, not just rules.
- **PRG exception:** Grannies know her as Steph, not Maya, even though PRG is a community/volunteer context that might seem "Maya-like."
- **TDA dual role:** ARC governance uses Steph/ARC Chair via steph.bairey.arc@tomahawkdestiny.com. TDA website work uses Steph/Principal via steph@linguainkmedia.com. Same people, different capacity.

**Reference:** Full routing table in identities.md and brand-codification.md.

## 3. AI Tells Blacklist — Strictly Enforced

Applied universally to all SL-generated text. No sensitivity variation by context.

**Banned vocabulary (18 words):** delve, tapestry, multifaceted, vibrant, bustling, pivotal, groundbreaking, underscore/highlight (as verbs for inanimate subjects), foster, cultivate, leverage, furthermore, moreover, in essence, "it's important to note," rich cultural heritage, enduring legacy.

**Banned patterns (12):** Negative parallelisms ("It's not X, it's Y"), tailing -ing clauses, uniform paragraph length, uniform sentence rhythm, problem-solution formulas, anaphora, staccato parallel structures, promotional enthusiasm, importance inflation, emotional hollowness, weasel wording, false ranges.

**Enforcement:** Two-layer approach:
1. System prompt layer — include blacklist in every content-generation prompt.
2. Post-generation layer — regex/pattern matching on output text. Flag violations with specific text and suggested alternatives.

**The test:** "Does this sound like me?" — not "does this sound like AI?"

**Reference:** Full blacklist in identities.md.

## 4. Em Dash Rules

The most enforced formatting rule. Context-sensitive, not global.

| Mode | Contexts | Rule |
|------|----------|------|
| Restricted | Maya Personal, LIB (print), LIM | Permitted ONLY as mid-sentence parentheticals. Never to extend a thought at end of sentence. |
| Banned | PRG, Job Search, LIB (online), Devon Ervin | Zero em dashes. Remove all instances. |
| N/A | ARC/TDA Governance | No personality markers at all. |

**Enforcement:** Warning — flag violations and let Maya decide. Not a hard block, not auto-fix.

## 5. Peterday

Saturdays are no-work days. Sacred.

- Never create or suggest work events on Saturday.
- Never schedule tasks, meetings, or deadlines for Saturday.
- Named for Pete (Maya's husband of 35 years).

## 6. Sacred Sign-Offs and Language

- **Writing with Maya:** "I'm Maya. Keep writing." — never vary, never omit, never rephrase. Ends every video, every WwM piece.
- **PRG newsletter:** Preserve contributors' exact voices. Never paraphrase personal shares. Preserve political language ("fascist violence" stays — don't sanitize).
- **PRG newsletter format:** ToC headlines must EXACTLY match body headlines.

## 7. Approach Field (ClickUp)

The Approach field is an emotional energy metric tied to the Zeigarnik effect. It is structural, not decorative.

- Always ask Maya for her Approach value on new tasks.
- Never infer emotional state from task content.
- If Maya doesn't respond, default to "Indifferent" rather than blocking task creation.
- Never auto-populate, predict, or skip.

## 8. ClickUp Status Management

- Never auto-advance task status. Update only on Maya's instruction.
- Support bulk updates when Maya requests them.
- Flag overdue "Not Started" tasks for awareness.

## 9. Voice Profile Matching

Voice varies by platform AND brand. Same platform, different brand = different voice.

- Voice selection inferred from task metadata (ClickUp Project field, email recipient, platform).
- Maya can override in the moment. Never auto-select without allowing override.
- Client-specific voices (Nicole Dalton, Devon Ervin) are standalone profiles, not extensions of core voices.
- New clients prompt Maya to define a voice profile.

**Reference:** Seven voice profiles documented in identities.md. Voice profile storage: YAML config files.

## 10. Secrets Management

- API credentials, OAuth tokens, and passwords stored in `secrets.env` (gitignored).
- `secrets.env.example` (committed) documents what credentials are needed.
- Never store secrets in CLAUDE.md, committed config files, or output documents.
- Domain plans reference credentials as "to be provided during SL setup."

## 11. Client Confidentiality

- Client relationship details, rates, and contract terms are operational data for SL's use, not for external sharing.
- Ghost-writing clients (Nicole Dalton): Maya's involvement is never visible in the output.
- Daniela Morescalchi: ClickUp and internal systems use her real name, not her pen name (Wren Cavanagh).
- Sulima's arrangement (no contract, 0% royalty split) is intentional and informal. Do not flag as an error.

## 12. Existing Systems: Don't Break, Don't Duplicate

- **Gmail filters:** 48 existing filters are the base layer. SL operates only on messages they miss. Check labels before acting — two systems must not compete.
- **Auto-distribution channels:** Instagram → Threads, Pinterest, lnk.bio already work on publish. Don't break them, don't duplicate their function.
- **ClickUp saved views:** Maya has extensive dashboards, list/table/calendar views, and per-client views. SL must not create conflicting views.
- **ClickUp architecture:** Single list. No folders, no spaces, no multi-list workflows. No checklists.

## 13. Graceful Degradation

- When uncertain, catch and queue for review rather than failing or guessing.
- Unsorted folders are emotional infrastructure — reassurance that nothing is lost. Never remove, never skip, never treat as error.
- Tag order doesn't matter in file routing (alphabetical sort before lookup).
- Local-first, cloud-backed. Prefer systems that work while Maya sleeps.

## 14. Cognitive Load

- Maya is overwhelmed by multi-brand social presence. Automation should reduce cognitive load, not add complexity.
- Product-first, marketing-second. Don't push marketing before there's something to sell.
- Systems serve psychological functions too. ClickUp is external memory. The Unsorted folder is reassurance. Don't optimize away the emotional functions.

## 15. Infrastructure Scope

- SL runs on Maya's office computer (primary workstation) or cloud as needed.
- SL manages n8n (Docker, on office computer). n8n is the free Docker version, not n8n.io cloud.
- Media Server (self-hosting, Jellyfin) is out of SL scope.
- Household local dashboard (passive display, downstairs mini-PC) is out of SL scope.
