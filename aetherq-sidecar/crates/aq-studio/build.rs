//! Windows exe ikonkasi va fayl ma'lumotlari.

fn main() {
    println!("cargo:rerun-if-changed=assets/icon.ico");
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        let mut res = winresource::WindowsResource::new();
        res.set_icon("assets/icon.ico")
            .set("ProductName", "AETHER-Q Sidecar Studio")
            .set("FileDescription", "AETHER-Q Sidecar Studio — post-kvant tunellarni boshqarish")
            .set("CompanyName", "AETHER-Q");
        if let Err(e) = res.compile() {
            // rc.exe topilmasa ham dastur yig'iladi — faqat ikonkasiz.
            println!("cargo:warning=ikonka qo'shilmadi: {e}");
        }
    }
}
