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
    assert "thanks for holding" not in response.text


def test_fake_company_menu_enters_hold_then_waits_for_speech() -> None:
    response = TestClient(app).post("/fake-company/menu", data={"Digits": "1"})

    assert response.status_code == 200
    assert "<Play>" in response.text
    assert 'voice="Telnyx.Ultra.' in response.text
    assert "please hold for the next available reservations agent" in response.text
    assert "thanks for holding, this is sarah with willow creek hotel reservations" in response.text
    assert 'input="speech"' in response.text
    assert "/fake-company/reservation?step=guest_name" in response.text


def test_fake_company_reservation_advances_one_step_after_speech() -> None:
    response = TestClient(app).post(
        "/fake-company/reservation?step=guest_name",
        data={"SpeechResult": "i am calling to book a one night hotel reservation"},
    )

    assert response.status_code == 200
    assert "may i have the guest name for the reservation" in response.text
    assert "/fake-company/reservation?step=check_in" in response.text
    assert "what date would you like to check in" not in response.text


def test_fake_company_reservation_completes_after_confirmation() -> None:
    response = TestClient(app).post(
        "/fake-company/reservation?step=complete",
        data={"SpeechResult": "yes please reserve that"},
    )

    assert response.status_code == 200
    assert "i have reserved a standard room for alex morgan" in response.text
    assert "<Hangup/>" in response.text


def test_fake_company_dtmf_endpoint_returns_wav() -> None:
    response = TestClient(app).get("/fake-company/dtmf/1.wav")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content.startswith(b"RIFF")
