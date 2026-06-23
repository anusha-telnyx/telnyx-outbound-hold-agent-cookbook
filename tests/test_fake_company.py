from fastapi.testclient import TestClient

from telnyx_hold_agent.server import app


def test_fake_company_texml_starts_with_dtmf_menu() -> None:
    response = TestClient(app).get("/fake-company/texml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "willow creek hotel" in response.text
    assert 'voice="Telnyx.Ultra.' in response.text
    assert 'input="dtmf"' in response.text
    assert "/fake-company/menu" in response.text
    assert "for reservations, press 1" in response.text
    assert "<Play>" not in response.text
    assert "thanks for holding" not in response.text


def test_fake_company_menu_enters_hold_then_pauses_for_representative_assistant() -> None:
    response = TestClient(app).post("/fake-company/menu", data={"Digits": "1"})

    assert response.status_code == 200
    assert "<Play>" in response.text
    assert 'voice="Telnyx.Ultra.' in response.text
    assert "please hold for the next available reservations agent" in response.text
    assert "thanks for holding, this is sarah with willow creek hotel reservations" in response.text
    assert '<Pause length="60"/>' in response.text
    assert "/fake-company/reservation" not in response.text


def test_fake_company_menu_timeout_fallback_does_not_play_late_click() -> None:
    response = TestClient(app).post("/fake-company/menu", data={})

    assert response.status_code == 200
    assert "<Play>" not in response.text
    assert "connecting you to reservations" in response.text
    assert "/fake-company/menu?Digits=1" in response.text


def test_fake_company_dtmf_endpoint_returns_wav() -> None:
    response = TestClient(app).get("/fake-company/dtmf/1.wav")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content.startswith(b"RIFF")
