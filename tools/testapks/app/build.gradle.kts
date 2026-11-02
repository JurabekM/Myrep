plugins { id("com.android.application") }

android {
    namespace = "uz.rostor.testapk"
    compileSdk = 35
    defaultConfig { minSdk = 26; targetSdk = 35; versionCode = 1; versionName = "1.0" }
    flavorDimensions += "kind"
    productFlavors {
        // Soxta "Click": bank troyani manifest belgilari (SMS + Accessibility + overlay + dropper).
        create("fakeclick") { dimension = "kind"; applicationId = "uz.click.bonus"; resValue("string", "app_name", "Click") }
        // Oddiy ilova: hech qanday xavfli ruxsat yo'q.
        create("benign") { dimension = "kind"; applicationId = "uz.rostor.testbenign"; resValue("string", "app_name", "Kalkulyator") }
    }
    buildTypes { getByName("debug") { isMinifyEnabled = false } }
}
