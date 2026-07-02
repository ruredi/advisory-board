from __future__ import annotations

import unittest
from unittest.mock import patch

from memory_builder.discovery.youtube_ytdlp import (
    _upload_date_iso,
    _youtube_videos_tab_url,
    discover_youtube_channel_ytdlp,
    resolve_youtube_channel_id_ytdlp,
)
from memory_builder.models import SourceType


class YoutubeYtdlpTests(unittest.TestCase):
    def test_videos_tab_url(self) -> None:
        self.assertEqual(
            _youtube_videos_tab_url("https://www.youtube.com/@AlexHormozi"),
            "https://www.youtube.com/@AlexHormozi/videos",
        )

    def test_upload_date_iso(self) -> None:
        self.assertEqual(_upload_date_iso("20260702"), "2026-07-02T00:00:00+00:00")
        self.assertIsNone(_upload_date_iso("NA"))

    @patch("memory_builder.discovery.youtube_ytdlp.ytdlp_available", return_value=True)
    @patch("memory_builder.discovery.youtube_ytdlp.subprocess.run")
    def test_discover_parses_ytdlp_output(self, mock_run, _mock_available) -> None:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            "https://www.youtube.com/watch?v=abc123\tEpisode Title\t20260701\n"
        )
        records = discover_youtube_channel_ytdlp(
            "hormozi",
            "https://www.youtube.com/@AlexHormozi",
            set(),
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].source_type, SourceType.YOUTUBE)
        self.assertEqual(records[0].source_title, "Episode Title")

    @patch("memory_builder.discovery.youtube_ytdlp.ytdlp_available", return_value=True)
    @patch("memory_builder.discovery.youtube_ytdlp.subprocess.run")
    def test_resolve_channel_id(self, mock_run, _mock_available) -> None:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "UCUyDOdBWhC1MCxEjC46d-zw\n"
        channel_id = resolve_youtube_channel_id_ytdlp("https://www.youtube.com/@AlexHormozi")
        self.assertEqual(channel_id, "UCUyDOdBWhC1MCxEjC46d-zw")


if __name__ == "__main__":
    unittest.main()
