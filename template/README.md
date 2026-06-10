# Concord shared site template

One template, every mod site. A member repo holds **only content and colors**
(`site/` directory); this template turns it into the full static site at build
time via [Eleventy](https://www.11ty.dev/) + Nunjucks. Output is plain HTML +
CDN Tailwind — identical in character to the hand-written sites it replaces,
with full SEO/OG support.

## How a mod uses it

1. Content lives in the mod repo:

```
site/
├── site.json          # identity, nav order, theme colors, links
├── pages/<slug>.json  # one file per page (index, features, config, …)
└── assets/            # logo.png, icon.png, og-image.png — copied to site root
```

2. A ~15-line workflow calls the reusable build
   (`.github/workflows/build-site.yml` in this repo). Pages source must be set
   to **GitHub Actions** in the mod repo's settings.

3. Local preview (repos checked out as siblings):

```bash
SITE_DIR=$PWD/site npx -y @11ty/eleventy@3.0.0 \
  --config=../concord/template/eleventy.config.cjs \
  --input=../concord/template/src --output=_site --serve
```

When `template/**` or `members.json` changes on main, `propagate.yml`
dispatches a rebuild to every member repo (`concord-template-updated` event).

## site.json

```jsonc
{
  "id": "tribulation",              // member id — must match members.json
  "name": "Tribulation",
  "domain": "tribulation.rfizzle.com",
  "url": "https://tribulation.rfizzle.com",
  "description": "…",               // footer brand blurb
  "metaKeywords": "…",              // optional, home page only
  "github": "https://github.com/rfizzle/tribulation",
  "defaultBranch": "master",        // for the footer LICENSE link
  "copyright": "© 2026 rfizzle. …",
  "footerMeta": "Minecraft 1.21.1 · Fabric",
  "nav": ["index", "features", "config", "commands", "guide", "faq", "developers"],
  "theme": {
    // surfaces/text default to the Concord shared tokens; override only if
    // the mod uses tinted surfaces (see design/DESIGN-SYSTEM.md)
    "accent": "#DC143C",            // brand accent 1
    "accentDark": "#8B0000",
    "accent2": "#FF6B35",           // brand accent 2
    "accent2Bright": "#FF4500",
    "glowRgb": "220, 20, 60"        // accent as r, g, b — hero glow / logo shadow
  }
}
```

The theme maps to generic utility classes available in all content HTML:
`text-accent`, `text-accent2`, `bg-accent/15`, `border-accent`, etc. — plus the
shared `text-bone` / `text-ash` / `text-smoke` and `bg-ink` / `bg-card` /
`bg-elevated`. **Never use mod-specific color names in content.**

## pages/<slug>.json

Common fields: `nav` (label), `metaTitle`, `metaDescription`, optional
`ogTitle`/`ogDescription`, `title` + `lede` (page header), `width`
(`4xl`|`5xl`|`6xl`), `scale` (`lg` for feature-style pages), and `sections`.

The home page sets `"type": "home"` and uses `hero` + banded sections instead
of a page header.

Each section: `{ id?, title?, plainTitle?, intro?, blocks: [...] }`.
Inline HTML is allowed inside content strings (use single-quoted attributes to
keep the JSON readable).

### Block types

| type | shape | renders |
|---|---|---|
| `prose` | `{ html: [str], wide? }` | paragraphs |
| `note` | `{ html, center? }` | small smoke-colored footnote |
| `sub` | `{ id?, title, intro?, blocks: [...] }` | h3 subsection (recursive) |
| `table` | `{ headers: [str], rows: [[str]], note?, nowrapHeaders?, bottomGap? }` | styled data table |
| `code` | `{ code, tone?: "bone"\|"accent2", label?, small?, bottomGap?, topGap? }` | standalone code block |
| `cards` | `{ mdColumns?, lgColumns?, leftAccent?, hoverAccent?, titleSize?, items: [card] }` | card grid |
| `list` | `{ ordered?, items: [str], spacing? }` | bullet / numbered list |
| `steps` | `{ items: [str], note? }` | numbered-circle install steps |
| `faq` | `{ items: [{q, a}] }` | accordion |
| `examples` | `{ items: [{title, suffix?, body: [{type: "code"\|"prose", …}]}] }` | example cards |
| `panel` | `{ title, items: [str] }` | single framed panel |

Card item: `{ id?, icon?, title, titleTone?: "accent"\|"bone", badge?, html: [str], bullets?: [str], bulletSpacing?, code?, note? }`.

## Generated for free

Header nav + mobile menu (from `nav`), the Concord footer (from
`../members.json` — adding a member there updates every site's footer on the
next rebuild), canonical/OG/Twitter meta, `sitemap.xml`, `robots.txt`, `CNAME`.
