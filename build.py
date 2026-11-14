#!/usr/bin/env python3
"""Build the early-access site from projects.json into dist/.

Usage:
    python3 build.py                              # build
    python3 -m http.server -d dist 8000           # preview at http://localhost:8000

Every project in projects.json gets its own page at /<slug>/, so each link you
share shows only that project. The home page lists projects with "listed": true.
"""

import hashlib
import json
from datetime import datetime
import re
import shutil
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = {"assets", "404", "index"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def asset_version(name):
    """A short fingerprint of an asset, added to its link so browsers fetch the new file after a change."""
    return hashlib.sha256((ROOT / "assets" / name).read_bytes()).hexdigest()[:10]


def rich(text):
    """Escape text and turn *words* into <em>words</em> (used for the headline accent)."""
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escape(text))
    # Keep hyphenated words ("job-ready") on one line so the headline never breaks at the hyphen.
    return re.sub(r"\b(\w+(?:-\w+)+)\b", r'<span class="nw">\1</span>', html)


def wordmark(p):
    """The project's name, with an optional subtitle where **letters** are highlighted."""
    if not p.get("subtitle"):
        return f'<p class="wordmark">{escape(p["name"])}</p>'
    sub = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(p["subtitle"]))
    return (f'<p class="wordmark lockup" aria-label="{escape(p["name"])}, {escape(plain(p["subtitle"]))}">'
            f'<span class="name">{escape(p["name"])}</span><span class="sub" aria-hidden="true">{sub}</span></p>')


def logo_tile(p, cls, tag="div"):
    """The project's logo image if it has one, else its emoji in a tile."""
    if p.get("logo"):
        return f'<img class="{cls} img" src="{escape(p["logo"])}" alt="" aria-hidden="true">'
    return f'<{tag} class="{cls}" aria-hidden="true">{escape(p.get("emoji", "✨"))}</{tag}>'


def plain(text):
    return text.replace("*", "")


def fail(message):
    sys.exit(f"error: {message}")


def load():
    try:
        data = json.loads((ROOT / "projects.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        fail(f"projects.json is not valid JSON (line {err.lineno}, column {err.colno}): {err.msg}")
    site, projects = data.get("site", {}), data.get("projects", [])
    if not site.get("domain"):
        fail("site.domain is required")
    seen = set()
    for i, p in enumerate(projects, 1):
        where = f"project #{i} ({p.get('slug', '?')})"
        for key in ("slug", "name", "tagline", "description"):
            if not str(p.get(key, "")).strip():
                fail(f"{where} is missing '{key}'")
        if not SLUG.match(p["slug"]) or p["slug"] in RESERVED:
            fail(f"{where}: slug must be lowercase letters, digits and dashes (not {sorted(RESERVED)})")
        if p["slug"] in seen:
            fail(f"{where}: slug '{p['slug']}' is used twice")
        seen.add(p["slug"])
        if p.get("accent") and not HEX.match(p["accent"]):
            fail(f"{where}: accent must look like #7c6af7")
        if p.get("launch_at"):
            if not p.get("launch_url"):
                fail(f"{where}: launch_at needs a launch_url")
            try:
                when = datetime.fromisoformat(p["launch_at"])
            except ValueError:
                fail(f"{where}: launch_at must look like 2026-11-16T00:00:00+05:30")
            if when.tzinfo is None:
                fail(f"{where}: launch_at needs a time zone, like +05:30 at the end")
    return site, projects


def page(site, *, title, description, url, accent, body, noindex=False, icon=None, touch_icon=None, og_image=None):
    e = escape
    robots = '<meta name="robots" content="noindex">' if noindex else ""
    rocket = "data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🚀</text></svg>"
    extra = ""
    if touch_icon:
        extra += f'<link rel="apple-touch-icon" href="{e(touch_icon)}">\n'
    if og_image:
        extra += f'<meta property="og:image" content="https://{e(site["domain"])}{e(og_image)}">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(url)}">
<meta name="twitter:card" content="{"summary_large_image" if og_image else "summary"}">
<meta name="theme-color" content="#07060b">
{robots}
<link rel="canonical" href="{e(url)}">
<link rel="icon" href="{e(icon) if icon else rocket}">
{extra}
<script>document.documentElement.classList.add("js")</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/assets/style.css?v={asset_version('style.css')}">
<style>:root{{--accent:{e(accent)}}}</style>
</head>
<body>
{body}
{footer(site)}
</body>
</html>
"""


def footer(site):
    links = " · ".join(
        f'<a href="{escape(l["url"])}">{escape(l["label"])}</a>' for l in site.get("links", [])
    )
    return f'<footer class="foot"><p>Built by {escape(site.get("owner", ""))}</p><p>{links}</p></footer>'


def topbar(site):
    return (
        '<header class="top"><a class="brand" href="/">'
        f'{escape(site.get("owner", ""))} <span>· {escape(site.get("title", "Early Access"))}</span></a></header>'
    )


def demo_block(demo):
    if not demo or not demo.get("lines"):
        return ""
    lines = "".join(
        f'<div class="line {"right" if l.get("side") == "right" else "left"}">'
        f'<span class="avatar" aria-hidden="true">{escape(l.get("avatar", "💬"))}</span>'
        f'<div class="bubble"><b>{escape(l.get("who", ""))}</b><p>{escape(l.get("text", ""))}</p></div></div>'
        for l in demo["lines"]
    )
    note = f'<p class="demo-note">{escape(demo["note"])}</p>' if demo.get("note") else ""
    return (
        '<section class="demo reveal" aria-label="Preview">'
        '<div class="window-bar" aria-hidden="true"><i></i><i></i><i></i><span>Live preview</span></div>'
        f'<div class="demo-body"><p class="kicker">A lesson in Cotsi style</p>'
        f'<h2>{escape(demo.get("title", ""))}</h2><div class="chat">{lines}</div>{note}</div></section>'
    )


def highlights_block(items):
    if not items:
        return ""
    cards = "".join(
        f'<li><div class="card-top"><span class="icon" aria-hidden="true">{escape(h.get("icon", "✨"))}</span>'
        f'<span class="num" aria-hidden="true">0{i}</span></div>'
        f'<h3>{escape(h.get("title", ""))}</h3><p>{escape(h.get("text", ""))}</p></li>'
        for i, h in enumerate(items, 1)
    )
    return f'<section class="highlights reveal"><ul>{cards}</ul></section>'


def live_attrs(p, text=None, href=None, show=False):
    """Attributes that switch an element to its 'live' state once the project launches.

    With launch_url and launch_at, form.js makes the switch in the visitor's browser at that
    moment, so no redeploy is needed on launch day. With launch_url alone it switches at once.
    """
    if not p.get("launch_url"):
        return ""
    at = p.get("launch_at") or "1970-01-01T00:00:00Z"
    attrs = f' data-live-at="{escape(at)}"'
    if text:
        attrs += f' data-live-text="{escape(text)}"'
    if href:
        attrs += f' data-live-href="{escape(href)}"'
    if show:
        attrs += " data-live-show hidden"
    return attrs


def live_label(p):
    return p.get("live_cta") or f"Open {p['name']}"


def live_href(p):
    """Where the main buttons point after launch: the app by default, or e.g. "#join"."""
    return p.get("live_href") or p.get("launch_url")


def form_block(site, p):
    e = escape
    cta = p.get("cta") or "Get early access"
    success = p.get("success") or f"You're on the {p['name']} list. You'll hear from me when it opens."
    launch = (
        f'<a class="launch" href="{e(p["launch_url"])}"{live_attrs(p, show=True)}>It\'s live: open {e(p["name"])} →</a>'
        if p.get("launch_url") and p.get("live_href", p.get("launch_url")) == p.get("launch_url") else ""
    )
    return f"""<section class="join reveal" id="join">
  {launch}
  <form class="signup" novalidate
        data-endpoint="{e(site.get('form_endpoint', ''))}"
        data-project="{e(p['slug'])}" data-project-name="{e(p['name'])}">
    <h2>{e(cta)}</h2>
    <p class="sub">Leave your email or phone number. One of them is enough.</p>
    <label>Email
      <input type="email" name="email" autocomplete="email" inputmode="email" placeholder="you@example.com">
    </label>
    <div class="or" aria-hidden="true"><span>or</span></div>
    <label>Phone / WhatsApp
      <input type="tel" name="phone" autocomplete="tel" inputmode="tel" placeholder="+91 98765 43210">
    </label>
    <label>Name <small>(optional)</small>
      <input type="text" name="name" autocomplete="name" maxlength="80" placeholder="What should I call you?">
    </label>
    <div class="hp" aria-hidden="true"><label>Leave this empty <input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
    <button type="submit">{e(cta)}</button>
    <p class="status" role="status" aria-live="polite"></p>
    <p class="fine">No spam. Only a message when {e(p['name'])} is ready.</p>
  </form>
  <div class="done" hidden>
    <div class="check" aria-hidden="true">✓</div>
    <h2>You're in!</h2>
    <p class="done-text">{e(success)}</p>
    <p class="position"></p>
  </div>
</section>"""


def project_page(site, p):
    url = f"https://{site['domain']}/{p['slug']}/"
    accent = p.get("accent") or "#7c6af7"
    hero = f"""{topbar(site)}
<main class="project">
  <section class="hero">
    {logo_tile(p, "logo")}
    <p class="badge"{live_attrs(p, text=p.get('status_live') or 'Live now')}><span class="pulse" aria-hidden="true"></span><span data-live-label>{escape(p.get('status', 'Early access'))}</span></p>
    {wordmark(p)}
    <h1>{rich(p['tagline'])}</h1>
    <p class="lede">{escape(p['description'])}</p>
    <div class="hero-cta">
      <a class="btn jump" href="#join"{live_attrs(p, text=live_label(p), href=live_href(p))}><span data-live-label>{escape(p.get('cta') or 'Get early access')}</span> <span aria-hidden="true">→</span></a>
      <p class="meta"{live_attrs(p, text=p.get('live_meta') or 'Founding members get first access')}>Limited founding spots · No spam · Takes 10 seconds</p>
    </div>
  </section>
  {demo_block(p.get('demo'))}
  {highlights_block(p.get('highlights'))}
  {form_block(site, p)}
</main>
<a class="float-cta" href="#join" aria-hidden="true" tabindex="-1"{live_attrs(p, text=live_label(p), href=live_href(p))}>
  <span data-live-label>{escape(p.get('cta') or 'Get early access')}</span><span class="arrow" aria-hidden="true">→</span>
</a>
<script src="/assets/form.js?v={asset_version('form.js')}" defer></script>"""
    return page(site, title=f"{p['name']}: {plain(p['tagline'])}", description=p["description"],
                url=url, accent=accent, body=hero,
                icon=p.get("logo"), touch_icon=p.get("touch_icon"), og_image=p.get("og_image"))


def home_page(site, projects):
    listed = [p for p in projects if p.get("listed")]
    cards = "".join(
        f'<li><a href="/{escape(p["slug"])}/" style="--accent:{escape(p.get("accent") or "#7c6af7")}">'
        f'{logo_tile(p, "logo", tag="span")}'
        f'<span><b>{escape(p["name"])}</b><em>{escape(plain(p["tagline"]))}</em>'
        f'<small{live_attrs(p, text=p.get("status_live") or "Live now")}><span data-live-label>{escape(p.get("status", "Early access"))}</span></small></span><i aria-hidden="true">→</i></a></li>'
        for p in listed
    ) or "<li class=\"empty\">New projects are on the way.</li>"
    body = f"""{topbar(site)}
<main class="home">
  <h1>What I'm building <em>next</em></h1>
  <p class="lede">Pick a project to get early access before anyone else.</p>
  <ul class="projects">{cards}</ul>
</main>"""
    return page(site, title=f"{site.get('owner', '')} · {site.get('title', 'Early Access')}",
                description="Get early access to new projects by " + site.get("owner", ""),
                url=f"https://{site['domain']}/", accent="#7c6af7", body=body)


def not_found(site):
    body = f"""{topbar(site)}
<main class="home">
  <h1>That project doesn't exist (yet)</h1>
  <p class="lede">The link may have a typo. <a href="/">See all projects →</a></p>
</main>"""
    return page(site, title="Not found", description="Page not found",
                url=f"https://{site['domain']}/", accent="#7c6af7", body=body, noindex=True)


def main():
    site, projects = load()
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets").mkdir(parents=True)
    for asset in (ROOT / "assets").iterdir():
        shutil.copy(asset, DIST / "assets" / asset.name)
    (DIST / "index.html").write_text(home_page(site, projects), encoding="utf-8")
    (DIST / "404.html").write_text(not_found(site), encoding="utf-8")
    for p in projects:
        out = DIST / p["slug"]
        out.mkdir()
        (out / "index.html").write_text(project_page(site, p), encoding="utf-8")
    (DIST / "CNAME").write_text(site["domain"] + "\n", encoding="utf-8")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Built {len(projects)} project page(s) into dist/")
    if not site.get("form_endpoint"):
        print("warning: site.form_endpoint is empty, so the form can't save signups yet")
    for p in projects:
        print(f"  https://{site['domain']}/{p['slug']}/")


if __name__ == "__main__":
    main()
