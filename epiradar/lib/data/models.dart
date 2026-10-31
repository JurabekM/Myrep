// Kotlin yadrodan (engine/json/Codec.kt) keladigan JSON modellari.
// UI pul/xavf hisoblamaydi: barcha ball va darajalar yadroda hisoblanadi.

List<T> _list<T>(Object? raw, T Function(Map<String, dynamic>) f) =>
    (raw as List<dynamic>? ?? const []).map((e) => f(e as Map<String, dynamic>)).toList();

List<String> _strings(Object? raw) => (raw as List<dynamic>? ?? const []).map((e) => e.toString()).toList();

DateTime? _date(Object? raw) => raw == null ? null : DateTime.tryParse(raw.toString());

class Level {
  const Level({required this.score, required this.level, required this.name, required this.advice});

  factory Level.fromJson(Map<String, dynamic> j) => Level(
        score: (j['score'] as num?)?.toInt() ?? 0,
        level: j['level'] as String? ?? 'CALM',
        name: j['name'] as String? ?? '',
        advice: j['advice'] as String? ?? '',
      );

  static const empty = Level(score: 0, level: 'CALM', name: 'Tinch', advice: '');

  final int score;

  /// CALM | WATCH | ADVISORY | WARNING | EMERGENCY
  final String level;
  final String name;
  final String advice;

  static const order = ['CALM', 'WATCH', 'ADVISORY', 'WARNING', 'EMERGENCY'];
  int get rank => order.indexOf(level);
}

class CountryRef {
  const CountryRef({required this.iso3, required this.name, this.nameEn = ''});

  factory CountryRef.fromJson(Map<String, dynamic> j) =>
      CountryRef(iso3: j['iso3'] as String, name: j['name'] as String? ?? j['iso3'] as String, nameEn: j['nameEn'] as String? ?? '');

  final String iso3;
  final String name;
  final String nameEn;
}

class SignalItem {
  const SignalItem({
    required this.id,
    required this.source,
    required this.sourceTitle,
    required this.title,
    required this.summary,
    required this.url,
    required this.publishedAt,
    required this.countries,
    required this.diseaseId,
    this.travelLevel,
  });

  factory SignalItem.fromJson(Map<String, dynamic> j) => SignalItem(
        id: j['id'] as String,
        source: j['source'] as String? ?? '',
        sourceTitle: j['sourceTitle'] as String? ?? '',
        title: j['title'] as String? ?? '',
        summary: j['summary'] as String? ?? '',
        url: j['url'] as String? ?? '',
        publishedAt: _date(j['publishedAt']) ?? DateTime.fromMillisecondsSinceEpoch(0),
        countries: _strings(j['countries']),
        diseaseId: j['diseaseId'] as String? ?? 'other',
        travelLevel: (j['travelLevel'] as num?)?.toInt(),
      );

  final String id;
  final String source;
  final String sourceTitle;
  final String title;
  final String summary;
  final String url;
  final DateTime publishedAt;
  final List<String> countries;
  final String diseaseId;
  final int? travelLevel;

  /// Yadro o'zbekcha yaratgan xabarlar (FluNet) — tarjima kerak emas.
  bool get isUzbek => source == 'WHO_FLUNET';
}

class OutbreakEvent {
  const OutbreakEvent({
    required this.id,
    required this.diseaseId,
    required this.diseaseName,
    required this.title,
    required this.countries,
    required this.firstSeen,
    required this.lastUpdated,
    required this.flags,
    required this.global,
    required this.personal,
    required this.reasons,
    required this.signals,
    this.travelLevel,
    this.distanceKm,
  });

  factory OutbreakEvent.fromJson(Map<String, dynamic> j) => OutbreakEvent(
        id: j['id'] as String,
        diseaseId: j['diseaseId'] as String? ?? 'other',
        diseaseName: j['diseaseName'] as String? ?? '',
        title: j['title'] as String? ?? '',
        countries: _list(j['countries'], CountryRef.fromJson),
        firstSeen: _date(j['firstSeen']) ?? DateTime.fromMillisecondsSinceEpoch(0),
        lastUpdated: _date(j['lastUpdated']) ?? DateTime.fromMillisecondsSinceEpoch(0),
        flags: _strings(j['flags']),
        travelLevel: (j['travelLevel'] as num?)?.toInt(),
        global: Level.fromJson(j['global'] as Map<String, dynamic>? ?? const {}),
        personal: Level.fromJson(j['personal'] as Map<String, dynamic>? ?? const {}),
        distanceKm: (j['distanceKm'] as num?)?.toInt(),
        reasons: _strings(j['reasons']),
        signals: _list(j['signals'], SignalItem.fromJson),
      );

  final String id;
  final String diseaseId;
  final String diseaseName;
  final String title;
  final List<CountryRef> countries;
  final DateTime firstSeen;
  final DateTime lastUpdated;
  final List<String> flags;
  final int? travelLevel;
  final Level global;
  final Level personal;
  final int? distanceKm;
  final List<String> reasons;
  final List<SignalItem> signals;

  Set<String> get sources => signals.map((s) => s.source).toSet();
}

class TrendPoint {
  const TrendPoint(this.week, this.value, this.tested);

  factory TrendPoint.fromJson(Map<String, dynamic> j) =>
      TrendPoint(DateTime.parse(j['week'] as String), (j['value'] as num).toDouble(), (j['tested'] as num?)?.toInt() ?? 0);

  final DateTime week;
  final double value;
  final int tested;
}

class Anomaly {
  const Anomaly({required this.week, required this.value, required this.expected, required this.threshold, required this.method});

  factory Anomaly.fromJson(Map<String, dynamic> j) => Anomaly(
        week: DateTime.parse(j['week'] as String),
        value: (j['value'] as num).toDouble(),
        expected: (j['expected'] as num).toDouble(),
        threshold: (j['threshold'] as num).toDouble(),
        method: j['method'] as String? ?? '',
      );

  final DateTime week;
  final double value;
  final double expected;
  final double threshold;
  final String method;
}

class Trend {
  const Trend({
    required this.id,
    required this.country,
    required this.countryName,
    required this.title,
    required this.unit,
    required this.status,
    required this.statusName,
    required this.note,
    required this.points,
    required this.anomalies,
    required this.novelFluWeeks,
  });

  factory Trend.fromJson(Map<String, dynamic> j) => Trend(
        id: j['id'] as String,
        country: j['country'] as String,
        countryName: j['countryName'] as String? ?? j['country'] as String,
        title: j['title'] as String? ?? '',
        unit: j['unit'] as String? ?? '',
        status: j['status'] as String? ?? 'NO_DATA',
        statusName: j['statusName'] as String? ?? '',
        note: j['note'] as String? ?? '',
        points: _list(j['points'], TrendPoint.fromJson),
        anomalies: _list(j['anomalies'], Anomaly.fromJson),
        novelFluWeeks: _strings(j['novelFluWeeks']),
      );

  final String id;
  final String country;
  final String countryName;
  final String title;
  final String unit;

  /// NORMAL | RISING | UNUSUAL | NO_DATA
  final String status;
  final String statusName;
  final String note;
  final List<TrendPoint> points;
  final List<Anomaly> anomalies;
  final List<String> novelFluWeeks;
}

class SourceStatus {
  const SourceStatus({
    required this.id,
    required this.title,
    required this.homepage,
    required this.ok,
    required this.itemCount,
    required this.fetchedAt,
    required this.stale,
    this.error,
  });

  factory SourceStatus.fromJson(Map<String, dynamic> j) => SourceStatus(
        id: j['id'] as String,
        title: j['title'] as String? ?? '',
        homepage: j['homepage'] as String? ?? '',
        ok: j['ok'] as bool? ?? false,
        itemCount: (j['itemCount'] as num?)?.toInt() ?? 0,
        fetchedAt: _date(j['fetchedAt']),
        error: j['error'] as String?,
        stale: j['stale'] as bool? ?? false,
      );

  final String id;
  final String title;
  final String homepage;
  final bool ok;
  final int itemCount;
  final DateTime? fetchedAt;
  final String? error;
  final bool stale;
}

class Snapshot {
  const Snapshot({
    required this.generatedAt,
    required this.country,
    required this.countryName,
    required this.global,
    required this.personal,
    required this.events,
    required this.trends,
    required this.sources,
  });

  factory Snapshot.fromJson(Map<String, dynamic> j) => Snapshot(
        generatedAt: _date(j['generatedAt']) ?? DateTime.fromMillisecondsSinceEpoch(0),
        country: j['country'] as String? ?? 'UZB',
        countryName: j['countryName'] as String? ?? '',
        global: Level.fromJson(j['global'] as Map<String, dynamic>? ?? const {}),
        personal: Level.fromJson(j['personal'] as Map<String, dynamic>? ?? const {}),
        events: _list(j['events'], OutbreakEvent.fromJson),
        trends: _list(j['trends'], Trend.fromJson),
        sources: _list(j['sources'], SourceStatus.fromJson),
      );

  final DateTime generatedAt;
  final String country;
  final String countryName;
  final Level global;
  final Level personal;
  final List<OutbreakEvent> events;
  final List<Trend> trends;
  final List<SourceStatus> sources;

  OutbreakEvent? eventById(String id) {
    for (final e in events) {
      if (e.id == id) return e;
    }
    return null;
  }
}

class Settings {
  const Settings({
    this.country = 'UZB',
    this.notificationsEnabled = true,
    this.alertThreshold = 'ADVISORY',
    this.syncHours = 3,
    this.watchCountries = const [],
    this.checklistDone = const [],
    this.onboardingDone = false,
    this.lightTheme = false,
  });

  factory Settings.fromJson(Map<String, dynamic> j) => Settings(
        country: j['country'] as String? ?? 'UZB',
        notificationsEnabled: j['notificationsEnabled'] as bool? ?? true,
        alertThreshold: j['alertThreshold'] as String? ?? 'ADVISORY',
        syncHours: (j['syncHours'] as num?)?.toInt() ?? 3,
        watchCountries: _strings(j['watchCountries']),
        checklistDone: _strings(j['checklistDone']),
        onboardingDone: j['onboardingDone'] as bool? ?? false,
        lightTheme: j['lightTheme'] as bool? ?? false,
      );

  final String country;
  final bool notificationsEnabled;
  final String alertThreshold;
  final int syncHours;
  final List<String> watchCountries;
  final List<String> checklistDone;
  final bool onboardingDone;
  final bool lightTheme;

  static const syncChoices = [1, 3, 6, 12, 24];

  Map<String, dynamic> toJson() => {
        'country': country,
        'notificationsEnabled': notificationsEnabled,
        'alertThreshold': alertThreshold,
        'syncHours': syncHours,
        'watchCountries': watchCountries,
        'checklistDone': checklistDone,
        'onboardingDone': onboardingDone,
        'lightTheme': lightTheme,
      };

  Settings copyWith({
    String? country,
    bool? notificationsEnabled,
    String? alertThreshold,
    int? syncHours,
    List<String>? watchCountries,
    List<String>? checklistDone,
    bool? onboardingDone,
    bool? lightTheme,
  }) =>
      Settings(
        country: country ?? this.country,
        notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
        alertThreshold: alertThreshold ?? this.alertThreshold,
        syncHours: syncHours ?? this.syncHours,
        watchCountries: watchCountries ?? this.watchCountries,
        checklistDone: checklistDone ?? this.checklistDone,
        onboardingDone: onboardingDone ?? this.onboardingDone,
        lightTheme: lightTheme ?? this.lightTheme,
      );
}

class Disease {
  const Disease({
    required this.id,
    required this.name,
    required this.group,
    required this.hazard,
    required this.pandemic,
    required this.transmission,
    required this.incubation,
    required this.fatality,
    required this.symptoms,
    required this.prevention,
    required this.redFlags,
    required this.vaccine,
    required this.treatment,
    required this.localNote,
  });

  factory Disease.fromJson(Map<String, dynamic> j) => Disease(
        id: j['id'] as String,
        name: j['name'] as String? ?? '',
        group: j['group'] as String? ?? '',
        hazard: (j['hazard'] as num?)?.toDouble() ?? 0,
        pandemic: j['pandemic'] as String? ?? 'low',
        transmission: j['transmission'] as String? ?? '',
        incubation: j['incubation'] as String? ?? '',
        fatality: j['fatality'] as String? ?? '',
        symptoms: _strings(j['symptoms']),
        prevention: _strings(j['prevention']),
        redFlags: _strings(j['redFlags']),
        vaccine: j['vaccine'] as String? ?? '',
        treatment: j['treatment'] as String? ?? '',
        localNote: j['localNote'] as String? ?? '',
      );

  final String id;
  final String name;
  final String group;
  final double hazard;
  final String pandemic;
  final String transmission;
  final String incubation;
  final String fatality;
  final List<String> symptoms;
  final List<String> prevention;
  final List<String> redFlags;
  final String vaccine;
  final String treatment;
  final String localNote;

  String get pandemicName => switch (pandemic) {
        'high' => 'Yuqori',
        'medium' => "O'rta",
        _ => 'Past',
      };
}

class LevelInfo {
  const LevelInfo({required this.level, required this.name, required this.minScore, required this.advice});

  factory LevelInfo.fromJson(Map<String, dynamic> j) => LevelInfo(
        level: j['level'] as String,
        name: j['name'] as String? ?? '',
        minScore: (j['minScore'] as num?)?.toInt() ?? 0,
        advice: j['advice'] as String? ?? '',
      );

  final String level;
  final String name;
  final int minScore;
  final String advice;
}

class Catalog {
  const Catalog({required this.diseases, required this.countries, required this.levels});

  factory Catalog.fromJson(Map<String, dynamic> j) => Catalog(
        diseases: _list(j['diseases'], Disease.fromJson),
        countries: _list(j['countries'], CountryRef.fromJson),
        levels: _list(j['levels'], LevelInfo.fromJson),
      );

  static const empty = Catalog(diseases: [], countries: [], levels: []);

  final List<Disease> diseases;
  final List<CountryRef> countries;
  final List<LevelInfo> levels;

  Disease? disease(String id) {
    for (final d in diseases) {
      if (d.id == id) return d;
    }
    return null;
  }

  String countryName(String iso3) {
    for (final c in countries) {
      if (c.iso3 == iso3) return c.name;
    }
    return iso3;
  }

  LevelInfo? level(String level) {
    for (final l in levels) {
      if (l.level == level) return l;
    }
    return null;
  }
}
