export 'package:zanjir_protocol/zanjir_protocol.dart' show summarizeValues;

/// QR kod mazmuni: `zanjir://app/n/<tugun id>` (Android deep link).
String nodeQrData(String nodeId) => 'zanjir://app/n/$nodeId';
