import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Pigeon orqali Kotlin bilan aloqa holatini ko'rsatadi.
class NativeBridgeCard extends ConsumerWidget {
  const NativeBridgeCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final info = ref.watch(nativeInfoProvider);
    final (icon, status) = switch (info) {
      AsyncData(:final value) => (
        Icons.verified_user_outlined,
        l10n.nativeBridgeOk(value.apiVersion, value.androidSdkInt),
      ),
      AsyncError() => (Icons.link_off, l10n.nativeBridgeUnavailable),
      _ => (Icons.hourglass_empty, l10n.nativeBridgeChecking),
    };
    return Card(
      child: ListTile(
        key: const Key('native-bridge'),
        leading: Icon(icon),
        title: Text(l10n.nativeBridgeTitle),
        subtitle: Text(status),
      ),
    );
  }
}
