from memory_builder.telemetry.run_mode import REPROCESS_MODE, describe_run_mode, resolve_run_mode


def test_describe_run_mode() -> None:
    assert describe_run_mode(skip_discovery=True) == "Feldolgozás"
    assert describe_run_mode(discover_only=True) == "Keresés"
    assert describe_run_mode() == "Keresés + feldolgozás"
    assert describe_run_mode(reprocess_transcripts=True) == REPROCESS_MODE
    assert describe_run_mode(reprocess_transcripts=True, skip_discovery=True) == REPROCESS_MODE


def test_resolve_run_mode_from_options() -> None:
    assert (
        resolve_run_mode(
            options={"skip_discovery": True},
            sources_discovered=0,
            sources_processed=0,
        )
        == "Feldolgozás"
    )
    assert (
        resolve_run_mode(
            options={"reprocess_transcripts": True},
            sources_discovered=0,
            sources_processed=0,
        )
        == REPROCESS_MODE
    )


def test_resolve_run_mode_from_counts() -> None:
    assert (
        resolve_run_mode(
            options=None,
            sources_discovered=100,
            sources_processed=0,
        )
        == "Keresés"
    )


def test_resolve_run_mode_from_discovery_events() -> None:
    assert (
        resolve_run_mode(
            options=None,
            sources_discovered=0,
            sources_processed=0,
            had_discovery=True,
        )
        == "Keresés"
    )


def test_resolve_run_mode_from_processing_events() -> None:
    assert (
        resolve_run_mode(
            options=None,
            sources_discovered=0,
            sources_processed=0,
            had_processing=True,
        )
        == "Feldolgozás"
    )


def test_resolve_run_mode_from_lifecycle_only() -> None:
    assert (
        resolve_run_mode(
            options=None,
            sources_discovered=0,
            sources_processed=0,
            had_run_started=True,
        )
        == "Feldolgozás"
    )
