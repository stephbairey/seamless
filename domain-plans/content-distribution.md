# Domain Plan: Content Distribution

## Purpose
Automate content distribution across Maya's multi-platform presence. Reduce the manual effort of cross-posting, format adaptation, and social media management. When a revenue-generating product is ready, this pipeline should be ready to promote it.

## Inputs
- knowledge/identities.md — Voice per platform, identity routing
- knowledge/rhythms.md — Content cadences, active vs. dormant platforms, priority assessment
- data/client-registry.yaml — Client-specific distribution requirements (Sulima, Nicole, Devon)
- extraction/content-marketing/workflows.md — Production pipelines, platform inventory, editorial rules

## System Overview
Maya maintains content across multiple brands and platforms, each with different voice, format, and audience requirements.

**Top priority: Writing with Maya (WwM).** Two distribution formats:
- **9:16 video shorts** — same video to Facebook Stories, Instagram Reels, TikTok, YouTube Shorts
- **16:9 longform** — "Write with Maya" lofi videos on YouTube
- Distribution: video channels first, then amplification on *every* other channel
- WwM automation is ideal but some manual intervention expected
- Maya's face is required for WwM branding — it's a trust signal
- Genre cohorts share Maya's branding/distribution under the WwM umbrella

**Active content production (March 2026):**
- LIB blog (linguaink.com) — ~monthly, 800-1000 words
- Maya personal blog (bairey.com) — companion piece to LIB post, ~monthly
- PRG newsletter — weekly, HTML via gaggle.email (good SL automation candidate)
- Sulima's Light Waves blog — ~2x/month, multi-platform (WordPress → MailPoet → Substack → Facebook). Already as automated as it can be.
- Social media — auto-distributes on post publish (Instagram → Threads, Pinterest, lnk.bio)

**In planning:**
- Writing with Maya video pipeline (ElevenLabs + Midjourney + Filmora + Submagic)
- YouTube channels (mayabairey, LIB) — created but no content yet

**On hold:**
- Paid cohort, active social media strategy beyond auto-distribution

**Platform inventory:**
- Active: Facebook (3 accounts), Instagram (2) → Threads, LinkedIn (2), Pinterest, lnk.bio
- YouTube: 2 channels, no content
- Dormant: Twitter, TikTok, Mastodon, BlueSky

**Content priority reality (March 2026):** Maya needs a product to promote first. Most marketing is on hold until a revenue-generating product (Gentle Guide, paid cohort, genre cohorts) is ready. Building something to sell takes precedence over promoting.

## Automation Requirements

### Blog Cross-Distribution Pipeline
When a blog post publishes on linguaink.com (LIB) or bairey.com (personal):
1. **Auto-distribute to existing channels:** Pinterest and lnk.bio already auto-update on publish — don't break this.
2. **Generate social media posts per platform:**
   - Facebook: topic-first, short, first-person, end with URL + engagement question. Use Maya Personal voice for bairey.com, LIB voice for linguaink.com.
   - Instagram: same as FB + 4-8 hashtags + "Link in bio, always." → auto-posts to Threads.
   - LinkedIn: professional framing, Steph identity for LIM/job-relevant content, Maya for author/publishing content.
3. **Generate marketing package:**
   - SEO meta description (150-160 chars, lead with reader value)
   - Social copy per platform (FB, Instagram, LinkedIn)
   - Midjourney image prompt using established template (Maya Personal aesthetic)
4. **Companion post reminder:** When LIB blog publishes, remind Maya to write companion piece for bairey.com (and vice versa).

### PRG Newsletter Automation
The weekly PRG newsletter is confirmed as a good SL automation candidate:
1. **Content collection:** Throughout the week, monitor Gmail for emails labeled "PRG/Newsletter" or from known PRG members → stephbairey@gmail.com (bypass pattern)
2. **Draft compilation:** Assemble collected items into newsletter structure:
   - 12-14 items per issue
   - Priority ordering: action items first, then team/committee notes, then articles/shares, then Joana Kirchhoff rollup (always last unless PRG group action)
3. **HTML formatting:** Apply strict PRG newsletter format:
   - `div.items` container with inline styles
   - Title/headline color: `#d6616c`
   - Header color: `#bd3435`
   - Paragraph breaks: `<br/>\n<br/>`
   - Links: `&raquo;` prefix with contextual text
   - Special characters: `&raquo;`, `&hellip;`, `&amp;` — NO em dashes
   - Table of contents headlines must exactly match body headlines
4. **Editorial judgment required:** Preserve contributor's exact voice, don't paraphrase personal shares, bold agenda topic headers, apply stale content rules. This step requires Maya's review.
5. **Distribution:** Maya pastes final HTML into Gmail → sends to granny-newsletter@gaggle.email → moderates/accepts the final send via gaggle.email magic link.
6. **Known technical issue:** multipart/related emails (embedded images) return empty bodies through Gmail API. Flag these for Maya to paste content manually.

### Sulima Light Waves Multi-Platform
Already as automated as it can be, but document the workflow for SL awareness:
1. Sulima writes → Maya publishes on WordPress (sulimamalzin.net)
2. **Video embed swap for email (1-3 videos per post):**
   a. Create publishable post with embedded YouTube videos
   b. Save the original HTML (with embeds)
   c. Replace each embedded video with a YouTube screenshot thumbnail linked via `<a>` to the video URL — email clients (MailPoet included) cannot render embedded videos
   d. Publish the screenshot-link version
3. MailPoet sends email notification to subscribers (pulls from published post)
4. **After email sends:** Replace the post HTML with the original embedded-video version and republish — the live website version should have real embeds
5. Substack import: Settings → Import posts, feed URL uses fivefilters.net full text feed converter
6. Post-import cleanup: remove "ad free" footer, replace with original publication link, add BuyMeACoffee boilerplate
7. Facebook posting (manual)
8. Preserve Sulima's formatting preferences: heavy bold, informal contractions

### Writing with Maya Video Pipeline (Future)
Not yet active, but documented for SL readiness:
1. **Script:** From 28 pre-written scripts or new content
2. **Audio:** ElevenLabs voice clone narration
3. **Visual:** Midjourney B-roll images with Ken Burns effect
4. **Edit:** Filmora assembly
5. **Captions:** Submagic
6. **Distribute (Tier 1):** YouTube Shorts, TikTok
7. **Distribute (Tier 2):** Instagram Reels, Facebook Reels
8. **Amplify:** All other channels with adapted copy
9. **Email:** Weekly Substack email with embedded video + 300-500 word expansion
10. **Sign-off:** Every video ends with "I'm Maya. Keep writing."

Hashtag strategy: Core (#WritingTips #WritingCommunity #AmWriting) + platform-specific + rotating by content type.
Best posting times: 12-4pm PT weekdays.

### Nicole Dalton SEO Content Distribution
Website-focused, not social-first:
1. Structure article per required format (hook → quick answers → scene-setting → case example → Nicole's take → steps → testimonial → CTA)
2. HTML cleanup: wrap in `<section class="wrapzone">`, clean `<h2>` headings
3. Schema: unified JSON-LD @graph
4. Internal linking: every article includes contextual links within Dalton site cluster
5. Publish to Dalton Law Office website

### Devon Ervin Event Pages
1. Event sales pages via Eventin Pro + PayPal + Zoom
2. WordPress/Enfold/Avia theme — no staging, work on live site
3. Brand: #4c6e90 deep blue, #57a8b9 teal, #d4c2b5 warm sand, Questrial/Work Sans
4. Em dashes banned

## Edge Cases & Constraints
- **Voice varies by platform AND brand.** Instagram post for LIB is LIB voice; Instagram post for Maya personal is Maya Personal voice. Same platform, different brand, different voice.
- **PRG newsletter is not fully automatable.** Editorial judgment (ordering, stale content rules, contributor voice preservation) requires Maya's review. SL can draft, Maya finalizes.
- **Sulima's Substack import requires fivefilters.net converter** and manual cleanup. The RSS-to-Substack path has friction that may not be eliminable.
- **Writing with Maya sign-off is sacred.** "I'm Maya. Keep writing." — never vary across any platform.
- **Auto-distribution channels (Instagram → Threads, Pinterest, lnk.bio) already work.** Don't break them. Don't duplicate their function.
- **Genre cohort model is new and unbuilt.** May create new distribution needs when launched. Under Maya's branding/distribution, 50/50 split.
- **Maya is overwhelmed by multi-brand social presence.** Automation should reduce cognitive load, not add more channels to manage. Consolidate where possible.
- **Product-first, marketing-second.** Current priority is building revenue products, not expanding distribution. SL should be ready when the product launches, not push marketing prematurely.
- **TikTok API access is restricted.** Comment automation planned but may not be feasible depending on API availability.
- **Later (social scheduling) is configured but not actively used.** Could be activated when content volume increases.

## Implementation Notes

### Platform API Requirements
- **Facebook Graph API:** 3 pages (Maya personal, Maya Author, LIB). Posting, scheduling.
- **Instagram API:** 2 accounts (mayabairey, LIB). Instagram → Threads auto-posts (don't duplicate).
- **YouTube Data API:** 2 channels (mayabairey, LIB). Upload, metadata, thumbnail.
- **LinkedIn API:** 2 profiles (stephbairey, LIB). Post creation.
- **TikTok API:** Restricted access. May need to use manual upload or third-party tool.
- **Pinterest API:** Auto-posts on publish already work.
- **Gmail API:** For PRG newsletter distribution via gaggle.email.
- **WordPress REST API:** For blog publishing hooks and content retrieval.
- **WooCommerce REST API:** For product sales data (Writing with Maya templates).

### Active Social Accounts
| Platform | Account | Brand | Identity |
|----------|---------|-------|----------|
| Facebook | Maya Bairey (personal) | Personal | Maya |
| Facebook | Maya Bairey, Author | Author | Maya |
| Facebook | Lingua Ink Books | LIB | Maya |
| Instagram | mayabairey | Author | Maya |
| Instagram | linguainkbooks | LIB | Maya |
| LinkedIn | stephbairey | Professional | Steph |
| LinkedIn | Lingua Ink Books | LIB | Maya/Steph |
| Pinterest | mayabairey | Author | Maya |
| YouTube | mayabairey | Author | Maya |
| YouTube | Lingua Ink Books | LIB | Maya |
| lnk.bio | mayabairey | Author | Maya |

### Newsletter Infrastructure
- **MailPoet:** ~600 subscribers (Maya Bairey author audience). WordPress plugin on bairey.com. No segmentation.
- **gaggle.email:** PRG distribution lists. 8 lists managed by Maya:
  - prg-members@gaggle.email (main)
  - grannynewsletter@gaggle.email (submissions)
  - granny-newsletter@gaggle.email (distribution)
  - prg-enviro-team, prg-gender-team, prg-rij-team, prg-social-team, prg-gagh (sub-groups)
- **Substack:** Maya Bairey + Sulima Malzin. Blog post republishing.

### PRG Newsletter HTML Template Reference
Full style guide: `sources/drive-files/portland-raging-grannies-style-guide.md`
Key format rules:
- Container: `<div class="items">` with inline styles
- Headline color: `#d6616c`
- Header color: `#bd3435`
- No em dashes (use `&hellip;` for ellipsis, `&raquo;` for link indicators)
- ToC headlines must exactly match body headlines

## Resolved Questions
- **First product to launch:** Writing with Maya — PDF templates ($12 each / $39 bundle) + video content pipeline. See `sources/prior-work/Handoff_Writing_with_Maya_2026-02-27.md` for full product details.
- **Channel priority for promotion:** Video channels first (YouTube, TikTok), then large social platforms with older audiences (Facebook, Instagram).
- **WwM video pipeline automation level:** As automated as possible.
- **Sulima's Substack import:** As automated as it can be. No further automation needed.
- **Genre cohort distribution:** Cohorts will share Maya's channels, not have their own social presence.
- **Comment automation:** Human-in-the-loop.
