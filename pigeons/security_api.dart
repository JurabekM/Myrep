// Pigeon kontrakti: Flutter ↔ Kotlin xavfsizlik qatlami.
//
// Generatsiya: `dart run pigeon --input pigeons/security_api.dart`
// Qo'lda yozilgan MethodChannel taqiqlangan (SPEC 4.1).
// Kontrakt o'zgarsa Kotlin'dagi `SecurityApiImpl.API_VERSION` oshiriladi.
import 'package:pigeon/pigeon.dart';

@ConfigurePigeon(
  PigeonOptions(
    dartOut: 'lib/core/security/security_api.pigeon.dart',
    dartOptions: DartOptions(),
    kotlinOut:
        'android/app/src/main/kotlin/uz/barakadaftari/app/native/SecurityApi.g.kt',
    kotlinOptions: KotlinOptions(package: 'uz.barakadaftari.app.native'),
    dartPackageName: 'baraka_daftari',
  ),
)
/// Native qatlam haqida qisqa ma'lumot — ko'prik ishlayotganini tekshirish
/// uchun.
class NativeInfo {
  NativeInfo({required this.apiVersion, required this.androidSdkInt});

  /// Kontrakt versiyasi. Kontrakt o'zgarsa oshiriladi.
  final int apiVersion;
  final int androidSdkInt;
}

/// Qurilma yaxlitligi belgilari. MVP'da ilova bloklanmaydi, faqat
/// ogohlantiriladi.
class IntegritySignals {
  IntegritySignals({
    required this.isRooted,
    required this.isEmulator,
    required this.isDebuggerAttached,
    required this.isDebuggableBuild,
    required this.signatureSha256,
    required this.isSignatureValid,
  });

  final bool isRooted;
  final bool isEmulator;
  final bool isDebuggerAttached;

  /// `android:debuggable` bayrog'i (debug build'da doim true).
  final bool isDebuggableBuild;

  /// Imzo sertifikatining SHA-256 xeshi (hex, katta harf).
  final String signatureSha256;

  /// Kutilgan xesh bilan mosligi. `null` — kutilgan xesh sozlanmagan.
  final bool? isSignatureValid;
}

enum BiometricOutcome { success, failed, cancelled, lockedOut, unavailable }

enum BiometricAvailability { available, noneEnrolled, noHardware, unavailable }

@HostApi()
abstract class SecurityApi {
  /// Ko'prik tekshiruvi.
  NativeInfo ping();

  /// 256-bit tasodifiy DB kaliti. Birinchi chaqiruvda yaratiladi, Keystore'dagi
  /// AES-GCM kalit bilan wrap qilinib private storage'ga yoziladi; keyingi
  /// chaqiruvlarda unwrap qilib qaytariladi.
  @async
  Uint8List getOrCreateDatabaseKey();

  /// PIN hosilasi: PBKDF2-HMAC-SHA256 (fon oqimida). `iterations` ≥ 310 000.
  @async
  Uint8List derivePinKey(String pin, Uint8List salt, int iterations);

  /// Keystore kaliti bilan shifrlangan kichik blob'ni o'qiydi; yo'q bo'lsa
  /// `null`. Nom: `[a-z0-9_]{1,40}`.
  /// Zaxira nusxani shifrlash (Vazifa 15): PBKDF2-HMAC-SHA256 (parol, tasodifiy
  /// tuz) → AES-256-GCM. Natija: sarlavha (sehr, versiya, iteratsiya, tuz, IV)
  /// + shifrmatn. Fon oqimida.
  @async
  Uint8List encryptBackup(String password, Uint8List plain);

  /// Zaxira nusxani ochish. Parol noto'g'ri yoki fayl buzilgan —
  /// `BACKUP_BAD_PASSWORD` / `BACKUP_FORMAT` xatosi.
  @async
  Uint8List decryptBackup(String password, Uint8List data);

  /// Zaxira faylini tanlash (ACTION_OPEN_DOCUMENT, plaginsiz). `null` —
  /// foydalanuvchi bekor qildi. Fayl 64 MB dan katta bo'lsa `PICK_TOO_LARGE`.
  @async
  Uint8List? pickBackupFile();

  Uint8List? readSecureBlob(String name);

  void writeSecureBlob(String name, Uint8List data);

  void deleteSecureBlob(String name);

  BiometricAvailability getBiometricAvailability();

  /// BiometricPrompt (BIOMETRIC_STRONG yoki qurilma krediensiali).
  /// `cancelLabel` faqat krediensial qo'llanmaydigan (API < 30) qurilmada
  /// ko'rinadi.
  @async
  BiometricOutcome authenticate(
    String title,
    String subtitle,
    String cancelLabel,
  );

  /// FLAG_SECURE ni yoqish/o'chirish (skrinshot va ekran yozuvini taqiqlash).
  void setSecureFlag({required bool enabled});

  /// Root, emulyator, debugger va imzo belgilari.
  IntegritySignals getIntegritySignals();
}
