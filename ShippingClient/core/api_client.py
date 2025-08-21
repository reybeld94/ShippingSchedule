import requests
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
import time
import json


@dataclass
class ApiResponse:
    """Respuesta estandarizada de la API"""
    success: bool
    data: Any = None
    error: str = ""
    status_code: int = 0

    def is_success(self) -> bool:
        return self.success

    def get_data(self) -> Any:
        return self.data if self.success else None

    def get_error(self) -> str:
        return self.error if not self.success else ""


class RobustApiClient:
    """Cliente API con retry automático y manejo robusto de errores"""

    def __init__(self, base_url: str, token: str, max_retries: int = 3, timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.max_retries = max_retries
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })

    def update_token(self, new_token: str):
        """Actualizar token de autenticación"""
        self.token = new_token
        self.session.headers.update({"Authorization": f"Bearer {new_token}"})

    def _make_request(self, method: str, endpoint: str, **kwargs) -> ApiResponse:
        """Hacer request con retry automático y manejo de errores"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        kwargs.setdefault('timeout', self.timeout)
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code in [200, 201]:
                    try:
                        data = response.json()
                        return ApiResponse(success=True, data=data, status_code=response.status_code)
                    except json.JSONDecodeError:
                        return ApiResponse(success=True, data=response.text, status_code=response.status_code)

                error_msg = self._extract_error_message(response)
                return ApiResponse(success=False, error=error_msg, status_code=response.status_code)

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < self.max_retries:
                    print(
                        f"Connection failed (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {attempt + 1} seconds...")
                    time.sleep(attempt + 1)
                    continue

            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    print(
                        f"Request timeout (attempt {attempt + 1}/{self.max_retries + 1}), retrying...")
                    time.sleep(1)
                    continue

            except requests.exceptions.RequestException as e:
                return ApiResponse(success=False, error=f"Request error: {str(e)}")

            except Exception as e:
                return ApiResponse(success=False, error=f"Unexpected error: {str(e)}")

        if isinstance(last_exception, requests.exceptions.ConnectionError):
            return ApiResponse(success=False, error="Unable to connect to server after multiple attempts")
        elif isinstance(last_exception, requests.exceptions.Timeout):
            return ApiResponse(success=False, error="Request timeout after multiple attempts")
        else:
            return ApiResponse(success=False, error=f"Max retries exceeded: {str(last_exception)}")

    def _extract_error_message(self, response: requests.Response) -> str:
        """Extraer mensaje de error legible de la respuesta"""
        try:
            error_data = response.json()
            if isinstance(error_data, dict) and 'detail' in error_data:
                return error_data['detail']
            elif isinstance(error_data, dict) and 'error' in error_data:
                return error_data['error']
            elif isinstance(error_data, dict) and 'message' in error_data:
                return error_data['message']
            else:
                return str(error_data)
        except (json.JSONDecodeError, ValueError):
            if response.text:
                return f"HTTP {response.status_code}: {response.text[:100]}"
            else:
                return f"HTTP {response.status_code}: {response.reason}"

    def get(self, endpoint: str, params: Optional[Dict] = None) -> ApiResponse:
        """GET request"""
        return self._make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict] = None) -> ApiResponse:
        """POST request"""
        return self._make_request("POST", endpoint, json=data)

    def put(self, endpoint: str, data: Optional[Dict] = None) -> ApiResponse:
        """PUT request"""
        return self._make_request("PUT", endpoint, json=data)

    def delete(self, endpoint: str) -> ApiResponse:
        """DELETE request"""
        return self._make_request("DELETE", endpoint)

    def get_shipments(self) -> ApiResponse:
        """Obtener todos los shipments"""
        return self.get("/shipments")

    def create_shipment(self, shipment_data: Dict) -> ApiResponse:
        """Crear nuevo shipment"""
        return self.post("/shipments", data=shipment_data)

    def update_shipment(self, shipment_id: int, data: Dict) -> ApiResponse:
        """Actualizar shipment existente"""
        return self.put(f"/shipments/{shipment_id}", data=data)

    def delete_shipment(self, shipment_id: int) -> ApiResponse:
        """Eliminar shipment"""
        return self.delete(f"/shipments/{shipment_id}")

    def login(self, username: str, password: str) -> ApiResponse:
        """Autenticar usuario"""
        return self.post("/login", data={"username": username, "password": password})
