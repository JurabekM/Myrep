import 'enums.dart';

class MeasurementSession {
  const MeasurementSession({
    required this.id,
    required this.siteId,
    required this.kind,
    required this.engineerId,
    this.ambientTempC,
    this.humidityPct,
  });

  final String id;
  final String siteId;
  final SessionKind kind;
  final String engineerId;
  final double? ambientTempC;
  final double? humidityPct;
}
