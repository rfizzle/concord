#!/usr/bin/env node
/*
 * Generate <site>/pages/changelog.json for a Concord member site.
 *
 * The site changelog is derived, never hand-written: it unions the mod's
 * committed changelogs/<version>.md files (hand-authored or recorded by the
 * release pipeline) with its GitHub Releases, so it can't drift from what
 * actually shipped. Runs BEFORE Eleventy — the template reads pages/<slug>.json
 * at config-eval time, so the file must exist first.
 *
 * Opt-in: no-op unless site.json's nav includes "changelog" (that is the same
 * switch that puts it in the header nav). Markdown is parsed with the vendored
 * markdown-it (template/vendor/), so a body can wrap, nest, or use any CommonMark
 * without shattering; only the Releases fetch needs the network (built-in fetch).
 *
 * Policy:
 *   - Stable releases only; prereleases (a "-suffix" version, or a release
 *     flagged prerelease) are omitted — they stay on GitHub Releases.
 *   - A committed changelogs/<version>.md wins over the release body.
 *   - A stable committed version with no published release yet renders under an
 *     "Unreleased" section.
 *   - A release whose body is the raw GitHub auto-note format (## What's Changed
 *     with "by @user in <pr-url>") degrades to a version + date + a link to the
 *     GitHub release, so PR noise never reaches the player-facing page.
 *
 * Usage:  node gen-changelog.cjs <site-dir>
 * Env:    GITHUB_REPOSITORY  owner/repo (falls back to parsing site.json github)
 *         GITHUB_TOKEN       optional, for API rate limits
 *         CHANGELOG_OUT      optional output path override (testing)
 */
const fs = require("fs");
const path = require("path");
const MarkdownIt = require("../vendor/markdown-it.min.js");

const ACCENT = "text-accent hover:text-accent2 underline";

// One parser, configured to emit the site's HTML conventions: no raw HTML,
// soft/hard wraps collapse to a space, and inline emphasis/code/links carry the
// site's CSS classes. Everything else (nesting, escaping, edge cases) is
// markdown-it's job, not ours.
const md = new MarkdownIt({ html: false, linkify: false, typographer: false });
md.renderer.rules.softbreak = () => " ";
md.renderer.rules.hardbreak = () => " ";
md.renderer.rules.strong_open = () => "<strong class='text-bone'>";
md.renderer.rules.em_open = () => "<em class='text-bone'>";
md.renderer.rules.code_inline = (t, i) => `<code class='text-bone'>${md.utils.escapeHtml(t[i].content)}</code>`;
md.renderer.rules.link_open = (t, i) => `<a href='${md.utils.escapeHtml(t[i].attrGet("href") || "#")}' class='${ACCENT}'>`;

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const renderInline = (tok) => md.renderer.renderInline(tok.children, md.options, {}).trim();

// Detect the raw GitHub auto-generated release note format.
function isRawFormat(body) {
  return /^#{1,3}\s+What's Changed/im.test(body) ||
    /\bby @[\w-]+ in https?:\/\/\S+\/pull\/\d+/i.test(body) ||
    /^\*\*Full Changelog\*\*:/im.test(body);
}

// Walk markdown-it's block tokens into the template's block schema: headings ->
// accent-titled `sub` sections, bullet/ordered lists -> `list`, paragraphs ->
// `prose`. Anything else CommonMark allows (blockquotes, tables, code fences, …)
// is rendered to HTML and kept as a `prose` block so nothing is silently dropped.
function parseBody(body) {
  const tokens = md.parse(body || "", {});
  const root = [];
  let sub = null;
  const target = () => (sub ? sub.blocks : root);
  let i = 0;
  while (i < tokens.length) {
    const t = tokens[i];
    if (t.type === "heading_open") {
      if (sub) root.push(sub);
      sub = { type: "sub", title: `<span class='text-accent uppercase tracking-wider'>${renderInline(tokens[i + 1])}</span>`, blocks: [] };
      i += 3; // heading_open, inline, heading_close
    } else if (t.type === "paragraph_open") {
      target().push({ type: "prose", html: [renderInline(tokens[i + 1])] });
      i += 3;
    } else if (t.type === "bullet_list_open" || t.type === "ordered_list_open") {
      const list = { type: "list", spacing: 1, items: [] };
      if (t.type === "ordered_list_open") list.ordered = true;
      const close = t.type === "ordered_list_open" ? "ordered_list_close" : "bullet_list_close";
      i++;
      while (i < tokens.length && tokens[i].type !== close) {
        if (tokens[i].type === "list_item_open") {
          const level = tokens[i].level;
          const parts = [];
          i++;
          while (i < tokens.length && !(tokens[i].type === "list_item_close" && tokens[i].level === level)) {
            if (tokens[i].type === "inline") parts.push(renderInline(tokens[i]));
            i++;
          }
          list.items.push(parts.join(" "));
        }
        i++;
      }
      i++; // list close
      target().push(list);
    } else {
      // Unmapped block: render its balanced token span (tracked by nesting) to
      // HTML and keep it as prose rather than dropping it.
      let j = i + 1, depth = t.nesting;
      while (j < tokens.length && depth > 0) { depth += tokens[j].nesting; j++; }
      const html = md.renderer.render(tokens.slice(i, j), md.options, {}).trim();
      if (html) target().push({ type: "prose", html: [html] });
      i = j;
    }
  }
  if (sub) root.push(sub);
  return root;
}

function parseVersion(v) {
  const m = String(v).match(/^(\d+)\.(\d+)\.(\d+)/);
  return m ? [+m[1], +m[2], +m[3]] : [0, 0, 0];
}

function isPrerelease(version) {
  return version.includes("-");
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("en-US",
    { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
}

async function fetchReleases(repo, token) {
  const out = [];
  for (let page = 1; page <= 10; page++) {
    const headers = { Accept: "application/vnd.github+json", "User-Agent": "concord-changelog" };
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(
      `https://api.github.com/repos/${repo}/releases?per_page=100&page=${page}`, { headers });
    if (!res.ok) throw new Error(`GitHub API ${res.status} for ${repo}/releases`);
    const batch = await res.json();
    out.push(...batch);
    if (batch.length < 100) break;
  }
  return out;
}

async function main() {
  const siteDir = process.argv[2] && path.resolve(process.argv[2]);
  if (!siteDir || !fs.existsSync(path.join(siteDir, "site.json"))) {
    console.error("gen-changelog: <site-dir> must contain site.json");
    process.exit(2);
  }
  const site = readJson(path.join(siteDir, "site.json"));
  if (!Array.isArray(site.nav) || !site.nav.includes("changelog")) {
    console.log("gen-changelog: nav has no 'changelog' — opted out, nothing to generate");
    return;
  }

  const repo = process.env.GITHUB_REPOSITORY ||
    (site.github || "").replace(/^https?:\/\/github\.com\//, "").replace(/\/$/, "");
  const ghBase = site.github || (repo ? `https://github.com/${repo}` : "");

  // Committed changelogs/<version>.md (sibling of site/).
  const clDir = path.join(siteDir, "..", "changelogs");
  const committed = {};
  if (fs.existsSync(clDir)) {
    for (const f of fs.readdirSync(clDir)) {
      if (f.endsWith(".md")) committed[f.slice(0, -3)] = fs.readFileSync(path.join(clDir, f), "utf8");
    }
  }

  // GitHub Releases (best-effort — a fetch failure still renders committed files).
  let releases = [];
  if (repo) {
    try {
      releases = await fetchReleases(repo, process.env.GITHUB_TOKEN);
    } catch (e) {
      console.log(`::warning::gen-changelog: ${e.message}; rendering committed files only`);
    }
  }
  const relByVersion = {};
  for (const r of releases) {
    const v = (r.tag_name || "").replace(/^v/, "");
    if (v) relByVersion[v] = r;
  }

  // Union of committed + released versions, stable only.
  const versions = new Set([...Object.keys(committed), ...Object.keys(relByVersion)]);
  const entries = [];
  for (const v of versions) {
    const rel = relByVersion[v];
    if (isPrerelease(v) || (rel && rel.prerelease)) continue; // stable only
    const body = committed[v] !== undefined ? committed[v] : (rel ? rel.body || "" : "");
    entries.push({
      version: v,
      date: rel ? rel.published_at : null,
      degrade: committed[v] === undefined && rel && isRawFormat(body || ""),
      body,
    });
  }

  // Unreleased (no published release) first; then released newest-first.
  entries.sort((a, b) => {
    if (!a.date && b.date) return -1;
    if (a.date && !b.date) return 1;
    if (!a.date && !b.date) {
      const [A, B] = [parseVersion(b.version), parseVersion(a.version)];
      return A[0] - B[0] || A[1] - B[1] || A[2] - B[2];
    }
    return new Date(b.date) - new Date(a.date);
  });

  const sections = entries.map((e) => {
    const id = "v" + e.version.replace(/\./g, "-");
    const tagUrl = `${ghBase}/releases/tag/v${e.version}`;
    if (!e.date) {
      return {
        id: "unreleased-" + id,
        title: `Unreleased <span class='text-smoke'>— v${e.version}</span>`,
        blocks: parseBody(e.body),
      };
    }
    const title = `v${e.version} <span class='text-smoke'>— ${fmtDate(e.date)}</span>`;
    if (e.degrade) {
      return {
        id, title,
        blocks: [{ type: "note", html: `Full notes on <a href='${tagUrl}' class='${ACCENT}'>GitHub Releases →</a>` }],
      };
    }
    const blocks = parseBody(e.body);
    blocks.push({ type: "note", html: `<a href='${tagUrl}' class='${ACCENT}'>Download &amp; full notes on GitHub →</a>` });
    return { id, title, blocks };
  });

  // Opted-in but nothing to show yet (pre-release, no committed notes): a
  // graceful "coming soon" instead of an empty page.
  if (!entries.length) {
    sections.push({
      id: "unreleased",
      title: "Unreleased",
      blocks: [
        { type: "prose", html: [`${esc(site.name)} is in active development ahead of its first public release. This page lists each version once releases begin.`] },
        { type: "note", html: `Watch <a href='${ghBase}/releases' class='${ACCENT}'>GitHub Releases</a> for the first tagged build.` },
      ],
    });
  }

  sections.push({
    id: "versioning",
    title: "Versioning",
    blocks: [{
      type: "prose",
      html: [`${esc(site.name)} follows <a href='https://semver.org/' class='${ACCENT}'>semantic versioning</a>. Every tagged release is on <a href='${ghBase}/releases' class='${ACCENT}'>GitHub Releases</a>, the canonical download source; prereleases are published there but omitted from this page.`],
    }],
  });

  const page = {
    nav: "Changelog",
    metaTitle: `Changelog — ${site.name}`,
    metaDescription: `Release history for ${site.name}: every stable version with its player-facing changes, linked to GitHub Releases.`,
    ogTitle: `Changelog — ${site.name}`,
    ogDescription: `Release history for ${site.name} with per-version changes.`,
    title: "Changelog",
    lede: `Every stable release. Jars and full notes live on <a href='${ghBase}/releases' class='${ACCENT}'>GitHub Releases</a> — the canonical download source.`,
    width: "4xl",
    sections,
  };

  const out = process.env.CHANGELOG_OUT || path.join(siteDir, "pages", "changelog.json");
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(page, null, 2) + "\n");
  console.log(`gen-changelog: wrote ${out} (${entries.length} version(s))`);
}

main().catch((e) => { console.error("gen-changelog:", e.message); process.exit(1); });
