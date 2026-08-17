"""Adapter fallbacks, demo channel ingestion and report generation."""

from __future__ import annotations

import tempfile
from datetime import timedelta
from pathlib import Path

from app.integrations.channels import DemoChannelAdapter
from app.integrations.crm import InternalCRMExporter
from app.integrations.llm import DemoRuleBasedProvider
from app.integrations.telephony import DemoTelephonyAdapter
from app.models.enums import Channel
from app.reports import excel_export, pdf_export, report_builder
from app.services import conversation_service, integration_service
from app.services.analytics_service import PeriodFilter
from app.utils.dates import today


# --------------------------------------------------------------------------- #
# Adapter resolution
# --------------------------------------------------------------------------- #
def test_channel_adapter_falls_back_to_demo() -> None:
    """Without credentials every channel resolves to the demo adapter."""
    for channel in (Channel.TELEGRAM, Channel.WHATSAPP, Channel.INSTAGRAM, Channel.WEBSITE):
        adapter = integration_service.channel_adapter(channel)
        assert adapter.is_demo


def test_llm_falls_back_to_the_rule_based_agent() -> None:
    """The deterministic agent is used when no LLM key is configured."""
    provider = integration_service.llm_provider()
    assert isinstance(provider, DemoRuleBasedProvider)
    assert provider.test_connection().ok


def test_telephony_and_crm_fall_back_to_demo() -> None:
    """Telephony and CRM exporters degrade gracefully."""
    assert isinstance(integration_service.telephony_adapter(), DemoTelephonyAdapter)
    assert isinstance(integration_service.crm_exporter(), InternalCRMExporter)


def test_unconfigured_real_adapter_reports_a_clear_status() -> None:
    """A real adapter without credentials never raises, it reports its state."""
    from app.integrations.channels import TelegramAdapter

    adapter = TelegramAdapter()
    result = adapter.test_connection()
    assert not result.ok
    assert result.error_code == "not_configured"
    assert adapter.status() == "not_configured"


def test_status_overview_lists_every_provider() -> None:
    """The top bar receives one entry per tracked provider."""
    overview = integration_service.status_overview()
    providers = {entry["provider"] for entry in overview}
    assert {"telegram", "whatsapp", "instagram", "openai_compatible"} <= providers


# --------------------------------------------------------------------------- #
# Demo channel round trip
# --------------------------------------------------------------------------- #
def test_demo_channel_simulates_and_ingests_a_new_lead() -> None:
    """A simulated message creates a lead, a conversation and a message."""
    adapter = DemoChannelAdapter(Channel.DEMO, seed=42)
    message = adapter.simulate_new_lead(Channel.TELEGRAM)
    assert message.text
    drained = adapter.poll()
    assert len(drained) == 1

    result = conversation_service.ingest_incoming(drained[0])
    assert result["lead_id"] > 0
    assert result["conversation_id"] > 0
    assert result["is_new_lead"] == 1

    messages = conversation_service.messages_of(result["conversation_id"])
    assert messages[-1].body == message.text


def test_demo_telephony_produces_an_analysable_call() -> None:
    """The demo telephony adapter returns a scripted transcript."""
    adapter = DemoTelephonyAdapter(seed=7)
    result = adapter.place_call("+998901234567")
    assert result.ok
    call = result.data["call"]
    assert call.transcript_text


def test_call_analysis_extracts_structured_fields() -> None:
    """The rule-based analyser fills every documented field."""
    provider = DemoRuleBasedProvider()
    analysis = provider.analyze_call(
        "Operator: Assalomu alaykum. Mijoz: Meni ertaga yozing, raqamim +998901234567.",
        "uz",
    )
    for key in (
        "summary",
        "customer_need",
        "objections",
        "operator_mistakes",
        "next_best_action",
        "sentiment",
        "quality_score",
    ):
        assert key in analysis
    assert 0 <= analysis["quality_score"] <= 100


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
def test_every_report_builds_and_exports() -> None:
    """All 12 reports produce non-empty PDF and Excel files."""
    flt = PeriodFilter(date_from=today() - timedelta(days=120), date_to=today())
    with tempfile.TemporaryDirectory() as tmp:
        for spec in report_builder.REPORTS:
            sections = report_builder.build(spec.key, flt)
            assert sections, spec.key
            payload = [(s.title, s.headers, s.rows) for s in sections]

            pdf_path = Path(tmp) / f"{spec.key}.pdf"
            pdf_export.build_report(str(pdf_path), spec.key, payload)
            assert pdf_path.exists() and pdf_path.stat().st_size > 800

            xlsx_path = Path(tmp) / f"{spec.key}.xlsx"
            excel_export.export_table(str(xlsx_path), payload)
            assert xlsx_path.exists() and xlsx_path.stat().st_size > 2000


def test_lead_excel_round_trip(admin) -> None:
    """Exported leads can be read back by the importer."""
    from app.repositories.lead_repository import LeadFilter
    from app.services import lead_service

    leads, _ = lead_service.search_leads(LeadFilter(), actor=admin, limit=20)
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "leads.xlsx")
        excel_export.export_leads(leads, path)
        parsed = excel_export.import_leads(path)
    assert len(parsed) == len(leads)
    assert all("channel" in row and "status" in row for row in parsed)
