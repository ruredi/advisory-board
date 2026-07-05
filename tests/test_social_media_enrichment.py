from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from memory_builder.fetch.supadata_client import (
    _extract_transcript_text,
    fetch_transcript,
    normalize_supadata_url,
)
from memory_builder.fetch.scrapfly_instagram import (
    _attach_carousel_images,
    _convert_v1_media_to_legacy,
    _extract_post_media_from_graphql,
    _format_instagram_graphql_errors,
    _is_retryable_instagram_error,
)
from memory_builder.processors.social_media_enrichment import (
    append_image_texts_section,
    append_transcript_section,
    classify_social_media_format,
    instagram_cover_image_urls,
    instagram_has_video,
    instagram_image_urls,
    instagram_media_format,
    resolve_source_nature,
    tweet_has_video,
    tweet_image_urls,
    tweet_media_format,
)
from memory_builder.models import MediaFormat, SourceNature


class SupadataUrlTests(unittest.TestCase):
    def test_normalize_x_video_url(self) -> None:
        url = "https://x.com/WaldronLewis/status/2072605320132575489/video/1?s=46"
        self.assertEqual(
            normalize_supadata_url(url),
            "https://x.com/WaldronLewis/status/2072605320132575489",
        )

    def test_extract_plain_text_payload(self) -> None:
        text = _extract_transcript_text({"content": "Hello world", "lang": "en"})
        self.assertEqual(text, "Hello world")

    def test_extract_chunk_payload(self) -> None:
        text = _extract_transcript_text(
            {"content": [{"text": "Part one"}, {"text": "Part two"}], "lang": "en"}
        )
        self.assertEqual(text, "Part one\nPart two")


class SupadataFetchTests(unittest.TestCase):
    @patch("memory_builder.fetch.supadata_client.get_supadata_key", return_value="test-key")
    @patch("memory_builder.fetch.supadata_client._record_supadata_usage")
    @patch("memory_builder.fetch.supadata_client.httpx.Client")
    def test_fetch_transcript_immediate(self, mock_client_cls, _mock_record, _mock_key) -> None:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"content": "Transcript body", "lang": "en"}
        response.headers = {"x-billable-requests": "3"}

        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = response
        mock_client_cls.return_value = client

        text = fetch_transcript("https://www.instagram.com/reel/ABC123/")
        self.assertEqual(text, "Transcript body")


class InstagramCarouselTests(unittest.TestCase):
    def test_graphql_error_message(self) -> None:
        message = _format_instagram_graphql_errors(
            {"errors": [{"message": "execution error", "severity": "CRITICAL"}]}
        )
        self.assertIn("execution error", message)

    def test_retryable_instagram_errors(self) -> None:
        self.assertTrue(_is_retryable_instagram_error("Instagram: execution error"))
        self.assertFalse(_is_retryable_instagram_error("No text extracted from social post"))

    def test_convert_v1_media_to_legacy(self) -> None:
        legacy = _convert_v1_media_to_legacy(
            {
                "media_type": 1,
                "code": "ABC123",
                "pk": "999",
                "taken_at": 1700000000,
                "like_count": 42,
                "comment_count": 3,
                "caption": {"text": "Hello caption"},
                "image_versions2": {"candidates": [{"url": "https://img/1.jpg"}]},
            }
        )
        self.assertEqual(legacy["shortcode"], "ABC123")
        self.assertEqual(legacy["display_url"], "https://img/1.jpg")
        self.assertEqual(legacy["edge_media_preview_like"]["count"], 42)
        self.assertEqual(legacy["edge_media_to_caption"]["edges"][0]["node"]["text"], "Hello caption")

    def test_extract_post_media_from_v1_graphql(self) -> None:
        media = _extract_post_media_from_graphql(
            {
                "data": {
                    "xdt_api__v1__media__shortcode__web_info": {
                        "items": [{"media_type": 2, "code": "REEL1", "pk": "1", "taken_at": 1}]
                    }
                }
            },
            shortcode="REEL1",
        )
        self.assertTrue(media["is_video"])
        self.assertEqual(media["shortcode"], "REEL1")

    def test_attach_carousel_images(self) -> None:
        raw = {
            "edge_sidecar_to_children": {
                "count": 2,
                "edges": [
                    {"node": {"id": "1", "shortcode": "a", "display_url": "https://img/1.jpg", "is_video": False}},
                    {"node": {"id": "2", "shortcode": "b", "display_url": "https://img/2.jpg", "is_video": False}},
                ],
            }
        }
        result = _attach_carousel_images(raw, {"id": "root", "shortcode": "root", "src": "https://img/root.jpg"})
        self.assertTrue(result["is_carousel"])
        self.assertEqual(len(result["images"]), 2)

    def test_instagram_image_urls_skip_video_slides(self) -> None:
        post = {
            "is_carousel": True,
            "images": [
                {"display_url": "https://img/1.jpg", "is_video": False},
                {"display_url": "https://vid/1.mp4", "is_video": True},
            ],
        }
        self.assertTrue(instagram_has_video(post))
        self.assertEqual(instagram_image_urls(post), ["https://img/1.jpg"])

    def test_instagram_cover_image_urls_for_video(self) -> None:
        post = {
            "is_video": True,
            "src": "https://img/cover.jpg",
            "images": [{"display_url": "https://img/cover.jpg", "is_video": True}],
        }
        self.assertEqual(instagram_cover_image_urls(post), ["https://img/cover.jpg"])


class SocialEnrichmentTests(unittest.TestCase):
    def test_tweet_video_detection(self) -> None:
        tweet = {"media": [{"type": "video", "url": "https://video.example"}]}
        self.assertTrue(tweet_has_video(tweet, "https://x.com/user/status/1"))

    def test_tweet_photo_urls(self) -> None:
        tweet = {"media": [{"type": "photo", "url": "https://img.example/1.jpg"}]}
        self.assertEqual(tweet_image_urls(tweet), ["https://img.example/1.jpg"])

    def test_append_sections(self) -> None:
        text = append_transcript_section("Caption", "Spoken words")
        self.assertIn("## Transcript", text)
        text = append_image_texts_section("Caption", ["Slide one", "Slide two"])
        self.assertIn("## Képek szövege", text)
        self.assertIn("### 1. kép", text)

    def test_resolve_source_nature(self) -> None:
        self.assertEqual(
            resolve_source_nature(has_transcript=True, base_text="caption"),
            SourceNature.NATURAL_SPOKEN,
        )
        self.assertEqual(
            resolve_source_nature(has_transcript=False, base_text="caption"),
            SourceNature.WRITTEN,
        )


class MediaFormatClassificationTests(unittest.TestCase):
    def test_priority_video_over_image_over_text(self) -> None:
        self.assertEqual(
            classify_social_media_format(has_video=True, has_images=True, has_text=True),
            MediaFormat.VIDEO,
        )
        self.assertEqual(
            classify_social_media_format(has_video=False, has_images=True, has_text=True),
            MediaFormat.IMAGE,
        )
        self.assertEqual(
            classify_social_media_format(has_video=False, has_images=False, has_text=True),
            MediaFormat.TEXT,
        )
        self.assertEqual(
            classify_social_media_format(has_video=False, has_images=False, has_text=False),
            MediaFormat.UNKNOWN,
        )

    def test_instagram_media_format_video(self) -> None:
        post = {"is_video": True, "captions": ["hi"], "images": [{"is_video": True, "src": "v.jpg"}]}
        self.assertEqual(instagram_media_format(post), MediaFormat.VIDEO)

    def test_instagram_media_format_image(self) -> None:
        post = {"is_video": False, "images": [{"display_url": "https://img/1.jpg", "is_video": False}]}
        self.assertEqual(instagram_media_format(post), MediaFormat.IMAGE)

    def test_instagram_media_format_text_only(self) -> None:
        post = {"is_video": False, "images": [], "captions": ["just words"]}
        self.assertEqual(instagram_media_format(post), MediaFormat.TEXT)

    def test_tweet_media_format(self) -> None:
        video_tweet = {"media": [{"type": "video"}], "full_text": "hi"}
        self.assertEqual(tweet_media_format(video_tweet, "https://x.com/u/status/1"), MediaFormat.VIDEO)
        photo_tweet = {"media": [{"type": "photo", "url": "https://img/1.jpg"}], "full_text": "hi"}
        self.assertEqual(tweet_media_format(photo_tweet, "https://x.com/u/status/2"), MediaFormat.IMAGE)
        text_tweet = {"full_text": "just words"}
        self.assertEqual(tweet_media_format(text_tweet, "https://x.com/u/status/3"), MediaFormat.TEXT)


if __name__ == "__main__":
    unittest.main()
