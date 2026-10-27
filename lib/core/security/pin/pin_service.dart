import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:baraka_daftari/core/security/pin/lockout_policy.dart';
import 'package:baraka_daftari/core/security/pin/pin_hasher.dart';
import 'package:baraka_daftari/core/security/pin/pin_models.dart';
import 'package:baraka_daftari/core/security/pin/pin_policy.dart';
import 'package:baraka_daftari/core/security/secure_blob_store.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'pin_service.g.dart';

/// PIN tekshiruvi natijasi.
sealed class PinCheck {
  const PinCheck();
}

final class PinAccepted extends PinCheck {
  const PinAccepted();
}

final class PinRejected extends PinCheck {
  const PinRejected({required this.attemptsBeforeLockout});

  final int attemptsBeforeLockout;
}

final class PinLockedOut extends PinCheck {
  const PinLockedOut({required this.until});

  /// UTC.
  final DateTime until;
}

/// Muhim amal (masalan, «Kelajagim»dan pul olish) uchun PIN qayta
/// kiritilganining isboti. Faqat [PinService.approve] yaratadi (konstruktor
/// yopiq), bir marta ishlatiladi va [lifetime] dan keyin eskiradi.
class PinApproval {
  PinApproval._(this.issuedAt);

  static const lifetime = Duration(minutes: 1);

  /// UTC.
  final DateTime issuedAt;
  bool _used = false;

  bool get isUsed => _used;

  /// Ruxsat yaroqli bo'lsa ishlatiladi (qayta ishlatib bo'lmaydi).
  /// Yaroqsiz bo'lsa `false`.
  bool consume(DateTime nowUtc) {
    final fresh =
        !nowUtc.isBefore(issuedAt) && nowUtc.difference(issuedAt) <= lifetime;
    if (_used || !fresh) return false;
    _used = true;
    return true;
  }
}

/// PIN o'rnatish va tekshirish (SPEC 4.5: PBKDF2-SHA256 ≥ 310k, PIN o'zi
/// saqlanmaydi).
class PinService {
  PinService({
    required SecureBlobStore store,
    required PinHasher hasher,
    required Clock clock,
    Random? random,
    this.iterations = defaultIterations,
  }) : _store = store,
       _hasher = hasher,
       _clock = clock,
       _random = random ?? Random.secure();

  static const defaultIterations = 310000;
  static const recordBlob = 'pin_record';
  static const lockoutBlob = 'pin_lockout';
  static const algorithm = 'PBKDF2-HMAC-SHA256';
  static const _saltLength = 16;

  final SecureBlobStore _store;
  final PinHasher _hasher;
  final Clock _clock;
  final Random _random;
  final int iterations;

  Future<bool> isPinSet() async => await _store.read(recordBlob) != null;

  /// Yangi PIN o'rnatadi va lockout holatini tozalaydi.
  Future<void> setPin(String pin) async {
    final record = await createRecord(pin);
    await _store.writeJson(recordBlob, record.toJson());
    await _store.delete(lockoutBlob);
  }

  /// PIN hosilasini yaratadi (PIN o'zi saqlanmaydi). Oila a'zosining
  /// shaxsiy PIN'i ham shu bilan yaratiladi.
  Future<PinRecord> createRecord(String pin) async {
    final issue = PinPolicy.validate(pin);
    if (issue != null) throw ArgumentError.value(issue, 'pin');
    final salt = Uint8List.fromList(
      List<int>.generate(_saltLength, (_) => _random.nextInt(256)),
    );
    final hash = await _hasher.derive(pin, salt, iterations);
    return PinRecord(
      version: 1,
      algorithm: algorithm,
      iterations: iterations,
      salt: base64Encode(salt),
      hash: base64Encode(hash),
    );
  }

  Future<PinCheck> verify(String pin) async {
    final json = await _store.readJson(recordBlob);
    if (json == null) throw StateError("PIN o'rnatilmagan");
    return verifyRecord(PinRecord.fromJson(json), pin, lockoutKey: lockoutBlob);
  }

  /// [record] ga qarshi tekshiradi; xatolar [lockoutKey] blobida
  /// hisoblanadi (asosiy PIN va har bir a'zoning PIN'i alohida).
  Future<PinCheck> verifyRecord(
    PinRecord record,
    String pin, {
    required String lockoutKey,
  }) async {
    final now = _clock.nowUtc();
    var lockout = await _readLockout(lockoutKey);

    final until = lockout.lockedUntil;
    final startedAt = lockout.lockStartedAt;
    if (until != null && startedAt != null) {
      if (now.isBefore(startedAt)) {
        // Soat orqaga surilgan — kutishni hozirdan to'liq qayta boshlaymiz.
        lockout = lockout.copyWith(
          lockStartedAt: now,
          lockedUntil: now.add(until.difference(startedAt)),
        );
        await _writeLockout(lockoutKey, lockout);
        return PinLockedOut(until: lockout.lockedUntil!);
      }
      if (now.isBefore(until)) return PinLockedOut(until: until);
    }

    final derived = await _hasher.derive(
      pin,
      base64Decode(record.salt),
      record.iterations,
    );

    if (_constantTimeEquals(derived, base64Decode(record.hash))) {
      if (lockout.failedAttempts > 0) await _store.delete(lockoutKey);
      return const PinAccepted();
    }

    final failed = lockout.failedAttempts + 1;
    final delay = LockoutPolicy.delayAfter(failed);
    final next = LockoutState(
      failedAttempts: failed,
      lockStartedAt: delay == null ? null : now,
      lockedUntil: delay == null ? null : now.add(delay),
    );
    await _writeLockout(lockoutKey, next);
    return delay == null
        ? PinRejected(
            attemptsBeforeLockout: LockoutPolicy.attemptsBeforeLockout(failed),
          )
        : PinLockedOut(until: next.lockedUntil!);
  }

  /// PIN'ni tekshiradi va to'g'ri bo'lsa bir martalik [PinApproval] beradi.
  /// Lockout qoidalari oddiy tekshiruvdagidek amal qiladi.
  Future<(PinCheck, PinApproval?)> approve(String pin) async {
    final check = await verify(pin);
    return (
      check,
      check is PinAccepted ? PinApproval._(_clock.nowUtc()) : null,
    );
  }

  /// Biometriya orqali ishonchli kirishdan keyin xatolar hisoblagichini
  /// tozalaydi.
  Future<void> resetFailures({String key = lockoutBlob}) => _store.delete(key);

  /// Ekranni ochganda joriy kutish holatini ko'rsatish uchun.
  Future<DateTime?> activeLockoutUntil({String key = lockoutBlob}) async {
    final lockout = await _readLockout(key);
    final until = lockout.lockedUntil;
    if (until == null) return null;
    final now = _clock.nowUtc();
    final startedAt = lockout.lockStartedAt;
    if (startedAt != null && now.isBefore(startedAt)) return until;
    return now.isBefore(until) ? until : null;
  }

  Future<LockoutState> _readLockout(String key) async {
    final json = await _store.readJson(key);
    return json == null ? const LockoutState() : LockoutState.fromJson(json);
  }

  Future<void> _writeLockout(String key, LockoutState state) =>
      _store.writeJson(key, state.toJson());

  static bool _constantTimeEquals(List<int> a, List<int> b) {
    if (a.length != b.length) return false;
    var diff = 0;
    for (var i = 0; i < a.length; i++) {
      diff |= a[i] ^ b[i];
    }
    return diff == 0;
  }
}

@Riverpod(keepAlive: true)
PinService pinService(Ref ref) => PinService(
  store: ref.watch(secureBlobStoreProvider),
  hasher: ref.watch(pinHasherProvider),
  clock: ref.watch(clockProvider),
);
