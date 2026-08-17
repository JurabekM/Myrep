import unittest
from services.finance_service import finance_service

class TestFinanceService(unittest.TestCase):
    def test_roi(self):
        self.assertEqual(finance_service.calculate_roi(100, 10), 10.0)
        self.assertEqual(finance_service.calculate_roi(0, 10), 0.0)

    def test_break_even(self):
        self.assertEqual(finance_service.calculate_break_even(1000, 20, 10), 100)

    def test_uzb_taxes_turnover(self):
        res = finance_service.calculate_uzb_taxes(10000, 5000, "turnover")
        self.assertEqual(res["total_tax"], 400.0) # 4% of 10000
        
    def test_uzb_taxes_vat(self):
        res = finance_service.calculate_uzb_taxes(10000, 5000, "vat_profit")
        # Gross profit = 5000
        # VAT = 5000 * 0.12 = 600
        # Profit before CIT = 4400
        # CIT = 4400 * 0.15 = 660
        # Total Tax = 1260
        self.assertEqual(res["total_tax"], 1260.0)

if __name__ == '__main__':
    unittest.main()
