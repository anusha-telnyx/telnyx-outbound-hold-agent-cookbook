from fastapi.testclient import TestClient

from telnyx_hold_agent.server import app


def test_fake_company_texml_includes_hotel_hold_and_representative_cues() -> None:
    response = TestClient(app).get("/fake-company/texml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "willow creek hotel" in response.text
    assert "<Play>" in response.text
    assert "please hold for the next available reservations agent" in response.text
    assert "thanks for holding, this is sarah with willow creek hotel reservations" in response.text
    assert "may i have the guest name for the reservation" in response.text
    assert "i have reserved a standard room for alex morgan" in response.text


def test_fake_company_dtmf_endpoint_returns_wav() -> None:
    response = TestClient(app).get("/fake-company/dtmf/1.wav")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content.startswith(b"RIFF")
