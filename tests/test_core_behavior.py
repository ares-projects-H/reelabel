"""Regression tests based on the original CLI and supplied screenshots.

These tests use the standard library so the safety foundation can be verified
even before optional desktop-development dependencies are installed.
"""

import tempfile
import unittest
from pathlib import Path

from media_renamer.core import build_report, parse_media_name


class CoreBehaviorTests(unittest.TestCase):
    def test_movie_release_name_is_cleaned(self) -> None:
        path = Path("/library/Always.Sunset.on.Third.Street.2005.1080p.BluRay.x264.mkv")
        parsed = parse_media_name(path, Path("/library"))
        self.assertEqual(parsed.display(), "Always Sunset on Third Street (2005)")

    def test_ep_release_infers_first_season(self) -> None:
        path = Path(
            "/library/Toumei na Yurikago 2018 S01 1080p NF WEB-DL/"
            "Toumei.na.Yurikago.EP01.1080p.NF.WEB-DL.DDP2.0.H.264-MagicStar.mkv"
        )
        parsed = parse_media_name(path, Path("/library"))
        self.assertEqual(parsed.display(), "Toumei na Yurikago S01 E01")

    def test_idx_and_sub_pair_keep_matching_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "Campaign.2007.DVDRip.XviD.AC3.Glaeken.CG.avi"
            idx = root / "Campaign.2007.DVDRip.XviD.AC3.Glaeken.CG.idx"
            sub = root / "Campaign.2007.DVDRip.XviD.AC3.Glaeken.CG.sub"
            for path in (video, idx, sub):
                path.touch()

            report = build_report(root)
            targets = {rename.destination.name for rename in report.renames}
            self.assertIn("Campaign (2007).avi", targets)
            self.assertIn("Campaign (2007).idx", targets)
            self.assertIn("Campaign (2007).sub", targets)

    def test_related_images_are_not_proposed_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Campaign.2007.DVDRip.XviD.AC3.Glaeken.CG.avi").touch()
            (root / "poster.jpg").touch()
            self.assertEqual(build_report(root).deletions, [])

    def test_related_images_require_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Campaign.2007.DVDRip.XviD.AC3.Glaeken.CG.avi").touch()
            poster = root / "poster.jpg"
            poster.touch()
            report = build_report(root, include_sidecars=True)
            self.assertEqual([deletion.path for deletion in report.deletions], [poster.resolve()])

    def test_custom_config_does_not_leak_between_scans(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            custom = root / "config.json"
            custom.write_text('{"technical_tokens": ["collector"]}', encoding="utf-8")
            first = root / "Title.2020.collector.mkv"
            first.touch()

            configured = build_report(root, config_path=custom)
            unconfigured = build_report(root)
            configured_target = next(
                rename.destination.name
                for rename in configured.renames
                if rename.source == first.resolve()
            )
            unconfigured_target = next(
                rename.destination.name
                for rename in unconfigured.renames
                if rename.source == first.resolve()
            )
            self.assertEqual(configured_target, "Title (2020).mkv")
            self.assertEqual(unconfigured_target, "Title collector (2020).mkv")


if __name__ == "__main__":
    unittest.main()
