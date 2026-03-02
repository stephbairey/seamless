# Domain Plan: Brand Codification

## Purpose
Ensure every piece of SL-generated text uses the correct voice, identity, visual brand, and formatting rules for its context. Automate identity routing (Steph vs. Maya), voice selection, em dash enforcement, and AI tells filtering. Prevent brand contamination across contexts.

## Inputs
- knowledge/identities.md — Seven voice profiles, identity routing table, universal rules, AI tells blacklist
- data/client-registry.yaml — Per-client identity, brand, brand colors, fonts, em dash rules
- extraction/brand-identity/voices-personas.md — Source-level voice extraction with citations
- extraction/brand-identity/visual-identity.md — Color palettes, typography, imagery guidelines, positioning

## System Overview
Maya operates seven+ distinct voices across different contexts. The correct name, title, email, tone, vocabulary, and formatting rules must be selected automatically based on the target context. The system currently lives entirely in Maya's head and in scattered style guides.

**Identity routing:** "Steph Bairey" for LIM, job search, PRG, ARC/TDA. "Maya Bairey" for LIB, bairey.com, author work, Writing with Maya. Ghost-writing (Nicole Dalton) uses the client's name entirely. This is non-negotiable.

**Voice selection:** Each context has a defined register, from intimate/confessional (Maya Personal) to deliberately impersonal/procedural (ARC/TDA Governance). Voice rules include vocabulary preferences, sentence rhythm, pronoun usage, and visual vocabulary.

**Em dash enforcement:** The single most enforced mechanical rule. Three modes: (1) permitted only as mid-sentence parentheticals, (2) banned entirely (PRG, job search, LIB online, Devon Ervin), (3) not applicable (ARC governance uses no personality markers at all).

**AI tells filtering:** A vocabulary and pattern blacklist that applies across all voices. Specific banned words (delve, tapestry, multifaceted, vibrant, etc.) and banned patterns (negative parallelisms, tailing -ing clauses, uniform paragraph length, promotional enthusiasm). The test: "Does this sound like me?" not "Does this sound like AI?"

**Visual brand:** Each context has defined colors, typography, and imagery guidelines. LIB (Charcoal/Light Gray/Brick Red, Bitter/Domine), LIM (Deep Wine/Warm Gold), Maya Personal (Dark Blue/Accent Blue/Beige, Montserrat/Christmas Shine/Cosmic Lemonade), Writing with Maya (Blue/Beige/Gold/Dark Blue), PRG (Red #bf3434, coral-red/darker-red newsletter), Devon Ervin (deep blue/teal/warm sand, Questrial/Work Sans), Lynn Haller (lavender #a78fbf, Merriweather Sans).

## Automation Requirements

### Identity Router
- Given a task context (client, project, platform, audience), automatically determine:
  - **Name:** Steph Bairey or Maya Bairey (or client name for ghost-writing)
  - **Title:** Principal, Creative Director, Author, ARC Chair, Tech granny, Web Granny, or none
  - **Email:** Which Send-As address from the 17 available
  - **Voice profile:** Which of the 7+ voices to use
- Routing table (from identities.md):

| Context | Name | Title | Email | Voice |
|---------|------|-------|-------|-------|
| LIM client work | Steph Bairey | Principal | steph@linguainkmedia.com | LIM |
| LIB publishing/blog (public) | Maya Bairey | Creative Director | maya@linguaink.com | LIB |
| LIB business/clients | Steph Bairey | Founder | steph@linguaink.com | LIB |
| Author / personal brand | Maya Bairey | Author | maya@bairey.com | Maya Personal |
| Writing with Maya | Maya Bairey | — | maya@bairey.com | Writing with Maya |
| Job search / LinkedIn | Steph Bairey | Director of Content Strategy | steph@bairey.com | Job Search |
| ARC/TDA governance (association) | Steph Bairey | ARC Chair | steph.bairey.arc@tomahawkdestiny.com | ARC/TDA |
| TDA website (business) | Steph Bairey | Principal | steph@linguainkmedia.com | LIM |
| PRG / Raging Grannies | Steph Bairey | Tech granny | stephbairey@gmail.com | PRG |
| IRG | Steph Bairey | Web Granny | webgranny@gmail.com | PRG |
| Nicole Dalton content | Nicole Dalton | — | — | Nicole Dalton SEO |

- **Multi-context rule:** When Maya is speaking across context boundaries (e.g., promoting LIB content on personal social), the voice follows the speaker, not the subject. Maya promoting LIB = Maya Personal voice.

### Voice Profile System
Each voice profile encodes:
- **Register:** Tone and formality level
- **Pronoun rules:** "I" permitted (Maya Personal, Writing with Maya), "we" for company (LIB, LIM), "the committee" only (ARC/TDA)
- **Sentence rhythm:** Lyrical long + short punchy (Maya Personal), short paragraphs (Nicole), matter-of-fact (ARC)
- **Vocabulary:** Context-specific terms and phrasings
- **Avoids:** Per-voice restrictions beyond the universal blacklist

Voice selection method: **inferred from task metadata** (Project field in ClickUp, email recipient, platform), with **Maya override in the moment**. Never auto-select without allowing override.

### Em Dash Enforcement
Three modes, checked per-context:

| Mode | Contexts | Rule |
|------|----------|------|
| Restricted | Maya Personal, LIB (print), LIM | Permitted ONLY as mid-sentence parentheticals. Never to extend a thought at end of sentence. Discouraged overall. |
| Banned | PRG, Job Search, LIB (online), Devon Ervin | Zero em dashes. Remove all instances. |
| N/A | ARC/TDA Governance | No personality markers at all, so em dashes would be out of character regardless. |

Enforcement mechanism: **warning** (not hard block, not auto-fix). Flag em dash violations and let Maya decide.

### AI Tells Filter
Applied to all SL-generated text as a post-generation quality gate.

**Banned vocabulary (18 words):** delve, tapestry, multifaceted, vibrant, bustling, pivotal, groundbreaking, underscore (as verb for inanimate subject), highlight (same), foster, cultivate, leverage, furthermore, moreover, in essence, "it's important to note," rich cultural heritage, enduring legacy.

**Banned patterns (12):** Negative parallelisms ("It's not X, it's Y"), tailing -ing clauses, uniform paragraph length, uniform sentence rhythm, problem-solution formulas, anaphora, staccato parallel structures, promotional enthusiasm, importance inflation, emotional hollowness, weasel wording, false ranges.

**Implementation:** Both embedded in system prompts (prevent generation) AND post-generation check (catch what slips through). Per Maya's design decision.

**Enforcement:** Warning. Flag violations with specific text highlighted and suggested alternatives. Maya makes the final call.

### Visual Brand Token System
Stored as a design system for use in generated assets (social media graphics, documents, web content):

| Context | Primary Colors | Typography | Imagery |
|---------|---------------|------------|---------|
| Maya Personal | #275988, #6CC9EA, #E0CBA4, #F2F2EB, #031521 | Montserrat, Christmas Shine, Cosmic Lemonade | Abstract impressionist, impasto, blue and beige |
| Writing with Maya | #2B75B9, #F2F2EB, #EFC469, #15415F | Montserrat, Christmas Shine, Cosmic Lemonade | Hands writing, coffee steam, rain on windows |
| LIB | #484C53, #F3F3F3, #CC302B | Bitter, Domine | Half-tone black and white |
| LIM | #722F37, #C5A55A | Bitter, Domine | Corporate editorial |
| PRG Newsletter | #d6616c, #bd3435 | Helvetica Neue, Helvetica, Arial | — |
| PRG Brand | #bf3434 | — | — |
| Devon Ervin | #4c6e90, #57a8b9, #d4c2b5, #faf8f5 | Questrial, Work Sans | calm ocean/beach/coastal |
| Lynn Haller | #a78fbf | Merriweather Sans | Dreamy bokeh Hasselblad, shallow depth-of-field |
| ARC/TDA | — | Aptos Display (ARC docs), Playfair Display (TDA letterhead) | — |

## Edge Cases & Constraints
- **Identity routing is non-negotiable.** Wrong name in wrong context is a critical failure. If unsure, ask Maya.
- **Relationship override.** If a contact knows Maya by a name that doesn't match strict role logic, the relationship name wins. This requires learning from history, not just rule application.
- **Writing with Maya sign-off is sacred.** "I'm Maya. Keep writing." — never vary, never omit, never rephrase.
- **PRG uses "Steph."** Grannies know her as Steph, not Maya. This is consistent even though PRG is a volunteer/community context that might seem "Maya-like."
- **Ghost-writing is complete identity suppression.** Nicole Dalton content uses Nicole's name, Nicole's voice, Nicole's brand. Maya doesn't exist in that context.
- **Em dash rules are context-sensitive, not global.** A single piece of text can have different em dash rules depending on where it will be published. The same LIB content might allow em dashes in print but ban them online.
- **AI tells blacklist applies universally and is strictly enforced.** No sensitivity variation by context — all SL-generated text gets the same rigorous check.
- **Visual brand colors supersede older references.** If any style guide conflicts with the token table above, the token table (from Phase 3 extraction) is authoritative.

## Implementation Notes

### Voice Profile Data Structure
Each voice profile can be represented as a structured object:
```yaml
voice_id: maya-personal
register: intimate, confessional, sensory
pronouns: ["I", "you"]
em_dash_mode: restricted
sentence_rhythm: "lyrical long sentences with sensory detail, interrupted by short punchy truths"
avoids: ["sentimentality", "uniform paragraph length", "promotional enthusiasm", "tailing -ing clauses"]
sign_off: null
context_triggers: ["bairey.com", "personal blog", "Maya Bairey author"]
```

### AI Tells Blacklist Implementation
Two-layer approach per Maya's design decision:
1. **System prompt layer:** Include blacklist in every content-generation prompt. Reference `knowledge/identities.md` "AI Tells Blacklist" section.
2. **Post-generation layer:** Regex/pattern matching on output text. Flag matches with line number and suggested alternative.

### Midjourney Prompt Template (Maya Personal)
```
an abstract impressionist painting of [subject], impasto, blue and beige,
[angles, shot distance, vibe] --ar 16:9
```

### ARC Board Report Format
- One page maximum
- Aptos Display 11pt
- Sections: Membership, Completed, In Progress, Upcoming, Support Needed
- No "I" — use "the committee" or collective voice
- No loaded language (especially in enforcement contexts)

### Writing with Maya Video Format
- [0-1 sec] text branding
- [1-3 sec] hook
- [4-45 sec] content (problem → solution)
- [45-55 sec] CTA
- [55-60 sec] sign-off: "I'm Maya. Keep writing."

## Resolved Questions
- **Voice profile storage:** YAML config files.
- **AI tells filter sensitivity:** Strictly enforced regardless of context. No configurable sensitivity levels.
- **Client-specific voice profiles (Nicole, Devon):** Standalone voice profiles. These will be less used (or not used) once those projects complete, so keeping them separate avoids polluting core voices.
- **New client with no established voice profile:** Prompt Maya to define. Do not default to LIM or any existing voice.
