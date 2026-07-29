"""Regression tests based on the original CLI and supplied screenshots.

These tests use the standard library so the safety foundation can be verified
even before optional desktop-development dependencies are installed.
"""

import tempfile
import unittest
from pathlib import Path

from reelabel.core import (
    Rename,
    Report,
    build_report,
    normalize_folder_name,
    parse_media_name,
    print_report,
)


class CoreBehaviorTests(unittest.TestCase):
    def test_release_folder_name_is_cleaned(self) -> None:
        self.assertEqual(
            normalize_folder_name("Lumen Harbor.S04.1080p.x265-ZMNT"),
            "Lumen Harbor S04",
        )

    def test_movie_release_name_is_cleaned(self) -> None:
        path = Path("/library/Evening.Over.Cedar.Street.2005.1080p.BluRay.x264.mkv")
        parsed = parse_media_name(path, Path("/library"))
        self.assertEqual(parsed.display(), "Evening Over Cedar Street (2005)")

    def test_ep_release_infers_first_season(self) -> None:
        path = Path(
            "/library/Moonlit Cradle 2018 S01 1080p NF WEB-DL/"
            "Moonlit.Cradle.EP01.1080p.NF.WEB-DL.DDP2.0.H.264-ExampleGroup.mkv"
        )
        parsed = parse_media_name(path, Path("/library"))
        self.assertEqual(parsed.display(), "Moonlit Cradle S01 E01")

    def test_idx_and_sub_pair_keep_matching_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "Glass Meridian.2007.DVDRip.XviD.AC3.Glaeken.CG.avi"
            idx = root / "Glass Meridian.2007.DVDRip.XviD.AC3.Glaeken.CG.idx"
            sub = root / "Glass Meridian.2007.DVDRip.XviD.AC3.Glaeken.CG.sub"
            for path in (video, idx, sub):
                path.touch()

            report = build_report(root)
            targets = {rename.destination.name for rename in report.renames}
            self.assertIn("Glass Meridian (2007).avi", targets)
            self.assertIn("Glass Meridian (2007).idx", targets)
            self.assertIn("Glass Meridian (2007).sub", targets)

    def test_related_images_are_not_proposed_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Glass Meridian.2007.DVDRip.XviD.AC3.Glaeken.CG.avi").touch()
            (root / "poster.jpg").touch()
            self.assertEqual(build_report(root).deletions, [])

    def test_related_images_require_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Glass Meridian.2007.DVDRip.XviD.AC3.Glaeken.CG.avi").touch()
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

    def test_terminal_report_escapes_control_characters(self) -> None:
        report = Report(
            renames=[
                Rename(
                    Path("title\x1b]52;c;payload\x07.mkv"),
                    Path("Title.mkv"),
                    "test",
                )
            ]
        )

        with unittest.mock.patch("builtins.print") as output:
            print_report(report, verbose=False)

        rendered = "\n".join(
            str(argument)
            for call in output.call_args_list
            for argument in call.args
        )
        self.assertNotIn("\x1b", rendered)
        self.assertNotIn("\x07", rendered)
        self.assertIn("\\x1b", rendered)
        self.assertIn("\\x07", rendered)


if __name__ == "__main__":
    unittest.main()
