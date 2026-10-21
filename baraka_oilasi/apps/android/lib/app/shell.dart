import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/core.dart';
import '../core/query.dart';
import 'i18n.dart';
import 'screens.dart';
import 'shell_state.dart';
import 'theme.dart';

/// Android avto-qulf (7.4): fonga o'tgandan 2 daqiqa keyin.
const backgroundLockAfter = Duration(minutes: 2);

/// Asosiy oyna: yon menyuda makonlar va bo'limlar, markazda ekran, pastda Sobir hoji.
class Shell extends ConsumerStatefulWidget {
  const Shell({super.key});

  @override
  ConsumerState<Shell> createState() => _ShellState();
}

class _ShellState extends ConsumerState<Shell> {
  late final AppLifecycleListener _life;
  DateTime? _hiddenAt;

  @override
  void initState() {
    super.initState();
    _life = AppLifecycleListener(
      onHide: () => _hiddenAt = DateTime.now(),
      onShow: () {
        final at = _hiddenAt;
        _hiddenAt = null;
        if (at != null && DateTime.now().difference(at) >= backgroundLockAfter) {
          unawaited(ref.read(sessionActionsProvider).lock());
        }
      },
    );
  }

  @override
  void dispose() {
    _life.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final household = ref.watch(query(['household'], (c) => c.household()));
    final roleQ = ref.watch(query(['deviceRole'], (c) => c.deviceRole()));
    final settings = ref.watch(query(['settings'], (c) => c.settings()));
    final ui = ref.watch(shellProvider);

    // Bazadagi til (shu qurilma yoki xonadon) — UI shu tilda; qulf ekrani uchun ham eslab qolinadi.
    ref.listen(query(['settings'], (c) => c.settings()), (_, next) {
      final l = next.valueOrNull?.locale;
      if (l != null && l != ref.read(localeProvider)) {
        ref.read(localeProvider.notifier).state = l;
        final prefs = ref.read(servicesProvider).prefs;
        prefs.write(prefs.read().copyWith(locale: l));
      }
    });

    final h = household.valueOrNull;
    final role = roleQ.valueOrNull;
    if (h == null || role == null || !settings.hasValue) {
      return Scaffold(
        body: household.hasError || roleQ.hasError
            ? Center(child: Text(context.t('error.GENERIC')))
            : const Center(child: CircularProgressIndicator()),
      );
    }
    final ctx = ShellContext.from(h, role, ui);
    final nav = ctx.nav;
    final screen = nav.any((n) => n.id == ui.screen) ? ui.screen : 'home';
    final def = screenDefs[screen];
    final title = context.t(nav.firstWhere((n) => n.id == screen, orElse: () => nav.first).label);

    return PopScope(
      canPop: screen == 'home',
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) ref.read(shellProvider.notifier).go('home');
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(screen == 'home' && ctx.active != null ? context.t('space.${ctx.active!.kind}') : title),
          actions: [
            IconButton(
              tooltip: context.t('nav.lock'),
              icon: const Icon(Icons.lock_outline),
              onPressed: () => unawaited(ref.read(sessionActionsProvider).lock()),
            ),
          ],
        ),
        drawer: _Drawer(ctx: ctx, current: screen),
        floatingActionButton: ctx.active == null ? null : quickAction(context, ref, ctx, screen),
        body: ctx.active == null && def?.needsSpace != false
            ? const SizedBox.shrink()
            : Column(
                children: [
                  if (role.role == 'ACCOUNTANT')
                    Container(
                      key: const Key('role-read-only'),
                      width: double.infinity,
                      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        border: Border.all(color: context.palette.warn),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        context.t('role.readOnly'),
                        style: TextStyle(color: context.palette.warn, fontSize: 14),
                      ),
                    ),
                  Expanded(child: def == null ? const SizedBox.shrink() : def.build(ctx)),
                ],
              ),
      ),
    );
  }
}

class _Drawer extends ConsumerWidget {
  const _Drawer({required this.ctx, required this.current});

  final ShellContext ctx;
  final String current;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final p = context.palette;
    void go(String id) {
      Navigator.of(context).pop();
      ref.read(shellProvider.notifier).go(id);
    }

    final role = ctx.role.role;
    return Drawer(
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Text(
                context.t('app.name'),
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, fontFamily: 'NotoSerif'),
              ),
            ),
            Semantics(
              container: true,
              label: context.t('a11y.spaces'),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final s in ctx.spaces)
                      ChoiceChip(
                        label: Text(context.t('space.${s.kind}')),
                        selected: s.id == ctx.active?.id,
                        onSelected: (_) {
                          Navigator.of(context).pop();
                          ref.read(shellProvider.notifier).setSpace(s.id);
                        },
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: Semantics(
                container: true,
                label: context.t('a11y.mainNav'),
                child: ListView(
                  children: [
                    for (final n in ctx.nav)
                      ListTile(
                        selected: n.id == current,
                        selectedTileColor: p.surface,
                        selectedColor: p.ink,
                        title: Text(context.t(n.label)),
                        onTap: () => go(n.id),
                      ),
                  ],
                ),
              ),
            ),
            if (role == 'HOME' || role == 'SELLER' || role == 'ACCOUNTANT')
              Container(
                key: const Key('role-badge'),
                margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(color: p.line),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  context.t('role.badge.$role', {'space': context.t('space.${ctx.roleSpaceKind ?? 'KASBKOR'}')}),
                  style: TextStyle(color: p.inkMuted, fontSize: 13),
                ),
              ),
            if ((role == 'OWNER' || role == 'HOME') && offerCheckOpener != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                child: OutlinedButton(
                  onPressed: () {
                    Navigator.of(context).pop();
                    offerCheckOpener?.call(context);
                  },
                  child: Text(context.t('offer.open')),
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: OutlinedButton.icon(
                icon: const Icon(Icons.lock_outline),
                onPressed: () {
                  Navigator.of(context).pop();
                  unawaited(ref.read(sessionActionsProvider).lock());
                },
                label: Text(context.t('nav.lock')),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
