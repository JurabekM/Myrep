//! ML skorlovchi (ADR-0005): `MlScorer` trait, standart — `tract-onnx` (sof Rust).
//!
//! Model `shield-ml/train.py` da LightGBM → ONNX (`TreeEnsembleClassifier`, LOGISTIC) sifatida
//! eksport qilinadi; metadata JSON'dagi belgi nomlari `TXN_FEATURES` bilan aynan mos bo'lishi shart.

use serde::Deserialize;
use tract_onnx::prelude::*;

use crate::features::TXN_FEATURES;

/// Standart model (binarga joylangan).
pub const DEFAULT_MODEL: &[u8] = include_bytes!("../models/shield_v0.onnx");
/// Standart model metadatasi.
pub const DEFAULT_MODEL_META: &str = include_str!("../models/shield_v0.json");

/// ML skorlovchi.
pub trait MlScorer: Send + Sync + std::fmt::Debug {
    /// Fraud ehtimoli `[0, 1]`.
    fn predict(&self, features: &[f32]) -> Result<f32, String>;
    fn version(&self) -> &str;
}

/// Model metadatasi.
#[derive(Debug, Clone, Deserialize)]
pub struct ModelMeta {
    pub version: String,
    pub feature_names: Vec<String>,
    #[serde(default)]
    pub trained_on: String,
}

type Plan = std::sync::Arc<TypedRunnableModel>;

/// `tract-onnx` asosidagi skorlovchi.
pub struct TractScorer {
    plan: Plan,
    meta: ModelMeta,
}

impl std::fmt::Debug for TractScorer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "TractScorer({})", self.meta.version)
    }
}

impl TractScorer {
    /// ONNX baytlari va metadata JSON'dan.
    pub fn load(onnx: &[u8], meta_json: &str) -> Result<Self, String> {
        let meta: ModelMeta =
            serde_json::from_str(meta_json).map_err(|e| format!("model metadata: {e}"))?;
        if meta.feature_names.len() != TXN_FEATURES.len()
            || meta
                .feature_names
                .iter()
                .zip(TXN_FEATURES.iter())
                .any(|(a, b)| a != b)
        {
            return Err("model belgilari dvigatel belgilariga mos emas (train/serve drift)".into());
        }
        let n = TXN_FEATURES.len();
        let plan = tract_onnx::onnx()
            .model_for_read(&mut std::io::Cursor::new(onnx))
            .and_then(|m| m.with_input_fact(0, f32::fact([1, n]).into()))
            .and_then(|m| m.into_optimized())
            .and_then(|m| m.into_runnable())
            .map_err(|e| format!("ONNX modelni yuklab bo'lmadi: {e}"))?;
        Ok(Self { plan, meta })
    }

    pub fn default_model() -> Result<Self, String> {
        Self::load(DEFAULT_MODEL, DEFAULT_MODEL_META)
    }

    pub fn meta(&self) -> &ModelMeta {
        &self.meta
    }
}

impl MlScorer for TractScorer {
    fn predict(&self, features: &[f32]) -> Result<f32, String> {
        let n = TXN_FEATURES.len();
        if features.len() != n {
            return Err("belgilar soni noto'g'ri".into());
        }
        let input = tract_ndarray::Array2::from_shape_vec((1, n), features.to_vec())
            .map_err(|e| e.to_string())?;
        let out = self
            .plan
            .run(tvec!(Tensor::from(input).into()))
            .map_err(|e| format!("ONNX: {e}"))?;
        // onnxmltools (zipmap=False): 0 — label, 1 — ehtimollar [1, 2].
        let probs = out
            .get(1)
            .ok_or("ONNX: ehtimollar chiqishi yo'q")?
            .to_plain_array_view::<f32>()
            .map_err(|e| e.to_string())?;
        probs
            .iter()
            .nth(1)
            .copied()
            .map(|p| p.clamp(0.0, 1.0))
            .ok_or_else(|| "ONNX: ehtimollar shakli".into())
    }

    fn version(&self) -> &str {
        &self.meta.version
    }
}
