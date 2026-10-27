import 'package:baraka_daftari/core/security/secure_blob_store.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'security_settings.freezed.dart';
part 'security_settings.g.dart';

@freezed
abstract class SecuritySettings with _$SecuritySettings {
  const factory SecuritySettings({
    @Default(false) bool biometricEnabled,

    /// Fonga o'tgandan keyin necha daqiqada qayta qulflanadi.
    @Default(2) int lockTimeoutMinutes,
  }) = _SecuritySettings;

  factory SecuritySettings.fromJson(Map<String, dynamic> json) =>
      _$SecuritySettingsFromJson(json);
}

class SecuritySettingsRepository {
  const SecuritySettingsRepository(this._store);

  static const blob = 'security_settings';

  final SecureBlobStore _store;

  Future<SecuritySettings> load() async {
    final json = await _store.readJson(blob);
    return json == null
        ? const SecuritySettings()
        : SecuritySettings.fromJson(json);
  }

  Future<void> save(SecuritySettings settings) =>
      _store.writeJson(blob, settings.toJson());
}

@Riverpod(keepAlive: true)
SecuritySettingsRepository securitySettingsRepository(Ref ref) =>
    SecuritySettingsRepository(ref.watch(secureBlobStoreProvider));
