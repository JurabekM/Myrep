import 'dart:convert';
import 'dart:io';

import 'package:baraka_daftari/app/settings/app_settings.dart';
import 'package:baraka_daftari/app/settings/settings_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/pump_app.dart';

Set<String> _arbKeys(String path) {
  final json =
      jsonDecode(File(path).readAsStringSync()) as Map<String, dynamic>;
  return json.keys.where((k) => !k.startsWith('@')).toSet();
}

void main() {
  test(
    'uz ARB imlosi: oʻ/gʻ — U+02BB, tutuq — U+02BC, ASCII apostrof yoʻq',
    () {
      final json =
          jsonDecode(File('lib/app/l10n/arb/app_uz.arb').readAsStringSync())
              as Map<String, dynamic>;
      final bad = [
        for (final MapEntry(:key, :value) in json.entries)
          if (!key.startsWith('@') &&
              value is String &&
              // Harflar orasida yoki so'z oxiridagi oʻ/gʻ («Obroʻ»).
              RegExp(
                "[A-Za-z]['‘’`][A-Za-z]|[A-Za-z][oOgG]['‘’`]",
              ).hasMatch(value))
            key,
      ];
      expect(bad, isEmpty, reason: 'python tools/uz_orthography.py');
    },
  );

  test('uz va ru ARB fayllarida kalitlar bir xil', () {
    final uz = _arbKeys('lib/app/l10n/arb/app_uz.arb');
    final ru = _arbKeys('lib/app/l10n/arb/app_ru.arb');
    expect(ru, equals(uz));
  });

  testWidgets('til uz ↔ ru almashadi', (tester) async {
    final env = await pumpBarakaApp(tester, unlock: false);
    expect(find.text('PIN kodni kiriting'), findsOneWidget);

    await tester.tap(find.byKey(const Key('switch-language')));
    await tester.pumpAndSettle();
    expect(
      env.container.read(settingsControllerProvider).language,
      AppLanguage.ru,
    );
    expect(find.text('Введите PIN-код'), findsOneWidget);
    expect(find.text('Барака Дастур'), findsOneWidget);

    await tester.tap(find.byKey(const Key('switch-language')));
    await tester.pumpAndSettle();
    expect(find.text('PIN kodni kiriting'), findsOneWidget);
  });

  testWidgets("mavzu yorug' ↔ qorongʻi almashadi", (tester) async {
    await pumpBarakaApp(tester);
    Brightness current() =>
        Theme.of(tester.element(find.byType(Scaffold))).brightness;
    final before = current();

    await tester.tap(find.byKey(const Key('switch-theme')));
    await tester.pumpAndSettle();
    expect(current(), isNot(before));

    await tester.tap(find.byKey(const Key('switch-theme')));
    await tester.pumpAndSettle();
    expect(current(), before);
  });

  test('AppSettings JSON orqali aylanib qaytadi', () {
    const settings = AppSettings(
      language: AppLanguage.ru,
      themeMode: ThemeMode.dark,
    );
    expect(AppSettings.fromJson(settings.toJson()), settings);
  });
}
