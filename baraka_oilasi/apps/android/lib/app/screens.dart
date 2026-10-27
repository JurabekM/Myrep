import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/core.dart';
import '../features/audit/audit_screen.dart';
import '../features/ceremony/ceremonies_screen.dart';
import '../features/expenses/expenses_screen.dart';
import '../features/governance/agreements_screen.dart';
import '../features/home/home_screen.dart';
import '../features/income/income_sheet.dart';
import '../features/inventory/debts_screen.dart';
import '../features/kasbkor/kk_cash_screen.dart';
import '../features/kasbkor/kk_close_screen.dart';
import '../features/kasbkor/kk_credit_screen.dart';
import '../features/kasbkor/kk_entry_sheet.dart';
import '../features/kasbkor/kk_equipment_screen.dart';
import '../features/kasbkor/kk_gate_screen.dart';
import '../features/kasbkor/kk_home_screen.dart';
import '../features/kasbkor/kk_labor_screen.dart';
import '../features/kasbkor/kk_measure_screen.dart';
import '../features/kasbkor/kk_quote_screen.dart';
import '../features/kasbkor/kk_seller_screen.dart';
import '../features/kasbkor/kk_shift_screen.dart';
import '../features/kasbkor/kk_staff_screen.dart';
import '../features/kasbkor/kk_stock_screen.dart';
import '../features/kasbkor/kk_suppliers_screen.dart';
import '../features/kasbkor/kk_zakat_screen.dart';
import '../features/learning/learning_screen.dart';
import '../features/musofir/mf_entry_sheet.dart';
import '../features/musofir/mf_home_screen.dart';
import '../features/musofir/two_shores_screen.dart';
import '../features/partnership/partnerships_screen.dart';
import '../features/payoff/payoff_screen.dart';
import '../features/receipt/receipt_screen.dart';
import '../features/settings/settings_screen.dart';
import '../features/sync/sync_screen.dart';
import '../features/vault/vault_screen.dart';
import '../features/venture/ideas_screen.dart';
import '../features/venture/offer_check.dart';
import 'i18n.dart';
import 'shell_state.dart';

/// Bo'lim: menyu yorlig'i, moliyaviy maslahatchi maslahati va ekran quruvchisi.
class ScreenDef {
  const ScreenDef(this.id, this.label, this.build, {this.needsSpace = true});

  final String id;
  final String label;
  final Widget Function(ShellContext ctx) build;

  /// Ekran faol makonsiz ham ochiladi (sinxronlash, sozlamalar).
  final bool needsSpace;
}

/// Qobiq holati: xonadon, qurilma roli, faol makon va unga mos menyu (desktop `Shell.tsx`).
class ShellContext {
  ShellContext._(this.household, this.role, this.spaces, this.active, this.mfSpaceId, this.ui);

  factory ShellContext.from(HouseholdDto h, DeviceRoleDto role, ShellState ui) {
    // Uydagi oila qurilmasi (ADR-0004): Musofir makoni — musofirning shaxsiy hisobi, ko'rsatilmaydi.
    final home = role.role == 'HOME';
    final spaces = home ? h.spaces.where((s) => s.kind != 'MUSOFIR').toList() : h.spaces;
    final active = spaces.where((s) => s.id == ui.spaceId).firstOrNull ?? spaces.firstOrNull;
    // «Ikki qirg'oq» (M2): xonadonda Musofir makoni bo'lsa — Uy makonida uy tomoni ekrani.
    final mf = home ? role.spaceId : h.spaces.where((s) => s.kind == 'MUSOFIR').firstOrNull?.id;
    return ShellContext._(h, role, spaces, active, mf, ui);
  }

  final HouseholdDto household;
  final DeviceRoleDto role;
  final List<SpaceDto> spaces;
  final SpaceDto? active;
  final String? mfSpaceId;
  final ShellState ui;

  String get spaceId => active?.id ?? '';
  bool get seller => role.role == 'SELLER';
  bool get kasbkor => active?.kind == 'KASBKOR';
  bool get musofir => active?.kind == 'MUSOFIR';

  String? get roleSpaceKind => spaces.where((s) => s.id == role.spaceId).firstOrNull?.kind;

  /// Faol makon menyusi; ekrani hali qo'shilmagan bo'limlar ko'rsatilmaydi.
  List<({String id, String label})> get nav {
    final ids = seller
        ? _sellerNav
        : kasbkor
        ? _kkNav
        : musofir
        ? _mfNav
        : [
            ..._uyNav.sublist(0, _uyNav.length - 2),
            if (mfSpaceId != null) 'twoShores',
            ..._uyNav.sublist(_uyNav.length - 2),
          ];
    return [
      for (final id in ids)
        if (screenDefs.containsKey(id)) (id: id, label: _label(id)),
    ];
  }

  String _label(String id) => switch (id) {
    'home' when seller => 'nav.kkSell',
    _ => 'nav.$id',
  };
}

const _uyNav = [
  'home',
  'vault',
  'expenses',
  'audit',
  'inventory',
  'debts',
  'ceremonies',
  'partnerships',
  'ideas',
  'learning',
  'agreements',
  'receipt',
  'sync',
  'settings',
];

const _kkNav = [
  'home',
  'kkCash',
  'kkCredit',
  'kkStock',
  'kkSuppliers',
  'kkStaff',
  'kkEquipment',
  'kkLabor',
  'kkQuote',
  'kkClose',
  'kkGate',
  'kkZakat',
  'kkMeasure',
  'sync',
  'settings',
];

const _mfNav = ['home', 'sync', 'settings'];

const _sellerNav = ['home', 'kkSellerCredit', 'kkShift', 'sync', 'settings'];

/// Bo'limlar ro'yxati. Har bir makon ekrani o'z bosqichida qo'shiladi (A1–A4).
final Map<String, ScreenDef> screenDefs = {
  'home': const ScreenDef('home', 'nav.home', _home),
  'vault': ScreenDef('vault', 'nav.vault', (c) => VaultScreen(spaceId: c.spaceId)),
  'expenses': ScreenDef('expenses', 'nav.expenses', (c) => ExpensesScreen(spaceId: c.spaceId)),
  'audit': ScreenDef('audit', 'nav.audit', (c) => AuditScreen(spaceId: c.spaceId)),
  'inventory': ScreenDef('inventory', 'nav.inventory', (c) => DebtsScreen(spaceId: c.spaceId)),
  'debts': ScreenDef('debts', 'nav.debts', (c) => PayoffScreen(spaceId: c.spaceId)),
  'ceremonies': ScreenDef('ceremonies', 'nav.ceremonies', (c) => CeremoniesScreen(spaceId: c.spaceId)),
  'receipt': ScreenDef('receipt', 'nav.receipt', (c) => ReceiptScreen(spaceId: c.spaceId)),
  'partnerships': ScreenDef('partnerships', 'nav.partnerships', (c) => PartnershipsScreen(spaceId: c.spaceId)),
  'ideas': ScreenDef('ideas', 'nav.ideas', (c) => IdeasScreen(spaceId: c.spaceId)),
  'learning': ScreenDef('learning', 'nav.learning', (c) => LearningScreen(spaceId: c.spaceId)),
  'agreements': ScreenDef('agreements', 'nav.agreements', (c) => AgreementsScreen(spaceId: c.spaceId)),
  'kkCash': ScreenDef('kkCash', 'nav.kkCash', (c) => KkCashScreen(spaceId: c.spaceId)),
  'kkCredit': ScreenDef('kkCredit', 'nav.kkCredit', (c) => KkCreditScreen(spaceId: c.spaceId)),
  'kkStock': ScreenDef('kkStock', 'nav.kkStock', (c) => KkStockScreen(spaceId: c.spaceId)),
  'kkSuppliers': ScreenDef('kkSuppliers', 'nav.kkSuppliers', (c) => KkSuppliersScreen(spaceId: c.spaceId)),
  'kkStaff': ScreenDef('kkStaff', 'nav.kkStaff', (c) => KkStaffScreen(spaceId: c.spaceId)),
  'kkEquipment': ScreenDef('kkEquipment', 'nav.kkEquipment', (c) => KkEquipmentScreen(spaceId: c.spaceId)),
  'kkLabor': ScreenDef('kkLabor', 'nav.kkLabor', (c) => KkLaborScreen(spaceId: c.spaceId)),
  'kkQuote': ScreenDef('kkQuote', 'nav.kkQuote', (c) => KkQuoteScreen(spaceId: c.spaceId)),
  'kkClose': ScreenDef('kkClose', 'nav.kkClose', (c) => KkCloseScreen(spaceId: c.spaceId)),
  'kkGate': ScreenDef('kkGate', 'nav.kkGate', (c) => KkGateScreen(spaceId: c.spaceId)),
  'kkZakat': ScreenDef('kkZakat', 'nav.kkZakat', (c) => KkZakatScreen(spaceId: c.spaceId)),
  'kkMeasure': ScreenDef('kkMeasure', 'nav.kkMeasure', (c) => KkMeasureScreen(spaceId: c.spaceId)),
  'kkSellerCredit': ScreenDef('kkSellerCredit', 'nav.kkSellerCredit', (c) => KkSellerCreditScreen(spaceId: c.spaceId)),
  'kkShift': ScreenDef('kkShift', 'nav.kkShift', (c) => KkShiftScreen(spaceId: c.spaceId)),
  'twoShores': ScreenDef(
    'twoShores',
    'nav.twoShores',
    (c) => TwoShoresScreen(mfSpaceId: c.mfSpaceId!, uySpaceId: c.spaceId),
  ),
  'sync': ScreenDef('sync', 'nav.sync', (_) => const SyncScreen(), needsSpace: false),
  'settings': ScreenDef('settings', 'nav.settings', (_) => const SettingsScreen(), needsSpace: false),
};

/// Bosh sahifadagi tez yozuv tugmasi (desktop'dagi `Ctrl+N`): Uy — daromad, Kasb-kor — tushum,
/// Musofir — maosh.
Widget? quickAction(BuildContext context, WidgetRef ref, ShellContext ctx, String screen) {
  if (screen != 'home' || ctx.seller || ctx.role.role == 'ACCOUNTANT') return null;
  if (!ctx.kasbkor && !ctx.musofir) {
    return FloatingActionButton.extended(
      onPressed: () => openIncome(context, ctx.spaceId),
      icon: const Icon(Icons.add),
      label: Text(context.t('home.quickIncome')),
    );
  }
  if (ctx.musofir) {
    return FloatingActionButton.extended(
      onPressed: () => openMfEntry(context, ctx.spaceId, 'SALARY'),
      icon: const Icon(Icons.add),
      label: Text(context.t('mf.action.SALARY')),
    );
  }
  if (ctx.kasbkor) {
    return FloatingActionButton.extended(
      onPressed: () => openKkEntry(context, ctx.spaceId, 'SALE'),
      icon: const Icon(Icons.add),
      label: Text(context.t('kk.action.SALE')),
    );
  }
  return null;
}

/// Bosh sahifa makon va rolga qarab: sotuvchi — sotuv, Kasb-kor — biznes, Musofir — chet el, Uy — oila.
Widget _home(ShellContext ctx) => ctx.seller
    ? KkSellerScreen(spaceId: ctx.spaceId)
    : ctx.kasbkor
    ? KkHomeScreen(spaceId: ctx.spaceId)
    : ctx.musofir
    ? MfHomeScreen(spaceId: ctx.spaceId)
    : HomeScreen(spaceId: ctx.spaceId);

/// «Taklifni tekshirish» (uy/SPEC 2E.5) — ilovaning istalgan joyidan; `null` — ekran hali yo'q.
void Function(BuildContext context)? get offerCheckOpener => openOfferCheck;
