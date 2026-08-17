# DataForge Pro

**A universal data and log intelligence platform** — reads from any source, analyses
deeply, edits, plots 25 kinds of chart, and uses Machine Learning to find patterns,
anomalies and forecasts.

Python · PySide6 (modern dark UI) · pandas · scikit-learn · matplotlib

---

## Getting started

```bash
pip install -r requirements.txt
```

```bash
python run.py
```

All three invocation styles work:

```bash
python run.py
python -m dataforge
python dataforge/main.py
```

Generate the demo data:

```bash
python run.py --samples
```

---

## Features

### 1. Import — any source, any format

| Source | Details |
|---|---|
| **File** | CSV, TSV, JSON, JSONL/NDJSON, Excel, Parquet, XML, YAML, HTML tables, SQLite, `.gz`, `.zip` |
| **Log file** | The format is **detected automatically**: Apache/Nginx access, Nginx error, Syslog (RFC3164), Python logging, JSON Lines, logfmt (key=value), ISO+level, delimited, free text |
| **Folder** | Merges hundreds of files into one table (with a `_source` column) |
| **Internet** | HTTP/HTTPS — JSON APIs, CSV, HTML tables, raw logs; custom headers (tokens) supported |
| **Database** | SQLite: a table or an arbitrary SQL query |
| **Text** | Clipboard or manually entered text |

Encoding (`chardet`), delimiter and column types (numeric / datetime / boolean /
category) are detected automatically. Epoch timestamps (seconds and milliseconds)
are understood as well.

### 2. Transform — 30+ operations with full undo/redo

**Filter:** by expression (`pandas.query`), text/regex search, numeric range, time range
**Cleaning:** duplicates, empty rows, missing-value imputation (mean/median/mode/
interpolation/forward/backward fill), outlier handling (IQR / quantile / z-score),
dropping constant columns
**Columns:** select, drop, rename, change type
**Text:** find & replace, case conversion, splitting, regex extraction
**Compute:** derived column from an expression, date parts (year/month/hour/weekday/
daypart), binning, scaling (z-score / min-max / robust / log1p)
**Encoding:** one-hot, label encoding
**Structure:** group & aggregate, pivot, melt, time resampling, transpose

Cells are editable directly in the table, and the column-header context menu gives
quick access to the operations. Every change goes into the history — you can jump
back to any earlier state.

### 3. Profile & analysis

- Per column: kind, missing/unique share, min/max/mean/median/quantiles, skew,
  kurtosis, entropy, outliers, most frequent values
- A **data quality score (0–100)** with automatic warnings: heavily missing columns,
  constant columns, ID-like columns, strong skew, many outliers, duplicates
- Correlation (Pearson / Spearman / Kendall) plus a list of the strongest pairs
- Categorical association — Cramér's V
- Interactive grouping / pivoting and time series analysis

### 4. Charts — 25 types

Line · Area · Step · Bar · Horizontal bar · Stacked bar · Pie · Donut · Count ·
Scatter · Bubble · Hexbin · Histogram · KDE · ECDF · Box · Violin · Strip ·
Heatmap · Correlation matrix · Pair plot · Missing value map · Time series ·
Hour × weekday · Rolling average

Each one supports colour (hue), size, an aggregation function, log axes and a trend
line. Charts save as PNG / SVG / PDF or go straight into the report gallery.

### 5. ML Studio

**AutoML** — the task (classification/regression) is detected automatically, up to 11
models are compared with cross-validation, and a leaderboard is produced. Numeric,
categorical and text (TF-IDF) features run through a single pipeline, and datetime
columns are expanded into features automatically.

Models: Logistic/Linear Regression, Ridge, ElasticNet, Decision Tree, Random Forest,
Extra Trees, Gradient Boosting, HistGradientBoosting, KNN, SVM/SVR, Naive Bayes,
MLP, SGD

Results: metrics (accuracy, balanced accuracy, precision, recall, F1, ROC AUC /
R², MAE, RMSE, MAPE), confusion matrix, ROC curves, residual analysis and feature
importance (from the model or via permutation importance).
Models are saved as `.joblib` and can be applied to new data.

**Clustering** — KMeans (automatic `k` by silhouette score), Agglomerative,
GaussianMixture, DBSCAN. PCA projection, cluster profiles and an optimal-`k` chart.

**Anomaly detection** — Isolation Forest, Local Outlier Factor, One-Class SVM,
Elliptic Envelope, Z-score, IQR, EWMA (for time series). The result can be written
back into the data as a column.

**Dimensionality reduction** — PCA (with explained variance), t-SNE, TruncatedSVD.

**Forecasting** — Holt-Winters with seasonality and a 95% confidence interval.

### 6. Log AI

- **Template mining** — variable parts (`<NUM>`, `<IP>`, `<UUID>`, `<PATH>`,
  `<STR>`, `<TS>`) are masked and identical patterns are grouped
- **Rare templates** — anomaly candidates
- **Burst detection** — by z-score inside a time window
- **Text clustering** — TF-IDF + KMeans with key terms and examples per cluster
- **Entity extraction** — IP, IPv6, MAC, UUID, email, URL

### 7. Report

The profile, quality warnings, correlations, charts (embedded as base64), ML results
and the edit history are collected into a single **self-contained HTML file** — no
external dependencies, opens in any browser.

Data can be exported as CSV / Excel / Parquet / JSON / JSONL / SQLite / HTML /
Markdown. The whole session is saved into a `.dfp` project file.

---

## Layout

```
dataforge_en/
├── run.py                      launcher
├── requirements.txt
├── dataforge/
│   ├── main.py                 entry point (--samples, --version)
│   ├── config.py               paths, limits, colour palette
│   ├── core/                   pure logic, no GUI (fully tested)
│   │   ├── ingest.py           universal loading + export
│   │   ├── logparse.py         log format detection, parsers, template mining
│   │   ├── profile.py          statistics, quality checks, correlation
│   │   ├── transform.py        registry of 30+ operations + undo/redo history
│   │   ├── ml.py               AutoML, clustering, anomalies, PCA, forecasting
│   │   ├── charting.py         25 chart types (matplotlib)
│   │   ├── report.py           HTML report
│   │   └── project.py          .dfp project save/load
│   └── ui/                     PySide6 layer
│       ├── theme.py            dark theme (QSS)
│       ├── store.py            central data store (signal based)
│       ├── widgets.py          Card, StatTile, DataFrameModel, ChartCanvas…
│       ├── tasks.py            background threads (the GUI never freezes)
│       ├── main_window.py      sidebar + pages
│       └── pages/              8 pages
├── samples/generate_samples.py demo data generator
└── tests/                      173 tests
```

## Tests

```bash
python -m pytest tests/ -q
```

`tests/test_core.py` — loading, log parsing, profiling, transforms, ML, charts,
reporting, projects and a full integration pipeline.
`tests/test_ui.py` — the store, widgets, pages and navigation (offscreen, so no
display is required).

## Shortcuts

`Ctrl+O` import · `Ctrl+S` save project · `Ctrl+Shift+O` open project ·
`Ctrl+Z` undo · `Ctrl+Y` redo · `Ctrl+E` export · `Ctrl+C` copy · `F1` help
