import 'dart:math';

import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'key_store.dart';

/// Joriy foydalanuvchi va qurilma.
class Profile {
  const Profile({
    required this.orgId,
    required this.userId,
    required this.deviceId,
    required this.fullName,
    required this.role,
  });
  final String orgId;
  final String userId;
  final String deviceId;
  final String fullName;
  final String role;

  bool get canEditSettings => SettingsRepository.editorRoles.contains(role);
}

/// Oflayn laboratoriya profili: tashkilot, foydalanuvchi (LEAD/ADMIN), qurilma kaliti, normalar to'plami. Ilova to'liq
/// oflayn (ADR-0017): yangi telefonga — shifrlangan zaxiradan yoki almashish fayli orqali.
class ProfileService {
  ProfileService({required this.db, required this.keyStore, DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;
  final ZanjirDatabase db;
  final DeviceKeyStore keyStore;
  final DateTime Function() _clock;

  static const creatorRoles = ['LEAD', 'ADMIN'];

  Future<Profile?> load() async {
    final prefs = LocalPrefRepository(db);
    final orgId = await prefs.get(LocalPrefRepository.orgId);
    final userId = await prefs.get(LocalPrefRepository.userId);
    final deviceId = await prefs.get(LocalPrefRepository.deviceId);
    if (orgId == null || userId == null || deviceId == null) return null;
    if (await keyStore.readSeed() == null) return null;
    final user = await UserRepository(DataContext(db: db, orgId: orgId)).get(userId);
    if (user == null) return null;
    return Profile(orgId: orgId, userId: userId, deviceId: deviceId, fullName: user.fullName, role: user.role);
  }

  /// Zaxiradan tiklash: telefon yangi qurilma kalitini oladi (eski kalit zaxirada yo'q), ma'lumot bo'sh bazaga
  /// nusxalanadi ([restoreBackup]).
  Future<Profile> restore(List<int> backup, String password) async {
    final seed = await keyStore.readSeed() ?? _newSeed();
    await keyStore.writeSeed(seed);
    await restoreBackup(db, backup, password: password, signer: await Ed25519Signer.fromSeed(seed), clock: _clock);
    // Tiklangan zaxira — eng so'nggi zaxira (bazadagi qiymat undan oldingisi).
    await LocalPrefRepository(db)
        .set(LocalPrefRepository.lastBackupAt, isoUtcMillis(readBackupHeader(backup).createdAt));
    return (await load()) ?? (throw StateError('restore_profile'));
  }

  /// Taklif fayli orqali laboratoriyaga qo'shilish (yangi telefon, [joinWithInvite]).
  Future<Profile> join(List<int> invite, String password) async {
    final seed = await keyStore.readSeed() ?? _newSeed();
    await keyStore.writeSeed(seed);
    await joinWithInvite(db, invite, password: password, signer: await Ed25519Signer.fromSeed(seed), clock: _clock);
    return (await load()) ?? (throw StateError('join_profile'));
  }

  static List<int> _newSeed() {
    final rnd = Random.secure();
    return List<int>.generate(32, (_) => rnd.nextInt(256));
  }

  Future<Profile> create({
    required String labName,
    required String fullName,
    required String phone,
    required String role,
    required String normsYaml,
  }) async {
    if (!creatorRoles.contains(role)) throw ArgumentError.value(role, 'role');
    final seed = _newSeed();
    // Avval kalit: tranzaksiya muvaffaqiyatsiz bo'lsa, ortiqcha seed keyingi urinishda qayta yoziladi.
    await keyStore.writeSeed(seed);
    late Profile profile;
    await db.transaction(() async {
      final orgId = await OrganizationRepository(db, clock: _clock).create(name: labName);
      final ctx = DataContext(db: db, orgId: orgId, clock: _clock);
      final user = await UserRepository(ctx).create(fullName: fullName, phone: phone, role: role);
      final signer = await Ed25519Signer.fromSeed(seed);
      final device = await DeviceRepository(ctx)
          .register(userId: user.id, publicKeyHex: signer.publicKeyHex, sigAlg: signer.sigAlg);
      final repos = Repositories(ctx, signer: signer, deviceId: device.id, actorId: user.id);
      final norms = await repos.normSets.import(normsYaml);
      await repos.settings.update(byUserId: user.id, activeNormSetVersion: norms.version);
      final prefs = LocalPrefRepository(db);
      await prefs.set(LocalPrefRepository.orgId, orgId);
      await prefs.set(LocalPrefRepository.userId, user.id);
      await prefs.set(LocalPrefRepository.deviceId, device.id);
      // Laboratoriya kaliti shu yerda — zaxiraga tushadi; xodimlar uni taklif orqali oladi.
      await labKey(db);
      profile = Profile(orgId: orgId, userId: user.id, deviceId: device.id, fullName: fullName, role: role);
    });
    return profile;
  }
}
