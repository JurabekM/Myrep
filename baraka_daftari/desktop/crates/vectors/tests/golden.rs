#![allow(clippy::expect_used)]

use std::path::PathBuf;

#[test]
fn all_golden_vectors_pass() {
    let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../spec/test-vectors");
    let report = vectors::run_dir(&dir).expect("vektorlar yuklanishi kerak");
    assert!(report.passed > 0, "bironta ham vektor ishga tushmadi");
    assert!(
        report.is_green(),
        "yiqilgan vektorlar:\n{}",
        report.failures.join("\n")
    );
}
