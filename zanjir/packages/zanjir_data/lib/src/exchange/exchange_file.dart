import 'dart:convert';
import 'dart:io' show gzip;
import 'dart:math';

import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../crypto/sealed_file.dart';
import '../db/database.dart';
import '../repo/context.dart';
import '../repo/settings_repository.dart';
import '../sync/wire.dart';

/// Telefonlar o'rtasida almashish fayli (ADR-0017 8-band). Qobiq — [framePrefix] (magic `ZNJX`), ichida gzip qilingan
/// kanonik JSON: `{body, sig}`; `body` — tashkilotning to'liq surati, `sig` — yuboruvchi qurilmaning Ed25519 imzosi
/// (`sha256(canonical(body))` ustidan).
///
/// - `kind = data` — laboratoriya kaliti bilan shifrlangan (kundalik almashish);
/// - `kind = invite` — bir martalik taklif paroli bilan (Argon2id); `body.invite` da taklif va laboratoriya kaliti.
const exchangeFormat = 'zanjir.exchange/1';
const exchangeFileExtension = 'zanjirx';
const _magic = [0x5A, 0x4E, 0x4A, 0x58]; // "ZNJX"
const _version = 1;
const _bodyFormat = 'zanjir.exchange.body/1';

/// Taklif paroli — tasodifiy, 12 belgi (32 belgili alifbo, ~60 bit), Argon2id bilan.
const invitePasswordLength = 12;
const _inviteAlphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';

/// Laboratoriya kaliti (`local_pref`, base64). Zaxirada ham bor — tiklangan telefon almashishni davom ettiradi.
const labKeyPref = 'exchange.lab_key';

enum ExchangeKind { data, invite }

class ExchangeHeader {
  const ExchangeHeader({
    required this.kind,
    required this.createdAt,
    required this.schemaVersion,
    required this.orgId,
    required this.nonce,
    this.kdf,
    this.salt,
  });
  final ExchangeKind kind;
  final DateTime createdAt;
  final int schemaVersion;
  final String orgId;
  final List<int> nonce;
  final KdfParams? kdf;
  final List<int>? salt;

  Map<String, Object?> toJson() => {
    'format': exchangeFormat,
    'kind': kind.name,
    'created_at': isoUtcMillis(createdAt),
    'schema_version': schemaVersion,
    'org_id': orgId,
    'cipher': 'chacha20-poly1305',
    'nonce': base64Encode(nonce),
    if (kdf != null) 'kdf': kdf!.toJson(),
    if (salt != null) 'salt': base64Encode(salt!),
  };

  static ExchangeHeader fromJson(Object? j) {
    if (j is! Map || j['format'] != exchangeFormat || j['cipher'] != 'chacha20-poly1305') {
      throw const DataRuleException('exchange_invalid', 'header');
    }
    try {
      final kind = ExchangeKind.values.byName(j['kind']! as String);
      return ExchangeHeader(
        kind: kind,
        createdAt: DateTime.parse(j['created_at']! as String),
        schemaVersion: j['schema_version']! as int,
        orgId: j['org_id']! as String,
        nonce: base64Decode(j['nonce']! as String),
        kdf: kind == ExchangeKind.invite ? KdfParams.fromJson(j['kdf'], invalidCode: 'exchange_invalid') : null,
        salt: kind == ExchangeKind.invite ? base64Decode(j['salt']! as String) : null,
      );
    } on Object catch (e) {
      if (e is DataRuleException) rethrow;
      throw const DataRuleException('exchange_invalid', 'header');
    }
  }
}

/// Taklif: kimga, laboratoriya kaliti.
typedef InviteInfo = ({String inviteId, String userId, List<int> labKey});

/// Ochilgan va imzosi tekshirilgan fayl tanasi.
class ExchangeBody {
  ExchangeBody._(this.header, this.json, this.senderDeviceId, this.tables, this.invite);
  final ExchangeHeader header;
  final Map<String, Object?> json;
  final String senderDeviceId;

  /// Jadval → qatorlar (sim formati).
  final Map<String, List<Map<String, Object?>>> tables;
  final InviteInfo? invite;
}

ExchangeHeader readExchangeHeader(List<int> bytes) =>
    ExchangeHeader.fromJson(parseFrame(bytes, _magic, _version, 'exchange_invalid').header);

/// Laboratoriya kaliti (yo'q bo'lsa — yaratiladi: laboratoriyani yaratgan telefon).
Future<List<int>> labKey(ZanjirDatabase db, {Random? random}) async {
  final prefs = LocalPrefRepository(db);
  final v = await prefs.get(labKeyPref);
  if (v != null) return base64Decode(v);
  final rnd = random ?? Random.secure();
  final key = List<int>.generate(32, (_) => rnd.nextInt(256));
  await prefs.set(labKeyPref, base64Encode(key));
  return key;
}

String newInvitePassword({Random? random}) {
  final rnd = random ?? Random.secure();
  return String.fromCharCodes(
    List.generate(invitePasswordLength, (_) => _inviteAlphabet.codeUnitAt(rnd.nextInt(_inviteAlphabet.length))),
  );
}

/// Tashkilotning to'liq surati (sim formati, barqaror tartibda).
Future<Map<String, List<Map<String, Object?>>>> snapshot(DataContext ctx) async {
  final out = <String, List<Map<String, Object?>>>{};
  for (final table in syncTables) {
    final cols = wireColumns(ctx.db, table);
    final where = table == 'organization' ? 'id = ?' : 'org_id = ?';
    final rows = await ctx.db
        .customSelect('SELECT * FROM "$table" WHERE $where ORDER BY id', variables: [Variable(ctx.orgId)])
        .get();
    out[table] = [for (final r in rows) rowToWire(cols, r.data)];
  }
  return out;
}

/// Kundalik almashish fayli (laboratoriya kaliti bilan).
Future<Uint8List> createExchangeFile(
  DataContext ctx, {
  required Signer signer,
  required String deviceId,
  Random? random,
}) async => _create(
  ctx,
  signer: signer,
  deviceId: deviceId,
  kind: ExchangeKind.data,
  key: (_) => labKey(ctx.db, random: random),
  random: random,
);

/// Taklif fayli: [inviteId] (`INVITE_CREATED` yozilgan bo'lishi kerak), parol — yuzma-yuz aytiladi.
Future<Uint8List> createInviteFile(
  DataContext ctx, {
  required Signer signer,
  required String deviceId,
  required String inviteId,
  required String userId,
  required String password,
  KdfParams kdf = KdfParams.standard,
  Random? random,
}) async {
  final lab = await labKey(ctx.db, random: random);
  return _create(
    ctx,
    signer: signer,
    deviceId: deviceId,
    kind: ExchangeKind.invite,
    kdf: kdf,
    key: (salt) => deriveKey(password, kdf, salt!),
    extra: {
      'invite': {'invite_id': inviteId, 'user_id': userId, 'lab_key': base64Encode(lab)},
    },
    random: random,
  );
}

Future<Uint8List> _create(
  DataContext ctx, {
  required Signer signer,
  required String deviceId,
  required ExchangeKind kind,
  required Future<List<int>> Function(List<int>? salt) key,
  KdfParams? kdf,
  Map<String, Object?> extra = const {},
  Random? random,
}) async {
  final body = <String, Object?>{
    'format': _bodyFormat,
    'org_id': ctx.orgId,
    'sender_device_id': deviceId,
    'created_at': isoUtcMillis(ctx.now()),
    'tables': await snapshot(ctx),
    ...extra,
  };
  return sealExchangeBody(
    body,
    signer: signer,
    kind: kind,
    createdAt: ctx.now(),
    schemaVersion: ctx.db.schemaVersion,
    key: key,
    kdf: kdf,
    random: random,
  );
}

/// Tanani imzolab shifrlaydi (fayl yaratish va testlarda — o'zgartirilgan tanani qayta imzolash uchun).
Future<Uint8List> sealExchangeBody(
  Map<String, Object?> body, {
  required Signer signer,
  required ExchangeKind kind,
  required DateTime createdAt,
  required int schemaVersion,
  required Future<List<int>> Function(List<int>? salt) key,
  KdfParams? kdf,
  Random? random,
}) async {
  final rnd = random ?? Random.secure();
  final sig = hexEncode(await signer.sign(_bodyDigest(body)));
  final plain = gzip.encode(canonicalJsonBytes({'body': body, 'sig': sig}));
  final salt = kind == ExchangeKind.invite ? List.generate(16, (_) => rnd.nextInt(256)) : null;
  final header = ExchangeHeader(
    kind: kind,
    createdAt: createdAt,
    schemaVersion: schemaVersion,
    orgId: body['org_id']! as String,
    nonce: List.generate(12, (_) => rnd.nextInt(256)),
    kdf: kdf,
    salt: salt,
  );
  final prefix = framePrefix(_magic, _version, header.toJson());
  final sealed = await sealBytes(plain, key: await key(salt), nonce: header.nonce, aad: prefix);
  return Uint8List.fromList([...prefix, ...sealed]);
}

/// Faylni ochish va yuboruvchi imzosini tekshirish (imzo kaliti — fayldagi qurilma qatoridan; qurilmaga ishonch
/// importda alohida tekshiriladi). [key] — `data` uchun laboratoriya kaliti, `invite` uchun — parol.
Future<ExchangeBody> openExchangeFile(List<int> bytes, {List<int>? labKey, String? password}) async {
  final frame = parseFrame(bytes, _magic, _version, 'exchange_invalid');
  final header = ExchangeHeader.fromJson(frame.header);
  final List<int> key;
  switch (header.kind) {
    case ExchangeKind.data:
      key = labKey ?? (throw const DataRuleException('exchange_no_lab_key'));
    case ExchangeKind.invite:
      key = await deriveKey(password ?? '', header.kdf!, header.salt!);
  }
  final plain =
      await openFrame(frame, key: key, nonce: header.nonce) ??
      (throw DataRuleException(header.kind == ExchangeKind.invite ? 'invite_wrong_password' : 'exchange_wrong_key'));
  final Object? outer;
  try {
    outer = jsonDecode(utf8.decode(gzip.decode(plain)));
  } on FormatException {
    throw const DataRuleException('exchange_invalid', 'body');
  }
  if (outer is! Map || outer['body'] is! Map || outer['sig'] is! String) {
    throw const DataRuleException('exchange_invalid', 'body');
  }
  final body = (outer['body'] as Map).cast<String, Object?>();
  if (body['format'] != _bodyFormat || body['org_id'] != header.orgId || body['tables'] is! Map) {
    throw const DataRuleException('exchange_invalid', 'body');
  }
  final sender = body['sender_device_id'];
  if (sender is! String) throw const DataRuleException('exchange_invalid', 'sender');
  final tables = <String, List<Map<String, Object?>>>{};
  for (final MapEntry(:key, :value) in (body['tables'] as Map).entries) {
    if (key is! String || !syncTables.contains(key) || value is! List || value.any((r) => r is! Map)) {
      throw DataRuleException('exchange_invalid', 'table:$key');
    }
    tables[key] = [for (final r in value) (r as Map).cast<String, Object?>()];
  }
  final device = tables['device']?.where((d) => d['id'] == sender).firstOrNull;
  final pub = device?['public_key_ed25519'];
  final alg = device?['sig_alg'];
  if (pub is! String ||
      alg is! String ||
      !supportedSigAlgs.contains(alg) ||
      !await verifySignature(
        sigAlg: alg,
        publicKeyHex: pub,
        message: _bodyDigest(body),
        signatureHex: outer['sig']! as String,
      )) {
    throw const DataRuleException('exchange_bad_signature');
  }
  InviteInfo? invite;
  if (header.kind == ExchangeKind.invite) {
    final i = body['invite'];
    if (i is! Map || i['invite_id'] is! String || i['user_id'] is! String || i['lab_key'] is! String) {
      throw const DataRuleException('exchange_invalid', 'invite');
    }
    invite = (
      inviteId: i['invite_id']! as String,
      userId: i['user_id']! as String,
      labKey: base64Decode(i['lab_key']! as String),
    );
  }
  return ExchangeBody._(header, body, sender, tables, invite);
}

List<int> _bodyDigest(Map<String, Object?> body) => hexDecode(sha256Hex(canonicalJsonBytes(body)));
