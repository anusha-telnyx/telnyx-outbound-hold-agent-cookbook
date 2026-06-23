from telnyx_hold_agent.models import DtmfToolRequest, HoldDetectedToolRequest, normalize_tool_payload


def test_normalizes_nested_tool_arguments() -> None:
    payload = {
        "data": {
            "arguments": {
                "digits": "1",
                "reason": "reservations option",
            }
        }
    }

    request = DtmfToolRequest.model_validate(normalize_tool_payload(payload))

    assert request.digits == "1"
    assert request.reason == "reservations option"


def test_normalizes_stringified_tool_arguments() -> None:
    payload = {"arguments": '{"callControlId":"abc","dtmf_digits":"2","reason":"front desk"}'}

    request = DtmfToolRequest.model_validate(normalize_tool_payload(payload))

    assert request.call_control_id == "abc"
    assert request.digits == "2"
    assert request.reason == "front desk"


def test_normalizes_nullable_wrapper_fields() -> None:
    payload = {
        "data": {
            "call_control_id": None,
            "arguments": '{"digits":"1","reason":"select reservations"}',
        }
    }

    request = DtmfToolRequest.model_validate(normalize_tool_payload(payload))

    assert request.call_control_id == ""
    assert request.digits == "1"
    assert request.reason == "select reservations"


def test_normalizes_hold_detected_arguments() -> None:
    payload = {"parameters": {"reason": "queue prompt", "confidence": 0.9}}

    request = HoldDetectedToolRequest.model_validate(normalize_tool_payload(payload))

    assert request.reason == "queue prompt"
    assert request.confidence == 0.9
