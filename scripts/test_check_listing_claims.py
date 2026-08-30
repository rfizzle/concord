#!/usr/bin/env python3
"""Tests for check-listing-claims.py.

Every case here is a defect the checker met in the real repos, or a false
positive an earlier draft produced against them.
"""

import importlib.util
import json
import pathlib
import sys
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
        return check.check_repo(self.repo, MEMBERS)

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
        """Every member suggests every sibling at `*`, so it excuses nothing.

        Distillation suggests tribulation and claimed "its shard debuffs gain
        brewable antidotes of their own"; nothing in the repo registers one.
        Counting the entry as evidence hid a phantom claim.
        """
        self.meta(suggests={"tribulation": "*"})
        self.listing("With **Tribulation**, veterancy accrues double.")
        errors, _ = self.run_check()
        self.assertTrue(any("Tribulation" in e for e in errors), errors)

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
