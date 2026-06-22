from telnyx_hold_agent.orchestrator import extract_call_control_id, extract_event_type, extract_transcript


def test_extract_telnyx_event_fields() -> None:
    payload = {
        "data": {
            "event_type": "call.transcription",
            "payload": {
                "call_control_id": "abc",
                "transcription_data": {"transcript": "thanks for holding"},
            },
        }
    }

    assert extract_event_type(payload) == "call.transcription"
    assert extract_call_control_id(payload) == "abc"
    assert extract_transcript(payload) == "thanks for holding"

