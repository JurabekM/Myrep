import 'norm.dart';
import 'norm_loader.dart';

/// Elektromagnit ajratgich zonasi: Ia = k · In (ADR-0002, S2).
class TripMultipliers {
  const TripMultipliers({required this.byCurve, required this.source, required this.status});
  final Map<String, double> byCurve;
  final NormSource source;
  final NormStatus status;

  double? forCurve(String curve) => byCurve[curve];
}

/// Normalar to'plami (`norms/*.yaml`).
class NormSet {
  const NormSet({
    required this.schemaVersion,
    required this.version,
    required this.reviewedBy,
    required this.reviewedAt,
    required this.marginPct,
    required this.tripMultipliers,
    required this.norms,
  });

  /// YAML'ni qat'iy tekshirib yuklaydi; xato bo'lsa [NormFormatException].
  factory NormSet.fromYaml(String yaml) => parseNormSet(yaml);

  final int schemaVersion;
  final String version;
  final String reviewedBy;
  final String reviewedAt;
  final double marginPct;
  final TripMultipliers tripMultipliers;
  final List<Norm> norms;

  /// Litsenziyali muhandis imzolaganmi (release darvozasi, ADR-0004).
  bool get isReviewed => reviewedBy.trim().isNotEmpty && reviewedAt.trim().isNotEmpty;
}
