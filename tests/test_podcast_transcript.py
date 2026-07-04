from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from memory_builder.processors.diarized_transcript import build_diarized_transcribe_prompt
from memory_builder.processors.podcast_transcript import (
    is_podcast_audio_url,
    process_podcast,
    transcribe_audio_with_gemini,
)
from memory_builder.review.manual_link import parse_manual_review_link, register_manual_content_channel


class PodcastAudioUrlTests(unittest.TestCase):
    def test_mp3_url(self) -> None:
        self.assertTrue(is_podcast_audio_url("https://episode.flightcast.com/abc.mp3"))

    def test_spotify_page_not_audio(self) -> None:
        self.assertFalse(is_podcast_audio_url("https://open.spotify.com/show/abc"))

    def test_pseudo_entry_not_audio(self) -> None:
        self.assertFalse(is_podcast_audio_url("podcast-entry:flightcast:01KWGD"))


class ManualReviewLinkTests(unittest.TestCase):
    def test_spotify_show_with_tracking_params(self) -> None:
        parsed = parse_manual_review_link(
            "https://open.spotify.com/show/6YNopzKDGDwf0auIpPTIID?si=78187ca3d2dc491a&nd=1"
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.kind, "content_channel")
        self.assertEqual(parsed.channel_type, "spotify_show")
        self.assertIn("open.spotify.com/show/6YNopzKDGDwf0auIpPTIID", parsed.url)

    def test_x_profile_is_social(self) -> None:
        parsed = parse_manual_review_link("https://x.com/alexhormozi")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.kind, "social")


class PodcastTranscriptProcessorTests(unittest.TestCase):
    def test_diarized_prompt_includes_display_name(self) -> None:
        prompt = build_diarized_transcribe_prompt("Alex Hormozi", ["Alex Hormozi"])
        self.assertIn("Alex Hormozi", prompt)
        self.assertIn("speaker_type", prompt)

    @patch("memory_builder.processors.podcast_transcript.build_diarized_document_text")
    @patch("memory_builder.processors.podcast_transcript.download_podcast_audio")
    def test_process_podcast_diarized(self, mock_download, mock_diarized) -> None:
        from memory_builder.processors.diarized_transcript import TranscriptSegment, TranscriptSegments

        mock_download.return_value = (Path("/tmp/test.mp3"), {"content-type": "audio/mpeg"})
        segments = TranscriptSegments(
            display_name="Alex Hormozi",
            segments=[
                TranscriptSegment(
                    segment_id="seg-1",
                    speaker="Alex Hormozi",
                    speaker_type="target",
                    text="Hello from the podcast.",
                )
            ],
        )
        mock_diarized.return_value = (
            "[Alex Hormozi]\nHello from the podcast.",
            segments,
            {"transcript_segments.json": "/tmp/transcript_segments.json"},
        )

        doc = process_podcast(
            "hormozi",
            "https://episode.flightcast.com/test.mp3",
            transcription_model="gemini-2.5-flash",
            title="Test Episode",
            display_name="Alex Hormozi",
            speaker_labeled_transcription=True,
        )
        self.assertIn("Hello from the podcast", doc.text)
        self.assertEqual(doc.metadata["transcription_mode"], "diarized")
        mock_diarized.assert_called_once()

    @patch("memory_builder.processors.podcast_transcript.transcribe_audio_with_gemini")
    @patch("memory_builder.processors.podcast_transcript.download_podcast_audio")
    def test_process_podcast_plain(self, mock_download, mock_transcribe) -> None:
        mock_download.return_value = (Path("/tmp/test.mp3"), {"content-type": "audio/mpeg"})
        mock_transcribe.return_value = "Hello from the podcast."

        doc = process_podcast(
            "hormozi",
            "https://episode.flightcast.com/test.mp3",
            transcription_model="gemini-2.5-flash",
            title="Test Episode",
        )
        self.assertIn("Hello from the podcast", doc.text)
        self.assertEqual(doc.title, "Test Episode")

    @patch("google.genai.Client")
    def test_transcribe_inline(self, mock_client_cls) -> None:
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = "Transcribed text."
            mock_client.models.generate_content.return_value = mock_response
            audio = Path(__file__).parent / "_fixtures" / "tiny.mp3"
            audio.parent.mkdir(parents=True, exist_ok=True)
            audio.write_bytes(b"fake" * 100)
            try:
                text = transcribe_audio_with_gemini(audio, "gemini-2.5-flash")
                self.assertEqual(text, "Transcribed text.")
            finally:
                if audio.exists():
                    audio.unlink()


class ManualChannelRegistrationTests(unittest.TestCase):
    @patch("memory_builder.review.manual_link.add_channel")
    @patch("memory_builder.review.manual_link.resolve_spotify_show_rss")
    def test_register_spotify_channel(self, mock_resolve, mock_add) -> None:
        mock_resolve.return_value = ("https://rss.example.com/feed.xml", "1254720112")
        mock_add.return_value = MagicMock(channel_id="spotify-show-test")
        parsed = parse_manual_review_link("https://open.spotify.com/show/abc123")
        assert parsed is not None
        channel_id = register_manual_content_channel("hormozi", parsed, root=None)
        self.assertEqual(channel_id, "spotify-show-test")
        mock_add.assert_called_once()


if __name__ == "__main__":
    unittest.main()
