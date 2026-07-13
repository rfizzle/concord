# Concord shared site template

One template, every mod site. A member repo holds **only content and colors**
(`site/` directory); this template turns it into the full static site at build
time via [Eleventy](https://www.11ty.dev/) + Nunjucks. Output is plain HTML +
a Tailwind stylesheet compiled at build time (no CDN, no client-side JS
required for styling), with full SEO/OG support. Utilities reference the theme
CSS variables, so each mod's colors apply via a small inline `:root` block
without recompiling per theme.

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

When `template/**` or `members.json` changes on master, `propagate.yml`
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

A block whose `type` isn't in this table fails the build with an error naming
the page and section — content never silently renders as nothing.

| type | shape | renders |
|---|---|---|
| `prose` | `{ html: [str], wide? }` | paragraphs |
| `note` | `{ html, center? }` | small smoke-colored footnote |
| `sub` | `{ id?, title, intro?, blocks: [...] }` | h3 subsection (recursive) |
| `table` | `{ headers: [str], rows: [[cell]], note?, nowrapHeaders?, bottomGap?, sortable?, sort?, defaultSort? }` | styled data table (optionally sortable) |
| `code` | `{ code, tone?: "bone"\|"accent2", label?, small?, bottomGap?, topGap? }` | standalone code block |
| `cards` | `{ mdColumns?, lgColumns?, leftAccent?, hoverAccent?, titleSize?, items: [card] }` | card grid |
| `list` | `{ ordered?, items: [str], spacing? }` | bullet / numbered list |
| `steps` | `{ items: [str], note? }` | numbered-circle install steps |
| `faq` | `{ items: [{q, a}] }` | accordion |
| `examples` | `{ items: [{title, suffix?, body: [{type: "code"\|"prose", …}]}] }` | example cards |
| `panel` | `{ title, items: [str] }` | single framed panel |

Card item: `{ id?, icon?, title, titleTone?: "accent"\|"bone", badge?, html: [str], bullets?: [str], bulletSpacing?, code?, note? }`.

### Sortable tables

Set `sortable: true` on a `table` to make its headers click-to-sort. Sorting is
a progressive enhancement — without JavaScript the table renders in source
order and stays fully readable; the script only adds the reordering.

Each column decides *how* it sorts via a `sort` array parallel to `headers`.
An entry may be:

- `"text"` — case-insensitive alphabetical (the default for any column when
  `sort` is omitted or the entry is missing).
- `"number"` — the first number found in the cell (`"+5%"` → `5`); non-numeric
  cells sort last.
- `"roman"` — Roman numerals read as integers, so `I < V < VII` (not `I < V <
  VII` alphabetically, which would be wrong).
- `{ "type": "order", "order": ["Common", "Uncommon", "Rare", "Very Rare"] }` —
  rank by position in an explicit list, for tiers that aren't alphabetical.
  Values not in the list sort after every listed tier.
- `false` — this column is not sortable (no button).

Set `defaultSort: { "column": 0, "dir": "asc" }` to sort on load (`dir` defaults
to `"asc"`). A build error is raised for an unknown sort type, an `order`
strategy with no list, or a `defaultSort` pointing at a missing or non-sortable
column.

When a cell's visible text isn't its true sort value (an icon, a formatted
label), give that cell an explicit key: write it as `{ "html": "…", "sort":
"…" }` instead of a bare string. Mixed bare-string and object cells in the same
row are fine.

```jsonc
{
  "type": "table",
  "sortable": true,
  "headers": ["Enchantment", "Max", "Rarity", "Effect"],
  "sort": ["text", "roman", { "type": "order", "order": ["Common", "Uncommon", "Rare", "Very Rare"] }, false],
  "defaultSort": { "column": 0, "dir": "asc" },
  "rows": [
    ["Sharpness", "V", "Common", "Increases melee damage"],
    ["Protection", "IV", "Common", "Reduces most damage"]
  ]
}
```

## Generated for free

Header nav + mobile menu (from `nav`), the cross-mod Concord footer strip
(from `../members.json` — names, taglines, status; adding a member there
updates every site's footer on the next rebuild), the home page `<title>`
(`Name — Tagline`, single-sourced from `members.json`; other pages keep their
own `metaTitle`; the tagline is also exposed to templates as `tagline`),
canonical/OG/Twitter meta, a themed `404.html` (served by GitHub Pages for
unknown paths), `sitemap.xml`, `robots.txt`, `CNAME`.
