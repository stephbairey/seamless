# Tools

Reference document for all tools in Maya's ecosystem. Covers what each tool does, how it's configured, and where it connects to other systems.

## Core Operational Stack

### Gmail (stephbairey@gmail.com)
Maya's "operational nervous system." One inbox receives all email across 17 Send-As identities spanning 6 domains. Identity selection follows a two-axis model: **name** (Steph for business/operations, Maya for creative/author) and **domain** (indicating organizational context). Reply-from is automatic based on which address received the inbound message. For new compositions, the decision is "what hat am I wearing?" — though relationship history can override strict role logic when a contact knows Maya by a particular name.

27 labels organize incoming mail. 48 Gmail filters handle automatic labeling, archiving, and noise management. All domain email (bairey.com, linguaink.com, linguainkmedia.com, tomahawkdestiny.com, lynnahaller.com) forwards to stephbairey@gmail.com at the hosting level. All other Gmail accounts (mjbairey, scb.zombie, grannynewsletter, pdxraginggrannies, webgranny) also forward to stephbairey@gmail.com. Every address funnels into one inbox.

See `data/email-identities.yaml` for the complete identity map and routing rules.

### ClickUp
Task management. Single list: Master Task List (ID `901318968458`) in the Personal project, within Space "Task Dashboard" (ID `90139879792`), Workspace ID `90132317650`.

Six statuses: Not Started, On Hold, Waiting, Begun, Scratch, Complete.

Six required custom fields on every task: Project (16 options covering all clients and contexts), Effort (Tiny through Very Big), Revenue (None through Direct High), Scope (Internal/External), Approach (Dread through Excited — an emotional energy metric, not decorative), Readiness (Prepared/Upskilling).

Naming convention: lowercase verb first, short and actionable. Due dates mandatory. Descriptions used optionally for meeting notes, zoom links, addresses. Checklists not used. Maya uses ClickUp almost daily; the only inconsistency is occasionally letting a few days pass before marking tasks complete.

See `data/clickup-fields.yaml` for all field and option IDs.

### Google Calendar
Three calendars, all visible in a unified view from linguainkmedia@gmail.com:

- **linguainkmedia@gmail.com** — Business and operations. Client meetings, organizational commitments, business tasks.
- **mjbairey@gmail.com** — Creative and writing. Cohort, critique groups, publishing tasks.
- **stephbairey@gmail.com** — Home and personal. Household events, Pete's entries via Alexa. Displays on the local dashboard. Goes back to 2000.

Calendar invites are sent from whichever identity the contact knows. All three are in America/Los_Angeles timezone.

ClickUp's native calendar sync was tried and abandoned (didn't work well). The ✅-prefixed events visible on the linguainkmedia calendar are legacy artifacts from that integration.

See `data/calendar-map.yaml` for the complete calendar configuration.

### Google Drive
File storage and intake pipeline for automated routing. Client-specific intake folders (/LYNN, /MAYA, /SULIMA) feed into n8n file routing workflows. All clients have Google Drive folders, though only three have automated routing so far. Maya hosts the files and shares client-specific folders via Drive sharing.

See `data/file-routing.yaml` for the tag vocabulary and routing configuration.

## Automation Layer

### n8n (Docker, local)
Core automation engine running locally in Docker. Six active workflows:
- 3 file sort workflows (Lynn, Maya, Sulima) — hourly trigger, tag-pair matrix lookup, route to destination or Unsorted
- 2 Amazon delivery tracking workflows — parse Gmail notifications into Google Sheets
- 1 folder ID discovery utility (inactive, manual use)

Maya is comfortable with n8n (built the file routing system from scratch including symmetry normalization) but the matrix maintenance burden limits scaling. She wants a system that doesn't require manually encoding Excel matrices into n8n code.

### TagSpaces
Local file tagging application. Tags are bracketed and appended directly to filenames (not stored in metadata), making them visible everywhere — in Drive, in search, in n8n string parsing. Up to 2 tags per file. The tag vocabulary includes client tags, content-type tags, and project-specific tags (31 total across 3 clients).

### Excel
Two uses: (1) file routing matrix source of truth (tag-pair to folder-ID mappings), and (2) KDP royalty report template. The routing matrix is manually encoded into n8n workflow code — no automated sync.

### Google Sheets
Data store for n8n output, primarily the Amazon delivery tracking dashboard.

## Publishing & Content

### WordPress (6.9.1)
Platform for all web properties. Three Maya-owned sites:
- **linguainkmedia.com** — Marketing consulting (Elementor, Contact Form 7). Live.
- **linguaink.com** — Publishing imprint (WooCommerce, The Events Calendar). 146 blog posts, 12 book products.
- **bairey.com** — Personal author site (FS Poster, Robo Gallery). 75 blog posts. Blog posts auto-duplicate to linguaink.com.

Client sites hosted on Maya's Nixihost account: sulimamalzin.net, lynnahaller.com, Raging Grannies sites (portland.raginggrannies.org, raginggrannies.org, raginggrannies.net), Devon Ervin (URL unknown).

Dev environment: Local by Flywheel on Windows 11, junction points to connect plugin repos.

### WooCommerce
Book sales on linguaink.com. Products: Arms Filled with Bittersweet, Words That Dance (1st + 2nd ed), All in the Soup Together, Painting Celia, Tributaries, Metrophobia. Each available as paperback and/or ebook.

### MailPoet
WordPress plugin for email newsletters. ~600 subscribers for Maya Bairey (author audience). No segmentation. Gathered via marketing and subscriptions over time.

### Substack
Two uses: (1) Sulima Malzin's Light Waves content at sulima.substack.com (imported via RSS feed), and (2) Maya's own bairey.com blog posts republished there.

### KDP + IngramSpark
Book distribution. KDP for Amazon, IngramSpark for wider distribution. Royalty reports require manual data wrangling from KDP exports into Maya's Excel template (automation target).

## Social Media

### Platforms
**Maya Bairey (author):** Bluesky (@mayabairey.bsky.social), Facebook (Maya Bairey, Author), Instagram (mayabairey), TikTok (@mayabairey), Pinterest (mayabairey), Mastodon (mayabairey), Medium (Maya Bairey), Substack (Maya Bairey).

**Lingua Ink Books:** Facebook, Instagram, LinkedIn.

**Steph Bairey:** LinkedIn.

### Posting workflow
Auto-channels from bairey.com blog posts: Pinterest, lnk.bio. Manual posting to Facebook, Instagram, Substack when a blog post goes live. Later is configured for Facebook and Instagram but not actively used.

## Analytics

### GA4
Single "Bairey Web" account (ID 296827458). Properties: bairey.com (420399644), linguaink.com (481632955), sulimamalzin.net (420435585), lynnahaller.com (520632482). linguainkmedia.com probably does not have GA4.

### Ahrefs
SEO analysis tool. API access is non-functional (free tier limitation). Manual use only.

## Meeting & Media Tools

### Granola
Meeting transcription. Used whenever possible for Zoom calls and in-person meetings. Single-mic setup limits speaker attribution.

### Zoom
Video conferencing for client meetings and organizational meetings. Used with Granola for transcription.

### HeyGen
AI avatar generation for the planned "Writing with Maya" YouTube channel. Still in planning stages.

### Midjourney
Visual asset creation for marketing and content.

### Wondershare Filmora
Video editing.

## Home Infrastructure

### Local Dashboard
Household information display on a dedicated 1920x1080 screen. 8 slides: weather, wind, tides/moon, river conditions, calendar (stephbairey), deliveries, bills, account balances. Python fetchers → JSON → JavaScript frontend. Runs on a headless Windows 11 mini-PC. Amber instrument panel aesthetic, 15+ year design history.

### RustDesk
Remote access to the dashboard mini-PC.

### Docker Services
Self-hosted via Docker: n8n, bazarr, calibre-web, gluetun, hbbr, hbbs, jellyfin, lidarr, navidrome, nextcloud-app, nextcloud-db, nginx-proxy-manager, portainer, prowlarr, qbittorrent, radarr, sabnzbd, sonarr.

### Airtable
Used for ARC (moorage committee) workflow management. Details to be gathered in Phase 2.

## Dev Environment

### Primary Machine (Upstairs)
Windows 11 (username: scbzo). WSL2 + Ubuntu (username: linguainkmedia). Node 24.14.0, Claude Code 2.1.59, Git 2.43.0. SSH key: ed25519, label "WSL2 Upstairs." Repos at `/mnt/c/Users/scbzo/Documents/GitHub/`. GitHub account: stephbairey.

### Secondary Machine (Laptop)
PowerShell (no WSL). GitHub Desktop. Repos at `C:\Users\mjbai\Documents\GitHub\`.

### Local by Flywheel
WordPress dev site: "Lingua Ink Media Dev" at lingua-ink-media-dev.local. PHP 8.2.27, nginx, WordPress 6.9.1. Plugins connected via junction points (not symlinks — Windows PHP can't follow WSL symlinks).
