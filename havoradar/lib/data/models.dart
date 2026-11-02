// Kotlin yadro JSON formati (engine/.../json/Codec.kt) bilan bir xil. Flutter hech narsa hisoblamaydi:
// darajalar, sabablar va tavsiyalar yadrodan o'zbekcha tayyor holda keladi.

List<String> _strings(Object? v) => (v as List<dynamic>? ?? const []).map((e) => e as String).toList();

List<Map<String, dynamic>> _objects(Object? v) => (v as List<dynamic>? ?? const []).cast<Map<String, dynamic>>();

double? _num(Object? v) => (v as num?)?.toDouble();

DateTime? _time(Object? v) => v == null ? null : DateTime.tryParse(v as String);

class Level {
  const Level({required this.score, required this.level, required this.name, required this.advice});

  factory Level.fromJson(Map<String, dynamic> j) => Level(
        score: j['score'] as int,
        level: j['level'] as String,
        name: j['name'] as String,
        advice: j['advice'] as String? ?? '',
      );

  final int score;

  /// CALM | WATCH | ADVISORY | WARNING | EMERGENCY
  final String level;
  final String name;
  final String advice;

  static const order = ['CALM', 'WATCH', 'ADVISORY', 'WARNING', 'EMERGENCY'];

  int get rank => order.indexOf(level);
}

class HazardRisk {
  const HazardRisk({
    required this.hazard,
    required this.name,
    required this.base,
    required this.personal,
    required this.reasons,
    required this.advice,
  });

  factory HazardRisk.fromJson(Map<String, dynamic> j) => HazardRisk(
        hazard: j['hazard'] as String,
        name: j['name'] as String,
        base: Level.fromJson(j['base'] as Map<String, dynamic>),
        personal: Level.fromJson(j['personal'] as Map<String, dynamic>),
        reasons: _strings(j['reasons']),
        advice: _strings(j['advice']),
      );

  /// HEAT | AIR
  final String hazard;
  final String name;

  /// Umumiy aholi uchun.
  final Level base;

  /// Profilingiz (sezgir guruhlar) bilan.
  final Level personal;
  final List<String> reasons;
  final List<String> advice;

  bool get isHeat => hazard == 'HEAT';
}

class AirDay {
  const AirDay({this.pm25, this.pm10, this.ozone8h, this.no2, this.no2Max, this.dustShare, this.worstHour});

  factory AirDay.fromJson(Map<String, dynamic> j) => AirDay(
        pm25: _num(j['pm25']),
        pm10: _num(j['pm10']),
        ozone8h: _num(j['ozone8h']),
        no2: _num(j['no2']),
        no2Max: _num(j['no2Max']),
        dustShare: _num(j['dustShare']),
        worstHour: j['worstHour'] as int?,
      );

  final double? pm25;
  final double? pm10;
  final double? ozone8h;
  final double? no2;
  final double? no2Max;
  final double? dustShare;
  final int? worstHour;
}

class UvInfo {
  const UvInfo({required this.category, required this.name, required this.advice});

  factory UvInfo.fromJson(Map<String, dynamic> j) =>
      UvInfo(category: j['category'] as String, name: j['name'] as String, advice: j['advice'] as String);

  final String category;
  final String name;
  final String advice;
}

class DayReport {
  const DayReport({
    required this.date,
    this.overall,
    this.tempMax,
    this.tempMin,
    this.feelsMax,
    this.feelsPeakHour,
    this.uvMax,
    this.uv,
    this.air,
    this.heatRisk,
    this.airRisk,
  });

  factory DayReport.fromJson(Map<String, dynamic> j) => DayReport(
        date: DateTime.parse(j['date'] as String),
        overall: j['overall'] == null ? null : Level.fromJson(j['overall'] as Map<String, dynamic>),
        tempMax: _num(j['tempMax']),
        tempMin: _num(j['tempMin']),
        feelsMax: _num(j['feelsMax']),
        feelsPeakHour: j['feelsPeakHour'] as int?,
        uvMax: _num(j['uvMax']),
        uv: j['uv'] == null ? null : UvInfo.fromJson(j['uv'] as Map<String, dynamic>),
        air: j['air'] == null ? null : AirDay.fromJson(j['air'] as Map<String, dynamic>),
        heatRisk: j['heatRisk'] == null ? null : HazardRisk.fromJson(j['heatRisk'] as Map<String, dynamic>),
        airRisk: j['airRisk'] == null ? null : HazardRisk.fromJson(j['airRisk'] as Map<String, dynamic>),
      );

  final DateTime date;

  /// Eng yomon xavf (profilingiz bilan); ma'lumot bo'lmasa null.
  final Level? overall;
  final double? tempMax;
  final double? tempMin;
  final double? feelsMax;
  final int? feelsPeakHour;
  final double? uvMax;
  final UvInfo? uv;
  final AirDay? air;
  final HazardRisk? heatRisk;
  final HazardRisk? airRisk;

  List<HazardRisk> get risks => [?heatRisk, ?airRisk];
}

class HourPoint {
  const HourPoint({required this.time, this.temp, this.feels, this.humidity, this.uv, this.pm25, this.pm10});

  factory HourPoint.fromJson(Map<String, dynamic> j) => HourPoint(
        time: DateTime.parse(j['time'] as String),
        temp: _num(j['temp']),
        feels: _num(j['feels']),
        humidity: _num(j['humidity']),
        uv: _num(j['uv']),
        pm25: _num(j['pm25']),
        pm10: _num(j['pm10']),
      );

  /// Joyning mahalliy vaqti (zonasiz).
  final DateTime time;
  final double? temp;
  final double? feels;
  final double? humidity;
  final double? uv;
  final double? pm25;
  final double? pm10;
}

class PlaceReport {
  const PlaceReport({
    required this.id,
    required this.name,
    required this.localNow,
    this.weatherFetchedAt,
    this.airFetchedAt,
    this.today,
    this.current,
    this.days = const [],
    this.hours = const [],
  });

  factory PlaceReport.fromJson(Map<String, dynamic> j) => PlaceReport(
        id: j['id'] as String,
        name: j['name'] as String,
        localNow: DateTime.parse(j['localNow'] as String),
        weatherFetchedAt: _time(j['weatherFetchedAt']),
        airFetchedAt: _time(j['airFetchedAt']),
        today: j['today'] == null ? null : Level.fromJson(j['today'] as Map<String, dynamic>),
        current: j['current'] == null ? null : HourPoint.fromJson(j['current'] as Map<String, dynamic>),
        days: _objects(j['days']).map(DayReport.fromJson).toList(),
        hours: _objects(j['hours']).map(HourPoint.fromJson).toList(),
      );

  final String id;
  final String name;

  /// Joyning hozirgi mahalliy vaqti.
  final DateTime localNow;
  final DateTime? weatherFetchedAt;
  final DateTime? airFetchedAt;
  final Level? today;
  final HourPoint? current;
  final List<DayReport> days;
  final List<HourPoint> hours;

  DayReport? get todayReport {
    for (final d in days) {
      if (d.date.year == localNow.year && d.date.month == localNow.month && d.date.day == localNow.day) return d;
    }
    return null;
  }

  List<HourPoint> hoursOn(DateTime date) =>
      hours.where((h) => h.time.year == date.year && h.time.month == date.month && h.time.day == date.day).toList();
}

class SourceStatus {
  const SourceStatus({
    required this.id,
    required this.title,
    required this.homepage,
    required this.ok,
    this.fetchedAt,
    this.error,
    this.stale = false,
  });

  factory SourceStatus.fromJson(Map<String, dynamic> j) => SourceStatus(
        id: j['id'] as String,
        title: j['title'] as String,
        homepage: j['homepage'] as String? ?? '',
        ok: j['ok'] as bool? ?? false,
        fetchedAt: _time(j['fetchedAt']),
        error: j['error'] as String?,
        stale: j['stale'] as bool? ?? false,
      );

  final String id;
  final String title;
  final String homepage;
  final bool ok;
  final DateTime? fetchedAt;
  final String? error;
  final bool stale;
}

class Snapshot {
  const Snapshot({required this.generatedAt, required this.profile, required this.places, required this.sources});

  factory Snapshot.fromJson(Map<String, dynamic> j) => Snapshot(
        generatedAt: DateTime.parse(j['generatedAt'] as String),
        profile: _strings(j['profile']),
        places: _objects(j['places']).map(PlaceReport.fromJson).toList(),
        sources: _objects(j['sources']).map(SourceStatus.fromJson).toList(),
      );

  final DateTime generatedAt;
  final List<String> profile;

  /// Birinchisi — asosiy joy.
  final List<PlaceReport> places;
  final List<SourceStatus> sources;

  PlaceReport? get main => places.isEmpty ? null : places.first;

  PlaceReport? place(String id) {
    for (final p in places) {
      if (p.id == id) return p;
    }
    return null;
  }
}

class Settings {
  const Settings({
    this.placeId = 'tashkent',
    this.extraPlaces = const [],
    this.profile = const [],
    this.notificationsEnabled = true,
    this.alertThreshold = 'WARNING',
    this.syncHours = 3,
    this.quietHours = true,
    this.onboardingDone = false,
    this.lightTheme = false,
  });

  factory Settings.fromJson(Map<String, dynamic> j) => Settings(
        placeId: j['placeId'] as String? ?? 'tashkent',
        extraPlaces: _strings(j['extraPlaces']),
        profile: _strings(j['profile']),
        notificationsEnabled: j['notificationsEnabled'] as bool? ?? true,
        alertThreshold: j['alertThreshold'] as String? ?? 'WARNING',
        syncHours: j['syncHours'] as int? ?? 3,
        quietHours: j['quietHours'] as bool? ?? true,
        onboardingDone: j['onboardingDone'] as bool? ?? false,
        lightTheme: j['lightTheme'] as bool? ?? false,
      );

  final String placeId;
  final List<String> extraPlaces;

  /// Sezgir guruhlar (Vulnerability nomlari).
  final List<String> profile;
  final bool notificationsEnabled;
  final String alertThreshold;
  final int syncHours;
  final bool quietHours;
  final bool onboardingDone;
  final bool lightTheme;

  static const syncChoices = [1, 3, 6, 12];
  static const maxExtraPlaces = 3;

  List<String> get allPlaces => [placeId, ...extraPlaces.where((p) => p != placeId)];

  Map<String, dynamic> toJson() => {
        'placeId': placeId,
        'extraPlaces': extraPlaces,
        'profile': profile,
        'notificationsEnabled': notificationsEnabled,
        'alertThreshold': alertThreshold,
        'syncHours': syncHours,
        'quietHours': quietHours,
        'onboardingDone': onboardingDone,
        'lightTheme': lightTheme,
      };

  Settings copyWith({
    String? placeId,
    List<String>? extraPlaces,
    List<String>? profile,
    bool? notificationsEnabled,
    String? alertThreshold,
    int? syncHours,
    bool? quietHours,
    bool? onboardingDone,
    bool? lightTheme,
  }) =>
      Settings(
        placeId: placeId ?? this.placeId,
        extraPlaces: extraPlaces ?? this.extraPlaces,
        profile: profile ?? this.profile,
        notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
        alertThreshold: alertThreshold ?? this.alertThreshold,
        syncHours: syncHours ?? this.syncHours,
        quietHours: quietHours ?? this.quietHours,
        onboardingDone: onboardingDone ?? this.onboardingDone,
        lightTheme: lightTheme ?? this.lightTheme,
      );
}

class PlaceInfo {
  const PlaceInfo({required this.id, required this.name, required this.abroad});

  factory PlaceInfo.fromJson(Map<String, dynamic> j) =>
      PlaceInfo(id: j['id'] as String, name: j['name'] as String, abroad: j['abroad'] as bool? ?? false);

  final String id;
  final String name;
  final bool abroad;
}

class LevelInfo {
  const LevelInfo({required this.level, required this.name, required this.minScore, required this.advice});

  factory LevelInfo.fromJson(Map<String, dynamic> j) => LevelInfo(
        level: j['level'] as String,
        name: j['name'] as String,
        minScore: j['minScore'] as int,
        advice: j['advice'] as String,
      );

  final String level;
  final String name;
  final int minScore;
  final String advice;
}

class VulnerabilityInfo {
  const VulnerabilityInfo({required this.id, required this.name, required this.heat, required this.air});

  factory VulnerabilityInfo.fromJson(Map<String, dynamic> j) => VulnerabilityInfo(
        id: j['id'] as String,
        name: j['name'] as String,
        heat: j['heat'] as bool? ?? false,
        air: j['air'] as bool? ?? false,
      );

  final String id;
  final String name;
  final bool heat;
  final bool air;
}

class GuideSection {
  const GuideSection({required this.title, required this.items});

  factory GuideSection.fromJson(Map<String, dynamic> j) => GuideSection(title: j['title'] as String, items: _strings(j['items']));

  final String title;
  final List<String> items;
}

class GuideSource {
  const GuideSource({required this.name, required this.url});

  factory GuideSource.fromJson(Map<String, dynamic> j) => GuideSource(name: j['name'] as String, url: j['url'] as String);

  final String name;
  final String url;
}

class GuideEntry {
  const GuideEntry({
    required this.id,
    required this.title,
    required this.icon,
    required this.urgent,
    required this.summary,
    required this.sections,
    required this.sources,
  });

  factory GuideEntry.fromJson(Map<String, dynamic> j) => GuideEntry(
        id: j['id'] as String,
        title: j['title'] as String,
        icon: j['icon'] as String,
        urgent: j['urgent'] as bool? ?? false,
        summary: j['summary'] as String,
        sections: _objects(j['sections']).map(GuideSection.fromJson).toList(),
        sources: _objects(j['sources']).map(GuideSource.fromJson).toList(),
      );

  final String id;
  final String title;
  final String icon;
  final bool urgent;
  final String summary;
  final List<GuideSection> sections;
  final List<GuideSource> sources;
}

class Catalog {
  const Catalog({required this.places, required this.levels, required this.vulnerabilities, required this.guide});

  factory Catalog.fromJson(Map<String, dynamic> j) => Catalog(
        places: _objects(j['places']).map(PlaceInfo.fromJson).toList(),
        levels: _objects(j['levels']).map(LevelInfo.fromJson).toList(),
        vulnerabilities: _objects(j['vulnerabilities']).map(VulnerabilityInfo.fromJson).toList(),
        guide: _objects(j['guide']).map(GuideEntry.fromJson).toList(),
      );

  static const empty = Catalog(places: [], levels: [], vulnerabilities: [], guide: []);

  final List<PlaceInfo> places;
  final List<LevelInfo> levels;
  final List<VulnerabilityInfo> vulnerabilities;
  final List<GuideEntry> guide;

  String placeName(String id) {
    for (final p in places) {
      if (p.id == id) return p.name;
    }
    return id;
  }

  String vulnerabilityName(String id) {
    for (final v in vulnerabilities) {
      if (v.id == id) return v.name;
    }
    return id;
  }
}
