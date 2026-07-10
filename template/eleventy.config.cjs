/*
 * Concord shared site template — Eleventy config.
 *
 * Builds any member mod's website from structured content. The mod repo holds
 * only data (site/site.json + site/pages/*.json + site/assets/); this template
 * holds all layout and styling.
 *
 * Usage (from anywhere):
 *   SITE_DIR=/path/to/<mod>/site npx -y @11ty/eleventy@3.0.0 \
 *     --config=/path/to/concord/template/eleventy.config.cjs \
 *     --input=/path/to/concord/template/src --output=_site
 */
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

// Pinned Tailwind version — the compiled stylesheet ships with the site, so
// bumping this only requires a rebuild, never a content change.
const TAILWIND_VERSION = "4.3.0";

// Every block type blocks.njk can render. A page using anything else fails
// the build here instead of silently rendering nothing.
const BLOCK_TYPES = new Set([
  "prose", "note", "sub", "table", "code", "cards",
  "list", "steps", "faq", "examples", "panel",
]);

function validateBlocks(blocks, where) {
  for (const b of blocks || []) {
    if (!BLOCK_TYPES.has(b.type)) {
      throw new Error(
        `Unknown block type "${b.type}" in ${where} — known types: ${[...BLOCK_TYPES].join(", ")}`
      );
    }
    if (b.type === "sub") {
      validateBlocks(b.blocks, `${where} > sub "${b.title}"`);
    }
    if (b.type === "examples") {
      for (const ex of b.items || []) {
        for (const part of ex.body || []) {
          if (part.type !== "code" && part.type !== "prose") {
            throw new Error(
              `Unknown examples part type "${part.type}" in ${where} > example "${ex.title}" — must be "code" or "prose"`
            );
          }
        }
      }
    }
  }
}

function validatePage(pg, slug) {
  (pg.sections || []).forEach((s, i) => {
    validateBlocks(s.blocks, `${slug}.json section ${s.id || s.title || "#" + (i + 1)}`);
  });
}

module.exports = function (eleventyConfig) {
  const siteDir = process.env.SITE_DIR && path.resolve(process.env.SITE_DIR);
  if (!siteDir || !fs.existsSync(path.join(siteDir, "site.json"))) {
    throw new Error(
      "SITE_DIR must point at a mod's site/ directory (containing site.json). Got: " + siteDir
    );
  }

  const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
  const site = readJson(path.join(siteDir, "site.json"));
  const members = readJson(path.resolve(__dirname, "..", "members.json"));

  const pages = site.nav.map((slug) => {
    const pg = readJson(path.join(siteDir, "pages", slug + ".json"));
    validatePage(pg, slug);
    pg.slug = slug;
    pg.href = slug === "index" ? "/" : "/" + slug + ".html";
    pg.permalink = slug === "index" ? "index.html" : slug + ".html";
    return pg;
  });

  // The member entry for the site being built, matched on url/domain (falling
  // back to id) so a mod repo can't drift out of the registry silently. Null
  // for a site that isn't a registered member (e.g. a preview of a new mod).
  const host = (u) => String(u || "").replace(/^https?:\/\//, "").replace(/\/.*$/, "").toLowerCase();
  const currentMember =
    members.members.find((m) => host(m.url) === host(site.url) || host(m.url) === host(site.domain)) ||
    members.members.find((m) => m.id === site.id) ||
    null;

  eleventyConfig.addGlobalData("site", site);
  eleventyConfig.addGlobalData("members", members);
  eleventyConfig.addGlobalData("currentMember", currentMember);
  // Single-sourced tagline (DESIGN-SYSTEM §6): members.json is the one place
  // a member's tagline lives; templates and page content read it from here.
  eleventyConfig.addGlobalData("tagline", currentMember ? currentMember.tagline : "");
  eleventyConfig.addGlobalData("pages", pages);

  // Mod assets (logo.png, icon.png, og-image.png, …) land at the site root so
  // existing URLs like /logo.png keep working. Template CSS lands at /css/.
  const rel = (abs) => path.relative(process.cwd(), abs);
  eleventyConfig.addPassthroughCopy({ [rel(path.join(siteDir, "assets"))]: "/" });
  eleventyConfig.addPassthroughCopy({ [rel(path.join(__dirname, "css"))]: "/css" });

  // Compile Tailwind over the rendered HTML after every build (CI and --serve
  // alike), so the site ships static CSS instead of the browser JIT. The
  // placeholder values here only generate the utilities; each utility
  // references its var(--color-*), which base.njk's inline :root block
  // overrides with the mod's real theme at paint time — so the placeholders
  // must simply list every token content may use, with the same defaults
  // base.njk falls back to.
  // `directories` (not `dir`) carries the resolved output path including a
  // CLI --output override.
  eleventyConfig.on("eleventy.after", ({ directories }) => {
    const outDir = path.resolve(directories.output);
    // Install the pinned CLI once into a version-keyed cache dir. The input
    // stylesheet is written next to that node_modules so `@import
    // "tailwindcss"` resolves; later builds (and every --serve rebuild) reuse
    // the install.
    const twDir = path.join(os.tmpdir(), `concord-tailwind-${TAILWIND_VERSION}`);
    const twBin = path.join(twDir, "node_modules", ".bin", "tailwindcss");
    if (!fs.existsSync(twBin)) {
      fs.mkdirSync(twDir, { recursive: true });
      execFileSync(
        "npm",
        ["install", "--no-save", "--no-audit", "--no-fund",
          `tailwindcss@${TAILWIND_VERSION}`, `@tailwindcss/cli@${TAILWIND_VERSION}`],
        { cwd: twDir, stdio: "inherit" }
      );
    }
    const input = path.join(twDir, "input.css");
    fs.writeFileSync(input, `
@import "tailwindcss" source(none);
@source "${outDir}/**/*.html";
@theme {
  --color-ink: #0a0a0a;
  --color-card: #1a1a1a;
  --color-elevated: #222222;
  --color-bone: #e8e0d4;
  --color-ash: #a89f93;
  --color-smoke: #6b6359;
  --color-accent: #c9b79a;
  --color-accent-dark: #a89578;
  --color-accent2: #e8e0d4;
  --color-accent2-bright: #f4eee2;
  --font-mono: "SF Mono", "Cascadia Code", "Fira Code", Consolas, ui-monospace, monospace;
}
`);
    execFileSync(
      twBin,
      ["-i", input, "-o", path.join(outDir, "css", "tailwind.css"), "--minify"],
      { stdio: "inherit" }
    );
  });

  return {
    dir: { includes: "_includes" },
  };
};
