from __future__ import annotations

import unittest
from unittest.mock import patch

from memory_builder.submissions.link_submit import (
    LinkMetadata,
    analyze_submitted_link,
    match_personas_for_link,
    resolve_submitted_link,
)


class ResolveSubmittedLinkTests(unittest.TestCase):
    def test_youtube_video_is_content(self) -> None:
        resolved = resolve_submitted_link(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            metadata=LinkMetadata(title="Example video"),
        )
        self.assertEqual(resolved.kind, "content")
        self.assertEqual(resolved.source_type, "youtube")
        self.assertTrue(resolved.processable)

    def test_youtube_channel_is_content_channel(self) -> None:
        resolved = resolve_submitted_link("https://www.youtube.com/@hormozi")
        self.assertEqual(resolved.kind, "content_channel")
        self.assertTrue(resolved.processable)

    def test_x_profile_is_social_profile(self) -> None:
        resolved = resolve_submitted_link("https://x.com/elonmusk")
        self.assertEqual(resolved.kind, "social_profile")

    def test_homepage_is_unsupported(self) -> None:
        resolved = resolve_submitted_link("https://example.com/")
        self.assertEqual(resolved.kind, "unsupported")
        self.assertFalse(resolved.processable)


class MatchPersonasTests(unittest.TestCase):
    @patch("memory_builder.submissions.link_submit.load_persona_config")
    @patch("memory_builder.submissions.link_submit.load_channels")
    @patch("memory_builder.submissions.link_submit.load_approved")
    @patch("api.personas.list_persona_ids", return_value=["bezos", "musk"])
    def test_title_tokens_match_multiple_personas(
        self,
        _mock_ids,
        mock_approved,
        mock_channels,
        mock_config,
    ) -> None:
        mock_approved.return_value = None
        mock_channels.return_value = type("Registry", (), {"channels": []})()

        def config_side_effect(persona_id: str):
            from memory_builder.models import PersonaConfig

            names = {
                "bezos": PersonaConfig(
                    persona_id="bezos",
                    display_name="Jeff Bezos",
                    seed_link_files=[],
                    speaker_names=["Jeff Bezos", "Bezos"],
                ),
                "musk": PersonaConfig(
                    persona_id="musk",
                    display_name="Elon Musk",
                    seed_link_files=[],
                    speaker_names=["Elon Musk", "Musk"],
                ),
            }
            return names[persona_id]

        mock_config.side_effect = config_side_effect
        resolved = resolve_submitted_link(
            "https://example.com/podcast/bezos-musk-interview",
            metadata=LinkMetadata(title="Jeff Bezos and Elon Musk on leadership"),
        )
        matches = match_personas_for_link(resolved)
        matched_ids = {item.persona_id for item in matches}
        self.assertIn("bezos", matched_ids)
        self.assertIn("musk", matched_ids)

    @patch("memory_builder.submissions.link_submit.load_persona_config")
    @patch("memory_builder.submissions.link_submit.load_channels")
    @patch("memory_builder.submissions.link_submit.load_approved")
    @patch("api.personas.list_persona_ids", return_value=["hormozi"])
    def test_hint_persona_is_selected_when_no_other_match(
        self,
        _mock_ids,
        mock_approved,
        mock_channels,
        mock_config,
    ) -> None:
        from memory_builder.models import PersonaConfig

        mock_approved.return_value = None
        mock_channels.return_value = type("Registry", (), {"channels": []})()
        mock_config.return_value = PersonaConfig(
            persona_id="hormozi",
            display_name="Alex Hormozi",
            seed_link_files=[],
            speaker_names=["Alex Hormozi"],
        )
        resolved = resolve_submitted_link(
            "https://example.com/article/123",
            metadata=LinkMetadata(title="Generic article"),
        )
        matches = match_personas_for_link(resolved, hint_persona_id="hormozi")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].persona_id, "hormozi")
        self.assertTrue(matches[0].selected)


class AnalyzeSubmittedLinkTests(unittest.TestCase):
    @patch("memory_builder.submissions.link_submit.fetch_link_metadata")
    @patch("api.personas.list_persona_ids", return_value=["hormozi"])
    @patch("memory_builder.submissions.link_submit.load_persona_config")
    @patch("memory_builder.submissions.link_submit.load_channels")
    @patch("memory_builder.submissions.link_submit.load_approved")
    def test_analyze_returns_matches(
        self,
        mock_approved,
        mock_channels,
        mock_config,
        _mock_ids,
        mock_fetch,
    ) -> None:
        from memory_builder.models import PersonaConfig

        mock_fetch.return_value = LinkMetadata(title="Alex Hormozi on sales")
        mock_approved.return_value = None
        mock_channels.return_value = type("Registry", (), {"channels": []})()
        mock_config.return_value = PersonaConfig(
            persona_id="hormozi",
            display_name="Alex Hormozi",
            seed_link_files=[],
            speaker_names=["Alex Hormozi", "Hormozi"],
        )
        result = analyze_submitted_link(
            "https://www.youtube.com/watch?v=abc123",
            hint_persona_id="hormozi",
        )
        self.assertTrue(result.resolved.processable)
        self.assertGreaterEqual(len(result.matched_personas), 1)


if __name__ == "__main__":
    unittest.main()
