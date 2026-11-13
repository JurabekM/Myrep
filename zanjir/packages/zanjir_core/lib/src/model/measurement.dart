import 'enums.dart';
import 'frozen.dart';

/// O'lchov (append-only). Xato o'lchov o'chirilmaydi — `supersedesId` bilan yangisi qo'shiladi.
class Measurement {
  Measurement({
    required this.id,
    required this.sessionId,
    required this.nodeId,
    required this.type,
    required this.instrumentId,
    required Map<String, Object?> values,
    required this.enteredVia,
    this.supersedesId,
  }) : values = freezeMap(values);

  final String id;
  final String sessionId;
  final String nodeId;
  final MeasurementType type;
  final String instrumentId;

  /// `docs/PROMPT.md` 4-bo'lim, `measurement.values` tuzilishi.
  final Map<String, Object?> values;
  final EnteredVia enteredVia;
  final String? supersedesId;
}
