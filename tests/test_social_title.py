from __future__ import annotations

import unittest

from memory_builder.processors.social_post import _instagram_display_title, _sanitize_title_text


class SocialTitleTests(unittest.TestCase):
    def test_sanitize_title_strips_hashtags_and_emojis(self) -> None:
        title = _sanitize_title_text("🚀 Launch offer #pricing #business now")
        self.assertNotIn("#pricing", title)
        self.assertIn("Launch offer", title)

    def test_instagram_title_prefers_source_title(self) -> None:
        title = _instagram_display_title(
            {"shortcode": "abc", "caption": {"text": "short"}},
            username="hormozi",
            source_title="Discovery caption title",
            channel_url="https://instagram.com/hormozi",
        )
        self.assertEqual(title, "Discovery caption title")

    def test_instagram_title_uses_sanitized_caption(self) -> None:
        caption = "How to price your offer when demand exceeds capacity #pricing"
        title = _instagram_display_title(
            {"shortcode": "abc", "caption": {"text": caption}},
            username="hormozi",
            source_title="",
            channel_url="https://instagram.com/hormozi",
        )
        self.assertGreaterEqual(len(title), 20)
        self.assertNotIn("#pricing", title)

    def test_instagram_title_falls_back_to_account(self) -> None:
        title = _instagram_display_title(
            {"shortcode": "abc", "caption": {"text": "hi"}},
            username="hormozi",
            source_title="",
            channel_url="https://instagram.com/hormozi",
        )
        self.assertEqual(title, "@hormozi")


if __name__ == "__main__":
    unittest.main()
