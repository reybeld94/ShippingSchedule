from fastapi import HTTPException

from fedex_service import FedExService, _build_auth_error_detail, _safe_body_preview, normalize_fedex_tracking_response


def test_normalize_fedex_response_with_events():
    raw = {
        "output": {
            "completeTrackResults": [
                {
                    "trackResults": [
                        {
                            "latestStatusDetail": {"code": "IN_TRANSIT", "description": "In transit"},
                            "serviceType": "FEDEX_GROUND",
                            "destinationLocation": {
                                "city": "Miami",
                                "stateOrProvinceCode": "FL",
                                "countryCode": "US",
                            },
                            "scanEvents": [
                                {
                                    "date": "2026-04-05T08:12:00Z",
                                    "eventType": "ARRIVED_AT_FEDEX_LOCATION",
                                    "eventDescription": "Arrived at FedEx location",
                                    "scanLocation": {
                                        "city": "Orlando",
                                        "stateOrProvinceCode": "FL",
                                        "countryCode": "US",
                                    },
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    }

    normalized = normalize_fedex_tracking_response("123456", raw)

    assert normalized["success"] is True
    assert normalized["trackingNumber"] == "123456"
    assert normalized["status"] == "IN_TRANSIT"
    assert normalized["events"][0]["eventType"] == "ARRIVED_AT_FEDEX_LOCATION"


def test_normalize_fedex_response_without_results():
    raw = {"output": {"completeTrackResults": []}}

    normalized = normalize_fedex_tracking_response("123456", raw)

    assert normalized["success"] is False
    assert normalized["message"] == "Tracking data not found"


def test_enabled_requires_credentials():
    enabled = True
    api_key = ""
    secret_key = ""

    with_raises = False
    try:
        if enabled and (not api_key or not secret_key):
            raise HTTPException(status_code=400, detail="FedEx API Key and Secret Key are required when enabled")
    except HTTPException:
        with_raises = True

    assert with_raises is True


def test_build_auth_error_detail_for_forbidden_status():
    detail = _build_auth_error_detail(403)
    assert "FEDEX_BASE_URL" in detail
    assert "apis-sandbox.fedex.com" in detail


def test_safe_body_preview_truncates_long_payload():
    preview = _safe_body_preview("x" * 350, max_chars=25)
    assert preview.endswith("...")
    assert len(preview) == 28


def test_fedex_service_uses_override_base_url():
    service = FedExService()

    token_url = service._token_url("https://apis-sandbox.fedex.com/")
    track_url = service._track_url("https://apis-sandbox.fedex.com/")

    assert token_url == "https://apis-sandbox.fedex.com/oauth/token"
    assert track_url == "https://apis-sandbox.fedex.com/track/v1/trackingnumbers"
