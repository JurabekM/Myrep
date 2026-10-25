import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app.dart';
import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/prefs.dart';
import '../../core/query.dart';
import '../../shared/widgets.dart';
import '../setup/setup_screen.dart' show rhythms;

/// Sozlamalar: til (shu qurilma), ko'rinish (shrift, mavzu), daromad ritmi, qarz eslatmasi.
class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> with ActionState {
  Future<void> _save(SettingsDto cur, {String? locale, String? rhythm, bool clearRhythm = false, bool? debts}) async {
    final s = await act(
      () => ref
          .read(coreProvider)
          .updateSettings(
            input: SettingsInput(
              locale: locale ?? cur.deviceLocale,
              incomeRhythm: clearRhythm ? null : (rhythm ?? cur.incomeRhythm),
              debtsDeclared: debts ?? cur.debtsDeclared,
            ),
          ),
    );
    if (s != null && s.locale != ref.read(localeProvider)) {
      ref.read(localeProvider.notifier).state = s.locale;
      final prefs = ref.read(servicesProvider).prefs;
      prefs.write(prefs.read().copyWith(locale: s.locale));
    }
  }

  void _display(DisplayPrefs next) {
    ref.read(servicesProvider).prefs.write(next);
    ref.read(displayProvider.notifier).state = next;
  }

  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(query(['settings'], (c) => c.settings()));
    final display = ref.watch(displayProvider);
    final p = context.palette;
    return AsyncView(
      value: settings,
      data: (s) => ScreenBody(
        mentorKey: 'mentor.settings',
        children: [
          ErrorText(error),
          SectionCard(
            title: context.t('settings.language'),
            children: [
              Text(context.t('settings.languageHint'), style: TextStyle(color: p.inkMuted, fontSize: 14)),
              const SizedBox(height: 8),
              for (final l in locales)
                ChoiceTile(
                  label: context.t('locale.$l'),
                  selected: s.locale == l,
                  onTap: () => _save(s, locale: l),
                ),
            ],
          ),
          SectionCard(
            title: context.t('settings.display'),
            children: [
              Text(context.t('settings.displayHint'), style: TextStyle(color: p.inkMuted, fontSize: 14)),
              const SizedBox(height: 12),
              SegmentedChoice<int>(
                label: context.t('settings.fontSize'),
                options: [for (final f in DisplayPrefs.fontScales) (f, '$f%')],
                value: display.fontScale,
                onChanged: (f) => _display(display.copyWith(fontScale: f)),
              ),
              const SizedBox(height: 12),
              SegmentedChoice<String>(
                label: context.t('settings.theme'),
                options: [
                  for (final th in ['dark', 'light']) (th, context.t('settings.theme.$th')),
                ],
                value: display.theme,
                onChanged: (th) => _display(display.copyWith(theme: th)),
              ),
            ],
          ),
          SectionCard(
            title: context.t('settings.rhythm'),
            children: [
              Text(context.t('settings.rhythmHint'), style: TextStyle(color: p.inkMuted, fontSize: 14)),
              const SizedBox(height: 8),
              for (final r in rhythms)
                ChoiceTile(
                  label: context.t('rhythm.$r'),
                  hint: context.t('rhythmHint.$r'),
                  selected: s.incomeRhythm == r,
                  onTap: () => _save(s, rhythm: r),
                ),
              ChoiceTile(
                label: context.t('rhythm.NONE'),
                selected: s.incomeRhythm == null,
                onTap: () => _save(s, clearRhythm: true),
              ),
            ],
          ),
          SectionCard(
            title: context.t('settings.debts'),
            children: [
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: s.debtsDeclared,
                title: Text(context.t('settings.debtsReminder')),
                onChanged: busy ? null : (v) => _save(s, debts: v ?? false),
              ),
            ],
          ),
          SectionCard(
            title: context.t('settings.about'),
            children: [
              Text(context.t('app.name'), style: Theme.of(context).textTheme.titleMedium),
              Text(context.t('app.copyright')),
              Text(context.t('app.disclaimer')),
            ],
          ),
        ],
      ),
    );
  }
}
