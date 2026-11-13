# Early Access

Waitlist pages for my projects (with a floating "Get early access" button that follows visitors down the page) at **early.siddheshthapa.com**. Every project gets its own link
(for example `early.siddheshthapa.com/cotsi/`), so the person you send it to only sees that one
project. Signups land in a Google Sheet (one tab per project), and each one triggers an email alert.

```
projects.json                  ← the only file you edit day to day
assets/style.css, form.js      ← look and form logic
google-apps-script/Code.gs     ← paste into your Google Sheet (saves signups + emails you)
build.py                       ← turns projects.json into pages (GitHub runs it for you)
.github/workflows/deploy.yml   ← publishes to GitHub Pages on every push to main
```

## One-time setup (about 15 minutes)

### 1. The Google Sheet that collects signups
1. Signed in as **siddeshthapa02@gmail.com**, create a new Google Sheet named "Early Access signups".
2. **Extensions → Apps Script**. Delete what's there, paste all of `google-apps-script/Code.gs`, save.
3. In the function dropdown pick **sendTestSignup**, click **Run**, and allow the permissions it asks
   for. You should get a test alert email, and a `test` tab appears in the Sheet (delete it after).
4. **Deploy → New deployment → ⚙ Web app**. Set *Execute as:* **Me**, *Who has access:* **Anyone**.
   Deploy, then copy the **Web app URL** (it ends in `/exec`).
5. Paste that URL into `projects.json` as `"form_endpoint"`.

Alerts go to the Google account that owns the Sheet. To send them elsewhere, put an address in
`NOTIFY_EMAIL` at the top of the script.

### 2. GitHub Pages
1. Push this folder to a **public** repo, `OnePanda2/early-access`.
2. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Same page, **Custom domain:** `early.siddheshthapa.com` → Save. Tick **Enforce HTTPS** once it
   becomes available (can take up to an hour).

### 3. DNS (wherever siddheshthapa.com is registered)
Add one record:

| Type | Name / Host | Value / Target |
|---|---|---|
| CNAME | `early` | `onepanda2.github.io` |

## Adding a new project

1. Open `projects.json` on GitHub and click the ✏️ edit icon.
2. Copy the whole Cotsi block (from `{` to `}`), paste it after it, add a comma between the two
   blocks, and change the fields. `slug` becomes the link: `"slug": "my-app"` gives
   `early.siddheshthapa.com/my-app/`.
3. Commit. The page is live in about a minute (watch the **Actions** tab).

| Field | What it does |
|---|---|
| `slug` | The link. Lowercase letters, digits and dashes only. Don't change it after sharing. |
| `name`, `emoji`, `tagline`, `description` | The top of the page. Wrap words in the tagline with `*stars*` to make them the colored italic accent |
| `accent` | The page color, like `#7c6af7` |
| `status` | The small badge, like "Early access · launching soon" |
| `listed` | `true` shows it on the home page; `false` keeps it reachable only by its link |
| `highlights` | Optional feature cards |
| `demo` | Optional chat-style preview (delete the block if you don't want one) |
| `cta`, `success` | The button text and the message after someone signs up |
| `launch_url` | Optional. The live app's address. Adds an "It's live" button above the form, and the page's buttons open the app instead of the form |
| `launch_at` | Optional, with `launch_url`. When to switch, like `2026-11-16T00:00:00+05:30` (that's midnight in India). Before then the page looks unchanged; at that moment it switches by itself in visitors' browsers, no redeploy needed. Leave it out to switch right away |
| `status_live` | Optional. The badge text after launch (default "Live now") |

## Sharing links
- Send `https://early.siddheshthapa.com/cotsi/` to people who comment on a Cotsi reel.
- Add `?ref=` to see where people came from, e.g. `…/cotsi/?ref=reel-oct`. It shows in the
  Sheet's **Source** column.

## Good to know
- Signups are de-duplicated per project (same email or phone counts once) and each person sees
  their spot in line ("You're #12").
- Gmail lets Apps Script send about **100 emails a day** on a free account. If a reel goes viral
  past that, alerts pause until the next day, but every signup is still saved in the Sheet.
- Preview locally: `python3 build.py && python3 -m http.server -d dist 8000`.
- The demo dialogue uses character *types* rather than real sitcom character names, so the public
  page doesn't use copyrighted characters to promote the product.
