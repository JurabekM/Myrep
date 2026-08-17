from typing import Dict, Any

class FinanceService:
    """
    Financial and Tax calculators for Uzbekistan businesses.
    """

    @staticmethod
    def calculate_roi(investment: float, net_profit: float) -> float:
        """Calculate Return on Investment (%)"""
        if investment <= 0:
            return 0.0
        return (net_profit / investment) * 100

    @staticmethod
    def calculate_npv(discount_rate: float, cash_flows: list[float]) -> float:
        """Calculate Net Present Value"""
        npv = 0.0
        for t, cash_flow in enumerate(cash_flows):
            npv += cash_flow / ((1 + discount_rate) ** t)
        return npv

    @staticmethod
    def calculate_break_even(fixed_costs: float, price_per_unit: float, variable_cost_per_unit: float) -> float:
        """Calculate Break-Even Point in units"""
        if price_per_unit <= variable_cost_per_unit:
            return float('inf') # Will never break even
        return fixed_costs / (price_per_unit - variable_cost_per_unit)

    @staticmethod
    def calculate_uzb_taxes(revenue: float, costs: float, tax_type: str = "turnover") -> Dict[str, Any]:
        """
        Basic calculator for UZB taxes.
        tax_type: 'turnover' (aylanmadan olinadigan soliq) or 'vat_profit' (QQS va Foyda solig'i)
        """
        results = {
            "revenue": revenue,
            "costs": costs,
            "gross_profit": revenue - costs,
            "tax_type": tax_type,
            "total_tax": 0.0,
            "net_profit": 0.0,
            "details": {}
        }
        
        if tax_type == "turnover":
            # Assuming standard 4% turnover tax for simplified regime
            tax_rate = 0.04
            total_tax = revenue * tax_rate
            results["total_tax"] = total_tax
            results["net_profit"] = results["gross_profit"] - total_tax
            results["details"] = {"turnover_tax_4%": total_tax}
            
        elif tax_type == "vat_profit":
            # Assuming 12% VAT and 15% Corporate Income Tax (Foyda solig'i)
            # This is a highly simplified model
            vat_rate = 0.12
            cit_rate = 0.15
            
            # Simple assumption: VAT is charged on gross margin
            vat = results["gross_profit"] * vat_rate 
            profit_before_cit = results["gross_profit"] - vat
            cit = max(0, profit_before_cit * cit_rate)
            
            total_tax = vat + cit
            results["total_tax"] = total_tax
            results["net_profit"] = profit_before_cit - cit
            results["details"] = {
                "vat_12%": vat,
                "profit_tax_15%": cit
            }
            
        return results

finance_service = FinanceService()
