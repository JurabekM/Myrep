import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/core.dart';
import '../features/home/home_screen.dart';
import '../features/income/income_sheet.dart';
import '../features/settings/settings_screen.dart';
import 'i18n.dart';
import 'shell_state.dart';

/// Bo'lim: menyu yorlig'i, Sobir hoji maslahati va ekran quruvchisi.
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
  return null;
}

Widget _home(ShellContext ctx) => HomeScreen(spaceId: ctx.spaceId);

/// «Taklifni tekshirish» (uy/SPEC 2E.5) — ilovaning istalgan joyidan; `null` — ekran hali yo'q.
void Function(BuildContext context)? get offerCheckOpener => null;
