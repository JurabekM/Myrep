"""Flask compatibility adapter.

The service layer is framework-agnostic, so the same business logic can be
exposed through Flask for teams standardized on it. This adapter bridges
Flask's sync views to the async services via asgiref's async_to_sync.

Production recommendation remains FastAPI (streaming, WebSocket, OpenAPI);
this module exists to satisfy the Flask-support requirement and covers the
deterministic calculator endpoints, which need no streaming.
"""

from asgiref.sync import async_to_sync
from flask import Flask, jsonify, request

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.finance.calculations import annuity_loan_schedule, break_even, irr, npv, roi
from app.modules.tax.calculator import (
    calculate_general_regime,
    calculate_payroll_taxes,
    calculate_turnover_tax,
    compare_regimes,
)


def create_flask_app() -> Flask:
    settings = get_settings()
    app = Flask(settings.app_name)

    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):  # type: ignore[no-untyped-def]
        return jsonify(exc.to_payload()), exc.status_code

    @app.get("/health")
    def health():  # type: ignore[no-untyped-def]
        return {"status": "ok", "adapter": "flask"}

    # --- Tax ---

    @app.post("/api/v1/tax/turnover")
    def tax_turnover():  # type: ignore[no-untyped-def]
        payload = request.get_json(force=True)
        result = calculate_turnover_tax(float(payload["annual_revenue"]))
        return jsonify(_dataclass_dict(result))

    @app.post("/api/v1/tax/general")
    def tax_general():  # type: ignore[no-untyped-def]
        payload = request.get_json(force=True)
        result = calculate_general_regime(
            float(payload["annual_revenue"]), float(payload["deductible_expenses"])
        )
        return jsonify(_dataclass_dict(result))

    @app.post("/api/v1/tax/payroll")
    def tax_payroll():  # type: ignore[no-untyped-def]
        payload = request.get_json(force=True)
        return jsonify(calculate_payroll_taxes(float(payload["gross_monthly_salary"])))

    @app.post("/api/v1/tax/compare")
    def tax_compare():  # type: ignore[no-untyped-def]
        payload = request.get_json(force=True)
        result = compare_regimes(
            float(payload["annual_revenue"]), float(payload["deductible_expenses"])
        )
        return jsonify(
            {
                "turnover": _dataclass_dict(result["turnover"]),
                "general": _dataclass_dict(result["general"]),
                "recommended": result["recommended"],
                "savings": result["savings"],
            }
        )

    # --- Finance ---

    @app.post("/api/v1/finance/npv")
    def finance_npv():  # type: ignore[no-untyped-def]
        payload = request.get_json(force=True)
        return jsonify({"npv": npv(float(payload["rate"]), list(payload["cash_flows"]))})

    @app.post("/api/v1/finance/irr")
    def finance_irr():  # type: ignore[no-untyped-def]
        payload = request.get_json(force=True)
        return jsonify({"irr": irr(list(payload["cash_flows"]))})

    @app.post("/api/v1/finance/roi")
    def finance_roi():  # type: ignore[no-untyped-def]
        payload = request.get_json(force=True)
        return jsonify({"roi": roi(float(payload["gain"]), float(payload["cost"]))})

    @app.post("/api/v1/finance/break-even")
    def finance_break_even():  # type: ignore[no-untyped-def]
        payload = request.get_json(force=True)
        result = break_even(
            float(payload["fixed_costs"]),
            float(payload["price_per_unit"]),
            float(payload["variable_cost_per_unit"]),
        )
        return jsonify(_dataclass_dict(result))

    @app.post("/api/v1/finance/loan")
    def finance_loan():  # type: ignore[no-untyped-def]
        payload = request.get_json(force=True)
        payment, schedule = annuity_loan_schedule(
            float(payload["principal"]), float(payload["annual_rate"]), int(payload["months"])
        )
        return jsonify(
            {"monthly_payment": payment, "schedule": [_dataclass_dict(r) for r in schedule]}
        )

    return app


def _dataclass_dict(obj):  # type: ignore[no-untyped-def]
    from dataclasses import asdict, is_dataclass

    return asdict(obj) if is_dataclass(obj) else obj
