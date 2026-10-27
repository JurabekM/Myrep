import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:meta/meta.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'demo_config.g.dart';

/// Demo yig'ish (`tools/build_demo.ps1`): `--dart-define=BARAKA_DEMO=true` va
/// `--dart-define=BARAKA_DEMO_UNTIL=YYYY-MM-DD`. Oddiy reliz'da o'chiq.
/// Demo — ko'rsatish uchun: har ekranda «DEMO» belgisi va muallif, muddat
/// tugagach ilova ochilmaydi (Android tomonda alohida paket va debug imzo).
@immutable
final class DemoConfig {
  const DemoConfig({required this.enabled, this.until});

  factory DemoConfig.fromEnvironment() {
    const enabled = bool.fromEnvironment('BARAKA_DEMO');
    const until = String.fromEnvironment('BARAKA_DEMO_UNTIL');
    return DemoConfig(
      enabled: enabled,
      until: until.isEmpty ? null : LocalDate.parse(until),
    );
  }

  static const off = DemoConfig(enabled: false);

  final bool enabled;

  /// Demo ishlaydigan oxirgi kun (shu kun ham kiradi).
  final LocalDate? until;

  bool expiredOn(LocalDate today) {
    final last = until;
    return enabled && last != null && today.isAfter(last);
  }
}

@Riverpod(keepAlive: true)
DemoConfig demoConfig(Ref ref) => DemoConfig.fromEnvironment();
