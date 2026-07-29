---
name: django-docs-wiki
description: Expose a repo folder of Markdown/images as an admin-only, Jekyll-style wiki inside a Django app — server-rendered Markdown, inline image previews, safe raw downloads, breadcrumbs, and path-traversal protection. Use when someone wants to turn a docs/ folder into a browsable in-app knowledge base, render Markdown server-side in Django, or build a traversal-safe file browser gated to a role.
---

# Django docs-as-wiki

Turn a folder of Markdown + images (e.g. `documents/`) into a browsable,
role-gated wiki served by Django. Markdown renders inline (headings, tables,
fenced code, blockquotes), images preview inline, everything else downloads.
This is the approach used in this repo at `/admin-portal/wiki/` — see
`core/views.py` (`admin_wiki`, `admin_wiki_raw`, `_wiki_safe_path`),
`core/urls.py`, and `templates/core/admin_wiki_*.html`.

## When to use
- "Expose the `docs/` folder as a wiki for admins."
- "Render our Markdown specs inside the app so non-developers can read them."
- "Build a file browser over a directory, safely."

## Design at a glance
1. Pick a **root directory** inside the project (`WIKI_ROOT = BASE_DIR / "documents"`).
2. One **listing view** for directories, one **render view** for files, one **raw view** for downloads.
3. **Path-traversal guard**: resolve the candidate path and assert it stays under the root.
4. **Render policy**: `.md/.markdown` → HTML; images → inline `<img>`; everything else → download.
5. **Role-gate** every view (admins only here).

## Step 1 — dependency

```
# requirements.txt
Markdown>=3.6
```

## Step 2 — views

```python
# core/views.py
import mimetypes
from pathlib import Path

import markdown as md_lib
from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe

WIKI_ROOT = Path(settings.BASE_DIR) / "documents"
WIKI_RENDERABLE = {".md", ".markdown"}
WIKI_IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def _wiki_safe_path(rel_path: str) -> Path:
    """Resolve a wiki-relative path under WIKI_ROOT or raise Http404.

    This is the security boundary: resolve() collapses `..`, then
    relative_to() raises ValueError if the result escaped the root.
    """
    candidate = (WIKI_ROOT / rel_path).resolve()
    try:
        candidate.relative_to(WIKI_ROOT.resolve())
    except ValueError:
        raise Http404("path escapes wiki root")
    return candidate


def _wiki_breadcrumbs(rel_path: str):
    parts = [p for p in rel_path.split("/") if p]
    crumbs, cum = [], ""
    for p in parts:
        cum = f"{cum}/{p}".lstrip("/")
        crumbs.append({"name": p, "rel": cum})
    return crumbs


@admin_required  # swap for your own role gate / login_required
def admin_wiki(request, rel_path: str = ""):
    rel_path = (rel_path or "").strip("/")
    target = _wiki_safe_path(rel_path) if rel_path else WIKI_ROOT
    if not target.exists():
        raise Http404("not found")

    if target.is_dir():
        entries = []
        for child in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if child.name.startswith("."):
                continue
            child_rel = (Path(rel_path) / child.name).as_posix() if rel_path else child.name
            entries.append({
                "name": child.name, "rel": child_rel, "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.is_file() else None,
                "ext": child.suffix.lower(),
            })
        return render(request, "core/admin_wiki_index.html", {
            "entries": entries, "rel_path": rel_path,
            "breadcrumbs": _wiki_breadcrumbs(rel_path), "wiki_root_name": WIKI_ROOT.name,
        })

    ext = target.suffix.lower()
    if ext in WIKI_RENDERABLE:
        html = md_lib.markdown(
            target.read_text(encoding="utf-8", errors="replace"),
            extensions=["fenced_code", "tables", "toc", "sane_lists"],
        )
        return render(request, "core/admin_wiki_page.html", {
            "rel_path": rel_path, "breadcrumbs": _wiki_breadcrumbs(rel_path),
            "filename": target.name, "content_html": mark_safe(html),
            "wiki_root_name": WIKI_ROOT.name,
        })

    if ext in WIKI_IMAGE:
        img = mark_safe(
            f'<img src="/admin-portal/wiki/raw/{rel_path}" alt="{target.name}" '
            'style="max-width:100%;height:auto;">'
        )
        return render(request, "core/admin_wiki_page.html", {
            "rel_path": rel_path, "breadcrumbs": _wiki_breadcrumbs(rel_path),
            "filename": target.name, "content_html": img, "wiki_root_name": WIKI_ROOT.name,
        })

    return redirect("admin_wiki_raw", rel_path=rel_path)


@admin_required
def admin_wiki_raw(request, rel_path: str):
    target = _wiki_safe_path(rel_path.strip("/"))
    if not target.exists() or not target.is_file():
        raise Http404("not found")
    ctype, _ = mimetypes.guess_type(target.name)
    return FileResponse(open(target, "rb"), content_type=ctype or "application/octet-stream")
```

## Step 3 — URLs

Order matters: the `raw/` route must precede the catch-all `<path:rel_path>`.

```python
# core/urls.py
path("admin-portal/wiki/", views.admin_wiki, name="admin_wiki"),
path("admin-portal/wiki/raw/<path:rel_path>", views.admin_wiki_raw, name="admin_wiki_raw"),
path("admin-portal/wiki/<path:rel_path>", views.admin_wiki, name="admin_wiki_node"),
```

The `<path:...>` converter (not `<str:...>`) is what lets nested folders work.

## Step 4 — templates

`templates/core/admin_wiki_index.html` (directory listing):

```django
{% extends "core/base.html" %}
{% block content %}
<article class="wiki-main">
  <h1>{% if rel_path %}{{ rel_path }}/{% else %}Wiki — {{ wiki_root_name }}/{% endif %}</h1>
  {% if breadcrumbs %}
    <nav class="wiki-breadcrumbs small">
      <a href="{% url 'admin_wiki' %}">{{ wiki_root_name }}</a>
      {% for c in breadcrumbs %}<span> / </span><a href="{% url 'admin_wiki_node' c.rel %}">{{ c.name }}</a>{% endfor %}
    </nav>
  {% endif %}
  <ul class="wiki-list">
    {% for e in entries %}
      <li>
        {% if e.is_dir %}<a href="{% url 'admin_wiki_node' e.rel %}">📁 {{ e.name }}/</a>
        {% else %}<a href="{% url 'admin_wiki_node' e.rel %}">📄 {{ e.name }}</a>
          <span class="small muted">{{ e.size|filesizeformat }}</span>{% endif %}
      </li>
    {% empty %}<li class="muted small">Empty.</li>{% endfor %}
  </ul>
</article>
{% endblock %}
```

`templates/core/admin_wiki_page.html` (rendered file):

```django
{% extends "core/base.html" %}
{% block content %}
<article class="wiki-main wiki-page">
  {% if breadcrumbs %}
    <nav class="wiki-breadcrumbs small">
      <a href="{% url 'admin_wiki' %}">{{ wiki_root_name }}</a>
      {% for c in breadcrumbs %}<span> / </span>
        {% if forloop.last %}<span>{{ c.name }}</span>{% else %}<a href="{% url 'admin_wiki_node' c.rel %}">{{ c.name }}</a>{% endif %}
      {% endfor %}
    </nav>
  {% endif %}
  <div class="wiki-content">{{ content_html }}</div>
</article>
{% endblock %}
```

## Step 5 — Jekyll-ish CSS (optional but worth it)

Style `.wiki-content` so rendered Markdown looks like a docs site: bottom-bordered
`h1/h2`, padded `pre` with a dark background, bordered tables, blockquotes with a
left accent bar. See `static/css/app.css` in this repo for a complete block.

## Security checklist (do not skip)
- **Path traversal** is handled entirely by `_wiki_safe_path`. Test it:
  `/admin-portal/wiki/../settings.py` must return 404.
- **`mark_safe` on Markdown output** means the wiki trusts file authors.
  That's fine for repo-controlled docs; if files can come from untrusted
  users, run the HTML through `bleach.clean(...)` first.
- **Role-gate** every view (`admin_required`/`login_required`). The raw view
  too — otherwise it's an unauthenticated file read.
- Skip dotfiles in listings (`if child.name.startswith("."): continue`).

## Verify
```bash
python manage.py runserver
# as an admin:
#   GET /admin-portal/wiki/                      → directory listing
#   GET /admin-portal/wiki/<file>.md             → rendered HTML
#   GET /admin-portal/wiki/<image>.png           → inline preview
#   GET /admin-portal/wiki/raw/<file>            → download
#   GET /admin-portal/wiki/../README.md          → 404 (traversal blocked)
# as a non-admin: every route → redirect to login
```

## Adapting it
- **Different root**: change `WIKI_ROOT`.
- **Different framework**: the pattern (resolve+relative_to guard, render vs.
  download by extension, breadcrumbs from the rel path) ports directly to
  Flask/FastAPI — only the routing and template syntax change.
- **Search**: add a view that walks `WIKI_ROOT.rglob("*.md")` and greps, then
  links hits back into the same render route.
