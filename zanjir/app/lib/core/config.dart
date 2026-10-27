import 'package:zanjir_data/zanjir_data.dart';

/// QR tekshiruv havolasining asosi. Server domeni 2-darvozada belgilanadi:
/// `flutter build ... --dart-define=ZANJIR_VERIFY_BASE_URL=https://<domen>/v/`.
/// Berilmasa — ilova ichidagi havola `zanjir://app/v/<qr_token>` (faqat ZANJIR o'rnatilgan telefonda ochiladi).
const String verifyBaseUrl = String.fromEnvironment(
  'ZANJIR_VERIFY_BASE_URL',
  defaultValue: ProtocolRepository.defaultVerifyBaseUrl,
);

/// Server manzili: `--dart-define=ZANJIR_SERVER_URL=https://<domen>/` (2-darvoza). Bo'sh — ilova faqat oflayn.
const String serverUrl = String.fromEnvironment('ZANJIR_SERVER_URL');
