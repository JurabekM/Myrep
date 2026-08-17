plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.google.dagger.hilt.android")
    id("com.google.devtools.ksp")
}

android {
    namespace = "com.smartmoliya.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.smartmoliya.app"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Room migratsiya sxemalarini versiya nazoratiga saqlash uchun
        ksp {
            arg("room.schemaLocation", "$projectDir/schemas")
        }

        // Google Sign-In: Google Cloud Console'dan olingan Web (server) client ID.
        // Bo'sh qoldirilsa ilovada Google tugmasi ko'rinmaydi.
        buildConfigField("String", "GOOGLE_SERVER_CLIENT_ID", "\"\"")

        // Backend manzili. Emulyator uchun 10.0.2.2 = host mashina.
        buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8000/\"")

        // Certificate pinning: production domen va sertifikat SPKI SHA-256 pin'i.
        // Bo'sh bo'lsa pinning o'chiq (dev). Pin olish: docs/11_DEPLOYMENT.md.
        buildConfigField("String", "CERT_PIN_HOST", "\"\"")
        buildConfigField("String", "CERT_PIN_SHA256", "\"\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            isMinifyEnabled = false
        }
    }

    // Ikki xil APK: "online" (backend bilan) va "offline" (to'liq avtonom, tarmoqsiz).
    // Ikkalasi bitta qurilmaga yonma-yon o'rnatiladi (alohida applicationId).
    flavorDimensions += "mode"
    productFlavors {
        create("online") {
            dimension = "mode"
            buildConfigField("Boolean", "OFFLINE_MODE", "false")
            resValue("string", "app_name", "Smart Moliya")
        }
        create("offline") {
            dimension = "mode"
            applicationIdSuffix = ".offline"
            versionNameSuffix = "-offline"
            buildConfigField("Boolean", "OFFLINE_MODE", "true")
            resValue("string", "app_name", "Smart Moliya Offline")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    // Core / Compose
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation(platform("androidx.compose:compose-bom:2024.10.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.navigation:navigation-compose:2.8.4")

    // Dependency Injection
    implementation("com.google.dagger:hilt-android:2.52")
    ksp("com.google.dagger:hilt-android-compiler:2.52")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")

    // Offline database - Room + SQLCipher (baza fayli AES-256 bilan shifrlanadi)
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
    implementation("net.zetetic:sqlcipher-android:4.6.1")
    implementation("androidx.sqlite:sqlite-ktx:2.4.0")

    // Network
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Background sync
    implementation("androidx.work:work-runtime-ktx:2.10.0")

    // Authentication - biometric va shifrlangan lokal saqlash
    implementation("androidx.biometric:biometric:1.1.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    implementation("androidx.fragment:fragment-ktx:1.8.5")

    // Google Sign-In (Credential Manager)
    implementation("androidx.credentials:credentials:1.3.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.3.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.1.1")

    // Tests
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.10.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
