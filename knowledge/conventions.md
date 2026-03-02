# Conventions

Reference document for naming rules, formatting preferences, and operational patterns across Maya's systems.

## Identity Routing

The most important convention. Maya operates under multiple identities, and every system respects this distinction.

**Two-axis model:**
- **Name axis:** Steph = business, operations, technical, government-name contexts. Maya = creative, author, writing community.
- **Domain axis:** Which organization. bairey.com (personal), linguaink.com (publishing), linguainkmedia.com (marketing/coding), tomahawkdestiny.com (moorage), lynnahaller.com (client), raginggrannies (PRG/IRG).

**Decision rule for new compositions:** "What hat am I wearing?" Relationship history can override strict role logic — if a contact knows Maya by a particular name, that name sticks even when the conversation crosses domains.

**Reply behavior:** Gmail auto-sends from whichever address received the inbound message. No manual switching needed for replies.

## ClickUp Conventions

**Task names:** Start with a lowercase verb. Short and actionable. Examples: "review song librarian job description from Vicki," "create PRG newsletter," "sync calendar."

**Due dates:** Always set. Never left blank.

**Descriptions:** Optional. Used for meeting notes, zoom links, addresses, and post-meeting notes. Not usually for task specs.

**Checklists:** Not used.

**Custom fields:** All six are required on every task. See `data/clickup-fields.yaml` for exact values.

**Status flow:** Not Started → Begun → Complete is the typical path. On Hold and Waiting are parking states. Scratch is for abandoned tasks.

**The Approach field:** Dread, Reluctant, Indifferent, Interested, Excited. This is a genuine emotional energy metric, not decorative. It tracks how Maya feels about doing the work. The Zeigarnik effect (unfinished tasks creating cognitive burden) is a real factor in Maya's task management — the Approach field helps make that visible.

## File Naming & Tagging

**TagSpaces format:** Up to 2 bracketed tags appended to filenames. Tags embedded in the filename, not in metadata. Examples:
- `document[Cover Painting-Celia].pdf`
- `image[Newsletter].png`
- `file[Source Asset].docx`

**Symmetry rule:** Tag order in the filename doesn't matter for routing. The n8n workflow alphabetically sorts tags to create a canonical key. `[Cover Painting-Celia]` and `[Painting-Celia Cover]` route to the same destination.

**Client tag behavior:** The client tag (Lynn, Maya, Sulima) is stripped from the routing key because the intake folder already encodes client identity. It serves as searchable redundancy.

## Calendar Naming

**Client meetings:** `ClientName and Steph @ Lingua Ink` for formal meetings created by Calendly (e.g., "Devon Ervin and Steph @ Lingua Ink"). `Client:Maya` for informal touchpoints (e.g., "Carolyn:Maya").

**Multi-person meetings:** `Name:Name:Name` format (e.g., "Eve:Lynn:Maya").

**Calendar selection for invites:** Follows the identity axis. If the contact knows Maya as Maya, the invite goes from mjbairey. If as Steph or Lingua Ink, from linguainkmedia.

**HoD:** Shorthand for Lynn Haller's book, *The Hallway of Doorknobs*.

## Email Labels

27 labels, organized by function:

**Client/relationship:** Authors, Carolyn, Cohort, Daniela, Devon, Lynn, Nicole, Sulima

**Organizational:** ARC, PRG (with sub-labels: Newsletter, PRG Bumpf, PRG To Do, Webgranny), Tomahawk

**Business:** Amazon, Business (with sub-labels: SEO, Tools), Jobs, Lingua Ink, Taxes

**Content/reference:** Articles (with sub-labels: Business, SEO, Tools), Substack, Jobs, Taxes

**Personal:** My Travel, Snoozed, KEEPERS

## Communication Style

**Voice principles (from multiple handoffs):**
- Conversational, direct, warm
- Prose over bullet points and headers
- No em-dashes
- Match her energy — concise when quick, deep when architectural
- Formatting only when it genuinely helps clarity

**In client communications:** Warm but not sycophantic, professional but not corporate.

**On AI tells:** Maya has strong opinions and a reference document about AI-generated text markers. Avoid: generic phrasing, promotional enthusiasm, hype language, em-dash overuse, anything that doesn't sound like a specific human.

## WordPress Conventions

**Admin accounts per site:**
- linguainkmedia.com: limadmin
- linguaink.com: limadmin (admin), Maya Editor (editorial posts), maya (auto-duplicated bairey.com posts)
- bairey.com: mjbadmin (admin), Maya (author)

**Blog cross-posting:** Posts on bairey.com auto-duplicate to linguaink.com under the "maya" account. Editorial/publishing posts on linguaink.com are authored by "Maya Editor."

**Plugin authorship:** Lingua Ink Media, https://linguainkmedia.com

## Work Rhythms

**Peterday:** Saturdays are no-work days.

**Work allocation:** Roughly 70% Lingua Ink Media client work, 30% Lingua Ink Books — but her passion is the publishing side.

**Work hours:** 50+ hours per week.

**PRG newsletter:** Weekly, Thursday mornings.

**Royalty reports:** Quarterly, 1st of January, April, July, October.

**Writing Cohort:** Twice weekly, Thursday and Sundays noon-2pm (canonical calendar: mjbairey).

## Design Principles

These show up consistently across Maya's systems:

1. **Graceful degradation over failure.** When uncertain, catch and queue for review rather than failing or guessing. (Unsorted folder is the canonical example.)

2. **Describe, don't organize.** Tag what something IS, let the system decide where it GOES.

3. **Local-first, cloud-backed.** Infrastructure runs locally in Docker. Cloud services are integration targets, not primary infrastructure.

4. **Persistence over convenience.** Prefer systems that work while she sleeps (n8n over Cowork).

5. **Systems serve psychological functions too.** The Unsorted folder is reassurance. ClickUp is external memory. Don't optimize away the emotional functions.
