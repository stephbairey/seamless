# PRG Newsletter: Rewrite & Format Handoff for Claude Code

This document covers the step Claude Code is stuck on: taking categorized, sorted email content and transforming it into finished HTML newsletter items. Everything before this step — collecting emails, categorizing, sorting — you apparently have handled. This picks up where that leaves off.

---

## What You're Producing

The output is a single self-contained HTML file that Maya pastes directly into Gmail and sends. It's not rendered in a browser; it goes through Gmail's email client, which is strict about rendering. Every style must be inline. Nothing can rely on external CSS. The structure must be exact.

The final file has:
1. A fixed **header block** (logo, date, next meeting info, footer boilerplate)
2. A **table of contents** listing all item headlines
3. An ordered series of **item cards** — one `div.items` per newsletter item
4. A **footer** with the newsletter submission address

---

## The HTML Architecture

### The Outer Shell

This never changes. Copy it exactly. Fill in the date and next meeting info.

```html
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Portland Raging Grannies Newsletter</title>
    <style>a{color:#0066cc;text-decoration:underline;}a:visited{color:#5b4ab1;}</style>
  </head>
  <body style="margin:0;padding:0;background:#E6E0E0;font-family:'Helvetica Neue', Helvetica, Arial, sans-serif;font-size:16px;line-height:1.2;color:#000;">
    <span style="display:none !important; opacity:0; color:transparent; height:0; width:0; overflow:hidden;">Portland Raging Grannies Newsletter - latest events, actions, and reminders</span>
    <table bgcolor="#E6E0E0" width="100%" cellspacing="0" cellpadding="0">
      <tr>
        <td>
          <div bgcolor="#E6E0E0" class="frame" style="max-width:650px;margin:20px auto;padding:0 40px 5px 40px;">

            <!-- HEADER + TOC BLOCK -->
            <div class="top-items" style="max-width: 650px;margin: 20px auto;background: #ffffff;border-radius: 6px;box-shadow: 0 0 6px rgba(0, 0, 0, .15);padding: 0 40px 40px 40px;">
              <div class="header" style="font-size:22px;font-weight:700;color:#bd3435;text-align:left;margin: 0px 0 28px 0;padding: 40px 0 0 0px;">
                <img src="https://portland.raginggrannies.org/wp-content/uploads/2025/06/prg-newsletter-logo.jpg" alt="Portland Raging Grannies Newsletter" width="570" height="100" border="0" style="display:block;">
                <br/>
                <center>NEWSLETTER - [DATE HERE e.g. FEBRUARY 26, 2026]</center>
              </div>
              <div class="subhead" style="font-size:18px;color:#555;line-height:1.3;margin:0 0 24px 0;text-align: center;"><strong>Next Monthly Meeting</strong>
                <br/>[Day, Month Date, Year, Time]
                <br/>Location: [Venue Name, Address]
                <br/>
                <br/><em style="font-size:13px;color:gray;">MENTORS: remember to forward this to your mentees!<br/>Long newsletters can be cut off on tablets/phones. For best results, read on desktop/laptop.</em>
              </div>

              <!-- TABLE OF CONTENTS -->
              <div class="toc" style="margin: 0 0 30px 0px;padding: 0;border-top: 3px solid #d6616c;line-height: 14px;">
                <p style="margin: 16px 0 16px 0px;padding: 0;font-size: 20px;color: #d6616c;">IN THIS NEWSLETTER</p>
                <br/>
                <ul style="margin: 0 0 0 0;">
                  <li style="list-style:disc;font-size:14px;font-weight:600;margin:0 0 8px 0;">[Headline of Item 1]</li>
                  <li style="list-style:disc;font-size:14px;font-weight:600;margin:0 0 8px 0;">[Headline of Item 2]</li>
                  <!-- one <li> per item, in same order as items appear below -->
                </ul>
              </div>
            </div>

            <!-- ITEM CARDS GO HERE — one div.items per item -->

          </div>
          <div class="footer" style="font-size:18px;color:#555;line-height:1.3;margin:0 0 24px 0;text-align: center;"><em>Send newsletter items to <a style="color:blue;" href="mailto:grannynewsletter@gaggle.email">grannynewsletter@gaggle.email</a></em></div>
        </td>
      </tr>
    </table>
  </body>
</html>
```

### One Item Card

Every newsletter item — no matter what type — lives inside this container. The container is a `div.items`. It has a `p.title` and a `p.body` inside it. That's it. These styles are hardcoded and never vary.

```html
<div class="items" style="max-width: 650px;margin: 20px auto;background: #ffffff;border-radius: 6px;box-shadow: 0 0 6px rgba(0, 0, 0, .15);padding: 0 40px 40px 40px;">
  <p class="title" style="font-size:20px;font-weight:700;color:#d6616c;margin:30px 0 6px 0;mso-margin-top-alt:30px;border-top:3px solid #d6616c;padding: 27px 0 27px 0;">Headline Here in Title Case</p>
  <p class="body" style="font-size:14px;font-weight:400;line-height:1.55;margin:0 0 6px 0;">From: First Last
    <br/>
    <br/>Body content here.
  </p>
</div>
```

Do not invent alternate containers, wrapper divs, or style variations. Every item uses exactly this.

---

## The Rewrite Step: What It Actually Means

This is where Claude Code got stuck, and it's the most judgment-intensive part of the job.

Each email in your categorized list needs to be **rewritten** for the newsletter — not just reformatted. The raw email text is often too long, too casual, written as if for a listserv, full of internal context, and/or contains information in the wrong order for a reader scanning a newsletter. Your job is to translate it into something a busy granny can read in 30 seconds and know exactly what to do.

### The Rewrite Varies Dramatically by Item Type

You have to detect what type of item you're dealing with and apply the appropriate treatment. Here's how each type works:

---

#### Type 1: Action Items and Event Announcements

These are the most common and most important items. Someone is announcing a rally, a hearing, a testimony opportunity, a training, a march.

**Your job:** Lead with the essential facts. What, when, where. Everything else follows.

**Structure:**
- First sentence: What the event is + when it is
- Second sentence or line: Location (full address — grannies need to put it in their GPS)
- Following content: What to bring, what to wear, how to RSVP, contact info
- If it's not an official PRG action, say so explicitly at the end: "This is not an official PRG action, but grannies are welcome to attend individually."
- Scannable details go on separate lines using single `<br/>` between them

**Example of what this looks like rendered:**
```
The ICE Out of Oregon rally is Saturday, February 22, at noon.

Location: Holladay Park, NE 11th &amp; Multnomah, Portland

What to wear: your PRG gear if you have it
What to bring: a sign, water

This is not an official PRG action, but grannies are welcome to attend individually.

» RSVP on Mobilize
```

**Key decisions for action items:**
- If the email has a date that's already passed by the time the newsletter goes out Thursday, **drop the item**
- If someone gives a deadline for RSVPs or testimony and the deadline is before Thursday, **drop it or check with Maya**
- If there are multiple dates mentioned in one email (e.g., "March 5 training, March 12 action"), keep them all clearly labeled

---

#### Type 2: Meeting Notes — Inline

Someone emailed their team's meeting notes directly in the email body. These get mostly **preserved as-is** — the informal tone is intentional and reflects the organization's culture.

**Your job:** Minimal rewriting. Format the structure, fix obvious typos, add `<strong>` tags to agenda topic headers so it's scannable. Otherwise leave it alone.

**Do not:** Clean up the language. Do not make it sound more formal. Do not summarize what they said. Reproduce it.

**Structure:**
```
Meeting date, time, platform
In attendance: [list of names]

[Agenda topic as <strong>bold header</strong>]
The body of that discussion, as written.

[Next agenda topic]
Etc.
```

**The `From:` attribution line:** Use whoever sent the notes. Usually a team lead.

---

#### Type 3: Meeting Notes — Attachment

If notes came as an attached file (PDF), Maya will have already uploaded it to the PRG website and will give you a URL. Use a short teaser-style treatment:

```
Title: Meeting Notes from the [Team Name] Team

From: [Sender]

Catch up with what the [Team Name] team discussed at their latest meeting.

» Read the meeting notes
```

One sentence. A link. That's all.

Spell out abbreviations: RIJ = Racial and Immigration Justice, GAGH = Grannies Against Gun Harm.

---

#### Type 4: Article or Video Shares

Someone is sharing an external piece of content — a Substack essay, a YouTube video, a news article, a speech transcript.

**Your job:** Write a 2–3 paragraph summary. The granny should be able to read your summary and understand what the piece is about, why it matters, and whether they want to click through.

**Structure:**
- **Paragraph 1:** Who made this, what it is, and why it exists. Context. Be specific — "Kelly Hayes delivered these remarks at a vigil for Renee Nicole Good, a 37-year-old mother shot and killed by an ICE agent in Minneapolis" is far better than "Kelly Hayes wrote about ICE violence."
- **Paragraph 2:** The core content. Pull a quote or two that are specific and visceral. Not "this is important" — something that shows the piece's actual argument or emotional register.
- **Paragraph 3 (optional):** Why it connects to the grannies' work. A one-sentence reflection. Keep it brief.
- End with a `» Read on Substack` or `» Watch the video` or whatever's specific to the link.

**Important:** You may need to fetch the URL to read the article if the email only sent a link. Do that.

**Attribution:** Use whoever submitted it, not the article author (unless they're the same person). The article author goes in the body copy.

---

#### Type 5: Personal Shares and Announcements

Someone is announcing their own event, sharing a personal reflection, inviting grannies to something personal (a performance, a birthday party, a farewell message).

**Your job:** **Do not rewrite.** Keep their exact words and phrasing. These work because they're genuine. Your only role is to put their text into the HTML structure correctly.

If you find yourself smoothing out their sentence rhythm or swapping their word choices for "better" ones, stop. This is not that kind of content.

**Attribution:** Whoever sent it. Their voice is the whole point.

---

#### Type 6: The Joana Kirchhoff Rollup (Compiled Items)

Joana Kirchhoff is the Environment Team lead and forwards a very high volume of content — often 5–8 items in a week. Most of it is nice-to-know: petitions, event flyers, articles from other organizations, action alerts.

**The threshold for a standalone item vs. rollup:** Does this item describe something PRG is doing as a group, or where members need to make a decision? If yes → standalone item earlier in the newsletter. If it's FYI — something an individual granny might choose to engage with but PRG isn't taking action on — it goes in the rollup.

**The rollup is always the last item in the newsletter.**

**Structure of the rollup:**
- Title: `From Joana Kirchhoff: Environmental Action Links` (or "Action Links &amp; Resources" if topics are broader than environment)
- No `From:` attribution line in the body (the name is in the title)
- One intro sentence: "Joana shares the following resources and action items for grannies interested in environmental issues."
- Each sub-item gets: a `<strong>` bolded title, one descriptive sentence, one `» link`
- Double `<br/>` between sub-items

```html
<div class="items" style="max-width: 650px;margin: 20px auto;background: #ffffff;border-radius: 6px;box-shadow: 0 0 6px rgba(0, 0, 0, .15);padding: 0 40px 40px 40px;">
  <p class="title" style="font-size:20px;font-weight:700;color:#d6616c;margin:30px 0 6px 0;mso-margin-top-alt:30px;border-top:3px solid #d6616c;padding: 27px 0 27px 0;">From Joana Kirchhoff: Environmental Action Links</p>
  <p class="body" style="font-size:14px;font-weight:400;line-height:1.55;margin:0 0 6px 0;">Joana shares the following resources and action items for grannies interested in environmental issues.
    <br/>
    <br/><strong>Name of Event or Resource - Date if applicable</strong>
    <br/>One sentence describing what this is and why a granny might care.
    <br/><a href="URL">&raquo; View the flyer</a>
    <br/>
    <br/><strong>Next Sub-Item</strong>
    <br/>One sentence.
    <br/><a href="URL">&raquo; Register for the event</a>
  </p>
</div>
```

---

## HTML Rules That Cannot Break

These are the things that will silently destroy the newsletter's formatting if you get them wrong.

### Paragraph Breaks

Between paragraphs, use `<br/>` on its own line, then another `<br/>` on its own line:

```html
First paragraph.
<br/>
<br/>Second paragraph.
```

**Not:** `<br/><br/>` on the same line (some email clients choke on this)  
**Not:** `<br />` with a space before the slash  
**Not:** `<p>` tags inside `p.body` (nesting block elements inside a paragraph tag is invalid)

### Special Characters

These must always be entities. Never use the raw character inside HTML:

| Character | Use this |
|-----------|----------|
| & | `&amp;` |
| » | `&raquo;` |
| … | `&hellip;` |
| — (em dash) | **Never use em dashes at all.** Replace with ` - ` |
| -- | Replace with ` - ` |

### Bold

Always `<strong>`, never `<b>`.

### Links

The `»` link at the bottom of each item:
```html
<br/>
<br/><a href="https://example.com">&raquo; Descriptive link text here</a>
```

Link text should be specific: `» Register on Eventbrite`, `» Read the meeting notes`, `» Watch the video`. Not `» Read more` if you can say something better. Not bare URLs.

Email addresses get `mailto:` links when they appear in body copy and grannies need to contact someone. But when Maya is listing team email addresses that grannies need to copy and paste (e.g., for distribution list management), display them as visible text:
```html
<a href="mailto:prg-enviro-team@gaggle.email">prg-enviro-team@gaggle.email</a>
```

### Attribution Line

Every item except the Joana rollup gets this at the top of `p.body`:
```html
From: First Last
<br/>
<br/>Content starts here...
```

Note: the sample template shows `<strong>From: Name</strong>` — **do not bold the From line**. The style guide and actual newsletters do not bold it. Plain text only.

### Headlines

- Title case: "Oregon Senate Hearing on HB 2001" not "Oregon senate hearing on HB 2001"
- No trailing punctuation
- The headline in `p.title` must exactly match the `<li>` in the table of contents — character for character

### The Table of Contents

One `<li>` per item, in the same order the items appear in the newsletter body:
```html
<li style="list-style:disc;font-size:14px;font-weight:600;margin:0 0 8px 0;">Headline Here</li>
```

No line breaks inside the `<li>` tag. No nested elements. Just the headline text.

---

## Item Ordering (What Goes First)

Your categorization step probably assigns items to buckets. Here's the priority order for what goes where in the newsletter, top to bottom:

1. **Meeting reminder / call for agenda items** — Only if the monthly meeting is within the next few days. This goes first.
2. **Major organizational news** — Team name changes, leadership transitions, anything every granny needs to know.
3. **Time-sensitive actions** — Events happening in the next 2–3 days. Rallies with imminent dates, testimony deadlines this week.
4. **Upcoming actions and events** — Things in the next few weeks requiring sign-up or planning. Sort sooner before later within this tier.
5. **Team meeting notes** — What teams have been discussing and deciding.
6. **Community events and performances** — Granny-adjacent events, shows, performances.
7. **Nice-to-know content** — Articles, videos, resources, inspirational shares.
8. **Joana Kirchhoff rollup** — Always last.

Within each tier, sooner dates go before later dates.

---

## Stale Content: Drop It

Before writing any item, check whether it's still timely:

- **Event already happened:** Drop it. Don't include it, don't mention it.
- **Deadline already passed:** Drop it, unless the underlying issue has ongoing action (a future hearing, an open comment period). If there's nothing actionable for the granny reading Thursday's newsletter, it doesn't go in.
- **Duplicate:** If two emails are about the same event, pick the better source and drop the other. Prefer the person with a direct connection to the event over someone who forwarded it.

---

## What the Finished Output Looks Like

When you're done, you have a single `.html` file containing:

1. The outer shell (doctype, head, body, table)
2. Inside the frame div: the header block (logo + date + next meeting + mentor reminder)
3. The table of contents block with one `<li>` per item
4. A series of `div.items` cards, one per newsletter item, in priority order
5. The footer div

The newsletter should render cleanly when you open the file in a browser. Maya will then select all (Cmd+A), copy, and paste into Gmail's compose window. Gmail will strip the `<head>` styles but preserve all inline styles — which is why every style is inline.

---

## The Quality Control Pass

Before delivering the file, run through this:

- [ ] Every `<br/>` is `<br/>` with no spaces, no capital letters, no missing slash
- [ ] Headlines in `p.title` exactly match `<li>` text in the TOC — character for character
- [ ] Items appear in same order in the body as in the TOC
- [ ] Every item has a `From: First Last` attribution (except the Joana rollup)
- [ ] All `&` in copy are `&amp;`
- [ ] No em dashes anywhere — replaced with ` - `
- [ ] No `--` anywhere — replaced with ` - `
- [ ] All links use `&raquo;` and contextual text
- [ ] All email addresses in body copy are wrapped in `mailto:` links
- [ ] Stale/expired items were dropped
- [ ] Headlines are in title case
- [ ] No `<b>` tags — only `<strong>`
- [ ] The container div and both paragraph tags match the template exactly (spot-check one or two)

---

## A Complete Item, Start to Finish

Here is a realistic example showing the full transformation from raw email to finished HTML item.

**Raw email received:**
```
From: Karen Fletcher
Subject: Fwd: Vigil for Deportation Victims - THIS SATURDAY

Hi Steph, wanted to make sure this gets in the newsletter. There's a vigil 
this Saturday Feb 22 at 2pm at Lone Fir Cemetery, 2101 SE Morrison St. It's 
being organized by Portland Immigrant Rights Coalition (PIRC). Bring candles 
if you have them. Not a PRG official thing but grannies should know about it.
```

**Finished HTML item:**
```html
<div class="items" style="max-width: 650px;margin: 20px auto;background: #ffffff;border-radius: 6px;box-shadow: 0 0 6px rgba(0, 0, 0, .15);padding: 0 40px 40px 40px;">
  <p class="title" style="font-size:20px;font-weight:700;color:#d6616c;margin:30px 0 6px 0;mso-margin-top-alt:30px;border-top:3px solid #d6616c;padding: 27px 0 27px 0;">Vigil for Deportation Victims - Saturday, February 22</p>
  <p class="body" style="font-size:14px;font-weight:400;line-height:1.55;margin:0 0 6px 0;">From: Karen Fletcher
    <br/>
    <br/>The Portland Immigrant Rights Coalition (PIRC) is holding a vigil for victims of deportation this Saturday, February 22, at 2:00 PM.
    <br/>
    <br/>Location: Lone Fir Cemetery
    <br/>2101 SE Morrison St, Portland
    <br/>
    <br/>Bring candles if you have them.
    <br/>
    <br/>This is not an official PRG action, but grannies are welcome to attend individually.
  </p>
</div>
```

Notice what happened:
- The date moved to the headline so it's immediately visible
- The location got its own lines (scannable)
- The "PIRC" acronym got spelled out on first use
- "PRG official thing" became proper language
- The casual email framing ("Hi Steph, wanted to make sure...") was stripped
- Karen's voice is still there in tone; we just removed the listserv scaffolding

---

## The One Thing That Trips Up Automated Systems

The rewrite step is not a formatting step. It's an editorial step. The tool that does this has to make judgment calls:

- Is this item stale? (Requires knowing today's date and comparing to event dates)
- Is this a standalone item or does it go in the Joana rollup? (Requires understanding "is PRG taking group action?")
- What's the right headline? (Requires reading the email and deciding what's most important)
- Does this personal share need rewriting or preservation? (Requires detecting when preserving voice matters)
- What's the right link text? (Requires understanding what the link leads to)

A pure template-fill approach won't work here. The system needs to read the content, classify it, make the judgment call, and then write the item. If you're building this in Claude Code, the prompt for this step needs to convey all of the above — ideally by passing this document as context.

The item types and their rules are the core of it. Get those right and the HTML formatting is the easy part.
