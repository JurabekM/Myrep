import 'dart:typed_data';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability_service.dart';
import 'package:baraka_daftari/features/agreements/presentation/agreement_labels.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';

/// Ko'rik va nizo ekranlari uchun umumiy amallar: xatolarni tarjima qiladi,
/// ko'rinishni yangilaydi.
void refreshAccountability(WidgetRef ref, String agreementId) {
  ref
    ..invalidate(accountabilityViewProvider(agreementId))
    ..invalidate(agreementViewProvider(agreementId))
    ..invalidate(agreementsProvider)
    ..invalidate(agreementCenterProvider);
}

/// [action] bajariladi; muvaffaqiyatli bo'lsa `true`. Domen xatosi — tarjima
/// qilingan xabar, boshqa xato — umumiy xabar.
Future<bool> runAccountability(
  BuildContext context,
  WidgetRef ref,
  String agreementId,
  Future<void> Function(AccountabilityService s) action,
) async {
  final l10n = context.l10n;
  final messenger = ScaffoldMessenger.of(context);
  var ok = false;
  try {
    await action(await ref.read(accountabilityServiceProvider.future));
    ok = true;
  } on DomainRuleException catch (e) {
    AppLog.event('accountability_rejected_${e.code}');
    messenger.showSnackBar(SnackBar(content: Text(agError(l10n, e.code))));
  } on Object {
    AppLog.event('accountability_action_failed');
    messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
  }
  refreshAccountability(ref, agreementId);
  return ok;
}

/// PDF'ni ulashish (faylni saqlamasdan, xotiradan).
Future<void> sharePdfFile(Uint8List bytes, String name, String subject) =>
    SharePlus.instance.share(
      ShareParams(
        files: [XFile.fromData(bytes, mimeType: 'application/pdf', name: name)],
        fileNameOverrides: [name],
        subject: subject,
      ),
    );
