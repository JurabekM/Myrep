//! `cargo test -p baraka-vectors` — barcha oltin vektorlar yadro bilan mosligi.

#[test]
fn all_golden_vectors_pass() {
    match baraka_vectors::run_dir(&baraka_vectors::default_dir()) {
        Ok(count) => assert!(count >= 80, "kutilganidan kam case: {count}"),
        Err(failures) => {
            for f in &failures {
                eprintln!(
                    "FAIL {}/{}\n  expected: {}\n  actual:   {}",
                    f.suite, f.id, f.expected, f.actual
                );
            }
            panic!("{} ta vektor muvaffaqiyatsiz", failures.len());
        }
    }
}
