//! `shield-replay` — sintetik hodisalarni Shield dvigateli orqali o'tkazadi.
//!
//! ```text
//! shield-replay featurize <events.csv> <out_dir>      # o'qitish uchun belgilar (Rust feature store)
//! shield-replay evaluate  <events.csv> <report.json> [--model m.onnx --meta m.json]
//! shield-replay bench     <warmup.csv> <events.csv>    # skorlash kechikishi (p50/p95/p99)
//! shield-replay parity    <parity.csv> [--model m.onnx --meta m.json]
//! ```
#![forbid(unsafe_code)]
#![allow(clippy::print_stdout)]

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::process::ExitCode;
use std::sync::Arc;
use std::time::Instant;

use mpay_common::ports::{IdvDecision, RiskDecision};
use mpay_shield::engine::Shield;
use mpay_shield::features::{IDV_FEATURES, TXN_FEATURES};
use mpay_shield::model::{MlScorer, TractScorer};
use mpay_shield::replay::{parse_events, EventKind, LabeledEvent};
use mpay_shield::rules::RuleSet;
use serde_json::json;

fn read(p: &str) -> Result<String, String> {
    std::fs::read_to_string(p).map_err(|e| format!("{p}: {e}"))
}

fn load_events(p: &str, rules: &RuleSet) -> Result<Vec<LabeledEvent>, String> {
    parse_events(&read(p)?, |m| rules.is_p2p(m))
}

fn model_from_args(args: &[String]) -> Result<Option<Arc<dyn MlScorer>>, String> {
    let get = |k: &str| {
        args.iter()
            .position(|a| a == k)
            .and_then(|i| args.get(i + 1))
    };
    if args.iter().any(|a| a == "--no-model") {
        return Ok(None);
    }
    let m: Arc<dyn MlScorer> = match (get("--model"), get("--meta")) {
        (Some(m), Some(j)) => Arc::new(TractScorer::load(
            &std::fs::read(m).map_err(|e| format!("{m}: {e}"))?,
            &read(j)?,
        )?),
        _ => Arc::new(TractScorer::default_model()?),
    };
    Ok(Some(m))
}

fn featurize(events: &str, out_dir: &str) -> Result<(), String> {
    let rules = RuleSet::default_rules()?;
    let evs = load_events(events, &rules)?;
    let shield = Shield::new(rules, None);
    std::fs::create_dir_all(out_dir).map_err(|e| e.to_string())?;
    let mut txn = format!("label,scenario,{}\n", TXN_FEATURES.join(","));
    let mut idv = format!("label,scenario,{}\n", IDV_FEATURES.join(","));
    let row = |out: &mut String, label: u8, sc: &str, f: &[f32]| {
        let _ = write!(out, "{label},{sc}");
        for v in f {
            let _ = write!(out, ",{v}");
        }
        out.push('\n');
    };
    for e in &evs {
        match &e.kind {
            EventKind::Txn(t) => row(&mut txn, e.label, &e.scenario, &shield.featurize_txn(t)),
            EventKind::Provision(p) => row(
                &mut idv,
                e.label,
                &e.scenario,
                &shield.assess_provision(p).features,
            ),
        }
    }
    std::fs::write(format!("{out_dir}/features_txn.csv"), txn).map_err(|e| e.to_string())?;
    std::fs::write(format!("{out_dir}/features_idv.csv"), idv).map_err(|e| e.to_string())?;
    println!(
        "{} hodisa → {out_dir}/features_txn.csv, features_idv.csv",
        evs.len()
    );
    Ok(())
}

#[derive(Default)]
struct Counts {
    n: u64,
    review_plus: u64,
    decline: u64,
}

fn evaluate(events: &str, report: &str, args: &[String]) -> Result<(), String> {
    let rules = RuleSet::default_rules()?;
    let evs = load_events(events, &rules)?;
    let shield = Shield::new(rules, model_from_args(args)?);
    let mut txn: BTreeMap<String, Counts> = BTreeMap::new();
    let mut idv: BTreeMap<String, Counts> = BTreeMap::new();
    let mut rule_hits: BTreeMap<String, u64> = BTreeMap::new();
    for e in &evs {
        match &e.kind {
            EventKind::Txn(t) => {
                let a = shield.assess_txn(t);
                let c = txn.entry(e.scenario.clone()).or_default();
                c.n += 1;
                c.review_plus += u64::from(a.decision != RiskDecision::Approve);
                c.decline += u64::from(a.decision == RiskDecision::Decline);
                for r in a.reasons {
                    *rule_hits.entry(format!("{}:{r}", e.scenario)).or_default() += 1;
                }
            }
            EventKind::Provision(p) => {
                let d = shield.assess_provision(p).assessment;
                let c = idv.entry(e.scenario.clone()).or_default();
                c.n += 1;
                c.review_plus += u64::from(d.decision != IdvDecision::Green);
                c.decline += u64::from(d.decision == IdvDecision::Red);
            }
        }
    }
    let to_json = |m: &BTreeMap<String, Counts>| {
        m.iter()
            .map(|(k, c)| {
                (
                    k.clone(),
                    json!({
                        "n": c.n,
                        "flagged": c.review_plus,
                        "declined": c.decline,
                        "flagged_rate": c.review_plus as f64 / c.n.max(1) as f64,
                        "declined_rate": c.decline as f64 / c.n.max(1) as f64,
                    }),
                )
            })
            .collect::<serde_json::Map<_, _>>()
    };
    let out = json!({
        "events": evs.len(),
        "model": shield_model_name(&shield),
        "txn": to_json(&txn),
        "idv": to_json(&idv),
        "rule_hits": rule_hits,
    });
    std::fs::write(
        report,
        serde_json::to_string_pretty(&out).map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    println!(
        "{:<18} {:>8} {:>10} {:>10}",
        "TXN stsenariy", "n", "REVIEW+", "DECLINE"
    );
    for (k, c) in &txn {
        println!(
            "{k:<18} {:>8} {:>9.1}% {:>9.1}%",
            c.n,
            100.0 * c.review_plus as f64 / c.n.max(1) as f64,
            100.0 * c.decline as f64 / c.n.max(1) as f64
        );
    }
    println!(
        "{:<18} {:>8} {:>10} {:>10}",
        "ID&V stsenariy", "n", "YELLOW+", "RED"
    );
    for (k, c) in &idv {
        println!(
            "{k:<18} {:>8} {:>9.1}% {:>9.1}%",
            c.n,
            100.0 * c.review_plus as f64 / c.n.max(1) as f64,
            100.0 * c.decline as f64 / c.n.max(1) as f64
        );
    }
    Ok(())
}

fn shield_model_name(s: &Shield) -> String {
    format!("{s:?}")
}

fn percentile(sorted: &[f64], p: f64) -> f64 {
    let i = ((sorted.len() as f64 - 1.0) * p).round() as usize;
    sorted[i.min(sorted.len() - 1)]
}

fn bench(warmup: &str, events: &str, args: &[String]) -> Result<(), String> {
    let rules = RuleSet::default_rules()?;
    let warm = load_events(warmup, &rules)?;
    let evs = load_events(events, &rules)?;
    let shield = Shield::new(rules, model_from_args(args)?);
    for e in &warm {
        match &e.kind {
            EventKind::Txn(t) => {
                shield.featurize_txn(t);
            }
            EventKind::Provision(p) => {
                shield.assess_provision(p);
            }
        }
    }
    let mut lat = Vec::with_capacity(evs.len());
    for e in &evs {
        if let EventKind::Txn(t) = &e.kind {
            let t0 = Instant::now();
            let a = shield.assess_txn(t);
            lat.push(t0.elapsed().as_secs_f64() * 1000.0);
            std::hint::black_box(a);
        }
    }
    lat.sort_by(|a, b| a.total_cmp(b));
    let (p50, p95, p99, max) = (
        percentile(&lat, 0.5),
        percentile(&lat, 0.95),
        percentile(&lat, 0.99),
        lat[lat.len() - 1],
    );
    println!(
        "Shield skorlash (belgilar + qoidalar + ONNX), {} tranzaksiya, {} hodisa qizdirish:\n  p50 {p50:.3} ms  p95 {p95:.3} ms  p99 {p99:.3} ms  max {max:.3} ms",
        lat.len(),
        warm.len()
    );
    if p99 >= 50.0 {
        return Err(format!("p99 {p99:.3} ms ≥ 50 ms"));
    }
    Ok(())
}

fn parity(path: &str, args: &[String]) -> Result<(), String> {
    let model = model_from_args(args)?.ok_or("model kerak")?;
    let text = read(path)?;
    let mut lines = text.lines();
    let header = lines.next().ok_or("bo'sh")?;
    let cols: Vec<&str> = header.split(',').collect();
    if cols.len() != TXN_FEATURES.len() + 1 || cols.last() != Some(&"prob") {
        return Err("parity sarlavhasi: belgilar + prob".into());
    }
    let (mut n, mut worst) = (0, 0.0f32);
    for l in lines.filter(|l| !l.is_empty()) {
        let v: Vec<f32> = l
            .split(',')
            .map(|x| x.parse().map_err(|_| format!("son: {x}")))
            .collect::<Result<_, _>>()?;
        let (f, want) = v.split_at(TXN_FEATURES.len());
        let got = model.predict(f)?;
        worst = worst.max((got - want[0]).abs());
        n += 1;
    }
    println!("parity: {n} qator, maksimal farq {worst:.2e}");
    if worst > 1e-4 {
        return Err("Rust (tract) va Python (onnxruntime) ehtimollari farq qiladi".into());
    }
    Ok(())
}

fn run(args: &[String]) -> Result<(), String> {
    match args.get(1).map(String::as_str) {
        Some("featurize") if args.len() >= 4 => featurize(&args[2], &args[3]),
        Some("evaluate") if args.len() >= 4 => evaluate(&args[2], &args[3], args),
        Some("bench") if args.len() >= 4 => bench(&args[2], &args[3], args),
        Some("parity") if args.len() >= 3 => parity(&args[2], args),
        _ => Err("foydalanish: shield-replay featurize|evaluate|bench|parity ...".into()),
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    match run(&args) {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("xato: {e}");
            ExitCode::FAILURE
        }
    }
}
