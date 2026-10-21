import 'package:flutter/services.dart';

import '../platform/platform_api.g.dart';

/// Platforma siri manbai (7.2). Android — Kotlin Keystore (Pigeon); testlarda — xotiradagi qiymat.
abstract interface class SecretSource {
  /// Birinchi sozlash yoki xonadonga qo'shilish: yo'q bo'lsa yaratadi.
  Future<Uint8List> create();

  /// Ochish: faqat mavjud sir.
  Future<Uint8List> load();
}

/// `FLAG_SECURE` boshqaruvi (moliyaviy ekranlar). Testlarda — hech narsa qilmaydi.
// ignore: one_member_abstracts — platforma xizmati interfeysi (testda almashtiriladi).
abstract interface class SecureWindow {
  Future<void> setSecure({required bool secure});
}

class AndroidSecretSource implements SecretSource {
  AndroidSecretSource([PlatformSecretApi? api]) : _api = api ?? PlatformSecretApi();

  final PlatformSecretApi _api;

  @override
  Future<Uint8List> create() => _api.getOrCreatePlatformSecret();

  @override
  Future<Uint8List> load() => _api.loadPlatformSecret();
}

class AndroidSecureWindow implements SecureWindow {
  AndroidSecureWindow([SecureWindowApi? api]) : _api = api ?? SecureWindowApi();

  final SecureWindowApi _api;

  @override
  Future<void> setSecure({required bool secure}) async {
    try {
      await _api.setSecure(secure);
    } on PlatformException {
      // Oyna bayrog'i qo'yilmasa ham ilova ishlashda davom etadi (standart holda yoqiq).
    }
  }
}
