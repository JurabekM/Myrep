import 'package:baraka_daftari/app/l10n/gen/app_localizations.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/features/debts/presentation/debts_screen.dart';
import 'package:baraka_daftari/features/home/presentation/home_cards.dart';
import 'package:baraka_daftari/features/partnerships/presentation/partnerships_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'home_slots.g.dart';

/// Bosh ekrandagi karta joyi (MVP_PLAN 0-vazifa). Har bir modul (byudjet,
/// obunalar, qarzlar …) oʻz kartasini [homeCardSlots] roʻyxatiga qoʻshadi —
/// bosh ekran kodiga tegmasdan.
@immutable
final class HomeCardSlot {
  const HomeCardSlot({
    required this.id,
    required this.order,
    required this.builder,
  });

  /// Barqaror kalit (`home-card-<id>` widget kaliti ham shundan).
  final String id;

  /// Kichigi yuqorida. Oraliqlar (100, 200 …) keyingi kartalar uchun boʻsh.
  final int order;

  /// Karta. Koʻrsatadigan narsa boʻlmasa oʻzi `SizedBox.shrink()` qaytaradi.
  final WidgetBuilder builder;
}

/// «Boʻlimlar» roʻyxatidagi qator.
@immutable
final class HomeSection {
  const HomeSection({
    required this.route,
    required this.icon,
    required this.label,
    required this.order,
  });

  final String route;
  final IconData icon;
  final String Function(AppLocalizations l10n) label;
  final int order;
}

/// Bosh ekran kartalari (KPI blokidan keyin), tartiblangan.
@Riverpod(keepAlive: true)
List<HomeCardSlot> homeCardSlots(Ref ref) => _sorted(
  [
    HomeCardSlot(
      id: 'quick',
      order: 50,
      builder: (_) => const QuickExpenseCard(),
    ),
    HomeCardSlot(id: 'due', order: 70, builder: (_) => const DueHomeCard()),
    HomeCardSlot(
      id: 'debtFree',
      order: 75,
      builder: (_) => const DebtFreeHomeCard(),
    ),
    HomeCardSlot(id: 'audit', order: 100, builder: (_) => const AuditCard()),
    HomeCardSlot(
      id: 'offerCheck',
      order: 110,
      builder: (_) => const OfferCheckHomeCard(),
    ),
    HomeCardSlot(
      id: 'havas',
      order: 150,
      builder: (_) => const HavasHomeCard(),
    ),
    HomeCardSlot(
      id: 'accountability',
      order: 155,
      builder: (_) => const AccountabilityHomeCard(),
    ),
    HomeCardSlot(
      id: 'rescue',
      order: 160,
      builder: (_) => const RescueHomeCard(),
    ),
    HomeCardSlot(
      id: 'weekly-tasks',
      order: 200,
      builder: (_) => const WeeklyTasksSlot(),
    ),
  ],
  (s) => s.order,
);

/// Bosh ekrandagi «Boʻlimlar», tartiblangan.
@Riverpod(keepAlive: true)
List<HomeSection> homeSections(Ref ref) => _sorted(
  [
    HomeSection(
      route: AppRoutes.vault,
      icon: Icons.account_balance_wallet_outlined,
      label: (l) => l.vaultTitle,
      order: 100,
    ),
    HomeSection(
      route: AppRoutes.expenses,
      icon: Icons.receipt_long_outlined,
      label: (l) => l.sectionExpenses,
      order: 200,
    ),
    HomeSection(
      route: AppRoutes.debts,
      icon: Icons.receipt_long,
      label: (l) => l.debtsTitle,
      order: 210,
    ),
    HomeSection(
      route: AppRoutes.ceremonies,
      icon: Icons.event_note_outlined,
      label: (l) => l.ceremoniesTitle,
      order: 215,
    ),
    HomeSection(
      route: AppRoutes.partnerships,
      icon: Icons.join_inner,
      label: (l) => l.pnTitle,
      order: 220,
    ),
    HomeSection(
      route: AppRoutes.agreements,
      icon: Icons.history_edu_outlined,
      label: (l) => l.agTitle,
      order: 222,
    ),
    HomeSection(
      route: AppRoutes.ideas,
      icon: Icons.lightbulb_outline,
      label: (l) => l.ideasTitle,
      order: 225,
    ),
    HomeSection(
      route: AppRoutes.learning,
      icon: Icons.school_outlined,
      label: (l) => l.lnTitle,
      order: 227,
    ),
    HomeSection(
      route: AppRoutes.havas,
      icon: Icons.local_cafe_outlined,
      label: (l) => l.havasTitle,
      order: 250,
    ),
    HomeSection(
      route: AppRoutes.subscriptions,
      icon: Icons.autorenew,
      label: (l) => l.subscriptionsTitle,
      order: 260,
    ),
    HomeSection(
      route: AppRoutes.envelopes,
      icon: Icons.mail_outline,
      label: (l) => l.envelopesTitle,
      order: 270,
    ),
    HomeSection(
      route: AppRoutes.rescue,
      icon: Icons.shield_outlined,
      label: (l) => l.rescueTitle,
      order: 280,
    ),
    HomeSection(
      route: AppRoutes.prices,
      icon: Icons.menu_book_outlined,
      label: (l) => l.pricesTitle,
      order: 290,
    ),
    HomeSection(
      route: AppRoutes.obligations,
      icon: Icons.event_repeat_outlined,
      label: (l) => l.sectionObligations,
      order: 300,
    ),
    HomeSection(
      route: AppRoutes.nasiya,
      icon: Icons.storefront_outlined,
      label: (l) => l.sectionNasiya,
      order: 400,
    ),
    HomeSection(
      route: AppRoutes.audit,
      icon: Icons.fact_check_outlined,
      label: (l) => l.auditTitle,
      order: 500,
    ),
    HomeSection(
      route: AppRoutes.whoseMoney,
      icon: Icons.donut_small_outlined,
      label: (l) => l.sectionWhoseMoney,
      order: 600,
    ),
    HomeSection(
      route: AppRoutes.content,
      icon: Icons.menu_book_outlined,
      label: (l) => l.contentTitle,
      order: 700,
    ),
  ],
  (s) => s.order,
);

List<T> _sorted<T>(List<T> items, int Function(T) order) {
  final ids = <int>{};
  for (final i in items) {
    assert(ids.add(order(i)), 'Bir xil order: ${order(i)}');
  }
  final copy = <T>[...items]..sort((a, b) => order(a).compareTo(order(b)));
  return List<T>.unmodifiable(copy);
}
