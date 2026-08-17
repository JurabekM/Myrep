"""Lead import adapters: Alibaba, LinkedIn, CSV and an offline demo feed."""

from __future__ import annotations

import csv
import json
import random
from abc import abstractmethod
from pathlib import Path

from app.integrations.base import BaseProvider, ProviderResult
from app.utils.formatting import today
from app.utils.logging_setup import get_logger

log = get_logger(__name__)

#: Canonical fields produced by every lead import adapter.
LEAD_FIELDS = (
    "company_name",
    "contact_person",
    "country",
    "city",
    "email",
    "phone",
    "website",
    "linkedin",
    "buyer_type",
    "product_interest",
    "message",
    "source",
    "external_ref",
)


class LeadImportProvider(BaseProvider):
    """Fetches raw buyer/lead records from an external channel."""

    kind = "lead_import"

    @abstractmethod
    def fetch_leads(self, limit: int = 50) -> ProviderResult:
        """Return a list of lead dictionaries in ``ProviderResult.data``."""

    @staticmethod
    def normalize(raw: dict, source: str) -> dict:
        """Map an arbitrary record onto the canonical lead field set."""
        lowered = {str(key).strip().lower().replace(" ", "_"): value for key, value in raw.items()}
        result = dict.fromkeys(LEAD_FIELDS, "")
        aliases = {
            "company_name": ("company_name", "company", "buyer", "organisation", "organization"),
            "contact_person": ("contact_person", "contact", "name", "full_name"),
            "country": ("country", "location_country"),
            "city": ("city", "town"),
            "email": ("email", "e-mail", "mail"),
            "phone": ("phone", "telephone", "mobile", "tel"),
            "website": ("website", "site", "url"),
            "linkedin": ("linkedin", "linkedin_url", "profile"),
            "buyer_type": ("buyer_type", "type", "category"),
            "product_interest": ("product_interest", "product", "interest", "subject"),
            "message": ("message", "inquiry", "note", "notes", "text"),
            "external_ref": ("external_ref", "id", "ref", "rfq_id"),
        }
        for field, keys in aliases.items():
            for key in keys:
                if lowered.get(key):
                    result[field] = str(lowered[key]).strip()
                    break
        result["source"] = source
        return result


class DemoLeadProvider(LeadImportProvider):
    """Generates plausible export enquiries without any network access."""

    code = "demo_leads"
    label = "Demo lead feed (offline)"
    is_demo = True

    _SAMPLES = [
        ("Baltic Home Textile OÜ", "Marek Tamm", "Estonia", "Tallinn", "importer", "Bath towels"),
        ("Gulf Fresh Foods LLC", "Ahmed Al Farsi", "UAE", "Dubai", "distributor", "Dried apricots"),
        ("Anadolu Tekstil A.Ş.", "Emre Yilmaz", "Turkey", "Istanbul", "wholesaler", "Bed linen"),
        (
            "Nordwind Handel GmbH",
            "Klara Fischer",
            "Germany",
            "Hamburg",
            "importer",
            "Organic dried fruit",
        ),
        (
            "Almaty Retail Group",
            "Dinara Serik",
            "Kazakhstan",
            "Almaty",
            "retailer",
            "Ceramic tableware",
        ),
        ("Seoul Living Co.", "Ji-woo Park", "South Korea", "Seoul", "distributor", "Cotton towels"),
    ]

    def test_connection(self) -> ProviderResult:
        """Always available."""
        return ProviderResult.success("Demo lead feed ready")

    def fetch_leads(self, limit: int = 50) -> ProviderResult:
        """Return a small randomised batch of demo enquiries."""
        rng = random.Random(today().toordinal())
        picked = rng.sample(self._SAMPLES, k=min(limit, len(self._SAMPLES)))
        leads = []
        for index, (company, contact, country, city, buyer_type, product) in enumerate(picked, 1):
            leads.append(
                {
                    "company_name": company,
                    "contact_person": contact,
                    "country": country,
                    "city": city,
                    "email": f"purchase@{company.split()[0].lower()}.example",
                    "phone": f"+99871000{index:04d}",
                    "website": "",
                    "linkedin": "",
                    "buyer_type": buyer_type,
                    "product_interest": product,
                    "message": f"Please send your best price and MOQ for {product}.",
                    "source": "demo",
                    "external_ref": f"DEMO-{today().year}-{index:03d}",
                }
            )
        return ProviderResult.success(f"{len(leads)} demo lead(s)", data=leads)


class CSVImportAdapter(LeadImportProvider):
    """Reads leads from a delimited text file exported by any platform."""

    code = "csv"
    label = "CSV / TSV file"
    fields = (("file_path", "File path", False), ("delimiter", "Delimiter", False))

    def test_connection(self) -> ProviderResult:
        """Check that the configured file exists."""
        path = Path(self.settings.get("file_path") or "")
        if not path.exists():
            return ProviderResult.failure("File not found")
        return ProviderResult.success(f"File found: {path.name}")

    def fetch_leads(self, limit: int = 500) -> ProviderResult:
        """Parse the file and normalise every row."""
        path = Path(self.settings.get("file_path") or "")
        if not path.exists():
            return ProviderResult.failure("File not found")
        delimiter = self.settings.get("delimiter") or ","
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, delimiter=delimiter)
                rows = [self.normalize(row, "manual") for _, row in zip(range(limit), reader)]
            return ProviderResult.success(f"{len(rows)} row(s) read", data=rows)
        except Exception as exc:
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")


class _HttpLeadAdapter(LeadImportProvider):
    """Shared implementation for HTTP-based marketplace adapters."""

    endpoint_setting = "endpoint"

    def test_connection(self) -> ProviderResult:
        """Issue a HEAD request against the configured endpoint."""
        endpoint = self.settings.get(self.endpoint_setting) or ""
        if not endpoint:
            return ProviderResult.failure("Endpoint is not configured")
        if not self.secrets.get("api_key"):
            return ProviderResult.failure("API key is not configured")
        try:
            import httpx

            with httpx.Client(timeout=15) as client:
                response = client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {self.secrets['api_key']}"},
                    params={"limit": 1},
                )
            if response.status_code >= 400:
                return ProviderResult.failure(f"HTTP {response.status_code}")
            return ProviderResult.success("Connection successful")
        except Exception as exc:
            log.warning("%s test failed: %s", self.code, type(exc).__name__)
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")

    def fetch_leads(self, limit: int = 50) -> ProviderResult:
        """Download and normalise enquiries from the configured endpoint."""
        endpoint = self.settings.get(self.endpoint_setting) or ""
        if not endpoint or not self.secrets.get("api_key"):
            return ProviderResult.failure("Adapter is not configured")
        try:
            import httpx

            with httpx.Client(timeout=30) as client:
                response = client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {self.secrets['api_key']}"},
                    params={"limit": limit},
                )
            if response.status_code >= 400:
                return ProviderResult.failure(f"HTTP {response.status_code}")
            payload = response.json()
            records = payload if isinstance(payload, list) else payload.get("items", [])
            rows = [self.normalize(record, self.code) for record in records[:limit]]
            return ProviderResult.success(f"{len(rows)} lead(s) imported", data=rows)
        except Exception as exc:
            log.warning("%s fetch failed: %s", self.code, type(exc).__name__)
            return ProviderResult.failure(f"{type(exc).__name__}: {exc}")


class AlibabaImportAdapter(_HttpLeadAdapter):
    """Pulls RFQ enquiries from an Alibaba-compatible export endpoint."""

    code = "alibaba"
    label = "Alibaba RFQ import"
    fields = (("endpoint", "RFQ endpoint URL", False), ("api_key", "API key", True))


class LinkedInImportAdapter(_HttpLeadAdapter):
    """Pulls contacts exported from LinkedIn lead generation forms."""

    code = "linkedin"
    label = "LinkedIn lead import"
    fields = (("endpoint", "Lead form endpoint URL", False), ("api_key", "Access token", True))


def dump_leads(rows: list[dict]) -> str:
    """Serialise imported leads for the sync log."""
    return json.dumps(rows[:20], ensure_ascii=False, indent=2)
