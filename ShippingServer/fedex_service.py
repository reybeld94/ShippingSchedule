from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Any

import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class FedExService:
    def __init__(self):
        self.base_url = os.getenv("FEDEX_BASE_URL", "https://apis.fedex.com")
        self.timeout = int(os.getenv("FEDEX_TIMEOUT_SECONDS", "15"))
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._lock = threading.Lock()

    def _token_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/oauth/token"

    def _track_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/track/v1/trackingnumbers"

    def get_fedex_access_token(self, api_key: str, secret_key: str) -> str:
        now = time.time()
        if self._token and now < (self._token_expires_at - 60):
            return self._token

        with self._lock:
            now = time.time()
            if self._token and now < (self._token_expires_at - 60):
                return self._token

            payload = {
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key,
            }
            try:
                response = requests.post(
                    self._token_url(),
                    data=payload,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                raise HTTPException(status_code=502, detail="Unable to authenticate with FedEx right now") from exc

            if response.status_code != 200:
                body_preview = _safe_body_preview(response.text)
                logger.warning("FedEx auth failed: status=%s body=%s", response.status_code, body_preview)
                raise HTTPException(status_code=502, detail=_build_auth_error_detail(response.status_code))

            data = response.json()
            token = str(data.get("access_token") or "").strip()
            expires_in = int(data.get("expires_in") or 0)
            if not token:
                raise HTTPException(status_code=502, detail="FedEx authentication returned an invalid response")

            self._token = token
            self._token_expires_at = now + max(expires_in, 60)
            return token

    def track_fedex_number(self, tracking_number: str, api_key: str, secret_key: str) -> dict[str, Any]:
        token = self.get_fedex_access_token(api_key, secret_key)

        headers = {
            "Authorization": f"Bearer {token}",
            "content-type": "application/json",
            "x-locale": "en_US",
            "x-customer-transaction-id": str(uuid.uuid4()),
        }
        payload = {
            "includeDetailedScans": True,
            "trackingInfo": [
                {
                    "trackingNumberInfo": {
                        "trackingNumber": tracking_number,
                    }
                }
            ],
        }

        try:
            response = requests.post(
                self._track_url(),
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail="Unable to reach FedEx tracking service right now") from exc

        if response.status_code == 404:
            return {
                "success": False,
                "carrier": "FedEx",
                "trackingNumber": tracking_number,
                "message": "Tracking data not found",
                "events": [],
                "rawAlerts": [],
            }

        if response.status_code >= 400:
            logger.warning("FedEx tracking request failed: status=%s", response.status_code)
            raise HTTPException(status_code=502, detail="FedEx tracking request failed")

        raw = response.json()
        return normalize_fedex_tracking_response(tracking_number, raw)


def normalize_fedex_tracking_response(tracking_number: str, raw: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "success": False,
        "carrier": "FedEx",
        "trackingNumber": tracking_number,
        "status": None,
        "statusDescription": None,
        "estimatedDelivery": None,
        "deliveredAt": None,
        "destination": None,
        "packageCount": None,
        "serviceType": None,
        "events": [],
        "rawAlerts": [],
        "message": "Tracking data not found",
    }

    complete_results = (((raw or {}).get("output") or {}).get("completeTrackResults") or [])
    if not complete_results:
        return output

    result = complete_results[0] or {}
    track_results = result.get("trackResults") or []
    alerts = result.get("alerts") or []
    output["rawAlerts"] = alerts

    if not track_results:
        if alerts:
            output["message"] = "; ".join(str(a.get("message") or "") for a in alerts if isinstance(a, dict)).strip() or output["message"]
        return output

    track = track_results[0] or {}
    latest_status = track.get("latestStatusDetail") or {}
    destination = track.get("destinationLocation") or {}

    events = []
    for event in track.get("scanEvents") or []:
        if not isinstance(event, dict):
            continue
        location = event.get("scanLocation") or {}
        events.append(
            {
                "timestamp": event.get("date"),
                "eventType": event.get("eventType"),
                "description": event.get("eventDescription"),
                "city": location.get("city"),
                "stateOrProvinceCode": location.get("stateOrProvinceCode"),
                "countryCode": location.get("countryCode"),
            }
        )

    events.sort(key=lambda ev: str(ev.get("timestamp") or ""), reverse=True)

    output.update(
        {
            "success": True,
            "message": "",
            "status": latest_status.get("code") or track.get("latestStatusDetail", {}).get("statusByLocale"),
            "statusDescription": latest_status.get("description") or latest_status.get("statusByLocale"),
            "estimatedDelivery": track.get("estimatedDeliveryTimeWindow", {}).get("window", {}).get("ends")
            or track.get("estimatedDeliveryTimeWindow", {}).get("window", {}).get("begins")
            or track.get("dateAndTimes", [{}])[0].get("dateTime") if track.get("dateAndTimes") else None,
            "deliveredAt": _extract_date_time(track.get("dateAndTimes") or [], "ACTUAL_DELIVERY"),
            "destination": {
                "city": destination.get("city"),
                "stateOrProvinceCode": destination.get("stateOrProvinceCode"),
                "countryCode": destination.get("countryCode"),
            } if destination else None,
            "packageCount": track.get("packageCount"),
            "serviceType": track.get("serviceType"),
            "events": events,
        }
    )

    return output


def _extract_date_time(entries: list[dict[str, Any]], date_type: str) -> str | None:
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == date_type and entry.get("dateTime"):
            return str(entry["dateTime"])
    return None


def _safe_body_preview(raw_text: str, max_chars: int = 300) -> str:
    text = (raw_text or "").strip().replace("\n", " ")
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}..."


def _build_auth_error_detail(status_code: int) -> str:
    if status_code in (401, 403):
        return (
            "FedEx authentication failed: verify API Key/Secret Key and FEDEX_BASE_URL "
            "(sandbox credentials require https://apis-sandbox.fedex.com)"
        )
    return "FedEx authentication failed"
