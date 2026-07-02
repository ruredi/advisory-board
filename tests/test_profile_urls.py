from __future__ import annotations

import unittest

from memory_builder.discovery.profile_urls import canonicalize_profile_url, profile_identity_key
from memory_builder.discovery.source_discovery import discover_persona_source_candidates, _candidate_from_url, _merge_candidate
from memory_builder.source_registry import SourceCandidate


class ProfileUrlCanonicalizationTests(unittest.TestCase):
    def test_youtube_strips_videos_subpage(self) -> None:
        url = canonicalize_profile_url("https://youtube.com/@AlexHormozi/videos")
        self.assertEqual(url, "https://youtube.com/@AlexHormozi")

    def test_youtube_c_path_maps_to_handle(self) -> None:
        url = canonicalize_profile_url("https://youtube.com/c/Acquisitioncom")
        self.assertEqual(url, "https://youtube.com/@Acquisitioncom")

    def test_x_username_case_insensitive(self) -> None:
        lower = canonicalize_profile_url("https://x.com/alexhormozi")
        upper = canonicalize_profile_url("https://x.com/AlexHormozi")
        self.assertEqual(lower, "https://x.com/alexhormozi")
        self.assertEqual(upper, "https://x.com/alexhormozi")

    def test_x_and_youtube_share_identity_keys_for_variants(self) -> None:
        self.assertEqual(
            profile_identity_key("https://x.com/AlexHormozi"),
            profile_identity_key("https://x.com/alexhormozi"),
        )
        self.assertEqual(
            profile_identity_key("https://youtube.com/c/Acquisitioncom"),
            profile_identity_key("https://youtube.com/@Acquisitioncom"),
        )

    def test_rejects_non_profile_paths(self) -> None:
        self.assertIsNone(canonicalize_profile_url("https://youtube.com/watch?v=abc"))
        self.assertIsNone(canonicalize_profile_url("https://x.com/home"))


class ProfileCandidateMergeTests(unittest.TestCase):
    def test_merge_deduplicates_case_variants(self) -> None:
        store: dict[str, SourceCandidate] = {}
        first = _candidate_from_url(
            "https://x.com/alexhormozi",
            "seed_file",
            ["acquisition.com"],
        )
        second = _candidate_from_url(
            "https://x.com/AlexHormozi",
            "official_site",
            ["acquisition.com"],
            display_name="Alex Hormozi",
            speaker_names=["Alex Hormozi", "Hormozi"],
        )
        assert first is not None
        assert second is not None
        _merge_candidate(store, first)
        _merge_candidate(store, second)
        self.assertEqual(len(store), 1)
        winner = next(iter(store.values()))
        self.assertEqual(winner.url, "https://x.com/alexhormozi")
        self.assertEqual(winner.discovery_source, "official_site")

    def test_merge_deduplicates_youtube_c_and_handle(self) -> None:
        store: dict[str, SourceCandidate] = {}
        c_path = _candidate_from_url(
            "https://youtube.com/c/Acquisitioncom",
            "seed_file",
            ["acquisition.com"],
        )
        handle = _candidate_from_url(
            "https://youtube.com/@Acquisitioncom",
            "seed_file",
            ["acquisition.com"],
        )
        assert c_path is not None
        assert handle is not None
        _merge_candidate(store, c_path)
        _merge_candidate(store, handle)
        self.assertEqual(len(store), 1)
        self.assertEqual(next(iter(store.values())).url, "https://youtube.com/@Acquisitioncom")


class HormoziDiscoveryDedupTests(unittest.TestCase):
    def test_hormozi_candidates_have_no_obvious_duplicates(self) -> None:
        candidates = discover_persona_source_candidates("hormozi")
        urls = [candidate.url for candidate in candidates]
        keys = [profile_identity_key(url) for url in urls]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertNotIn("https://youtube.com/@AlexHormozi/videos", urls)
        self.assertNotIn("https://youtube.com/c/Acquisitioncom", urls)


if __name__ == "__main__":
    unittest.main()
