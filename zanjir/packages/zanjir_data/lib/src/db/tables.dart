// Drift CHECK cheklovlari ustunning o'ziga murojaat qiladi (masalan, `role.isIn(...)`) — hujjatlashtirilgan uslub.
// ignore_for_file: recursive_getters

import 'package:drift/drift.dart';

import 'converters.dart';

// Ma'lumotlar modeli: docs/PROMPT.md 4-bo'lim, ADR-0008.
// Barcha jadvallarda: id (UUIDv7), org_id (organization dan tashqari), created_at, updated_at, rev,
// deleted (soft delete; append-only jadvallarda yo'q).

mixin _Base on Table {
  TextColumn get id => text()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  IntColumn get rev => integer().withDefault(const Constant(1))();

  @override
  Set<Column> get primaryKey => {id};
}

mixin _OrgScoped on Table {
  TextColumn get orgId => text().references(Organizations, #id)();
}

mixin _SoftDelete on Table {
  BoolColumn get deleted => boolean().withDefault(const Constant(false))();
}

@DataClassName('OrganizationRow')
class Organizations extends Table with _Base, _SoftDelete {
  @override
  String get tableName => 'organization';
  TextColumn get name => text()();
  TextColumn get licenseNo => text().nullable()();
  DateTimeColumn get licenseValidUntil => dateTime().nullable()();
}

/// Foydalanuvchi. `password_hash` qurilmada saqlanmaydi (faqat serverda, argon2id).
@DataClassName('AppUserRow')
class AppUsers extends Table with _Base, _OrgScoped, _SoftDelete {
  @override
  String get tableName => 'app_user';
  TextColumn get fullName => text()();
  TextColumn get phone => text()();
  TextColumn get role => text().check(role.isIn(const ['ADMIN', 'LEAD', 'ENGINEER', 'VIEWER']))();
  TextColumn get safetyGroup => text().nullable().check(safetyGroup.isIn(const ['I', 'II', 'III', 'IV', 'V']))();
}

@DataClassName('DeviceRow')
class Devices extends Table with _Base, _OrgScoped, _SoftDelete {
  @override
  String get tableName => 'device';
  TextColumn get userId => text().references(AppUsers, #id)();
  TextColumn get publicKeyEd25519 => text()();
  TextColumn get sigAlg => text()();
  DateTimeColumn get registeredAt => dateTime()();
  DateTimeColumn get revokedAt => dateTime().nullable()();
}

@DataClassName('InstrumentRow')
class Instruments extends Table with _Base, _OrgScoped, _SoftDelete {
  @override
  String get tableName => 'instrument';
  TextColumn get kind => text()();
  TextColumn get model => text()();
  TextColumn get serialNo => text()();
  TextColumn get verificationCertNo => text().nullable()();
  DateTimeColumn get verifiedUntil => dateTime().nullable()();
}

@DataClassName('SiteRow')
class Sites extends Table with _Base, _OrgScoped, _SoftDelete {
  @override
  String get tableName => 'site';
  TextColumn get name => text()();
  TextColumn get address => text().nullable()();
  TextColumn get customer => text().nullable()();
  TextColumn get earthingSystem => text().map(earthingConverter).nullable()();
  RealColumn get u0Volts => real().nullable()();
}

@DataClassName('NodeRow')
class Nodes extends Table with _Base, _OrgScoped, _SoftDelete {
  @override
  String get tableName => 'node';
  TextColumn get siteId => text().references(Sites, #id)();
  TextColumn get kind => text().map(nodeKindConverter)();
  TextColumn get label => text()();
  TextColumn get panelId => text().nullable().references(Nodes, #id)();

  /// Faqat kommutatsiya apparatlarida (CLOSED/OPEN).
  TextColumn get state => text().map(switchStateConverter).nullable()();
  TextColumn get attrs => text().map(const JsonMapConverter()).withDefault(const Constant('{}'))();
  BoolColumn get verified => boolean().withDefault(const Constant(false))();
  RealColumn get x => real().nullable()();
  RealColumn get y => real().nullable()();
}

@DataClassName('EdgeRow')
class Edges extends Table with _Base, _OrgScoped, _SoftDelete {
  @override
  String get tableName => 'edge';
  TextColumn get siteId => text().references(Sites, #id)();
  TextColumn get aNodeId => text().references(Nodes, #id)();
  TextColumn get bNodeId => text().references(Nodes, #id)();
  TextColumn get conductors => text()();
}

@DataClassName('MeasurementSessionRow')
class MeasurementSessions extends Table with _Base, _OrgScoped, _SoftDelete {
  @override
  String get tableName => 'measurement_session';
  TextColumn get siteId => text().references(Sites, #id)();
  TextColumn get kind => text().map(sessionKindConverter)();
  TextColumn get engineerId => text().references(AppUsers, #id)();
  RealColumn get ambientTempC => real().nullable()();
  RealColumn get humidityPct => real().nullable()();
  DateTimeColumn get startedAt => dateTime()();
  DateTimeColumn get closedAt => dateTime().nullable()();
}

/// Append-only (CLAUDE.md, 5-qoida): UPDATE/DELETE — trigger bilan taqiqlangan.
@DataClassName('MeasurementRow')
class Measurements extends Table with _Base, _OrgScoped {
  @override
  String get tableName => 'measurement';
  TextColumn get sessionId => text().references(MeasurementSessions, #id)();
  TextColumn get nodeId => text().references(Nodes, #id)();
  TextColumn get type => text().map(measurementTypeConverter)();
  TextColumn get instrumentId => text().references(Instruments, #id)();
  TextColumn get values => text().map(const JsonMapConverter())();
  TextColumn get enteredVia => text().map(enteredViaConverter)();
  TextColumn get verdict => text().map(verdictConverter)();
  TextColumn get normId => text().nullable()();
  TextColumn get normSetVersion => text()();
  TextColumn get evalDetail => text().map(const JsonMapConverter())();

  /// Xato o'lchov o'chirilmaydi — yangisi `supersedes_id` bilan qo'shiladi; har bir o'lchov ko'pi bilan bir marta almashtiriladi.
  TextColumn get supersedesId => text().nullable().unique().references(Measurements, #id)();
}

/// Append-only: holat (bekor qilish) faqat `PROTOCOL_REVOKED` audit hodisasi orqali.
@DataClassName('ProtocolRow')
class Protocols extends Table with _Base, _OrgScoped {
  @override
  String get tableName => 'protocol';
  TextColumn get sessionId => text().references(MeasurementSessions, #id)();
  TextColumn get number => text()();
  TextColumn get payloadSha256 => text()();
  TextColumn get pdfSha256 => text()();
  TextColumn get signedBy => text().references(AppUsers, #id)();
  TextColumn get deviceId => text().references(Devices, #id)();
  TextColumn get signature => text()();
  TextColumn get sigAlg => text()();
  TextColumn get qrToken => text().unique()();

  @override
  List<Set<Column>> get uniqueKeys => [
    {orgId, number},
  ];
}

/// Imzolangan protokolning payload'i (kanonik JSON) va PDF fayli — append-only (ADR-0010).
/// PDF qayta render qilinmaydi: shrift yoki kutubxona yangilansa ham imzolangan baytlar o'zgarmaydi.
@DataClassName('ProtocolDocumentRow')
class ProtocolDocuments extends Table with _Base, _OrgScoped {
  @override
  String get tableName => 'protocol_document';
  TextColumn get protocolId => text().unique().references(Protocols, #id)();
  TextColumn get payloadJson => text()();
  BlobColumn get pdf => blob()();
}

/// Append-only audit hash-zanjiri (ADR-0007). Qurilma bo'yicha `seq` yagona.
@DataClassName('AuditEventRow')
class AuditEvents extends Table with _Base, _OrgScoped {
  @override
  String get tableName => 'audit_event';
  TextColumn get deviceId => text().references(Devices, #id)();
  IntColumn get seq => integer()();
  TextColumn get prevHash => text()();
  TextColumn get eventHash => text().unique()();
  TextColumn get actorId => text().references(AppUsers, #id)();
  TextColumn get eventType => text()();
  TextColumn get entityId => text().nullable()();
  TextColumn get payloadHash => text()();
  TextColumn get deviceSig => text()();
  TextColumn get sigAlg => text()();

  /// Zanjirdagi kanonik vaqt (`2026-10-26T07:05:03.120Z`) — hash shu satrdan hisoblanadi.
  TextColumn get eventAt => text()();

  @override
  List<Set<Column>> get uniqueKeys => [
    {deviceId, seq},
  ];
}

@DataClassName('IsolationPlanRow')
class IsolationPlans extends Table with _Base, _OrgScoped, _SoftDelete {
  @override
  String get tableName => 'isolation_plan';
  TextColumn get siteId => text().references(Sites, #id)();
  TextColumn get targetNodeIds => text().map(const JsonListConverter())();
  TextColumn get solverVersion => text()();
  TextColumn get graphSnapshotHash => text()();
  TextColumn get steps => text().map(const JsonListConverter())();
  TextColumn get warnings => text().map(const JsonListConverter())();
  TextColumn get status => text().check(status.isIn(const ['DRAFT', 'APPROVED', 'EXECUTED', 'CANCELLED', 'STALE']))();
  TextColumn get approvedBy => text().nullable().references(AppUsers, #id)();
}

@DataClassName('NormSetRow')
class NormSets extends Table with _Base, _OrgScoped, _SoftDelete {
  @override
  String get tableName => 'norm_set';
  TextColumn get version => text()();
  TextColumn get sha256 => text()();
  TextColumn get yaml => text()();
  TextColumn get reviewedBy => text().nullable()();
  TextColumn get reviewedAt => text().nullable()();

  @override
  List<Set<Column>> get uniqueKeys => [
    {orgId, version},
  ];
}

/// Laboratoriya (tashkilot) sozlamalari — faqat LEAD/ADMIN o'zgartiradi, har bir o'zgarish auditga yoziladi (ADR-0009).
@DataClassName('OrgSettingRow')
class OrgSettings extends Table with _Base, _OrgScoped {
  @override
  String get tableName => 'org_setting';

  /// Sirtmoq koeffitsienti, (0; 1].
  RealColumn get kCorr =>
      real().withDefault(const Constant(1.0)).check(kCorr.isBiggerThanValue(0) & kCorr.isSmallerOrEqualValue(1))();

  /// Laboratoriya zaxirasi, % [0; 50]; effektiv = max(normalar to'plami, laboratoriya).
  RealColumn get marginPct => real().withDefault(const Constant(0.0)).check(marginPct.isBetweenValues(0, 50))();
  TextColumn get activeNormSetVersion => text().nullable()();

  @override
  List<Set<Column>> get uniqueKeys => [
    {orgId},
  ];
}

/// Faqat shu qurilmaga tegishli sozlamalar (profil, til, katta shrift) — sinxronlanmaydi.
@DataClassName('LocalPrefRow')
class LocalPrefs extends Table {
  @override
  String get tableName => 'local_pref';
  TextColumn get key => text()();
  TextColumn get value => text()();

  @override
  Set<Column> get primaryKey => {key};
}
