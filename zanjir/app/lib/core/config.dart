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

/// Server manzili ruxsat etilganmi: faqat `https`; `http` — faqat debug rejimida va faqat lokal manzillar
/// (emulyator `10.0.2.2`, `localhost`). Android'da cleartext ham tizim darajasida taqiqlangan (ADR-0014).
bool isAllowedServerUrl(String url, {required bool debug}) {
  final u = Uri.tryParse(url);
  if (u == null || u.host.isEmpty || u.userInfo.isNotEmpty) return false;
  if (u.scheme == 'https') return true;
  return debug && u.scheme == 'http' && const {'localhost', '127.0.0.1', '10.0.2.2'}.contains(u.host);
}
