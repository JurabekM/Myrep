#!/usr/bin/env python3
"""countries.tsv generatori (engine resursi).

Manba: mledoze/countries (ODbL 1.0) — https://github.com/mledoze/countries
Foydalanish:
    curl -sSL -o /tmp/countries.json \
        https://raw.githubusercontent.com/mledoze/countries/master/countries.json
    python3 -I tool/gen_countries.py /tmp/countries.json \
        > engine/src/main/resources/epiradar/countries.tsv

Ustunlar: iso3, iso2, nomi (en), nomi (uz), kenglik, uzunlik, subregion, qo'shnilar (",")
va nom-sinonimlar ("|") — matndan mamlakatni topish uchun (WHO/CDC/ECDC yozuv uslubi).
"""
import json
import sys

# O'zbekcha (lotin) nomlar. Yo'q bo'lsa inglizcha nom ishlatiladi.
UZ = {
    "AFG": "Afg'oniston", "AGO": "Angola", "ALB": "Albaniya", "AND": "Andorra",
    "ARE": "Birlashgan Arab Amirliklari", "ARG": "Argentina", "ARM": "Armaniston",
    "ATG": "Antigua va Barbuda", "AUS": "Avstraliya", "AUT": "Avstriya", "AZE": "Ozarbayjon",
    "BDI": "Burundi", "BEL": "Belgiya", "BEN": "Benin", "BFA": "Burkina-Faso",
    "BGD": "Bangladesh", "BGR": "Bolgariya", "BHR": "Bahrayn", "BHS": "Bagama orollari",
    "BIH": "Bosniya va Gertsegovina", "BLR": "Belarus", "BLZ": "Beliz", "BOL": "Boliviya",
    "BRA": "Braziliya", "BRB": "Barbados", "BRN": "Bruney", "BTN": "Butan", "BWA": "Botsvana",
    "CAF": "Markaziy Afrika Respublikasi", "CAN": "Kanada", "CHE": "Shveytsariya",
    "CHL": "Chili", "CHN": "Xitoy", "CIV": "Kot-d'Ivuar", "CMR": "Kamerun",
    "COD": "Kongo Demokratik Respublikasi", "COG": "Kongo Respublikasi", "COL": "Kolumbiya",
    "COM": "Komor orollari", "CPV": "Kabo-Verde", "CRI": "Kosta-Rika", "CUB": "Kuba",
    "CYP": "Kipr", "CZE": "Chexiya", "DEU": "Germaniya", "DJI": "Jibuti", "DMA": "Dominika",
    "DNK": "Daniya", "DOM": "Dominikan Respublikasi", "DZA": "Jazoir", "ECU": "Ekvador",
    "EGY": "Misr", "ERI": "Eritreya", "ESP": "Ispaniya", "EST": "Estoniya", "ETH": "Efiopiya",
    "FIN": "Finlandiya", "FJI": "Fiji", "FRA": "Fransiya", "FSM": "Mikroneziya",
    "GAB": "Gabon", "GBR": "Buyuk Britaniya", "GEO": "Gruziya", "GHA": "Gana",
    "GIN": "Gvineya", "GMB": "Gambiya", "GNB": "Gvineya-Bisau", "GNQ": "Ekvatorial Gvineya",
    "GRC": "Gretsiya", "GRD": "Grenada", "GRL": "Grenlandiya", "GTM": "Gvatemala",
    "GUF": "Fransuz Gvianasi", "GUY": "Gayana", "HKG": "Gonkong", "HND": "Gonduras",
    "HRV": "Xorvatiya", "HTI": "Gaiti", "HUN": "Vengriya", "IDN": "Indoneziya",
    "IND": "Hindiston", "IRL": "Irlandiya", "IRN": "Eron", "IRQ": "Iroq", "ISL": "Islandiya",
    "ISR": "Isroil", "ITA": "Italiya", "JAM": "Yamayka", "JOR": "Iordaniya", "JPN": "Yaponiya",
    "KAZ": "Qozog'iston", "KEN": "Keniya", "KGZ": "Qirg'iziston", "KHM": "Kambodja",
    "KIR": "Kiribati", "KNA": "Sent-Kits va Nevis", "KOR": "Janubiy Koreya", "KWT": "Quvayt",
    "LAO": "Laos", "LBN": "Livan", "LBR": "Liberiya", "LBY": "Liviya", "LCA": "Sent-Lyusiya",
    "LIE": "Lixtenshteyn", "LKA": "Shri-Lanka", "LSO": "Lesoto", "LTU": "Litva",
    "LUX": "Lyuksemburg", "LVA": "Latviya", "MAC": "Makao", "MAR": "Marokash",
    "MCO": "Monako", "MDA": "Moldova", "MDG": "Madagaskar", "MDV": "Maldiv orollari",
    "MEX": "Meksika", "MHL": "Marshall orollari", "MKD": "Shimoliy Makedoniya", "MLI": "Mali",
    "MLT": "Malta", "MMR": "Myanma", "MNE": "Chernogoriya", "MNG": "Mo'g'uliston",
    "MOZ": "Mozambik", "MRT": "Mavritaniya", "MUS": "Mavrikiy", "MWI": "Malavi",
    "MYS": "Malayziya", "MYT": "Mayotta", "NAM": "Namibiya", "NER": "Niger", "NGA": "Nigeriya",
    "NIC": "Nikaragua", "NLD": "Niderlandiya", "NOR": "Norvegiya", "NPL": "Nepal",
    "NRU": "Nauru", "NZL": "Yangi Zelandiya", "OMN": "Ummon", "PAK": "Pokiston",
    "PAN": "Panama", "PER": "Peru", "PHL": "Filippin", "PLW": "Palau",
    "PNG": "Papua — Yangi Gvineya", "POL": "Polsha", "PRI": "Puerto-Riko",
    "PRK": "Shimoliy Koreya", "PRT": "Portugaliya", "PRY": "Paragvay", "PSE": "Falastin",
    "QAT": "Qatar", "ROU": "Ruminiya", "RUS": "Rossiya", "RWA": "Ruanda",
    "SAU": "Saudiya Arabistoni", "SDN": "Sudan", "SEN": "Senegal", "SGP": "Singapur",
    "SLB": "Solomon orollari", "SLE": "Syerra-Leone", "SLV": "Salvador", "SMR": "San-Marino",
    "SOM": "Somali", "SRB": "Serbiya", "SSD": "Janubiy Sudan", "STP": "San-Tome va Prinsipi",
    "SUR": "Surinam", "SVK": "Slovakiya", "SVN": "Sloveniya", "SWE": "Shvetsiya",
    "SWZ": "Esvatini", "SYC": "Seyshel orollari", "SYR": "Suriya", "TCD": "Chad",
    "TGO": "Togo", "THA": "Tailand", "TJK": "Tojikiston", "TKM": "Turkmaniston",
    "TLS": "Timor-Leste", "TON": "Tonga", "TTO": "Trinidad va Tobago", "TUN": "Tunis",
    "TUR": "Turkiya", "TUV": "Tuvalu", "TWN": "Tayvan", "TZA": "Tanzaniya", "UGA": "Uganda",
    "UKR": "Ukraina", "UNK": "Kosovo", "URY": "Urugvay", "USA": "AQSh", "UZB": "O'zbekiston",
    "VAT": "Vatikan", "VCT": "Sent-Vinsent va Grenadinlar", "VEN": "Venesuela",
    "VNM": "Vyetnam", "VUT": "Vanuatu", "WSM": "Samoa", "YEM": "Yaman",
    "ZAF": "Janubiy Afrika Respublikasi", "ZMB": "Zambiya", "ZWE": "Zimbabve",
    "REU": "Reyunion", "GLP": "Gvadelupa", "MTQ": "Martinika", "NCL": "Yangi Kaledoniya",
    "PYF": "Fransuz Polineziyasi", "ESH": "G'arbiy Sahroi Kabir", "CUW": "Kyurasao",
    "ABW": "Aruba", "BMU": "Bermud orollari", "GUM": "Guam", "ASM": "Amerika Samoasi",
}

# Rasmiy manbalar (WHO, CDC, ECDC) ishlatadigan qo'shimcha yozuvlar.
EXTRA_ALIASES = {
    "COD": ["Democratic Republic of the Congo", "DR Congo", "DRC", "Congo-Kinshasa"],
    "COG": ["Republic of the Congo", "Congo-Brazzaville"],
    "RUS": ["Russian Federation"],
    "TUR": ["Türkiye", "Turkiye"],
    "USA": ["United States of America", "United States", "USA", "U.S."],
    "GBR": ["United Kingdom of Great Britain and Northern Ireland", "United Kingdom", "UK",
            "England", "Scotland", "Wales"],
    "KOR": ["Republic of Korea", "South Korea"],
    "PRK": ["Democratic People's Republic of Korea", "North Korea"],
    "VNM": ["Viet Nam", "Vietnam"],
    "LAO": ["Lao People's Democratic Republic", "Lao PDR"],
    "IRN": ["Iran (Islamic Republic of)", "Islamic Republic of Iran"],
    "SYR": ["Syrian Arab Republic"],
    "BOL": ["Bolivia (Plurinational State of)", "Plurinational State of Bolivia"],
    "VEN": ["Venezuela (Bolivarian Republic of)", "Bolivarian Republic of Venezuela"],
    "TZA": ["United Republic of Tanzania", "Zanzibar"],
    "CIV": ["Côte d'Ivoire", "Cote d'Ivoire", "Ivory Coast"],
    "SAU": ["Kingdom of Saudi Arabia"],
    "MDA": ["Republic of Moldova"],
    "CZE": ["Czech Republic"],
    "MKD": ["Republic of North Macedonia"],
    "SWZ": ["Swaziland"],
    "MMR": ["Burma"],
    "CPV": ["Cabo Verde"],
    "TLS": ["East Timor"],
    "PSE": ["occupied Palestinian territory", "Gaza", "West Bank"],
    "HKG": ["Hong Kong SAR", "Hong Kong Special Administrative Region"],
    "MAC": ["Macao SAR", "Macao"],
    "TWN": ["Taiwan"],
    "FSM": ["Micronesia (Federated States of)"],
    "NLD": ["Netherlands (Kingdom of the)", "Kingdom of the Netherlands"],
}

# Noto'g'ri moslik beradigan yozuvlar (masalan, "Turkey" — kurka fermasi; "Georgia" — AQSh shtati).
BLOCKED = {"Turkey", "Jersey", "Chad", "Niue"}
SKIP = {"ATA", "BVT", "HMD", "IOT", "SGS", "UMI", "ATF", "CXR", "CCK", "PCN", "NFK", "ALA",
        "SJM", "TKL", "SPM", "SHN", "FLK", "WLF", "BLM", "MAF", "SXM", "BES", "MSR", "AIA",
        "VGB", "VIR", "TCA", "CYM", "GGY", "IMN", "GIB", "FRO", "NIU", "COK", "MNP"}


def clean(alias: str) -> str | None:
    alias = alias.strip()
    if len(alias) < 4 or alias in BLOCKED or not alias.isascii() and "ô" not in alias and "ü" not in alias:
        return None
    if alias.isupper() and len(alias) <= 3:
        return None
    return alias


def main(path: str) -> None:
    data = json.load(open(path, encoding="utf-8"))
    print("# iso3\tiso2\tname_en\tname_uz\tlat\tlng\tsubregion\tborders\taliases")
    print("# Manba: mledoze/countries (ODbL 1.0); o'zbekcha nomlar va sinonimlar — tool/gen_countries.py")
    for c in sorted(data, key=lambda c: c["cca3"]):
        iso3 = c["cca3"]
        if iso3 in SKIP:
            continue
        en = c["name"]["common"]
        if iso3 == "CIV":
            en = "Côte d'Ivoire"
        aliases: list[str] = []
        for a in [en, c["name"]["official"], *c.get("altSpellings", []), *EXTRA_ALIASES.get(iso3, [])]:
            a2 = clean(a) if a not in EXTRA_ALIASES.get(iso3, []) else a
            if a2 and a2 not in aliases:
                aliases.append(a2)
        lat, lng = c["latlng"]
        row = [iso3, c["cca2"], en, UZ.get(iso3, en), f"{lat:.2f}", f"{lng:.2f}",
               c.get("subregion") or c.get("region", ""), ",".join(c.get("borders", [])),
               "|".join(aliases)]
        print("\t".join(row))


if __name__ == "__main__":
    main(sys.argv[1])
