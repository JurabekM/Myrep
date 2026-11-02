/// Imzolangan offlayn baza modeli. Imzo Kotlin tomonida tekshirilgandan keyingina
/// Dart'ga payload sifatida beriladi (DbBundle.kt).
library;

import 'dart:convert';

import 'phone.dart';

class OrgPackage {
  OrgPackage(this.id, this.certSha256);
  final String id;
  final List<String> certSha256;
}

class Organization {
  Organization({
    required this.id,
    required this.name,
    required this.kind,
    required this.brandKeywords,
    required this.domains,
    required this.packages,
    required this.phones,
  });

  final String id;
  final String name;
  final String kind;
  final List<String> brandKeywords;
  final List<String> domains;
  final List<OrgPackage> packages;
  final List<String> phones;

  factory Organization.fromJson(Map<String, dynamic> j) => Organization(
        id: j['id'] as String,
        name: (j['name'] ?? j['org'] ?? j['id']) as String,
        kind: (j['kind'] ?? '') as String,
        brandKeywords: _strings(j['brand_keywords']).map((s) => s.toLowerCase()).toList(),
        domains: _strings(j['domains']).map((s) => s.toLowerCase()).toList(),
        packages: [
          for (final p in (j['packages'] as List? ?? const []))
            OrgPackage((p as Map)['id'] as String, _strings(p['cert_sha256']).map((s) => s.toLowerCase()).toList()),
        ],
        phones: [for (final p in (j['phones'] as List? ?? const [])) ((p as Map)['number'] as String)],
      );
}

List<String> _strings(Object? v) => [for (final x in (v as List? ?? const [])) x as String];

/// Rasmiy tashkilot nomini ishlatadigan, lekin rasmiy bo'lmagan Play ilovasi.
class Lookalike {
  Lookalike(this.id, this.claims, this.reason, this.infoOnly);
  final String id;
  final String claims;
  final String reason;
  final bool infoOnly;
}

class RostorDb {
  RostorDb({
    required this.version,
    required this.lookalikes,
    required this.organizations,
    required this.maliciousApk,
    required this.maliciousCerts,
    required this.maliciousDomains,
    required this.maliciousPhones,
    required this.shorteners,
    required this.riskyTlds,
    required this.trustedInstallers,
    required this.messengerInstallers,
  });

  final int version;
  final Map<String, Lookalike> lookalikes;
  final List<Organization> organizations;
  final Set<String> maliciousApk;
  final Set<String> maliciousCerts;
  final Set<String> maliciousDomains;
  final Set<String> maliciousPhones;
  final Set<String> shorteners;
  final Set<String> riskyTlds;
  final Map<String, String> trustedInstallers;
  final Map<String, String> messengerInstallers;

  factory RostorDb.fromPayload(String payload, int version) {
    final j = jsonDecode(payload) as Map<String, dynamic>;
    final mal = (j['malicious'] as Map?) ?? const {};
    Set<String> lower(Object? v) => _strings(v).map((s) => s.toLowerCase()).toSet();
    Map<String, String> smap(Object? v) => {for (final e in ((v as Map?) ?? const {}).entries) e.key as String: e.value as String};
    return RostorDb(
      version: version,
      lookalikes: {
        for (final l in (j['lookalike_packages'] as List? ?? const []))
          (l as Map)['id'] as String: Lookalike(
            l['id'] as String,
            (l['claims'] ?? '') as String,
            (l['reason'] ?? '') as String,
            l['severity'] == 'info',
          ),
      },
      organizations: [for (final o in (j['organizations'] as List? ?? const [])) Organization.fromJson(o as Map<String, dynamic>)],
      maliciousApk: lower(mal['apk_sha256']),
      maliciousCerts: lower(mal['cert_sha256']),
      maliciousDomains: lower(mal['domains']),
      maliciousPhones: {
        for (final p in (mal['phones'] as List? ?? const []))
          ?normalizePhone(p is Map ? p['number'] as String? : p as String),
      },
      shorteners: lower(j['url_shorteners']),
      riskyTlds: lower(j['risky_tlds']),
      trustedInstallers: smap(j['trusted_installers']),
      messengerInstallers: smap(j['messenger_installers']),
    );
  }

  /// Baza yuklanmagan holat uchun: qoidalar ishlaydi, faqat reestr tekshiruvlari bo'sh.
  factory RostorDb.empty() => RostorDb.fromPayload('{}', 0);

  Organization? orgByPackage(String pkg) {
    for (final o in organizations) {
      if (o.packages.any((p) => p.id == pkg)) return o;
    }
    return null;
  }

  OrgPackage? officialPackage(String pkg) {
    for (final o in organizations) {
      for (final p in o.packages) {
        if (p.id == pkg) return p;
      }
    }
    return null;
  }

  late final Map<String, List<Organization>> _byPhone = () {
    final m = <String, List<Organization>>{};
    for (final o in organizations) {
      for (final p in o.phones) {
        final n = normalizePhone(p);
        if (n != null) (m[n] ??= []).add(o);
      }
    }
    return m;
  }();

  /// Kanonik raqam (normalizePhone) qaysi tashkilotlarning rasmiy raqami.
  List<Organization> orgsByPhone(String normalized) => _byPhone[normalized] ?? const [];

  /// Domen rasmiy tashkilotga tegishlimi (aniq mos yoki uning subdomeni).
  Organization? orgByDomain(String host) {
    for (final o in organizations) {
      for (final d in o.domains) {
        if (host == d || host.endsWith('.$d')) return o;
      }
    }
    return null;
  }

  Iterable<String> get officialDomains sync* {
    for (final o in organizations) {
      yield* o.domains;
    }
  }
}
