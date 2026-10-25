#!/usr/bin/env python3
"""Tests for check-listing-claims.py.

Every case here is a defect the checker met in the real repos, or a false
positive an earlier draft produced against them.
"""

import importlib.util
import json
import pathlib
import sys
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "check_listing_claims",
    pathlib.Path(__file__).resolve().parent / "check-listing-claims.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)

MEMBERS = {"instinct": "Instinct", "tribulation": "Tribulation",
           "mercantile": "Mercantile", "meridian": "Meridian"}

SUITE_STRIP = """
## Part of Concord

Instinct is part of [Concord](https://github.com/rfizzle/concord) — a modular
collection of system overhauls. Install any, combine all:

- [Tribulation](https://tribulation.rfizzle.com) — Survive what comes next.
- [Mercantile](https://mercantile.rfizzle.com) — Every villager remembers.
"""


class ListingClaimsTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self._dir.name) / "repo"
        (self.repo / "src/main/resources/assets/instinct/lang").mkdir(parents=True)
        (self.repo / "site").mkdir(parents=True)
        (self.repo / "src/main/resources/fabric.mod.json").write_text(
            json.dumps({"schemaVersion": 1, "id": "instinct"}))
        self.lang({})

    def tearDown(self):
        self._dir.cleanup()

    def lang(self, entries):
        (self.repo / "src/main/resources/assets/instinct/lang/en_us.json").write_text(
            json.dumps(entries))

    def listing(self, body, curseforge=None):
        (self.repo / "site/listing-modrinth.md").write_text(body)
        (self.repo / "site/listing-curseforge.md").write_text(
            body if curseforge is None else curseforge)

    def meta(self, **fields):
        (self.repo / "src/main/resources/fabric.mod.json").write_text(
            json.dumps({"schemaVersion": 1, "id": "instinct", **fields}))

    def run_check(self):
        return check.check_repo(self.repo, MEMBERS, new_rules=False)

    def run_new(self, strict=None):
        return check.check_repo(self.repo, MEMBERS, strict_new=strict)

    def java(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    # --- phantom integrations -------------------------------------------

    def test_unbacked_claim_is_an_error(self):
        self.listing("With **Tribulation**, veterancy accrues double.")
        errors, _ = self.run_check()
        self.assertTrue(any("Tribulation" in e for e in errors), errors)

    def test_claim_inside_the_suite_section_is_still_judged(self):
        """The regression that made the first draft useless.

        Instinct's four phantom claims sat *inside* its `## Part of Concord`
        section, so excluding the whole section excluded the exact lie the
        check exists to catch. Only the link bullets are exempt.
        """
        self.listing(SUITE_STRIP + "\n**Enhanced by**: **Meridian** — shelves help.\n")
        errors, _ = self.run_check()
        self.assertTrue(any("Meridian" in e for e in errors), errors)

    def test_suite_strip_bullets_alone_are_not_a_claim(self):
        self.listing(SUITE_STRIP)
        errors, _ = self.run_check()
        self.assertEqual([], errors)

    def test_compat_package_backs_a_claim(self):
        (self.repo / "src/main/java/com/rfizzle/instinct/compat/tribulation").mkdir(parents=True)
        self.listing("With **Tribulation**, veterancy accrues double.")
        errors, _ = self.run_check()
        self.assertEqual([], errors)

    def test_a_bare_suggests_entry_does_not_back_a_claim(self):
        """A `suggests` entry declares soft compatibility, not an integration.

        Distillation suggests tribulation and claimed "its shard debuffs gain
        brewable antidotes of their own"; nothing in the repo registers one.
        Counting the entry as evidence hid a phantom claim.
        """
        self.meta(suggests={"tribulation": "*"})
        self.listing("With **Tribulation**, veterancy accrues double.")
        errors, _ = self.run_check()
        self.assertTrue(any("Tribulation" in e for e in errors), errors)

    def test_a_relation_without_a_store_slug_is_an_error(self):
        self.listing("A mod.")
        self.meta(depends={"fabric-api": "*", "minecraft": "~1.21.1"},
                  suggests={"appleskin": "*", "tribulation": "*"})
        orig = check.load_third_party
        check.load_third_party = lambda members_file=None: {"fabric-api"}
        try:
            errors, _ = self.run_check()
        finally:
            check.load_third_party = orig
        self.assertEqual(1, sum("thirdPartySlugs" in e for e in errors), errors)
        self.assertTrue(any("'appleskin'" in e for e in errors), errors)

    def test_mapped_sibling_and_builtin_relations_pass(self):
        self.listing("A mod.")
        self.meta(depends={"fabric-api": "*", "minecraft": "~1.21.1", "java": ">=21"},
                  suggests={"appleskin": "*", "tribulation": "*"})
        orig = check.load_third_party
        check.load_third_party = lambda members_file=None: {"fabric-api", "appleskin"}
        try:
            errors, _ = self.run_check()
        finally:
            check.load_third_party = orig
        self.assertFalse(any("thirdPartySlugs" in e for e in errors), errors)

    def test_a_depends_entry_backs_a_claim(self):
        self.meta(depends={"tribulation": ">=1.0.0"})
        self.listing("With **Tribulation**, veterancy accrues double.")
        errors, _ = self.run_check()
        self.assertEqual([], errors)

    def test_a_sibling_data_tree_backs_a_claim(self):
        (self.repo / "src/main/resources/data/tribulation").mkdir(parents=True)
        self.listing("With **Tribulation**, veterancy accrues double.")
        errors, _ = self.run_check()
        self.assertEqual([], errors)

    def test_the_mods_own_name_is_never_a_claim(self):
        self.listing("Instinct does a great many things.")
        errors, _ = self.run_check()
        self.assertEqual([], errors)

    # --- content that ships but is never named ---------------------------

    def test_unnamed_block_is_an_error(self):
        self.lang({"block.instinct.kennel_post": "Kennel Post"})
        self.listing("A mod about animals.")
        errors, _ = self.run_check()
        self.assertTrue(any("Kennel Post" in e for e in errors), errors)

    def test_unnamed_item_is_only_a_warning(self):
        self.lang({"item.instinct.vet_kit": "Vet Kit"})
        self.listing("A mod about animals.")
        errors, warnings = self.run_check()
        self.assertEqual([], errors)
        self.assertTrue(any("Vet Kit" in w for w in warnings), warnings)

    def test_a_hard_wrapped_name_still_counts_as_named(self):
        """`**Best in\\nShow**` is present; an earlier draft called it missing."""
        self.lang({"block.instinct.best_in_show": "Best in Show"})
        self.listing("Breed a prime animal for **Best in\nShow** — a fine beast.")
        errors, _ = self.run_check()
        self.assertEqual([], errors)

    def test_a_slash_compressed_family_counts_as_named(self):
        """Meridian writes three registered blocks as one line:

            Shelf of Seabound / Hellbound / End-Fused Rectification

        Each is named there. An earlier draft called all three missing.
        """
        self.lang({"block.instinct.rectifier": "Shelf of Seabound Rectification",
                   "block.instinct.rectifier_t2": "Shelf of Hellbound Rectification"})
        self.listing("- Shelf of Seabound / Hellbound / End-Fused Rectification\n")
        errors, _ = self.run_check()
        self.assertEqual([], errors)

    def test_the_relaxation_does_not_forgive_an_absent_name(self):
        self.lang({"block.instinct.stoneshelf": "Stoneshelf"})
        self.listing("- Shelf of Seabound / Hellbound / End-Fused Rectification\n")
        errors, _ = self.run_check()
        self.assertTrue(any("Stoneshelf" in e for e in errors), errors)

    def test_tooltip_subkeys_are_not_treated_as_content(self):
        """`item.<mod>.<name>.info.*` is a tooltip line, not an item.

        Tribulation alone carries 24 of these; treating them as content
        produced 24 warnings demanding a store page quote its own tooltips.
        """
        self.lang({"item.instinct.vet_kit": "Vet Kit",
                   "item.instinct.vet_kit.info.hold_shift": "Hold Shift for details"})
        self.listing("Revive a downed pet with a **Vet Kit**.")
        errors, warnings = self.run_check()
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    # --- advancements are judged against the listing's own choice ---------

    def test_advancements_are_ignored_when_the_listing_omits_the_section(self):
        self.lang({"advancements.instinct.old_friend.title": "Old Friend"})
        self.listing("A mod about animals.")
        errors, warnings = self.run_check()
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_an_advancements_section_owes_the_full_set(self):
        self.lang({"advancements.instinct.old_friend.title": "Old Friend",
                   "advancements.instinct.pack_leader.title": "Pack Leader"})
        self.listing("## Advancements\n\n**Old Friend** — raise a pet.\n")
        errors, _ = self.run_check()
        self.assertTrue(any("Pack Leader" in e for e in errors), errors)
        self.assertFalse(any("Old Friend" in e for e in errors), errors)

    def test_the_root_advancement_is_not_content(self):
        """Its title is the mod name, so it would always match trivially."""
        self.lang({"advancements.instinct.root.title": "Instinct"})
        self.listing("## Advancements\n\nNone worth listing.\n")
        errors, warnings = self.run_check()
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    # --- the website is the other half of the surface --------------------

    def page(self, name, text):
        d = self.repo / "site/pages"
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text)

    def test_a_page_claim_reports_but_does_not_fail(self):
        """Prose is looser than a listing, and the backing code may sit in a
        sibling repo a member's CI has not checked out."""
        self.listing("A mod.")
        self.page("features.json", '{"items": ["With Mercantile, clerics stock it."]}')
        errors, warnings = self.run_check()
        self.assertEqual([], errors)
        self.assertTrue(any("Mercantile" in w for w in warnings), warnings)

    def test_a_suite_row_on_a_page_is_not_a_claim(self):
        """The site JSON writes the suite list in its own markup; matching the
        registered tagline recognises it without knowing the markup."""
        self.listing("A mod.")
        self.page("features.json",
                  "{\"items\": [\"<strong class='x'>Mercantile</strong> "
                  "— Every villager remembers.\"]}")
        errors, warnings = self.run_check()
        self.assertEqual(([], []), (errors, warnings))

    def test_evidence_in_the_siblings_own_repo_counts(self):
        """Tribulation's pages say its HUD stacks with Mercantile's, and that
        is true — mercantile's overlay is what accounts for it."""
        peer = self.repo.parent / "mercantile" / "src/main/java"
        peer.mkdir(parents=True)
        (peer / "Overlay.java").write_text("// stacks under instinct's slot")
        self.listing("A mod.")
        self.page("features.json", '{"items": ["Stacks with Mercantile HUDs."]}')
        errors, warnings = self.run_check()
        self.assertEqual(([], []), (errors, warnings))

    # --- a shipped mod claiming it has not shipped ------------------------

    def test_an_unreleased_claim_fails_once_a_tag_exists(self):
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "x"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "tag", "v1.0.0-beta.1"], cwd=self.repo, check=True)
        self.listing("**Not yet released.** This page describes the first release.")
        errors, _ = self.run_check()
        self.assertTrue(any("not out yet" in e for e in errors), errors)

    def test_the_shipped_jar_phrasing_is_caught_too(self):
        """A reviewer found this wording on a live page after the gate passed
        it, and said plainly that it escaped on phrasing, not on facts."""
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "x"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "tag", "v1.0.0"], cwd=self.repo, check=True)
        self.listing("Implemented against the spec — not yet a shipped jar.")
        errors, _ = self.run_check()
        self.assertTrue(any("not out yet" in e for e in errors), errors)

    def test_the_same_wording_is_fine_before_a_tag_exists(self):
        self.listing("**Not yet released.** This page describes the first release.")
        errors, _ = self.run_check()
        self.assertEqual([], errors)

    # --- the short description -------------------------------------------

    def test_summary_over_the_cap_is_an_error(self):
        self.listing("A mod.")
        (self.repo / "site/listing-summary.txt").write_text("x" * 257)
        errors, _ = self.run_check()
        self.assertTrue(any("256-character cap" in e for e in errors), errors)

    def test_summary_within_the_cap_passes(self):
        self.listing("A mod.")
        (self.repo / "site/listing-summary.txt").write_text("x" * 256)
        errors, _ = self.run_check()
        self.assertEqual([], errors)

    def test_wrapped_summary_is_measured_after_flattening(self):
        self.listing("A mod.")
        (self.repo / "site/listing-summary.txt").write_text("x" * 200 + "\n" + "y" * 55)
        errors, _ = self.run_check()
        self.assertEqual([], errors)

    # --- new rules: warnings by default, errors under strict --------------

    MODRINTH = "[Modrinth](https://modrinth.com/mod/instinct)"

    def synced(self):
        self.lang({"block.instinct.kennel_post": "Kennel Post"})

    def test_client_optional_phrasing_warns_when_content_is_registered(self):
        self.synced()
        self.listing("Kennel Post. Required on the **server**; install client-side too "
                     f"for the HUD. {self.MODRINTH}")
        errors, warnings = self.run_new()
        self.assertEqual([], errors)
        self.assertTrue(any("client is required" in w for w in warnings), warnings)

    def test_client_optional_phrasing_errors_under_strict(self):
        self.synced()
        self.listing(f"Kennel Post. A client-only feature. {self.MODRINTH}")
        errors, _ = self.run_new(strict=True)
        self.assertTrue(any("client is required" in e for e in errors), errors)

    def test_required_on_server_and_client_is_fine(self):
        self.synced()
        self.listing(f"Kennel Post. Required on the server and the client. {self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertEqual([], warnings)

    def test_client_phrasing_ignored_without_registered_content(self):
        self.listing(f"Required on the server only. {self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertFalse(any("client is required" in w for w in warnings), warnings)

    def test_payload_registration_counts_as_synced_content(self):
        self.java("src/main/java/x/Net.java", "PayloadTypeRegistry.playS2C().register(a, b);")
        self.listing(f"A client-only feature. {self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertTrue(any("client is required" in w for w in warnings), warnings)

    def test_compat_package_without_a_declared_id_warns(self):
        self.java("src/main/java/x/compat/appleskin/Plugin.java", "class Plugin {}")
        self.listing(f"A mod. {self.MODRINTH}")
        errors, warnings = self.run_new()
        self.assertEqual([], errors)
        self.assertTrue(any("'appleskin'" in w for w in warnings), warnings)

    def test_declared_compat_package_is_fine(self):
        self.java("src/main/java/x/compat/appleskin/Plugin.java", "class Plugin {}")
        self.meta(suggests={"appleskin": "*"})
        self.listing(f"A mod. {self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertEqual([], warnings)

    def test_compat_aliases_and_layout_dirs(self):
        self.java("src/main/java/x/compat/rei/P.java", "class P {}")
        self.java("src/main/java/x/compat/common/P.java", "class P {}")
        self.meta(suggests={"roughlyenoughitems": "*"})
        self.listing(f"A mod. {self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertEqual([], warnings)

    def test_is_mod_loaded_literal_must_be_declared(self):
        self.java("src/main/java/x/A.java",
                  'class A { boolean b = FabricLoader.getInstance().isModLoaded("jei"); }')
        self.listing(f"A mod. {self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertTrue(any("'jei'" in w for w in warnings), warnings)

    def test_own_mod_id_needs_no_declaration(self):
        self.java("src/main/java/x/A.java", 'class A { boolean b = isModLoaded("instinct"); }')
        self.listing(f"A mod. {self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertEqual([], warnings)

    def test_cloth_config_import_needs_a_declaration(self):
        self.java("src/client/java/x/Screen.java",
                  "import me.shedaniel.clothconfig2.api.ConfigBuilder;")
        self.listing(f"A mod. {self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertTrue(any("'cloth-config'" in w for w in warnings), warnings)
        self.meta(suggests={"cloth-config": "*"})
        _, warnings = self.run_new()
        self.assertEqual([], warnings)

    def test_modmenu_entrypoint_importing_cloth_config_warns(self):
        self.java("src/client/java/x/compat/modmenu/ModMenuIntegration.java",
                  "import me.shedaniel.clothconfig2.api.ConfigBuilder;")
        self.meta(suggests={"cloth-config": "*", "modmenu": "*"},
                  entrypoints={"modmenu": ["x.compat.modmenu.ModMenuIntegration"]})
        self.listing(f"A mod. {self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertTrue(any("modmenu entrypoint" in w for w in warnings), warnings)

    def test_delegating_modmenu_entrypoint_is_fine(self):
        self.java("src/client/java/x/compat/modmenu/ModMenuIntegration.java", "class M {}")
        self.java("src/client/java/x/compat/modmenu/ClothConfigScreenBuilder.java",
                  "import me.shedaniel.clothconfig2.api.ConfigBuilder;")
        self.meta(suggests={"cloth-config": "*", "modmenu": "*"},
                  entrypoints={"modmenu": ["x.compat.modmenu.ModMenuIntegration"]})
        self.listing(f"A mod. {self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertEqual([], warnings)

    def test_curseforge_also_on_curseforge_warns(self):
        self.listing(f"A mod. {self.MODRINTH}",
                     curseforge="**Also on [CurseForge](https://www.curseforge.com/x).**\n"
                                f"{self.MODRINTH}")
        _, warnings = self.run_new()
        self.assertTrue(any("Also on CurseForge" in w for w in warnings), warnings)

    def test_curseforge_without_modrinth_link_warns(self):
        self.listing("A mod.", curseforge="A mod, no links.")
        _, warnings = self.run_new()
        self.assertTrue(any("does not link the Modrinth" in w for w in warnings), warnings)

    def test_curseforge_linking_modrinth_is_fine(self):
        self.listing("A mod.",
                     curseforge="**Also on [Modrinth](https://modrinth.com/mod/instinct).**")
        _, warnings = self.run_new()
        self.assertEqual([], warnings)

    def test_new_rules_are_warnings_by_default(self):
        self.assertFalse(check.STRICT_NEW_RULES)

    # --- degradation ------------------------------------------------------

    def test_a_repo_with_no_listing_is_not_an_error(self):
        (self.repo / "site/listing-modrinth.md").unlink(missing_ok=True)
        (self.repo / "site/listing-curseforge.md").unlink(missing_ok=True)
        errors, warnings = self.run_check()
        self.assertEqual(([], []), (errors, warnings))

    def test_an_unreadable_lang_file_does_not_raise(self):
        (self.repo / "src/main/resources/assets/instinct/lang/en_us.json").write_text("{not json")
        self.listing("A mod.")
        errors, warnings = self.run_check()
        self.assertEqual(([], []), (errors, warnings))


if __name__ == "__main__":
    unittest.main()
