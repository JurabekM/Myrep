import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/pump_app.dart';

/// «Baraka Dastur» nomi va nishoni (`tools/make_icon.py`).
void main() {
  testWidgets('qulf ekranida nishon va yangi nom', (tester) async {
    await pumpBarakaApp(tester, unlock: false);
    expect(find.byKey(const Key('brand-logo')), findsOneWidget);
    expect(find.text('Baraka Dastur'), findsOneWidget);
  });

  testWidgets('onboardingning birinchi sahifasida nishon', (tester) async {
    await pumpBarakaApp(tester, onboarded: false);
    expect(find.byKey(const Key('brand-logo')), findsOneWidget);
    expect(
      find.textContaining('Baraka Dasturga xush kelibsiz'),
      findsOneWidget,
    );
  });

  test('launcher ikonkalari kerakli oʻlchamda (PNG sarlavhasidan)', () {
    (int, int) size(String path) {
      final b = File(path).readAsBytesSync();
      final d = ByteData.sublistView(b);
      expect(b.sublist(1, 4), 'PNG'.codeUnits, reason: path);
      return (d.getUint32(16), d.getUint32(20));
    }

    const res = 'android/app/src/main/res';
    const legacy = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144};
    const adaptive = {'mdpi': 108, 'hdpi': 162, 'xhdpi': 216, 'xxhdpi': 324};
    for (final MapEntry(key: dpi, value: px) in legacy.entries) {
      expect(size('$res/mipmap-$dpi/ic_launcher.png'), (px, px));
    }
    for (final MapEntry(key: dpi, value: px) in adaptive.entries) {
      expect(size('$res/mipmap-$dpi/ic_launcher_foreground.png'), (px, px));
    }
    expect(size('assets/branding/logo.png'), (384, 384));
    expect(size('tools/store/play_icon_512.png'), (512, 512));
    expect(size('tools/store/feature_graphic_1024x500.png'), (1024, 500));
  });
}
