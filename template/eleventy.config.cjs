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
const path = require("path");

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
    pg.slug = slug;
    pg.href = slug === "index" ? "/" : "/" + slug + ".html";
    pg.permalink = slug === "index" ? "index.html" : slug + ".html";
    return pg;
  });

  eleventyConfig.addGlobalData("site", site);
  eleventyConfig.addGlobalData("members", members);
  eleventyConfig.addGlobalData("pages", pages);

  // Mod assets (logo.png, icon.png, og-image.png, …) land at the site root so
  // existing URLs like /logo.png keep working. Template CSS lands at /css/.
  const rel = (abs) => path.relative(process.cwd(), abs);
  eleventyConfig.addPassthroughCopy({ [rel(path.join(siteDir, "assets"))]: "/" });
  eleventyConfig.addPassthroughCopy({ [rel(path.join(__dirname, "css"))]: "/css" });

  return {
    dir: { includes: "_includes" },
  };
};
