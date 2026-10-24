import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/widget/widget_bridge.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Vidjetda ko'rsatiladigan shablonlar soni (Kotlin bilan bir xil).
const int widgetMaxTemplates = 4;

/// Shablonlar va matnlarni vidjetga uzatish.
Future<void> pushWidgetTemplates(
  WidgetRef ref,
  AppLocalizations l10n,
  String Function(Money) money,
  List<ExpenseTemplate> templates,
) async {
  try {
    await ref.read(widgetApiProvider).setTemplates(
      [
        for (final t in templates.take(widgetMaxTemplates))
          WidgetTemplate(
            id: t.meta.id,
            title: t.title,
            amountLabel: money(t.amount),
          ),
      ],
      WidgetTexts(
        title: l10n.widgetTitle,
        locked: l10n.widgetLocked,
        empty: l10n.widgetEmpty,
      ),
    );
  } on Object {
    AppLog.event('widget_push_failed');
  }
}

/// Vidjetda bosilgan yozuvlarni bazaga yozadi (faqat qulf ochiq paytda
/// chaqiriladi). Yozilganlar soni; o'chirilgan shablonniki o'tkazib
/// yuboriladi.
Future<int> drainWidgetQueue(WidgetRef ref) async {
  try {
    final pending = await ref.read(widgetApiProvider).takePending();
    if (pending.isEmpty) return 0;
    final service = await ref.read(expenseServiceProvider.future);
    final templates = {
      for (final t in await service.templates()) t.meta.id: t,
    };
    var count = 0;
    for (final p in pending) {
      final t = templates[p.templateId];
      if (t == null) continue;
      await service.recordTemplate(
        t,
        spentAt: DateTime.fromMillisecondsSinceEpoch(
          p.recordedAtMillis,
          isUtc: true,
        ),
      );
      count++;
    }
    if (count > 0) {
      refreshMoneyViews(ref);
      await recordTaskEvent(ref, TaskTrigger.expenseRecorded);
    }
    return count;
  } on Object {
    AppLog.event('widget_drain_failed');
    return 0;
  }
}
