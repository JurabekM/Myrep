from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

CLASSIFICATION = "classification"
REGRESSION = "regression"


@dataclass(slots=True)
class ModelRun:
    task: str
    target: str
    features: list[str]
    leaderboard: pd.DataFrame
    best_name: str
    best_pipeline: Any
    metrics: dict[str, float]
    predictions: pd.DataFrame
    notes: list[str] = field(default_factory=list)


def detect_task(target: pd.Series) -> str:
    unique = target.nunique(dropna=True)
    if (not pd.api.types.is_numeric_dtype(target) or pd.api.types.is_bool_dtype(target)
            or unique <= max(15, int(len(target) ** .45))):
        return CLASSIFICATION
    return REGRESSION


def train_automl(frame: pd.DataFrame, target: str, features: list[str] | None = None,
                 task: str | None = None, test_size: float = .2,
                 progress: Callable[[str, int], None] | None = None) -> ModelRun:
    from sklearn.base import clone
    from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
                                 mean_absolute_error, mean_squared_error, r2_score)
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline

    if target not in frame:
        raise ValueError("Nishon ustuni topilmadi")
    data = frame.dropna(subset=[target]).copy()
    if len(data) < 30:
        raise ValueError("Model uchun kamida 30 ta to'liq qator kerak")
    selected = [c for c in (features or list(data.columns)) if c != target and c in data]
    if not selected:
        raise ValueError("Xususiyatlar tanlanmagan")
    notes = leakage_warnings(data, target, selected)
    task = task or detect_task(data[target])
    y = data[target].astype("string") if task == CLASSIFICATION else pd.to_numeric(data[target], errors="coerce")
    valid = y.notna()
    X, y = data.loc[valid, selected], y.loc[valid]
    stratify = y if task == CLASSIFICATION and y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=max(.1, min(.4, test_size)), random_state=42, stratify=stratify)
    processor = _preprocessor(X_train)
    models = _model_zoo(task)
    rows, fitted = [], {}
    for index, (name, estimator) in enumerate(models.items(), 1):
        if progress:
            progress(f"Model: {name}", int(index / len(models) * 85))
        pipe = Pipeline([("prepare", clone(processor)), ("model", estimator)])
        try:
            pipe.fit(X_train, y_train)
            prediction = pipe.predict(X_test)
            if task == CLASSIFICATION:
                score = float(f1_score(y_test, prediction, average="macro"))
                row = {"model": name, "score": score,
                       "accuracy": float(accuracy_score(y_test, prediction)),
                       "balanced_accuracy": float(balanced_accuracy_score(y_test, prediction))}
            else:
                score = float(r2_score(y_test, prediction))
                row = {"model": name, "score": score,
                       "MAE": float(mean_absolute_error(y_test, prediction)),
                       "RMSE": float(mean_squared_error(y_test, prediction) ** .5)}
            rows.append(row)
            fitted[name] = (pipe, prediction)
        except Exception as exc:
            rows.append({"model": name, "score": -np.inf, "error": str(exc)})
    leaderboard = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    if leaderboard.empty or not np.isfinite(leaderboard.iloc[0]["score"]):
        raise RuntimeError("Hech bir model muvaffaqiyatli o'qitilmadi")
    best_name = str(leaderboard.iloc[0]["model"])
    best, prediction = fitted[best_name]
    pred_frame = pd.DataFrame({"actual": y_test.to_numpy(), "prediction": prediction}, index=y_test.index)
    if task == CLASSIFICATION and hasattr(best, "predict_proba"):
        probabilities = best.predict_proba(X_test)
        pred_frame["confidence"] = probabilities.max(axis=1)
    metrics = {key: float(value) for key, value in leaderboard.iloc[0].items()
               if key != "model" and isinstance(value, (int, float, np.number))}
    if progress:
        progress("Tayyor", 100)
    return ModelRun(task, target, selected, leaderboard, best_name, best, metrics,
                    pred_frame, notes)


def anomaly_detection(frame: pd.DataFrame, columns: list[str], contamination: float = .03,
                      method: str = "isolation_forest") -> pd.DataFrame:
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import RobustScaler

    values = frame[columns].apply(pd.to_numeric, errors="coerce")
    matrix = RobustScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(values))
    if method == "local_outlier":
        from sklearn.neighbors import LocalOutlierFactor
        model = LocalOutlierFactor(contamination=contamination)
        labels = model.fit_predict(matrix)
        score = -model.negative_outlier_factor_
    else:
        from sklearn.ensemble import IsolationForest
        model = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
        labels = model.fit_predict(matrix)
        score = -model.score_samples(matrix)
    result = frame.copy()
    result["_anomaly"] = labels == -1
    result["_anomaly_score"] = score
    return result


def cluster(frame: pd.DataFrame, columns: list[str], clusters: int = 4) -> tuple[pd.DataFrame, dict]:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    matrix = frame[columns].apply(pd.to_numeric, errors="coerce")
    values = StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(matrix))
    model = KMeans(n_clusters=max(2, min(12, clusters)), n_init=15, random_state=42)
    labels = model.fit_predict(values)
    coords = PCA(n_components=2, random_state=42).fit_transform(values)
    result = frame.copy()
    result["_cluster"] = labels
    result["_cluster_x"] = coords[:, 0]
    result["_cluster_y"] = coords[:, 1]
    return result, {"silhouette": float(silhouette_score(values, labels)),
                    "clusters": int(model.n_clusters)}


def predict(bundle: dict[str, Any], frame: pd.DataFrame) -> pd.DataFrame:
    features = bundle["features"]
    missing = [column for column in features if column not in frame]
    if missing:
        raise ValueError(f"Ustunlar yetishmaydi: {', '.join(missing)}")
    output = frame.copy()
    output["_prediction"] = bundle["pipeline"].predict(frame[features])
    return output


def save_model(run: ModelRun, path: str | Path) -> Path:
    import joblib
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": run.best_pipeline, "features": run.features,
                 "target": run.target, "task": run.task,
                 "model": run.best_name, "metrics": run.metrics}, p)
    return p


def load_trusted_model(path: str | Path, *, trusted: bool = False) -> dict[str, Any]:
    if not trusted:
        raise PermissionError("Joblib fayl faqat ishonchli manbadan bo'lsa yuklanadi")
    import joblib
    bundle = joblib.load(Path(path))
    required = {"pipeline", "features", "target", "task"}
    if not isinstance(bundle, dict) or not required.issubset(bundle):
        raise ValueError("Noto'g'ri model paketi")
    return bundle


def leakage_warnings(frame: pd.DataFrame, target: str, features: list[str]) -> list[str]:
    notes: list[str] = []
    target_values = frame[target]
    for column in features:
        series = frame[column]
        if len(series) and series.nunique(dropna=True) / len(series) > .98:
            notes.append(f"'{column}' ID bo'lishi mumkin; leakage xavfini tekshiring")
        try:
            if series.equals(target_values):
                notes.append(f"'{column}' target bilan bir xil")
        except Exception:
            pass
    if any(pd.api.types.is_datetime64_any_dtype(frame[column]) for column in features):
        notes.append("Vaqt ustuni topildi: temporal validation tavsiya qilinadi")
    return notes


def _preprocessor(frame: pd.DataFrame):
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    numeric = list(frame.select_dtypes(include=np.number).columns)
    categorical = [column for column in frame.columns if column not in numeric]
    numeric_pipe = Pipeline([("impute", SimpleImputer(strategy="median")),
                             ("scale", StandardScaler())])
    category_pipe = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                              ("encode", OneHotEncoder(handle_unknown="ignore", max_categories=50))])
    return ColumnTransformer([("numeric", numeric_pipe, numeric),
                              ("category", category_pipe, categorical)], remainder="drop")


def _model_zoo(task: str) -> dict[str, Any]:
    if task == CLASSIFICATION:
        from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.tree import DecisionTreeClassifier
        return {
            "Logistic Regression": LogisticRegression(max_iter=1200, class_weight="balanced"),
            "Decision Tree": DecisionTreeClassifier(max_depth=10, class_weight="balanced", random_state=42),
            "Random Forest": RandomForestClassifier(n_estimators=180, class_weight="balanced", n_jobs=-1, random_state=42),
            "Extra Trees": ExtraTreesClassifier(n_estimators=180, class_weight="balanced", n_jobs=-1, random_state=42),
            "Hist Gradient Boosting": HistGradientBoostingClassifier(random_state=42),
        }
    from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import ElasticNet, Ridge
    return {
        "Ridge": Ridge(alpha=1.0),
        "Elastic Net": ElasticNet(alpha=.1, l1_ratio=.5, max_iter=4000),
        "Random Forest": RandomForestRegressor(n_estimators=180, n_jobs=-1, random_state=42),
        "Extra Trees": ExtraTreesRegressor(n_estimators=180, n_jobs=-1, random_state=42),
        "Hist Gradient Boosting": HistGradientBoostingRegressor(random_state=42),
    }

