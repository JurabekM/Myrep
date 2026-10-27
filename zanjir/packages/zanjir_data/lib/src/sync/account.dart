import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import '../repo/context.dart';
import '../repo/settings_repository.dart';
import '../repo/user_repository.dart';
import 'server_api.dart';
import 'sync_engine.dart';

/// Qurilmadagi profil identifikatorlari (`local_pref`).
typedef ProfileIds = ({String orgId, String userId, String deviceId});

/// Server bilan hisob oqimlari (ADR-0012): oflayn laboratoriyani ro'yxatdan o'tkazish, taklif bilan qo'shilish,
/// yangi qurilmada kirish. Maxfiy kalit (seed) qurilmadan chiqmaydi — serverga faqat ochiq kalit yuboriladi.
class ServerAccount {
  ServerAccount(this.db, this.api);
  final ZanjirDatabase db;
  final ServerApi api;

  late final _prefs = LocalPrefRepository(db);

  Future<ProfileIds?> localProfile() async {
    final org = await _prefs.get(LocalPrefRepository.orgId);
    final user = await _prefs.get(LocalPrefRepository.userId);
    final device = await _prefs.get(LocalPrefRepository.deviceId);
    return org == null || user == null || device == null ? null : (orgId: org, userId: user, deviceId: device);
  }

  /// Oflayn yaratilgan laboratoriya (LEAD/ADMIN) serverda o'z ID lari bilan ro'yxatdan o'tadi, so'ng to'liq push.
  Future<SyncReport> registerLab({required String password, required String publicKeyHex}) async {
    final ids = await localProfile() ?? (throw StateError('Lokal profil yo\'q'));
    final ctx = DataContext(db: db, orgId: ids.orgId);
    final org = await SettingsRepository(ctx).organization();
    final user = await UserRepository(ctx).require(ids.userId);
    await api.register(
      orgName: org.name,
      fullName: user.fullName,
      phone: user.phone,
      password: password,
      role: user.role,
      orgId: org.id,
      userId: user.id,
      licenseNo: org.licenseNo,
      licenseValidUntil: org.licenseValidUntil,
      safetyGroup: user.safetyGroup,
    );
    await api.registerDevice(id: ids.deviceId, publicKeyHex: publicKeyHex);
    return SyncEngine(db, api).run();
  }

  /// Taklif kodi bilan yangi qurilmada qo'shilish: foydalanuvchi, qurilma, to'liq pull, lokal profil.
  Future<ProfileIds> join({
    required String code,
    required String fullName,
    required String phone,
    required String password,
    required String publicKeyHex,
    String? safetyGroup,
  }) async {
    await _requireEmpty();
    final user = await api.acceptInvite(
      code: code,
      fullName: fullName,
      phone: phone,
      password: password,
      userId: uuidV7(),
      safetyGroup: safetyGroup,
    );
    return _adopt(user, publicKeyHex);
  }

  /// Kirish. Lokal profil bo'lsa — faqat shu foydalanuvchi (tokenlar yangilanadi); bo'lmasa — yangi qurilma
  /// ro'yxatdan o'tadi va hamma narsa serverdan olinadi.
  Future<ProfileIds> login({required String phone, required String password, required String publicKeyHex}) async {
    final local = await localProfile();
    final previous = await api.tokens.read();
    final user = await api.login(phone: phone, password: password);
    if (local != null) {
      if (local.userId != user.id || local.orgId != user.orgId) {
        // Boshqa foydalanuvchi: yangi sessiya serverda yopiladi, oldingisi tiklanadi, lokal profil o'zgarmaydi.
        await api.logout();
        if (previous != null) await api.tokens.write(previous);
        throw StateError('profile_mismatch');
      }
      return local;
    }
    await _requireEmpty();
    return _adopt(user, publicKeyHex);
  }

  Future<ProfileIds> _adopt(ServerUser user, String publicKeyHex) async {
    final deviceId = uuidV7();
    await api.registerDevice(id: deviceId, publicKeyHex: publicKeyHex);
    await SyncEngine(db, api).run();
    await _prefs.set(LocalPrefRepository.orgId, user.orgId);
    await _prefs.set(LocalPrefRepository.userId, user.id);
    await _prefs.set(LocalPrefRepository.deviceId, deviceId);
    return (orgId: user.orgId, userId: user.id, deviceId: deviceId);
  }

  Future<void> _requireEmpty() async {
    if (await localProfile() != null) throw StateError('profile_exists');
  }
}
