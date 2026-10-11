fn main() {
    // Windows'da Tauri'ga bog'langan test binary'lari Common Controls v6 manifestisiz
    // `STATUS_ENTRYPOINT_NOT_FOUND` (0xc0000139) bilan yiqiladi; manifest faqat testlarga qo'shiladi.
    if std::env::var("CARGO_CFG_TARGET_OS").is_ok_and(|os| os == "windows")
        && std::env::var("CARGO_CFG_TARGET_ENV").is_ok_and(|e| e == "msvc")
    {
        let manifest =
            std::path::Path::new(&std::env::var("CARGO_MANIFEST_DIR").unwrap_or_default())
                .join("test-manifest.xml");
        println!("cargo:rerun-if-changed=test-manifest.xml");
        println!("cargo:rustc-link-arg-tests=/MANIFEST:EMBED");
        println!(
            "cargo:rustc-link-arg-tests=/MANIFESTINPUT:{}",
            manifest.display()
        );
    }
    tauri_build::build();
}
