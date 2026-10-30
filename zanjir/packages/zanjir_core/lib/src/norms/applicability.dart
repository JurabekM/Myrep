import '../model/node.dart';
import '../model/site.dart';
import 'norm.dart';

enum Applicability { match, noMatch, unknown }

class ApplicabilityResult {
  const ApplicabilityResult(this.status, [this.missing = const []]);
  final Applicability status;

  /// `unknown` bo'lsa — yetishmayotgan ma'lumot kalitlari (`site.u0_volts`, `node.attrs.role`, …).
  final List<String> missing;
}

/// Norma tugun, obyekt va o'lchov qiymatlariga qo'llanadimi.
/// Aniq mos kelmaslik (`noMatch`) ma'lumot yetishmasligidan (`unknown`) ustun.
ApplicabilityResult checkApplicability(Norm norm, Node node, Site site, Map<String, Object?> values) {
  final a = norm.appliesTo;
  if (!a.nodeKinds.contains(node.kind)) return const ApplicabilityResult(Applicability.noMatch);
  final missing = <String>[];
  var noMatch = false;

  final systems = a.earthingSystems;
  if (systems != null) {
    final es = site.earthingSystem;
    if (es == null) {
      missing.add('site.earthing_system');
    } else if (!systems.contains(es)) {
      noMatch = true;
    }
  }
  final u0Min = a.u0Min;
  final u0Max = a.u0Max;
  if (u0Min != null && u0Max != null) {
    final u0 = site.u0Volts;
    if (u0 == null) {
      missing.add('site.u0_volts');
    } else if (u0 < u0Min || u0 > u0Max) {
      noMatch = true;
    }
  }
  for (final e in a.attrs.entries) {
    final v = node.attrs[e.key];
    if (v == null) {
      missing.add('node.attrs.${e.key}');
    } else if (!e.value.contains(v)) {
      noMatch = true;
    }
  }
  for (final e in a.values.entries) {
    final v = values[e.key];
    if (v == null) {
      missing.add('values.${e.key}');
    } else if (!e.value.contains(v)) {
      noMatch = true;
    }
  }
  if (noMatch) return const ApplicabilityResult(Applicability.noMatch);
  if (missing.isNotEmpty) return ApplicabilityResult(Applicability.unknown, List.unmodifiable(missing));
  return const ApplicabilityResult(Applicability.match);
}
