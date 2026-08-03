# Release artifacts

`releases/` contains three build outputs, produced from `android/` at version `1.0.0`
(`versionCode 1`):

| File | Task | Purpose |
|---|---|---|
| `DehqonKomakchi-debug-v1.0.0.apk` | `assembleDebug` | Installable debug build; verbose logging, `.debug` application-id suffix so it can coexist on a device alongside the release build. |
| `DehqonKomakchi-release-v1.0.0.apk` | `assembleRelease` | Installable release-config build for side-loading/manual QA. |
| `DehqonKomakchi-release-v1.0.0.aab` | `bundleRelease` | Android App Bundle -- the format Play Store ingestion requires. |

## Important: this is a review build, not a Play Store-ready build

The release build type is configured with `isMinifyEnabled = false` (no R8 shrinking/
obfuscation) and, critically, **signed with the debug keystore** (`app/build.gradle.kts`,
`buildTypes.release.signingConfig = signingConfigs.getByName("debug")`), because no production
upload keystore exists in this environment. This was a deliberate choice so the deliverable
APK/AAB installs directly for review without requiring a keystore to be generated and
distributed alongside it -- but it means these specific files:

- **cannot be uploaded to Play Console** (Play requires a non-debug upload key), and
- should not be treated as a security-hardened production binary (no code shrinking/
  obfuscation, debug-key trust chain).

## Rebuilding

```bash
cd android
./gradlew assembleDebug assembleRelease bundleRelease
```

Outputs land in `app/build/outputs/apk/{debug,release}/` and `app/build/outputs/bundle/release/`.

## Producing a real Play Store-signed build

1. Generate an upload keystore (keep it out of version control):
   ```bash
   keytool -genkeypair -v -keystore upload-keystore.jks -alias dehqon-upload \
     -keyalg RSA -keysize 2048 -validity 10000
   ```
2. In `android/app/build.gradle.kts`, add a `signingConfigs { create("release") { ... } }`
   block reading the keystore path/passwords from environment variables or a local
   (gitignored) `keystore.properties`, and point `buildTypes.release.signingConfig` at it
   instead of `signingConfigs.getByName("debug")`.
3. Turn on shrinking for a real release: `isMinifyEnabled = true`, and verify the app still
   works against `proguard-rules.pro` (test all screens, especially anything using
   reflection/serialization -- Hilt- and kotlinx.serialization-generated code needs explicit
   keep rules if R8 removes something it shouldn't).
4. Re-run `./gradlew bundleRelease` and upload the resulting `.aab` to Play Console.
5. Set `API_BASE_URL` (`app/build.gradle.kts` `buildConfigField`) to the real production
   backend URL once the network layer described in `docs/PRODUCTION_READINESS.md` is wired
   up -- it currently points at a placeholder (`https://api.dehqonkomakchi.uz/`) that nothing
   in the app calls yet.

See `docs/PRODUCTION_READINESS.md` for the full pre-launch checklist beyond signing.
