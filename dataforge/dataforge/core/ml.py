"""Machine Learning yadrosi.

Imkoniyatlar:

* **AutoML** — vazifani (klassifikatsiya/regressiya) avtomatik aniqlash, bir necha
  modelni cross-validation bilan taqqoslash, eng yaxshisini tanlash
* **Klasterlash** — KMeans (avto-k), DBSCAN, Agglomerative, GaussianMixture
* **Anomaliya deteksiyasi** — IsolationForest, LOF, OneClassSVM, z-score, IQR, EWMA
* **O'lchov kamaytirish** — PCA, t-SNE, TruncatedSVD
* **Matn/log klasterlash** — TF-IDF + KMeans + har klaster uchun kalit so'zlar
* **Bashorat (forecast)** — Holt-Winters / trend fallback
* **Model saqlash/yuklash** va yangi ma'lumotga qo'llash
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..config import MAX_CATEGORY_ONEHOT, SAMPLE_FOR_HEAVY

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

CLASSIFICATION = "klassifikatsiya"
REGRESSION = "regressiya"


# ---------------------------------------------------------------------------
# Vazifa aniqlash va tayyorgarlik
# ---------------------------------------------------------------------------
def detect_task(y: pd.Series) -> str:
    """Nishon ustunidan vazifa turini aniqlaydi."""
    s = y.dropna()
    if s.empty:
        raise ValueError("Nishon ustuni bo'sh")
    if pd.api.types.is_bool_dtype(s) or isinstance(s.dtype, pd.CategoricalDtype):
        return CLASSIFICATION
    if not pd.api.types.is_numeric_dtype(s):
        return CLASSIFICATION
    nuniq = s.nunique()
    if nuniq <= 2:
        return CLASSIFICATION
    # butun sonli va kam unikal → klassifikatsiya
    is_int = np.allclose(s.astype(float) % 1, 0)
    if is_int and nuniq <= max(20, int(0.02 * len(s))):
        return CLASSIFICATION
    return REGRESSION


def split_feature_types(X: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    """Xususiyatlarni sonli / kategorik / matn turlariga ajratadi."""
    from .profile import column_kind, CATEGORICAL, NUMERIC, TEXT, BOOLEAN, DATETIME

    num, cat, txt = [], [], []
    for c in X.columns:
        kind = column_kind(X[c])
        if kind in (NUMERIC, BOOLEAN):
            num.append(c)
        elif kind == DATETIME:
            continue  # datetime xususiyatlari alohida chiqariladi
        elif kind == CATEGORICAL and X[c].nunique(dropna=True) <= MAX_CATEGORY_ONEHOT:
            cat.append(c)
        elif kind == TEXT:
            txt.append(c)
    return num, cat, txt


def expand_datetime(X: pd.DataFrame) -> pd.DataFrame:
    """Sana ustunlarini son xususiyatlarga aylantiradi."""
    out = X.copy()
    for c in list(out.columns):
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            d = pd.to_datetime(out[c], errors="coerce")
            try:
                d = d.dt.tz_localize(None)
            except (TypeError, AttributeError):
                pass
            out[f"{c}__year"] = d.dt.year
            out[f"{c}__month"] = d.dt.month
            out[f"{c}__day"] = d.dt.day
            out[f"{c}__hour"] = d.dt.hour
            out[f"{c}__dow"] = d.dt.dayofweek
            out[f"{c}__epoch"] = d.astype("int64", errors="ignore") // 10**9
            out.drop(columns=[c], inplace=True)
    return out


def build_preprocessor(X: pd.DataFrame, use_text: bool = True,
                       scale_numeric: bool = True):
    """Xususiyat turlariga mos ColumnTransformer quradi."""
    from sklearn.compose import ColumnTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    num, cat, txt = split_feature_types(X)
    parts: list[tuple[str, Any, Any]] = []

    if num:
        steps = [("imp", SimpleImputer(strategy="median"))]
        if scale_numeric:
            steps.append(("sc", StandardScaler()))
        parts.append(("num", Pipeline(steps), num))
    if cat:
        parts.append((
            "cat",
            Pipeline([
                ("imp", SimpleImputer(strategy="most_frequent")),
                ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False,
                                     min_frequency=0.01)),
            ]),
            cat,
        ))
    if txt and use_text:
        # faqat birinchi matn ustuni — TF-IDF juda kengayib ketmasligi uchun
        col = txt[0]
        parts.append((
            f"txt_{col}",
            Pipeline([
                ("str", _ToString()),
                ("tfidf", TfidfVectorizer(max_features=300, ngram_range=(1, 2),
                                          min_df=2, sublinear_tf=True)),
            ]),
            col,
        ))
    if not parts:
        raise ValueError("Modellash uchun mos xususiyat topilmadi")
    return ColumnTransformer(parts, remainder="drop", sparse_threshold=0.0)


class _ToString:
    """TF-IDF uchun matnga aylantiruvchi kichik transformer."""

    def fit(self, X, y=None):  # noqa: N803
        return self

    def transform(self, X):  # noqa: N803
        s = X if isinstance(X, pd.Series) else pd.Series(np.asarray(X).ravel())
        return s.fillna("").astype(str)

    def get_params(self, deep: bool = True) -> dict:
        return {}

    def set_params(self, **kw):
        return self


# ---------------------------------------------------------------------------
# Model to'plami
# ---------------------------------------------------------------------------
def model_zoo(task: str, fast: bool = False) -> dict[str, Any]:
    """Vazifaga mos modellar lug'ati."""
    from sklearn.ensemble import (ExtraTreesClassifier, ExtraTreesRegressor,
                                  GradientBoostingClassifier, GradientBoostingRegressor,
                                  HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                                  RandomForestClassifier, RandomForestRegressor)
    from sklearn.linear_model import (ElasticNet, LinearRegression, LogisticRegression,
                                      Ridge, SGDClassifier)
    from sklearn.naive_bayes import GaussianNB
    from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    from sklearn.svm import SVC, SVR
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

    if task == CLASSIFICATION:
        zoo = {
            "Logistik regressiya": LogisticRegression(max_iter=1500, n_jobs=None),
            "Qaror daraxti": DecisionTreeClassifier(max_depth=12, random_state=42),
            "Random Forest": RandomForestClassifier(n_estimators=250, n_jobs=-1,
                                                    random_state=42),
            "Extra Trees": ExtraTreesClassifier(n_estimators=250, n_jobs=-1,
                                                random_state=42),
            "Gradient Boosting": GradientBoostingClassifier(random_state=42),
            "HistGradientBoosting": HistGradientBoostingClassifier(random_state=42),
            "KNN": KNeighborsClassifier(n_neighbors=7),
            "SVM (RBF)": SVC(probability=True, random_state=42),
            "Naive Bayes": GaussianNB(),
            "Neyron tarmoq (MLP)": MLPClassifier(hidden_layer_sizes=(128, 64),
                                                 max_iter=400, random_state=42),
            "SGD": SGDClassifier(loss="modified_huber", random_state=42),
        }
        if fast:
            for k in ("SVM (RBF)", "Neyron tarmoq (MLP)", "Gradient Boosting", "SGD"):
                zoo.pop(k, None)
        return zoo

    zoo = {
        "Chiziqli regressiya": LinearRegression(),
        "Ridge": Ridge(alpha=1.0, random_state=42),
        "ElasticNet": ElasticNet(alpha=0.1, random_state=42),
        "Qaror daraxti": DecisionTreeRegressor(max_depth=12, random_state=42),
        "Random Forest": RandomForestRegressor(n_estimators=250, n_jobs=-1,
                                               random_state=42),
        "Extra Trees": ExtraTreesRegressor(n_estimators=250, n_jobs=-1, random_state=42),
        "Gradient Boosting": GradientBoostingRegressor(random_state=42),
        "HistGradientBoosting": HistGradientBoostingRegressor(random_state=42),
        "KNN": KNeighborsRegressor(n_neighbors=7),
        "SVR": SVR(),
        "Neyron tarmoq (MLP)": MLPRegressor(hidden_layer_sizes=(128, 64),
                                            max_iter=500, random_state=42),
    }
    if fast:
        for k in ("SVR", "Neyron tarmoq (MLP)", "Gradient Boosting", "ElasticNet"):
            zoo.pop(k, None)
    return zoo


# ---------------------------------------------------------------------------
# AutoML
# ---------------------------------------------------------------------------
@dataclass
class MLResult:
    task: str
    target: str
    features: list[str]
    leaderboard: pd.DataFrame
    best_name: str
    best_model: Any
    metrics: dict[str, float]
    y_true: np.ndarray | None = None
    y_pred: np.ndarray | None = None
    y_proba: np.ndarray | None = None
    classes: list[str] = field(default_factory=list)
    importance: pd.DataFrame | None = None
    confusion: pd.DataFrame | None = None
    n_train: int = 0
    n_test: int = 0
    warnings: list[str] = field(default_factory=list)

    def summary_text(self) -> str:
        lines = [
            f"Vazifa: {self.task}",
            f"Nishon: {self.target}",
            f"Xususiyatlar: {len(self.features)} ta",
            f"Trening/Test: {self.n_train:,} / {self.n_test:,}",
            f"Eng yaxshi model: {self.best_name}",
            "",
            "Metrikalar:",
        ]
        for k, v in self.metrics.items():
            lines.append(f"  · {k}: {v:.4f}" if isinstance(v, float) else f"  · {k}: {v}")
        return "\n".join(lines)


def _classification_metrics(y_true, y_pred, y_proba=None) -> dict[str, float]:
    from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
                                 precision_score, recall_score, roc_auc_score)

    m = {
        "aniqlik (accuracy)": float(accuracy_score(y_true, y_pred)),
        "balanslangan aniqlik": float(balanced_accuracy_score(y_true, y_pred)),
        "precision (makro)": float(precision_score(y_true, y_pred, average="macro",
                                                   zero_division=0)),
        "recall (makro)": float(recall_score(y_true, y_pred, average="macro",
                                             zero_division=0)),
        "F1 (makro)": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "F1 (vaznli)": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }
    if y_proba is not None:
        try:
            classes = np.unique(y_true)
            if len(classes) == 2:
                col = y_proba[:, 1] if y_proba.ndim > 1 else y_proba
                m["ROC AUC"] = float(roc_auc_score(y_true, col))
            else:
                m["ROC AUC (ovr)"] = float(
                    roc_auc_score(y_true, y_proba, multi_class="ovr", average="macro"))
        except Exception:
            pass
    return m


def _regression_metrics(y_true, y_pred) -> dict[str, float]:
    from sklearn.metrics import (mean_absolute_error, mean_squared_error,
                                 median_absolute_error, r2_score)

    mse = float(mean_squared_error(y_true, y_pred))
    yt = np.asarray(y_true, dtype=float)
    nz = np.abs(yt) > 1e-9
    mape = (float(np.mean(np.abs((yt[nz] - np.asarray(y_pred, dtype=float)[nz]) / yt[nz])) * 100)
            if nz.any() else float("nan"))
    return {
        "R²": float(r2_score(y_true, y_pred)),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mse)),
        "MSE": mse,
        "MedAE": float(median_absolute_error(y_true, y_pred)),
        "MAPE %": mape,
    }


def run_automl(df: pd.DataFrame, target: str, features: list[str] | None = None,
               task: str | None = None, models: list[str] | None = None,
               test_size: float = 0.2, cv: int = 3, fast: bool = False,
               max_rows: int = 200_000, use_text: bool = True,
               progress: Any = None) -> MLResult:
    """Bir necha modelni o'qitib, eng yaxshisini tanlaydi.

    ``progress`` — ``progress(msg: str, pct: int)`` ko'rinishidagi chaqiriluvchi.
    """
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.pipeline import Pipeline

    def report(msg: str, pct: int) -> None:
        if progress:
            progress(msg, pct)

    if target not in df.columns:
        raise ValueError(f"Nishon ustuni topilmadi: {target}")

    data = df.dropna(subset=[target])
    if len(data) > max_rows:
        data = data.sample(max_rows, random_state=42)
    if len(data) < 20:
        raise ValueError(f"Ma'lumot juda kam ({len(data)} qator). Kamida 20 ta kerak.")

    feats = [c for c in (features or [c for c in data.columns if c != target])
             if c != target and c in data.columns]
    if not feats:
        raise ValueError("Xususiyat ustunlari tanlanmagan")

    y = data[target]
    X = expand_datetime(data[feats])
    task = task or detect_task(y)
    notes: list[str] = []

    if task == CLASSIFICATION:
        y = y.astype(str)
        counts = y.value_counts()
        rare = counts[counts < 2]
        if not rare.empty:
            keep = y.isin(counts[counts >= 2].index)
            X, y = X[keep.to_numpy()], y[keep.to_numpy()]
            notes.append(f"{len(rare)} ta juda kam uchraydigan sinf olib tashlandi")
        if y.nunique() < 2:
            raise ValueError("Nishonda kamida 2 xil sinf bo'lishi kerak")
    else:
        y = pd.to_numeric(y, errors="coerce")
        ok = y.notna()
        X, y = X[ok.to_numpy()], y[ok.to_numpy()]

    report("Ma'lumot bo'linmoqda…", 5)
    strat = y if (task == CLASSIFICATION and y.value_counts().min() >= 2) else None
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=strat)

    pre = build_preprocessor(X, use_text=use_text)
    zoo = model_zoo(task, fast=fast)
    if models:
        zoo = {k: v for k, v in zoo.items() if k in models} or zoo

    scoring = "f1_macro" if task == CLASSIFICATION else "r2"
    rows: list[dict[str, Any]] = []
    fitted: dict[str, Any] = {}
    total = len(zoo)

    for i, (name, est) in enumerate(zoo.items(), 1):
        report(f"O'qitilmoqda: {name} ({i}/{total})", int(10 + 70 * i / total))
        pipe = Pipeline([("pre", pre), ("model", est)])
        try:
            import time

            t0 = time.perf_counter()
            pipe.fit(X_tr, y_tr)
            fit_s = time.perf_counter() - t0
            pred = pipe.predict(X_te)
            metrics = (_classification_metrics(y_te, pred) if task == CLASSIFICATION
                       else _regression_metrics(y_te, pred))
            row = {"model": name, **{k: round(v, 4) for k, v in metrics.items()},
                   "fit_s": round(fit_s, 2)}
            if cv and cv > 1 and len(X_tr) >= cv * 5:
                try:
                    sc = cross_val_score(pipe, X_tr, y_tr, cv=cv, scoring=scoring,
                                         n_jobs=1, error_score="raise")
                    row["CV o'rtacha"] = round(float(np.mean(sc)), 4)
                    row["CV std"] = round(float(np.std(sc)), 4)
                except Exception:
                    pass
            rows.append(row)
            fitted[name] = pipe
        except Exception as exc:
            rows.append({"model": name, "xato": str(exc)[:120]})

    if not fitted:
        raise RuntimeError("Hech bir model o'qitilmadi. Xususiyatlarni tekshiring.")

    board = pd.DataFrame(rows)
    key = "F1 (makro)" if task == CLASSIFICATION else "R²"
    if key in board.columns:
        board = board.sort_values(key, ascending=False, na_position="last")
    board = board.reset_index(drop=True)
    best_name = str(board.iloc[0]["model"])
    best = fitted.get(best_name) or next(iter(fitted.values()))

    report("Eng yaxshi model baholanmoqda…", 85)
    y_pred = best.predict(X_te)
    y_proba = None
    classes: list[str] = []
    confusion = None
    if task == CLASSIFICATION:
        classes = [str(c) for c in getattr(best, "classes_", np.unique(y_te))]
        if hasattr(best, "predict_proba"):
            try:
                y_proba = best.predict_proba(X_te)
            except Exception:
                pass
        from sklearn.metrics import confusion_matrix

        cm = confusion_matrix(y_te, y_pred, labels=classes)
        confusion = pd.DataFrame(cm, index=[f"haqiqiy {c}" for c in classes],
                                 columns=[f"bashorat {c}" for c in classes])
        metrics = _classification_metrics(y_te, y_pred, y_proba)
    else:
        metrics = _regression_metrics(y_te, y_pred)

    report("Xususiyat muhimligi hisoblanmoqda…", 92)
    importance = compute_importance(best, X_te, y_te, task)

    report("Tayyor", 100)
    return MLResult(
        task=task, target=target, features=list(X.columns), leaderboard=board,
        best_name=best_name, best_model=best, metrics=metrics,
        y_true=np.asarray(y_te), y_pred=np.asarray(y_pred), y_proba=y_proba,
        classes=classes, importance=importance, confusion=confusion,
        n_train=len(X_tr), n_test=len(X_te), warnings=notes,
    )


def compute_importance(pipe: Any, X: pd.DataFrame, y: pd.Series,
                       task: str, max_rows: int = 3000) -> pd.DataFrame | None:
    """Xususiyat muhimligi — model ichidan yoki permutation orqali."""
    try:
        model = pipe.named_steps.get("model") if hasattr(pipe, "named_steps") else pipe
        pre = pipe.named_steps.get("pre") if hasattr(pipe, "named_steps") else None
        names: list[str] | None = None
        if pre is not None:
            try:
                names = [str(n) for n in pre.get_feature_names_out()]
            except Exception:
                names = None

        if hasattr(model, "feature_importances_") and names is not None:
            vals = np.asarray(model.feature_importances_, dtype=float)
            if len(vals) == len(names):
                out = pd.DataFrame({"xususiyat": names, "muhimlik": vals})
                return out.sort_values("muhimlik", ascending=False).head(40).reset_index(drop=True)
        if hasattr(model, "coef_") and names is not None:
            coef = np.asarray(model.coef_, dtype=float)
            vals = np.abs(coef).mean(axis=0) if coef.ndim > 1 else np.abs(coef)
            if len(vals) == len(names):
                out = pd.DataFrame({"xususiyat": names, "muhimlik": vals})
                return out.sort_values("muhimlik", ascending=False).head(40).reset_index(drop=True)

        from sklearn.inspection import permutation_importance

        Xs, ys = (X, y)
        if len(X) > max_rows:
            idx = np.random.RandomState(42).choice(len(X), max_rows, replace=False)
            Xs, ys = X.iloc[idx], y.iloc[idx]
        scoring = "f1_macro" if task == CLASSIFICATION else "r2"
        r = permutation_importance(pipe, Xs, ys, n_repeats=5, random_state=42,
                                   scoring=scoring, n_jobs=1)
        out = pd.DataFrame({"xususiyat": list(X.columns),
                            "muhimlik": r.importances_mean,
                            "std": r.importances_std})
        return out.sort_values("muhimlik", ascending=False).head(40).reset_index(drop=True)
    except Exception:
        return None


def roc_curves(y_true: np.ndarray, y_proba: np.ndarray,
               classes: list[str]) -> dict[str, tuple[np.ndarray, np.ndarray, float]]:
    """Har bir sinf uchun ROC egri chiziqlari (fpr, tpr, auc)."""
    from sklearn.metrics import auc, roc_curve

    out: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}
    if y_proba is None:
        return out
    y = np.asarray(y_true).astype(str)
    if y_proba.ndim == 1:
        y_proba = np.column_stack([1 - y_proba, y_proba])
    for i, cls in enumerate(classes):
        if i >= y_proba.shape[1]:
            break
        try:
            fpr, tpr, _ = roc_curve((y == str(cls)).astype(int), y_proba[:, i])
            out[str(cls)] = (fpr, tpr, float(auc(fpr, tpr)))
        except Exception:
            continue
    return out


def learning_curve_data(pipe: Any, X: pd.DataFrame, y: pd.Series, task: str,
                        cv: int = 3) -> pd.DataFrame:
    """O'rganish egri chizig'i uchun ma'lumot."""
    from sklearn.model_selection import learning_curve

    scoring = "f1_macro" if task == CLASSIFICATION else "r2"
    sizes, train, test = learning_curve(
        pipe, X, y, cv=cv, scoring=scoring, n_jobs=1,
        train_sizes=np.linspace(0.15, 1.0, 6), random_state=42)
    return pd.DataFrame({
        "hajm": sizes,
        "trening": train.mean(axis=1),
        "validatsiya": test.mean(axis=1),
    })


# ---------------------------------------------------------------------------
# Klasterlash
# ---------------------------------------------------------------------------
@dataclass
class ClusterResult:
    labels: np.ndarray
    algo: str
    k: int
    silhouette: float
    coords: np.ndarray | None
    sizes: pd.Series
    centers: pd.DataFrame | None = None
    profile: pd.DataFrame | None = None
    noise: int = 0


def cluster(df: pd.DataFrame, columns: list[str], algo: str = "KMeans",
            k: int | None = None, auto_k_range: tuple[int, int] = (2, 8),
            eps: float = 0.5, min_samples: int = 5,
            max_rows: int = 100_000) -> ClusterResult:
    """Ma'lumotni klasterlarga ajratadi va sifat bahosini beradi."""
    from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
    from sklearn.decomposition import PCA
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import silhouette_score
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler

    cols = [c for c in columns if c in df.columns]
    if len(cols) < 1:
        raise ValueError("Kamida bitta ustun tanlang")
    data = df[cols].copy()
    if len(data) > max_rows:
        data = data.sample(max_rows, random_state=42)

    num = data.select_dtypes(include=[np.number])
    if num.shape[1] == 0:
        raise ValueError("Klasterlash uchun sonli ustun kerak")
    Xn = StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(num))

    noise = 0
    if algo == "DBSCAN":
        model = DBSCAN(eps=eps, min_samples=int(min_samples), n_jobs=-1)
        labels = model.fit_predict(Xn)
        noise = int((labels == -1).sum())
        k_eff = len(set(labels)) - (1 if noise else 0)
    else:
        if k is None:
            k, _ = auto_k(Xn, *auto_k_range, algo=algo)
        k = max(2, int(k))
        if algo == "Agglomerative":
            model = AgglomerativeClustering(n_clusters=k)
        elif algo == "GaussianMixture":
            model = GaussianMixture(n_components=k, random_state=42)
        else:
            model = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = model.fit_predict(Xn)
        k_eff = k

    sil = float("nan")
    try:
        mask = labels != -1
        if len(set(labels[mask])) > 1:
            sub = Xn[mask]
            if len(sub) > 10_000:
                idx = np.random.RandomState(42).choice(len(sub), 10_000, replace=False)
                sil = float(silhouette_score(sub[idx], labels[mask][idx]))
            else:
                sil = float(silhouette_score(sub, labels[mask]))
    except Exception:
        pass

    coords = None
    try:
        coords = PCA(n_components=2, random_state=42).fit_transform(Xn)
    except Exception:
        pass

    centers = None
    if hasattr(model, "cluster_centers_"):
        centers = pd.DataFrame(model.cluster_centers_, columns=list(num.columns))
        centers.index.name = "klaster"

    prof = num.copy()
    prof["klaster"] = labels
    profile = prof.groupby("klaster").mean(numeric_only=True).round(4).reset_index()

    return ClusterResult(
        labels=labels, algo=algo, k=int(k_eff), silhouette=sil, coords=coords,
        sizes=pd.Series(labels).value_counts().sort_index(),
        centers=centers, profile=profile, noise=noise,
    )


def auto_k(X: np.ndarray, kmin: int = 2, kmax: int = 8,
           algo: str = "KMeans") -> tuple[int, pd.DataFrame]:
    """Siluet bahosi bo'yicha optimal klasterlar sonini topadi."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    if len(X) > 10_000:
        X = X[np.random.RandomState(42).choice(len(X), 10_000, replace=False)]
    rows = []
    best_k, best_s = kmin, -2.0
    for k in range(max(2, kmin), max(3, kmax) + 1):
        try:
            km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
            s = float(silhouette_score(X, km.labels_))
            rows.append({"k": k, "siluet": round(s, 4), "inersiya": round(float(km.inertia_), 2)})
            if s > best_s:
                best_k, best_s = k, s
        except Exception:
            continue
    return best_k, pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Anomaliya deteksiyasi
# ---------------------------------------------------------------------------
ANOMALY_METHODS = [
    "Isolation Forest", "Local Outlier Factor", "One-Class SVM",
    "Elliptic Envelope", "Z-score", "IQR", "EWMA (vaqt qatori)",
]


@dataclass
class AnomalyResult:
    scores: np.ndarray
    is_anomaly: np.ndarray
    method: str
    threshold: float
    n_anomalies: int
    index: pd.Index
    detail: pd.DataFrame | None = None


def detect_anomalies(df: pd.DataFrame, columns: list[str],
                     method: str = "Isolation Forest", contamination: float = 0.02,
                     z_threshold: float = 3.0, ewma_span: int = 20,
                     max_rows: int = 200_000) -> AnomalyResult:
    """Tanlangan ustunlar bo'yicha anomal qatorlarni topadi."""
    from sklearn.covariance import EllipticEnvelope
    from sklearn.ensemble import IsolationForest
    from sklearn.impute import SimpleImputer
    from sklearn.neighbors import LocalOutlierFactor
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import OneClassSVM

    cols = [c for c in columns if c in df.columns]
    data = df[cols].select_dtypes(include=[np.number])
    if data.shape[1] == 0:
        raise ValueError("Anomaliya qidirish uchun sonli ustun kerak")
    work = data if len(data) <= max_rows else data.sample(max_rows, random_state=42)
    idx = work.index
    X = SimpleImputer(strategy="median").fit_transform(work)
    Xs = StandardScaler().fit_transform(X)

    if method == "Z-score":
        z = np.abs(Xs).max(axis=1)
        flags = z > z_threshold
        return AnomalyResult(z, flags, method, float(z_threshold), int(flags.sum()), idx)

    if method == "IQR":
        flags = np.zeros(len(work), dtype=bool)
        score = np.zeros(len(work))
        for j in range(X.shape[1]):
            col = X[:, j]
            q1, q3 = np.percentile(col, [25, 75])
            iqr = q3 - q1 or 1.0
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            dist = np.maximum(lo - col, col - hi) / iqr
            score = np.maximum(score, dist)
            flags |= (col < lo) | (col > hi)
        return AnomalyResult(score, flags, method, 0.0, int(flags.sum()), idx)

    if method == "EWMA (vaqt qatori)":
        col = work.iloc[:, 0]
        ew = col.ewm(span=int(ewma_span), adjust=False)
        mean, std = ew.mean(), ew.std().bfill().fillna(col.std() or 1.0)
        z = ((col - mean) / std.replace(0, np.nan)).abs().fillna(0)
        flags = (z > z_threshold).to_numpy()
        detail = pd.DataFrame({"qiymat": col.to_numpy(), "ewma": mean.to_numpy(),
                               "zscore": z.to_numpy()}, index=idx)
        return AnomalyResult(z.to_numpy(), flags, method, float(z_threshold),
                             int(flags.sum()), idx, detail)

    if method == "Local Outlier Factor":
        model = LocalOutlierFactor(n_neighbors=min(35, max(5, len(Xs) // 20)),
                                   contamination=contamination, n_jobs=-1)
        pred = model.fit_predict(Xs)
        scores = -model.negative_outlier_factor_
    elif method == "One-Class SVM":
        model = OneClassSVM(nu=min(0.5, max(0.001, contamination)), gamma="scale")
        pred = model.fit_predict(Xs)
        scores = -model.decision_function(Xs)
    elif method == "Elliptic Envelope":
        model = EllipticEnvelope(contamination=contamination, random_state=42,
                                 support_fraction=0.9)
        pred = model.fit_predict(Xs)
        scores = -model.decision_function(Xs)
    else:
        model = IsolationForest(contamination=contamination, n_estimators=250,
                                random_state=42, n_jobs=-1)
        pred = model.fit_predict(Xs)
        scores = -model.score_samples(Xs)

    flags = pred == -1
    thr = float(np.min(scores[flags])) if flags.any() else float("nan")
    return AnomalyResult(scores, flags, method, thr, int(flags.sum()), idx)


# ---------------------------------------------------------------------------
# O'lchov kamaytirish
# ---------------------------------------------------------------------------
def reduce_dim(df: pd.DataFrame, columns: list[str], method: str = "PCA",
               n_components: int = 2, perplexity: float = 30.0) -> tuple[np.ndarray, dict]:
    """PCA / t-SNE / SVD orqali 2–3 o'lchovga siqadi."""
    from sklearn.decomposition import PCA, TruncatedSVD
    from sklearn.impute import SimpleImputer
    from sklearn.manifold import TSNE
    from sklearn.preprocessing import StandardScaler

    data = df[[c for c in columns if c in df.columns]].select_dtypes(include=[np.number])
    if data.shape[1] < 2:
        raise ValueError("Kamida 2 ta sonli ustun kerak")
    if len(data) > SAMPLE_FOR_HEAVY and method == "t-SNE":
        data = data.sample(SAMPLE_FOR_HEAVY, random_state=42)
    X = StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(data))
    n_components = int(min(n_components, X.shape[1]))

    info: dict[str, Any] = {"method": method, "n": len(X), "index": data.index}
    if method == "t-SNE":
        per = float(min(perplexity, max(5, (len(X) - 1) / 3)))
        model = TSNE(n_components=min(n_components, 3), perplexity=per,
                     random_state=42, init="pca")
        coords = model.fit_transform(X)
        info["kl_divergence"] = float(getattr(model, "kl_divergence_", np.nan))
    elif method == "SVD":
        model = TruncatedSVD(n_components=n_components, random_state=42)
        coords = model.fit_transform(X)
        info["explained"] = model.explained_variance_ratio_.tolist()
    else:
        model = PCA(n_components=n_components, random_state=42)
        coords = model.fit_transform(X)
        info["explained"] = model.explained_variance_ratio_.tolist()
        info["loadings"] = pd.DataFrame(
            model.components_.T, index=data.columns,
            columns=[f"PC{i + 1}" for i in range(coords.shape[1])])
    return coords, info


# ---------------------------------------------------------------------------
# Matn / log klasterlash
# ---------------------------------------------------------------------------
@dataclass
class TextClusterResult:
    labels: np.ndarray
    k: int
    terms: dict[int, list[str]]
    sizes: pd.Series
    coords: np.ndarray | None
    examples: dict[int, list[str]]


def text_cluster(texts: pd.Series, k: int = 6, max_features: int = 5000,
                 max_rows: int = 50_000) -> TextClusterResult:
    """Matn (log xabarlari) ni TF-IDF + KMeans bilan mavzularga ajratadi."""
    from sklearn.cluster import KMeans
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    s = texts.dropna().astype(str)
    if len(s) > max_rows:
        s = s.sample(max_rows, random_state=42)
    if len(s) < k * 2:
        raise ValueError(f"Matn juda kam ({len(s)} qator)")

    vec = TfidfVectorizer(max_features=max_features, ngram_range=(1, 2),
                          min_df=2, sublinear_tf=True, stop_words=None,
                          token_pattern=r"(?u)\b[\w<>./-]{2,}\b")
    X = vec.fit_transform(s)
    km = KMeans(n_clusters=int(k), n_init=10, random_state=42)
    labels = km.fit_predict(X)

    names = np.array(vec.get_feature_names_out())
    terms: dict[int, list[str]] = {}
    order = km.cluster_centers_.argsort()[:, ::-1]
    for i in range(int(k)):
        terms[i] = [str(names[j]) for j in order[i, :10] if j < len(names)]

    examples: dict[int, list[str]] = {}
    arr = s.to_numpy()
    for i in range(int(k)):
        sel = arr[labels == i][:5]
        examples[i] = [str(x)[:220] for x in sel]

    coords = None
    try:
        coords = TruncatedSVD(n_components=2, random_state=42).fit_transform(X)
    except Exception:
        pass

    return TextClusterResult(labels=labels, k=int(k), terms=terms,
                             sizes=pd.Series(labels).value_counts().sort_index(),
                             coords=coords, examples=examples)


# ---------------------------------------------------------------------------
# Bashorat (forecast)
# ---------------------------------------------------------------------------
def forecast(series: pd.Series, periods: int = 24,
             seasonal_periods: int | None = None) -> pd.DataFrame:
    """Vaqt qatorini oldinga bashorat qiladi (Holt-Winters, trend fallback)."""
    s = series.dropna().astype(float)
    if len(s) < 8:
        raise ValueError("Bashorat uchun kamida 8 nuqta kerak")

    idx = s.index
    freq = None
    if isinstance(idx, pd.DatetimeIndex) and len(idx) > 2:
        try:
            freq = pd.infer_freq(idx) or (idx[1] - idx[0])
        except Exception:
            freq = idx[1] - idx[0]

    fitted = None
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        sp = seasonal_periods
        kwargs: dict[str, Any] = {"trend": "add", "initialization_method": "estimated"}
        if sp and len(s) >= 2 * sp:
            kwargs.update(seasonal="add", seasonal_periods=int(sp))
        model = ExponentialSmoothing(s.to_numpy(), **kwargs).fit(optimized=True)
        pred = model.forecast(periods)
        fitted = model.fittedvalues
    except Exception:
        x = np.arange(len(s))
        coef = np.polyfit(x, s.to_numpy(), 1)
        pred = np.polyval(coef, np.arange(len(s), len(s) + periods))
        fitted = np.polyval(coef, x)

    resid = s.to_numpy() - np.asarray(fitted)
    sigma = float(np.std(resid)) if len(resid) else 0.0

    if isinstance(idx, pd.DatetimeIndex) and freq is not None:
        try:
            future = pd.date_range(idx[-1], periods=periods + 1, freq=freq)[1:]
        except Exception:
            step = idx[1] - idx[0]
            future = pd.DatetimeIndex([idx[-1] + step * (i + 1) for i in range(periods)])
    else:
        future = pd.RangeIndex(len(s), len(s) + periods)

    return pd.DataFrame({
        "vaqt": future,
        "bashorat": np.asarray(pred, dtype=float),
        "past": np.asarray(pred, dtype=float) - 1.96 * sigma,
        "yuqori": np.asarray(pred, dtype=float) + 1.96 * sigma,
    })


# ---------------------------------------------------------------------------
# Model saqlash / yuklash
# ---------------------------------------------------------------------------
def save_model(result: MLResult, path: str | Path) -> str:
    """O'qitilgan modelni metama'lumot bilan saqlaydi."""
    import joblib

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": result.best_model,
            "task": result.task,
            "target": result.target,
            "features": result.features,
            "metrics": result.metrics,
            "classes": result.classes,
            "name": result.best_name,
        },
        p,
    )
    return str(p)


def load_model(path: str | Path) -> dict[str, Any]:
    """Saqlangan modelni yuklaydi."""
    import joblib

    return joblib.load(Path(path))


def predict_with(bundle: dict[str, Any], df: pd.DataFrame) -> pd.DataFrame:
    """Saqlangan modelni yangi ma'lumotga qo'llaydi."""
    model = bundle["model"]
    X = expand_datetime(df.copy())
    out = df.copy()
    pred = model.predict(X)
    out["bashorat"] = pred
    if bundle.get("task") == CLASSIFICATION and hasattr(model, "predict_proba"):
        try:
            proba = model.predict_proba(X)
            out["ishonch"] = proba.max(axis=1)
        except Exception:
            pass
    return out
