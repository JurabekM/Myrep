import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal

# Rich Offline Legislative Knowledge Base for Uzbekistan
OFFLINE_LEGAL_DB = [
    {
        "id": "tax_turnover",
        "title": "Turnover Tax (Aylanmadan olinadigan soliq) - Soliq Kodeksi Art. 461-470",
        "category": "Taxation",
        "keywords": ["tax", "turnover", "soliq", "aylanma", "rate", "stavka", "revenue", "daromad"],
        "summary": "Turnover tax is simplified taxation for small businesses with annual revenue under 1 billion UZS. The standard rate is 4%. For services/retail in remote areas, it ranges from 1% to 3%. Some sectors (e.g. IT-Park residents) are exempted.",
        "details": "Who is eligible: Legal entities and individual entrepreneurs whose revenue does not exceed 1 billion UZS per calendar year. Transition to general tax occurs automatically in the month revenue exceeds 1 billion UZS. Tax reporting is monthly, due by the 15th of the following month."
    },
    {
        "id": "tax_general",
        "title": "General Tax Regime (Umumiy soliq solish tizimi) - VAT, Profit Tax",
        "category": "Taxation",
        "keywords": ["vat", "qqs", "profit", "foyda", "general", "umumiy", "property", "mol-mulk"],
        "summary": "Mandatory for businesses with annual revenue exceeding 1 billion UZS. Includes VAT (QQS) at 12%, Profit Tax (Foyda solig'i) at 15%, and Property Tax at 1.5%.",
        "details": "VAT (QQS) is 12%. Input VAT can be offset if invoices are properly generated in the E-Faktura system. Profit Tax is 15% (7.5% for companies registered in specific economic zones or having high export shares). Social Tax (Ijtimoiy soliq) is 12% for standard businesses."
    },
    {
        "id": "it_park_benefits",
        "title": "IT-Park Residents Incentives - Cabinet of Ministers Decree No. 589 / PD-5077",
        "category": "Technology & Startups",
        "keywords": ["it-park", "it park", "resident", "it", "software", "benefit", "imtiyoz", "tax free"],
        "summary": "Residents of IT-Park Uzbekistan receive complete exemptions from corporate profit tax, VAT, and property tax. Personal income tax (JShDS) for employees is reduced to 7.5%.",
        "details": "Exemptions: 0% Profit Tax, 0% VAT on IT services, 0% Social Tax for the company, 0% Property Tax. Employees pay a flat 7.5% Personal Income Tax instead of the standard 12%. Social Tax for residents is reduced to 7.5%. Requirements: Must export software/IT services, obtain residency certificate, and submit quarterly reports."
    },
    {
        "id": "llc_registration",
        "title": "Registration of Limited Liability Company (MChJ ta'sis etish) - Law 'On LLCs'",
        "category": "Corporate Law",
        "keywords": ["register", "llc", "mchj", "incorporate", "charter", "ustav", "fond", "capital"],
        "summary": "Standard registration process for a startup or small business as an MChJ. Handled online via fo.birdarcha.uz or my.gov.uz using E-Signature (ERI).",
        "details": "No minimum statutory fund (Ustav Fondi) is strictly mandated for standard activities, but it must be declared in the Charter (Ustav) and paid within 12 months. Founders must reserve a company name, obtain E-Signature, prepare Charter, and submit online. Registration fee is 1x BHM (Basic Calculating Amount)."
    },
    {
        "id": "statutory_fund_rules",
        "title": "Statutory Fund (Ustav Fondi) Regulations - Civil Code & LLC Law",
        "category": "Corporate Law",
        "keywords": ["ustav fondi", "statutory fund", "capital", "shares", "hissa", "founder", "ta'sischi"],
        "summary": "Rules governing the formation, contribution, and valuation of the Statutory Fund. Changes must be registered with public services.",
        "details": "Contributions can be in cash or property/assets (valued by independent appraisers if exceeding certain thresholds). The fund represents the baseline capital for operations and determines shareholder voting weight and dividend distribution. It must be fully funded within 1 year of state registration."
    },
    {
        "id": "microloan_finance",
        "title": "Microloan and Financing Regulations - Law 'On Non-Bank Credit Organizations'",
        "category": "Finance",
        "keywords": ["microloan", "loan", "kredit", "mikrokredit", "finance", "moliya", "collateral", "garov"],
        "summary": "Financing limits and regulatory framework for microloans to small businesses, capped at 300 million UZS for simplified business microloans.",
        "details": "Interest rates are market-driven, typically 20-28% APR. Collateral can include real estate, vehicles, inventory, or third-party guarantees. The State Entrepreneurship Support Fund (Tadbirkorlikni qo'llab-quvvatlash jamg'armasi) can provide interest compensation or credit guarantees up to 50% of the loan amount."
    }
]

class LexScraperWorker(QThread):
    finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        results = []
        
        # 1. First, search the offline local database for exact/partial keyword matches
        query_words = self.query.lower().split()
        for doc in OFFLINE_LEGAL_DB:
            score = 0
            for word in query_words:
                if word in doc["title"].lower() or word in doc["category"].lower() or word in doc["summary"].lower():
                    score += 3
                for kw in doc["keywords"]:
                    if word in kw:
                        score += 2
            if score > 0:
                results.append({
                    "title": doc["title"],
                    "summary": doc["summary"],
                    "details": doc["details"],
                    "source": "Local Legislative Knowledge Base",
                    "link": "Offline Reference",
                    "score": score
                })
        
        # Sort local results by relevance score
        results.sort(key=lambda x: x["score"], reverse=True)
        for r in results:
            del r["score"]

        # 2. Try to scrape the live Lex.uz search portal
        try:
            # Lex.uz search endpoint
            # We use headers to mimic a normal browser and avoid blocks
            url = "https://lex.uz/search/nat"
            params = {
                "query": self.query,
                "title": self.query
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Lex.uz list page contains items, usually inside links or list containers
                # Let's inspect potential element anchors.
                # Document links usually look like /docs/123456 or /uz/docs/123456
                links = soup.find_all("a")
                scraped_count = 0
                for a in links:
                    href = a.get("href", "")
                    if "/docs/" in href and len(a.text.strip()) > 10:
                        doc_title = a.text.strip()
                        doc_link = href
                        if not doc_link.startswith("http"):
                            doc_link = "https://lex.uz" + doc_link
                            
                        # Find parent container to get a date or short snippet if available
                        parent = a.find_parent()
                        summary_text = "Uzbekistan Legislative Document"
                        if parent:
                            # Try to find a span or text sibling
                            sibling = parent.find_next_sibling()
                            if sibling:
                                summary_text = sibling.text.strip()[:200]
                                if len(summary_text) < 10:
                                    summary_text = parent.text.strip()[:250].replace(doc_title, "").strip()
                        
                        # Avoid duplicates
                        if not any(r["link"] == doc_link for r in results):
                            results.append({
                                "title": doc_title,
                                "summary": summary_text or "No snippet available.",
                                "details": f"Direct link to legislative document. Please refer to lex.uz for full official text.",
                                "source": "Lex.uz Live Portal",
                                "link": doc_link
                            })
                            scraped_count += 1
                            if scraped_count >= 10:  # limit live results to 10
                                break
                                
        except Exception as e:
            # Log error but don't crash, since local results are already populated
            print(f"Lex.uz live search error: {e}")
            
        self.finished.emit(results)
