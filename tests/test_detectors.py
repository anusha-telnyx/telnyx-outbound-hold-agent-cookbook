from telnyx_hold_agent.detectors import HoldDetector, RepresentativeDetector


def test_hold_detector_matches_strong_queue_phrase() -> None:
    result = HoldDetector().evaluate("Your call is important to us. Please hold for the next available representative.")
    assert result.matched
    assert result.confidence >= 0.72


def test_representative_detector_rejects_queue_announcement() -> None:
    result = RepresentativeDetector().evaluate("All representatives are busy. Please continue to hold.")
    assert not result.matched


def test_representative_detector_matches_human_greeting() -> None:
    result = RepresentativeDetector().evaluate("Thanks for holding, this is Sarah. How can I help you?")
    assert result.matched

