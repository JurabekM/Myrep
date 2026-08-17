"""Global search across farmers, farms, fields, crops, regions and districts."""
from __future__ import annotations

import pandas as pd

from database.engine import read_df


def global_search(query: str, limit: int = 30) -> pd.DataFrame:
    """Case-insensitive LIKE search across every named entity."""
    like = f"%{query.strip()}%"
    if not query.strip():
        return pd.DataFrame(columns=["turi", "nomi", "tafsilot"])
    df = read_df(
        "SELECT 'Fermer' AS turi, fm.name AS nomi,"
        " d.name || ', tel: ' || fm.phone AS tafsilot"
        " FROM farmers fm JOIN districts d ON d.id = fm.district_id"
        " WHERE fm.name LIKE :q"
        " UNION ALL "
        "SELECT 'Xo''jalik', fa.name, r.name || ' — ' ||"
        " CAST(ROUND(fa.area_ha) AS INTEGER) || ' ga'"
        " FROM farms fa"
        " JOIN districts d ON d.id = fa.district_id"
        " JOIN regions r ON r.id = d.region_id WHERE fa.name LIKE :q"
        " UNION ALL "
        "SELECT 'Dala', f.name, fa.name || ' — ' ||"
        " CAST(f.area_ha AS TEXT) || ' ga, ' || f.soil_type"
        " FROM fields f JOIN farms fa ON fa.id = f.farm_id WHERE f.name LIKE :q"
        " UNION ALL "
        "SELECT 'Ekin', c.name, c.category || ', ' || c.season || ' — bazaviy narx ' ||"
        " CAST(CAST(c.base_price_per_kg AS INTEGER) AS TEXT) || ' so''m/kg'"
        " FROM crops c WHERE c.name LIKE :q"
        " UNION ALL "
        "SELECT 'Viloyat', r.name, 'Markaz: ' || CAST(ROUND(r.lat,2) AS TEXT) ||"
        " ', ' || CAST(ROUND(r.lon,2) AS TEXT) FROM regions r WHERE r.name LIKE :q"
        " UNION ALL "
        "SELECT 'Tuman', d.name, r.name FROM districts d"
        " JOIN regions r ON r.id = d.region_id WHERE d.name LIKE :q"
        " LIMIT :n",
        {"q": like, "n": limit},
    )
    return df
