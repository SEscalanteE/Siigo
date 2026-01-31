"""Siigo API Client for Invoice Management."""

import requests
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class SiigoAuthError(Exception):
    pass


class SiigoAPIError(Exception):
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class SiigoClient:
    BASE_URL = "https://api.siigo.com"
    AUTH_ENDPOINT = "/auth"
    INVOICES_ENDPOINT = "/v1/invoices"

    def __init__(self, username: str, access_key: str, application_name: str = "MyApp"):
        self.username = username
        self.access_key = access_key
        self.application_name = application_name
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        if self._needs_token_refresh():
            self._authenticate()
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "Partner-Id": self.application_name,
        }

    def _needs_token_refresh(self) -> bool:
        if not self._access_token or not self._token_expiry:
            return True
        return datetime.now() >= self._token_expiry - timedelta(hours=1)

    def _authenticate(self) -> None:
        url = f"{self.BASE_URL}{self.AUTH_ENDPOINT}"
        payload = {"username": self.username, "access_key": self.access_key}
        headers = {"Content-Type": "application/json", "Partner-Id": self.application_name}

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            self._access_token = response.json().get("access_token")
            self._token_expiry = datetime.now() + timedelta(hours=24)
        except requests.exceptions.HTTPError as e:
            raise SiigoAuthError(f"Authentication failed: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise SiigoAuthError(f"Connection error: {str(e)}")

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_auth_headers()

        try:
            response = requests.request(method=method, url=url, headers=headers, json=data, params=params)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            error_response = {}
            try:
                error_response = e.response.json()
            except:
                pass
            raise SiigoAPIError(
                f"API request failed: {e.response.status_code} - {e.response.text}",
                status_code=e.response.status_code,
                response=error_response
            )
        except requests.exceptions.RequestException as e:
            raise SiigoAPIError(f"Connection error: {str(e)}")
    
    def get_invoices(
        self,
        page: int = 1,
        page_size: int = 25,
        created_start: Optional[str] = None,
        created_end: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        updated_start: Optional[str] = None,
        updated_end: Optional[str] = None,
        customer_identification: Optional[str] = None,
        customer_branch_office: Optional[int] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = {"page": page, "page_size": min(page_size, 100)}
        if created_start:
            params["created_start"] = created_start
        if created_end:
            params["created_end"] = created_end
        if date_start:
            params["date_start"] = date_start
        if date_end:
            params["date_end"] = date_end
        if updated_start:
            params["updated_start"] = updated_start
        if updated_end:
            params["updated_end"] = updated_end
        if customer_identification:
            params["customer_identification"] = customer_identification
        if customer_branch_office:
            params["customer_branch_office"] = customer_branch_office
        if name:
            params["name"] = name
        return self._make_request("GET", self.INVOICES_ENDPOINT, params=params)

    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        return self._make_request("GET", f"{self.INVOICES_ENDPOINT}/{invoice_id}")

    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._make_request("POST", self.INVOICES_ENDPOINT, data=invoice_data)

    def update_invoice(self, invoice_id: str, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._make_request("PUT", f"{self.INVOICES_ENDPOINT}/{invoice_id}", data=invoice_data)

    def delete_invoice(self, invoice_id: str) -> Dict[str, Any]:
        return self._make_request("DELETE", f"{self.INVOICES_ENDPOINT}/{invoice_id}")

    def get_invoice_pdf(self, invoice_id: str) -> bytes:
        url = f"{self.BASE_URL}{self.INVOICES_ENDPOINT}/{invoice_id}/pdf"
        headers = self._get_auth_headers()
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.content
        except requests.exceptions.HTTPError as e:
            raise SiigoAPIError(f"Failed to get invoice PDF: {e.response.status_code}", status_code=e.response.status_code)

    def send_invoice_email(self, invoice_id: str, email: str, copy_to: Optional[List[str]] = None) -> Dict[str, Any]:
        data = {"mail_to": email}
        if copy_to:
            data["copy_to"] = copy_to
        return self._make_request("POST", f"{self.INVOICES_ENDPOINT}/{invoice_id}/mail", data=data)
    
    def get_document_types(self) -> List[Dict[str, Any]]:
        return self._make_request("GET", "/v1/document-types", params={"type": "FV"})

    def get_payment_types(self, document_type: str = "FV") -> List[Dict[str, Any]]:
        return self._make_request("GET", "/v1/payment-types", params={"document_type": document_type})

    def get_taxes(self) -> List[Dict[str, Any]]:
        return self._make_request("GET", "/v1/taxes")

    def get_sellers(self) -> List[Dict[str, Any]]:
        return self._make_request("GET", "/v1/users", params={"role": "seller"})

    def get_products(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        return self._make_request("GET", "/v1/products", params={"page": page, "page_size": page_size})

    def get_customers(self, page: int = 1, page_size: int = 100, identification: str = None) -> Dict[str, Any]:
        params = {"page": page, "page_size": page_size}
        if identification:
            params["identification"] = identification
        return self._make_request("GET", "/v1/customers", params=params)

    def get_warehouses(self) -> List[Dict[str, Any]]:
        return self._make_request("GET", "/v1/warehouses")

    def get_cost_centers(self) -> List[Dict[str, Any]]:
        return self._make_request("GET", "/v1/cost-centers")
