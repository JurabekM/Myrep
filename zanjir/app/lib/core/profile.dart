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

/// Oflayn laboratoriya profili: tashkilot, foydalanuvchi (LEAD/ADMIN), qurilma kaliti, normalar to'plami.
/// Server ulangach (7–8-fazalar) profil serverda ro'yxatdan o'tkaziladi.
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

  Future<Profile> create({
    required String labName,
    required String fullName,
    required String phone,
    required String role,
    required String normsYaml,
  }) async {
    if (!creatorRoles.contains(role)) throw ArgumentError.value(role, 'role');
    final rnd = Random.secure();
    final seed = List<int>.generate(32, (_) => rnd.nextInt(256));
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
      profile = Profile(orgId: orgId, userId: user.id, deviceId: device.id, fullName: fullName, role: role);
    });
    return profile;
  }
}
