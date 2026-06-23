from fastapi.testclient import TestClient

from telnyx_hold_agent.server import app


def test_fake_company_texml_includes_hotel_hold_and_representative_cues() -> None:
    response = TestClient(app).get("/fake-company/texml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "willow creek hotel" in response.text
    assert "please hold for the next available reservations agent" in response.text
    assert "thanks for holding, this is sarah at the willow creek hotel front desk" in response.text
