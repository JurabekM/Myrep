import 'enums.dart';

/// Obyekt. Maydonlar ixtiyoriy: kiritilmagan qiymat baholashda NEEDS_REVIEW ga olib keladi.
class Site {
  const Site({required this.id, required this.name, this.earthingSystem, this.u0Volts});

  final String id;
  final String name;
  final EarthingSystem? earthingSystem;
  final double? u0Volts;
}
