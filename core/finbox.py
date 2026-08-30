import os
import requests
from django.conf import settings

class FinboxClient:
    def __init__(self):
        # Base URLs for UAT and Production (from postman collection)
        self.uat_base_url = getattr(settings, "FINBOX_UAT_BASE_URL", "https://apis-uat.bankconnect.finbox.in")
        self.prod_base_url = getattr(settings, "FINBOX_PROD_BASE_URL", "https://apis.bankconnect.finbox.in")
        
        # Credentials for Session Management (UAT by default in collection)
        self.uat_api_key = getattr(settings, "FINBOX_UAT_API_KEY", "VUWvcQZ4TRi3Ylpvazah2CuamS0xUxxi6zFmPb8w")
        self.uat_server_hash = getattr(settings, "FINBOX_UAT_SERVER_HASH", "a8017c902a444b7f8613fa88e2013034")
        
        # Credentials for Fetching Raw AA (Production by default in collection)
        self.prod_api_key = getattr(settings, "FINBOX_PROD_API_KEY", "wOK0Ra3Sn0QGmPl02cNl3qLfkhyaeXxNjQa0c0PC")
        self.prod_server_hash = getattr(settings, "FINBOX_PROD_SERVER_HASH", "d0ddf3f57aaa463bbb4e87809c1d0edb")

    def create_session(self, username, email, return_url="https://www.tatacapital.com?data="):
        """Call Create Session UAT API.
        
        Returns response dict containing 'redirectUrl' and 'tclStatementID'.
        """
        url = f"{self.uat_base_url.rstrip('/')}/bank-connect/v1/session/"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.uat_api_key,
            "server-hash": self.uat_server_hash
        }
        body = {
            "loanType": "Business Loan",
            "applicantId": str(username),
            "sourceSystemURL": return_url,
            "webtopNo": "386BZ9015698",
            "only_raw_xml_required": True,
            "program_id": "37289951-ce84-4fe0-93f0-b8776ce25897",
            "yearMonthFrom": "2025-07",
            "yearMonthTo": "2026-01",
            "aa_vendor": ""
        }
        try:
            r = requests.post(url, json=body, headers=headers, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print("Finbox create_session error:", e)
        return None

    def fetch_raw_aa(self, session_id):
        """Call Fetch Raw AA Production API to get PDF/XML statements list."""
        url = f"{self.prod_base_url.rstrip('/')}/bank-connect/v1/session_data/{session_id}/get_pdfs/"
        headers = {
            "x-api-key": self.prod_api_key,
            "server-hash": self.prod_server_hash
        }
        params = {
            "send_aa_data": "true",
            "aa_data_format": "xml"
        }
        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print("Finbox fetch_raw_aa error:", e)
        return None

    def download_xml(self, download_url):
        """Download raw XML document from secure statement S3 link."""
        try:
            r = requests.get(download_url, timeout=15)
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print("Finbox download_xml error:", e)
        return None

    def fetch_transactions(self, session_id):
        """Call Transactions API to get processed transaction logs.
        Attempts Production host first, then falls back to UAT host.
        """
        # 1. Try Production
        url_prod = f"{self.prod_base_url.rstrip('/')}/bank-connect/v1/entity/{session_id}/transactions/"
        headers_prod = {
            "x-api-key": self.prod_api_key,
            "server-hash": self.prod_server_hash
        }
        try:
            r = requests.get(url_prod, headers=headers_prod, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get("transactions"):
                    return data
        except Exception as e:
            print("Finbox fetch_transactions Production error:", e)
            
        # 2. Try UAT
        url_uat = f"{self.uat_base_url.rstrip('/')}/bank-connect/v1/entity/{session_id}/transactions/"
        headers_uat = {
            "x-api-key": self.uat_api_key,
            "server-hash": self.uat_server_hash
        }
        try:
            r = requests.get(url_uat, headers=headers_uat, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get("transactions"):
                    return data
        except Exception as e:
            print("Finbox fetch_transactions UAT error:", e)
            
        return None

    def fetch_session_progress_status(self, session_id):
        """Call Session Progress UAT API to get direct XML response."""
        url = f"{self.uat_base_url.rstrip('/')}/bank-connect/v1/session_data/session_progress_status/"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.uat_api_key,
            "server-hash": self.uat_server_hash
        }
        body = {
            "perfiosTransactionId": str(session_id)
        }
        try:
            r = requests.post(url, json=body, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print("Finbox fetch_session_progress_status error:", e)
        return None


