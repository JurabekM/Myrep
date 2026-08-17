"""Yadro qatlami testlari: yuklash, log tahlil, profil, tahrirlash, ML, grafik."""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dataforge.core import charting, ingest, logparse, ml, profile, project, report, transform  # noqa: E402


# ---------------------------------------------------------------- fixtures --
@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    n = 600
    t0 = datetime(2024, 5, 1)
    return pd.DataFrame({
        "ts": [t0 + timedelta(minutes=5 * i) for i in range(n)],
        "device": rng.choice(["A", "B", "C"], n),
        "temp": rng.normal(25, 4, n).round(2),
        "hum": rng.normal(50, 8, n).round(2),
        "volt": rng.normal(3.7, 0.05, n).round(3),
        "msg": rng.choice(["ok", "warn: high temp", "error: timeout"], n),
        "fault": rng.integers(0, 2, n),
    })


@pytest.fixture(scope="module")
def apache_lines() -> list[str]:
    return [
        '10.0.0.1 - - [01/May/2024:10:00:01 +0500] "GET /index.html HTTP/1.1" 200 5120 "-" "Mozilla/5.0"',
        '10.0.0.2 - - [01/May/2024:10:00:05 +0500] "POST /api/v1/login HTTP/1.1" 401 231 "-" "curl/8.4"',
        '45.155.205.233 - - [01/May/2024:10:00:07 +0500] "GET /.env HTTP/1.1" 404 162 "-" "python-requests/2.31"',
    ]


# ------------------------------------------------------------- logparse ----
class TestLogParse:
    def test_detect_apache(self, apache_lines):
        fmt = logparse.detect_format(apache_lines)
        assert fmt.parser == "apache"
        assert fmt.confidence > 0.9

    def test_detect_json_lines(self):
        lines = [json.dumps({"ts": "2024-05-01T10:00:00", "level": "INFO", "msg": f"n{i}"})
                 for i in range(20)]
        assert logparse.detect_format(lines).parser == "json"

    def test_detect_syslog(self):
        lines = [f"May  1 10:0{i}:00 srv-01 sshd[123]: Accepted password for root"
                 for i in range(9)]
        assert logparse.detect_format(lines).parser == "syslog"

    def test_detect_pylog(self):
        lines = [f"2024-05-01 10:00:0{i},123 - api.auth - ERROR - xato {i}"
                 for i in range(9)]
        assert logparse.detect_format(lines).parser == "pylog"

    def test_detect_logfmt(self):
        lines = [f'level=info msg="request done" ms={i} path=/api' for i in range(10)]
        assert logparse.detect_format(lines).parser == "logfmt"

    def test_detect_raw_fallback(self):
        lines = ["shunchaki matn", "yana bir qator", "hech qanday tuzilma yo'q"]
        assert logparse.detect_format(lines).parser == "raw"

    def test_parse_apache_columns(self, apache_lines):
        df, fmt = logparse.parse_lines(apache_lines)
        assert len(df) == 3
        assert {"status", "method", "path", "ts"} <= set(df.columns)
        assert df["status"].tolist() == [200, 401, 404]
        assert pd.api.types.is_datetime64_any_dtype(df["ts"])

    def test_parse_json_flattens_nested(self):
        lines = [json.dumps({"a": {"b": {"c": i}}, "msg": "x"}) for i in range(5)]
        df, _ = logparse.parse_lines(lines, parser="json")
        assert "a.b.c" in df.columns

    def test_parse_empty(self):
        df, fmt = logparse.parse_lines([])
        assert df.empty and fmt.name == "bo'sh"

    def test_mask_line(self):
        masked = logparse.mask_line(
            "user 12345 from 10.0.0.5 took 340ms id=550e8400-e29b-41d4-a716-446655440000")
        assert "<NUM>" in masked and "<IP>" in masked and "<UUID>" in masked

    def test_mine_templates_groups(self):
        msgs = pd.Series([f"So'rov {i} bajarildi {i * 10}ms" for i in range(50)]
                         + ["Xizmat ishga tushdi"] * 3)
        tids, table = logparse.mine_templates(msgs)
        assert len(table) == 2
        assert table["count"].max() == 50
        assert tids.notna().all()

    def test_rare_templates(self):
        msgs = pd.Series(["oddiy hodisa"] * 1000 + ["juda kam hodisa"])
        _, table = logparse.mine_templates(msgs)
        rare = logparse.rare_templates(table, threshold=0.01)
        assert len(rare) == 1
        assert "kam" in rare.iloc[0]["template"]

    def test_burst_detect(self):
        base = datetime(2024, 5, 1, 12, 0)
        normal = [base + timedelta(minutes=i) for i in range(60)]
        burst = [base + timedelta(minutes=30, seconds=s) for s in range(50)]
        out = logparse.burst_detect(pd.Series(normal + burst), freq="1min", z=3)
        assert out["is_burst"].sum() >= 1

    def test_enrich_extracts_ip(self):
        df = pd.DataFrame({"message": ["ulanish 192.168.1.10 dan", "xato yo'q"]})
        out = logparse.enrich(df)
        assert "e_ip" in out.columns
        assert out["e_ip"].iloc[0] == "192.168.1.10"

    def test_timestamp_epoch_seconds(self):
        s = pd.Series([1714550400, 1714554000])
        out = logparse.parse_timestamp_series(s)
        assert pd.api.types.is_datetime64_any_dtype(out)
        assert out.iloc[0].year == 2024


# --------------------------------------------------------------- ingest ----
class TestIngest:
    def test_load_csv(self, tmp_path, sample_df):
        p = tmp_path / "d.csv"
        sample_df.to_csv(p, index=False)
        res = ingest.load_file(p)
        assert res.kind == "jadval"
        assert len(res.df) == len(sample_df)
        assert pd.api.types.is_numeric_dtype(res.df["temp"])

    def test_load_csv_semicolon(self, tmp_path):
        p = tmp_path / "d.csv"
        p.write_text("a;b;c\n1;2;3\n4;5;6\n", encoding="utf-8")
        res = ingest.load_file(p)
        assert list(res.df.columns) == ["a", "b", "c"]
        assert res.df.shape == (2, 3)

    def test_load_jsonl(self, tmp_path):
        p = tmp_path / "d.jsonl"
        p.write_text("\n".join(json.dumps({"i": i, "v": i * 2}) for i in range(10)),
                     encoding="utf-8")
        res = ingest.load_file(p)
        assert len(res.df) == 10 and "v" in res.df.columns

    def test_load_json_array(self, tmp_path):
        p = tmp_path / "d.json"
        p.write_text(json.dumps([{"a": 1}, {"a": 2}]), encoding="utf-8")
        assert len(ingest.load_file(p).df) == 2

    def test_load_json_wrapped_list(self, tmp_path):
        p = tmp_path / "d.json"
        p.write_text(json.dumps({"meta": 1, "items": [{"a": i} for i in range(7)]}),
                     encoding="utf-8")
        assert len(ingest.load_file(p).df) == 7

    def test_load_parquet(self, tmp_path, sample_df):
        p = tmp_path / "d.parquet"
        sample_df.to_parquet(p, index=False)
        assert len(ingest.load_file(p).df) == len(sample_df)

    def test_load_excel(self, tmp_path, sample_df):
        p = tmp_path / "d.xlsx"
        sample_df.head(50).to_excel(p, index=False)
        assert len(ingest.load_file(p).df) == 50

    def test_load_sqlite(self, tmp_path, sample_df):
        p = tmp_path / "d.db"
        with sqlite3.connect(p) as conn:
            sample_df.head(30).to_sql("events", conn, index=False)
        assert "events" in ingest.sqlite_tables(p)
        res = ingest.load_sqlite(p, table="events")
        assert len(res.df) == 30
        res2 = ingest.load_sqlite(p, query="SELECT device, COUNT(*) n FROM events GROUP BY device")
        assert "n" in res2.df.columns

    def test_load_log_file(self, tmp_path, apache_lines):
        p = tmp_path / "access.log"
        p.write_text("\n".join(apache_lines * 20), encoding="utf-8")
        res = ingest.load_file(p)
        assert res.kind == "log"
        assert "Apache" in res.meta["format"]

    def test_load_gzip(self, tmp_path, apache_lines):
        import gzip

        p = tmp_path / "access.log.gz"
        with gzip.open(p, "wt", encoding="utf-8") as fh:
            fh.write("\n".join(apache_lines * 10))
        assert len(ingest.load_file(p).df) == 30

    def test_load_folder(self, tmp_path, apache_lines):
        d = tmp_path / "logs"
        d.mkdir()
        for i in range(3):
            (d / f"a{i}.log").write_text("\n".join(apache_lines), encoding="utf-8")
        res = ingest.load_folder(d, "*.log")
        assert len(res.df) == 9
        assert res.df["_source"].nunique() == 3

    def test_load_text_csvish(self):
        res = ingest.load_text("x,y\n1,2\n3,4\n", name="t")
        assert res.df.shape == (2, 2)

    def test_nrows_limit(self, tmp_path, sample_df):
        p = tmp_path / "d.csv"
        sample_df.to_csv(p, index=False)
        assert len(ingest.load_file(p, nrows=25).df) == 25

    def test_infer_types_numeric_with_commas(self):
        df = pd.DataFrame({"n": ["1,200", "3,400", "5,600"]})
        out = ingest.infer_types(df)
        assert pd.api.types.is_numeric_dtype(out["n"])
        assert out["n"].iloc[0] == 1200

    def test_infer_types_boolean(self):
        df = pd.DataFrame({"b": ["true", "false", "true"]})
        assert pd.api.types.is_bool_dtype(ingest.infer_types(df)["b"])

    def test_detect_encoding_utf8(self):
        assert ingest.detect_encoding("salom o'zbek".encode()) == "utf-8"

    @pytest.mark.parametrize("ext", ["csv", "json", "jsonl", "parquet", "html", "md"])
    def test_export_roundtrip(self, tmp_path, sample_df, ext):
        p = tmp_path / f"out.{ext}"
        ingest.export_df(sample_df.head(20), p)
        assert p.exists() and p.stat().st_size > 0

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            ingest.load_file("__yo'q__.csv")


# -------------------------------------------------------------- profile ----
class TestProfile:
    def test_column_kinds(self, sample_df):
        assert profile.column_kind(sample_df["temp"]) == profile.NUMERIC
        assert profile.column_kind(sample_df["ts"]) == profile.DATETIME
        assert profile.column_kind(sample_df["device"]) == profile.CATEGORICAL

    def test_profile_dataframe(self, sample_df):
        p = profile.profile_dataframe(sample_df)
        assert p.rows == len(sample_df)
        assert p.cols == sample_df.shape[1]
        assert 0 <= p.quality_score <= 100
        assert len(p.columns) == sample_df.shape[1]
        assert not p.to_frame().empty

    def test_issues_detect_constant(self):
        df = pd.DataFrame({"a": [1] * 100, "b": range(100)})
        issues = profile.profile_dataframe(df).issues
        assert any("Doimiy" in i["title"] for i in issues)

    def test_issues_detect_missing(self):
        df = pd.DataFrame({"a": [None] * 80 + list(range(20))})
        issues = profile.profile_dataframe(df).issues
        assert any("bo'sh" in i["title"].lower() for i in issues)

    def test_correlation(self, sample_df):
        corr = profile.correlation(sample_df)
        assert not corr.empty
        assert abs(corr.loc["temp", "temp"] - 1.0) < 1e-9

    def test_top_correlations(self):
        x = np.linspace(0, 10, 200)
        df = pd.DataFrame({"a": x, "b": 2 * x + 1, "c": np.random.default_rng(1).normal(size=200)})
        top = profile.top_correlations(profile.correlation(df), threshold=0.9)
        assert len(top) == 1 and top.iloc[0]["kuch"] == "juda kuchli"

    def test_iqr_outliers(self):
        s = pd.Series(list(range(100)) + [10_000])
        n, lo, hi = profile.iqr_outliers(s)
        assert n == 1

    def test_group_summary(self, sample_df):
        out = profile.group_summary(sample_df, "device", "temp")
        assert "mean" in out.columns and len(out) == 3

    def test_time_series(self, sample_df):
        ts = profile.time_series(sample_df, "ts", freq="1h")
        assert len(ts) > 0 and "count" in ts.columns

    def test_suggest_freq(self, sample_df):
        assert profile.suggest_freq(sample_df["ts"]) in ("1min", "15min", "1h", "1D")

    def test_cramers_v(self):
        a = pd.Series(["x", "x", "y", "y"] * 25)
        assert profile.cramers_v(a, a.copy()) > 0.9

    def test_entropy(self):
        assert profile.shannon_entropy(pd.Series(["a"] * 10)) == 0.0
        assert profile.shannon_entropy(pd.Series(["a", "b"] * 10)) == pytest.approx(1.0)


# ------------------------------------------------------------ transform ----
class TestTransform:
    def test_registry_not_empty(self):
        assert len(transform.OPS) >= 25
        assert "filter_query" in transform.OPS

    def test_filter_query(self, sample_df):
        out = transform.apply_op(sample_df, "filter_query", expr="temp > 25")
        assert (out["temp"] > 25).all()

    def test_filter_contains(self, sample_df):
        out = transform.apply_op(sample_df, "filter_contains", column="msg",
                                 pattern="error")
        assert out["msg"].str.contains("error").all()

    def test_filter_contains_invert(self, sample_df):
        out = transform.apply_op(sample_df, "filter_contains", column="msg",
                                 pattern="error", invert=True)
        assert not out["msg"].str.contains("error").any()

    def test_filter_range(self, sample_df):
        out = transform.apply_op(sample_df, "filter_range", column="temp",
                                 low=20, high=30)
        assert out["temp"].between(20, 30).all()

    def test_drop_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [1, 1, 3]})
        assert len(transform.apply_op(df, "drop_duplicates")) == 2

    def test_dropna(self):
        df = pd.DataFrame({"a": [1, None, 3]})
        assert len(transform.apply_op(df, "dropna")) == 2

    def test_fillna_median(self):
        df = pd.DataFrame({"a": [1.0, None, 3.0]})
        out = transform.apply_op(df, "fillna", columns=["a"], method="mediana")
        assert out["a"].isna().sum() == 0 and out["a"].iloc[1] == 2.0

    def test_sort(self, sample_df):
        out = transform.apply_op(sample_df, "sort", by=["temp"], ascending=False)
        assert out["temp"].is_monotonic_decreasing

    def test_select_and_drop_cols(self, sample_df):
        assert list(transform.apply_op(sample_df, "select_cols",
                                       columns=["temp", "hum"]).columns) == ["temp", "hum"]
        assert "temp" not in transform.apply_op(sample_df, "drop_cols",
                                                columns=["temp"]).columns

    def test_rename(self, sample_df):
        out = transform.apply_op(sample_df, "rename", column="temp", new_name="harorat")
        assert "harorat" in out.columns and "temp" not in out.columns

    def test_astype_variants(self, sample_df):
        out = transform.apply_op(sample_df, "astype", column="fault", dtype="matn")
        assert out["fault"].dtype == object
        back = transform.apply_op(out, "astype", column="fault", dtype="butun son")
        assert str(back["fault"].dtype) == "Int64"

    def test_derive_expression(self, sample_df):
        out = transform.apply_op(sample_df, "derive", new_name="idx",
                                 expr="temp * 2 + hum")
        assert np.allclose(out["idx"], sample_df["temp"] * 2 + sample_df["hum"])

    def test_str_op(self, sample_df):
        out = transform.apply_op(sample_df, "str_op", column="msg", action="katta harf")
        assert out["msg"].str.isupper().all()

    def test_extract_regex(self):
        df = pd.DataFrame({"m": ["took 120ms", "took 45ms"]})
        out = transform.apply_op(df, "extract", column="m", pattern=r"(\d+)ms",
                                 new_name="ms")
        assert out["ms"].tolist() == ["120", "45"]

    def test_split_col(self):
        df = pd.DataFrame({"m": ["a-b-c", "d-e-f"]})
        out = transform.apply_op(df, "split_col", column="m", sep="-", maxsplit=2)
        assert "m_1" in out.columns and out["m_1"].iloc[0] == "a"

    def test_datetime_parts(self, sample_df):
        out = transform.apply_op(sample_df, "datetime_parts", column="ts",
                                 parts=["yil", "soat"])
        assert "ts_yil" in out.columns and out["ts_yil"].iloc[0] == 2024

    def test_bin_numeric(self, sample_df):
        out = transform.apply_op(sample_df, "bin_numeric", column="temp", bins=4)
        assert out["temp_bin"].nunique() <= 4

    def test_scale_zscore(self, sample_df):
        out = transform.apply_op(sample_df, "scale", columns=["temp"],
                                 method="standart (z-score)")
        assert abs(out["temp"].mean()) < 1e-6

    def test_clip_outliers(self):
        df = pd.DataFrame({"a": list(range(100)) + [50_000]})
        out = transform.apply_op(df, "clip_outliers", columns=["a"], method="IQR")
        assert out["a"].max() < 1000

    def test_onehot(self, sample_df):
        out = transform.apply_op(sample_df, "onehot", columns=["device"])
        assert any(c.startswith("device_") for c in out.columns)

    def test_label_encode(self, sample_df):
        out = transform.apply_op(sample_df, "label_encode", columns=["device"])
        assert "device_code" in out.columns

    def test_groupby_agg(self, sample_df):
        out = transform.apply_op(sample_df, "groupby_agg", by=["device"],
                                 value="temp", aggs=["mean", "count"])
        assert len(out) == 3 and "mean" in out.columns

    def test_pivot(self, sample_df):
        df = sample_df.copy()
        df["hh"] = df["ts"].dt.hour
        out = transform.apply_op(df, "pivot", index="device", columns="hh",
                                 values="temp", aggfunc="mean")
        assert len(out) == 3

    def test_resample(self, sample_df):
        out = transform.apply_op(sample_df, "resample", column="ts", freq="1h")
        assert len(out) > 0

    def test_remove_constant(self):
        df = pd.DataFrame({"a": [1] * 10, "b": range(10)})
        assert list(transform.apply_op(df, "remove_constant").columns) == ["b"]

    def test_unknown_op_raises(self, sample_df):
        with pytest.raises(KeyError):
            transform.apply_op(sample_df, "yo'q_amal")

    def test_op_groups(self):
        groups = transform.op_groups()
        assert "Filtr" in groups and "Tozalash" in groups

    # ---- tarix
    def test_history_undo_redo(self, sample_df):
        h = transform.History(sample_df)
        assert not h.can_undo
        h.push(sample_df.head(10), "kesildi")
        assert h.can_undo and len(h.current) == 10
        h.undo()
        assert len(h.current) == len(sample_df)
        h.redo()
        assert len(h.current) == 10

    def test_history_branch_truncates_redo(self, sample_df):
        h = transform.History(sample_df)
        h.push(sample_df.head(10), "a")
        h.undo()
        h.push(sample_df.head(5), "b")
        assert not h.can_redo
        assert h.labels() == ["Yuklandi", "b"]

    def test_history_max_len(self, sample_df):
        h = transform.History(sample_df, max_len=3)
        for i in range(6):
            h.push(sample_df.head(i + 1), f"op{i}")
        assert len(h.entries()) == 3


# ------------------------------------------------------------------- ML ----
class TestML:
    def test_detect_task_classification(self):
        assert ml.detect_task(pd.Series([0, 1, 1, 0] * 10)) == ml.CLASSIFICATION
        assert ml.detect_task(pd.Series(["a", "b"] * 20)) == ml.CLASSIFICATION

    def test_detect_task_regression(self):
        s = pd.Series(np.random.default_rng(0).normal(size=200))
        assert ml.detect_task(s) == ml.REGRESSION

    def test_split_feature_types(self, sample_df):
        num, cat, txt = ml.split_feature_types(sample_df.drop(columns=["ts"]))
        assert "temp" in num and "device" in cat

    def test_expand_datetime(self, sample_df):
        out = ml.expand_datetime(sample_df[["ts", "temp"]])
        assert "ts__hour" in out.columns and "ts" not in out.columns

    def test_automl_classification(self, sample_df):
        df = sample_df.copy()
        df["target"] = (df["temp"] > 25).astype(int)
        res = ml.run_automl(df.drop(columns=["fault", "msg"]), target="target",
                            fast=True, cv=0)
        assert res.task == ml.CLASSIFICATION
        assert res.metrics["aniqlik (accuracy)"] > 0.8
        assert not res.leaderboard.empty
        assert res.confusion is not None
        assert res.importance is not None

    def test_automl_regression(self, sample_df):
        res = ml.run_automl(sample_df.drop(columns=["msg", "fault"]), target="temp",
                            fast=True, cv=0)
        assert res.task == ml.REGRESSION
        assert "R²" in res.metrics

    def test_automl_bad_target(self, sample_df):
        with pytest.raises(ValueError):
            ml.run_automl(sample_df, target="yo'q_ustun")

    def test_automl_too_few_rows(self, sample_df):
        with pytest.raises(ValueError):
            ml.run_automl(sample_df.head(5), target="fault")

    def test_cluster_kmeans(self, sample_df):
        res = ml.cluster(sample_df, ["temp", "hum", "volt"], algo="KMeans", k=3)
        assert res.k == 3
        assert len(res.labels) == len(sample_df)
        assert res.coords is not None and res.coords.shape[1] == 2
        assert res.profile is not None

    def test_cluster_auto_k(self, sample_df):
        res = ml.cluster(sample_df, ["temp", "hum"], algo="KMeans", k=None,
                         auto_k_range=(2, 4))
        assert 2 <= res.k <= 4

    def test_cluster_dbscan(self, sample_df):
        res = ml.cluster(sample_df, ["temp", "hum"], algo="DBSCAN", eps=0.8,
                         min_samples=10)
        assert res.algo == "DBSCAN"

    def test_cluster_needs_numeric(self, sample_df):
        with pytest.raises(ValueError):
            ml.cluster(sample_df, ["msg"], algo="KMeans", k=2)

    @pytest.mark.parametrize("method", ["Isolation Forest", "Z-score", "IQR",
                                        "Local Outlier Factor"])
    def test_anomaly_methods(self, sample_df, method):
        res = ml.detect_anomalies(sample_df, ["temp", "hum"], method=method)
        assert len(res.is_anomaly) == len(sample_df)
        assert res.n_anomalies >= 0

    def test_anomaly_finds_injected_outlier(self, sample_df):
        df = sample_df.copy()
        df.loc[df.index[0], "temp"] = 5000
        res = ml.detect_anomalies(df, ["temp"], method="Z-score", z_threshold=3)
        assert res.is_anomaly[0]

    def test_anomaly_ewma(self, sample_df):
        res = ml.detect_anomalies(sample_df, ["temp"], method="EWMA (vaqt qatori)")
        assert res.detail is not None

    def test_reduce_pca(self, sample_df):
        coords, info = ml.reduce_dim(sample_df, ["temp", "hum", "volt"], method="PCA")
        assert coords.shape[1] == 2 and "explained" in info

    def test_text_cluster(self):
        msgs = pd.Series(["ulanish xatosi timeout"] * 40
                         + ["foydalanuvchi kirdi sessiya"] * 40
                         + ["to'lov muvaffaqiyatli amalga oshirildi"] * 40)
        res = ml.text_cluster(msgs, k=3)
        assert res.k == 3 and len(res.terms) == 3
        assert all(len(v) > 0 for v in res.terms.values())

    def test_forecast(self, sample_df):
        ts = profile.time_series(sample_df, "ts", freq="1h")
        series = pd.Series(ts.iloc[:, 1].to_numpy(), index=pd.DatetimeIndex(ts.iloc[:, 0]))
        fc = ml.forecast(series, periods=6)
        assert len(fc) == 6
        assert (fc["yuqori"] >= fc["past"]).all()

    def test_forecast_too_short(self):
        with pytest.raises(ValueError):
            ml.forecast(pd.Series([1, 2, 3]), periods=5)

    def test_save_load_predict(self, tmp_path, sample_df):
        df = sample_df.copy()
        df["target"] = (df["temp"] > 25).astype(int)
        res = ml.run_automl(df.drop(columns=["fault", "msg"]), target="target",
                            fast=True, cv=0)
        p = tmp_path / "m.joblib"
        ml.save_model(res, p)
        bundle = ml.load_model(p)
        assert bundle["task"] == ml.CLASSIFICATION
        out = ml.predict_with(bundle, df.drop(columns=["fault", "msg", "target"]))
        assert "bashorat" in out.columns and len(out) == len(df)

    def test_roc_curves(self, sample_df):
        df = sample_df.copy()
        df["target"] = (df["temp"] > 25).astype(int)
        res = ml.run_automl(df.drop(columns=["fault", "msg"]), target="target",
                            fast=True, cv=0)
        if res.y_proba is not None:
            curves = ml.roc_curves(res.y_true, res.y_proba, res.classes)
            assert all(0 <= v[2] <= 1 for v in curves.values())


# ------------------------------------------------------------- charting ----
class TestCharting:
    @pytest.mark.parametrize("kind,kwargs", [
        ("line", {"x": "ts", "y": "temp"}),
        ("area", {"x": "ts", "y": "temp"}),
        ("step", {"x": "ts", "y": "temp"}),
        ("bar", {"x": "device", "y": "temp", "agg": "mean"}),
        ("barh", {"x": "device"}),
        ("stacked_bar", {"x": "device", "hue": "msg"}),
        ("pie", {"x": "device"}),
        ("donut", {"x": "device"}),
        ("count", {"x": "device"}),
        ("scatter", {"x": "temp", "y": "hum"}),
        ("bubble", {"x": "temp", "y": "hum", "size": "volt"}),
        ("hexbin", {"x": "temp", "y": "hum"}),
        ("hist", {"x": "temp"}),
        ("kde", {"x": "temp"}),
        ("ecdf", {"x": "temp"}),
        ("box", {"y": "temp", "x": "device"}),
        ("violin", {"y": "temp", "x": "device"}),
        ("strip", {"y": "temp", "x": "device"}),
        ("heatmap", {"x": "device", "y": "msg"}),
        ("corr", {}),
        ("pairplot", {}),
        ("missing", {}),
        ("timeseries", {"x": "ts"}),
        ("calendar", {"x": "ts"}),
        ("rolling", {"x": "ts", "y": "temp"}),
    ])
    def test_all_chart_types(self, sample_df, kind, kwargs):
        fig = charting.build_chart(sample_df, kind, **kwargs)
        assert fig is not None
        assert len(charting.figure_to_base64(fig)) > 100

    def test_chart_with_hue(self, sample_df):
        fig = charting.build_chart(sample_df, "scatter", x="temp", y="hum", hue="device")
        assert fig is not None

    def test_unknown_chart_raises(self, sample_df):
        with pytest.raises(ValueError):
            charting.build_chart(sample_df, "yo'q_grafik", x="temp")

    def test_empty_df_returns_message(self):
        fig = charting.build_chart(pd.DataFrame(), "hist", x="a")
        assert fig is not None

    def test_ml_figures(self, sample_df):
        cm = pd.DataFrame([[10, 2], [3, 15]], index=["haqiqiy 0", "haqiqiy 1"],
                          columns=["bashorat 0", "bashorat 1"])
        assert charting.confusion_figure(cm) is not None
        imp = pd.DataFrame({"xususiyat": ["a", "b"], "muhimlik": [0.7, 0.3]})
        assert charting.importance_figure(imp) is not None
        y = np.array([1.0, 2.0, 3.0])
        assert charting.residual_figure(y, y * 1.1) is not None

    def test_chart_types_registry(self):
        assert len(charting.CHART_TYPES) >= 20
        assert "Asosiy" in charting.chart_groups()


# --------------------------------------------------------------- report ----
class TestReport:
    def test_build_report_html(self, sample_df):
        html = report.build_report(sample_df, dataset_name="test")
        assert html.startswith("<!doctype html>")
        assert "Ustunlar profili" in html
        assert len(html) > 3000

    def test_report_with_figures(self, sample_df):
        fig = charting.build_chart(sample_df, "hist", x="temp")
        html = report.build_report(sample_df, figures=[(fig, "Harorat")])
        assert "data:image/png;base64," in html

    def test_save_report(self, tmp_path, sample_df):
        html = report.build_report(sample_df.head(20))
        p = report.save_report(html, tmp_path / "r.html")
        assert Path(p).exists()


# -------------------------------------------------------------- project ----
class TestProject:
    def test_save_load_roundtrip(self, tmp_path, sample_df):
        p = project.save_project(tmp_path / "loyiha", {"a": sample_df.head(50),
                                                       "b": sample_df.head(10)},
                                 active="a")
        assert Path(p).suffix == ".dfp"
        data, meta = project.load_project(p)
        assert set(data) == {"a", "b"}
        assert len(data["a"]) == 50
        assert meta["active"] == "a"

    def test_project_info(self, tmp_path, sample_df):
        p = project.save_project(tmp_path / "x", {"d": sample_df.head(5)})
        info = project.project_info(p)
        assert info["datasets"][0]["rows"] == 5


# ------------------------------------------------------- integratsiya ------
class TestIntegration:
    def test_full_pipeline(self, tmp_path, apache_lines):
        """Log → yuklash → tahrirlash → profil → ML → hisobot."""
        p = tmp_path / "access.log"
        p.write_text("\n".join(apache_lines * 60), encoding="utf-8")

        res = ingest.load_file(p)
        df = res.df
        assert len(df) == 180

        df = transform.apply_op(df, "drop_cols", columns=["_raw", "ident", "user"])
        df = transform.apply_op(df, "datetime_parts", column="ts", parts=["soat"])
        assert "ts_soat" in df.columns

        prof = profile.profile_dataframe(df)
        assert prof.rows == 180

        # yo'llar butunlay <PATH> ga niqoblanadi — shablonlarni agent ustunida sinaymiz
        tids, table = logparse.mine_templates(df["agent"].astype(str))
        assert len(table) >= 2
        assert int(table["count"].sum()) == 180

        df["xato"] = (df["status"] >= 400).astype(int)
        ml_res = ml.run_automl(df[["method", "path", "bytes", "ts_soat", "xato"]],
                               target="xato", fast=True, cv=0)
        assert ml_res.metrics["aniqlik (accuracy)"] > 0.5

        html = report.build_report(df, profile=prof, ml_result=ml_res,
                                   dataset_name="access")
        assert "Machine Learning natijalari" in html
