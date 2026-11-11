// Google Play skrinshotlari: ilovaning haqiqiy ekranlari (Flutter render, NotoSans va Material Icons shriftlari bilan),
// ma'lumot — yadroning test fixture'i (Toshkent, iyuldagi issiqlik to'lqini ssenariysi, «65 yoshdan kattalar» profili).
//
//   cd havoradar && TZ=Asia/Tashkent flutter test tool/store/screenshots_test.dart && python3 tool/store/compose.py
//
// Natija: build/store/raw/*.png (1080×2160) → compose.py → docs/store/.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:havoradar/app.dart';
import 'package:havoradar/data/models.dart';
import 'package:havoradar/state/app_state.dart';

import '../../test/fake_engine.dart';

const _out = 'build/store/raw';
final _root = GlobalKey();

Future<void> _loadFonts() async {
  final noto = FontLoader('NotoSans')
    ..addFont(rootBundle.load('assets/fonts/NotoSans-Regular.ttf'))
    ..addFont(rootBundle.load('assets/fonts/NotoSans-Bold.ttf'));
  await noto.load();
  final icons = FontLoader('MaterialIcons')..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
  await icons.load();
}

/// Do'kon uchun: faqat asosiy joy, manba vaqtlari «hozir» (aks holda «4 oy oldin» ko'rinadi).
class _StoreEngine extends FakeEngine {
  _StoreEngine({super.settings}) {
    permission = 'granted';
  }

  static Snapshot _snap() {
    final j = fixture('snapshot.json');
    final now = DateTime.now().toUtc().toIso8601String();
    j['places'] = [(j['places'] as List<dynamic>).first];
    for (final s in j['sources'] as List<dynamic>) {
      (s as Map<String, dynamic>)
        ..['fetchedAt'] = now
        ..['ok'] = true
        ..['error'] = null
        ..['stale'] = false;
    }
    return Snapshot.fromJson(j);
  }

  @override
  Future<Snapshot?> snapshot() async => _snap();

  @override
  Future<Snapshot> refresh() async => _snap();
}

Future<AppState> _pump(WidgetTester tester, Settings settings) async {
  tester.view.physicalSize = const Size(1080, 2160);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final state = AppState(_StoreEngine(settings: settings));
  await tester.pumpWidget(RepaintBoundary(key: _root, child: HavoRadarApp(state: state)));
  await state.init();
  await tester.pumpAndSettle();
  return state;
}

Future<void> _shot(WidgetTester tester, String name) async {
  await tester.pumpAndSettle();
  final boundary = _root.currentContext!.findRenderObject()! as RenderRepaintBoundary;
  await tester.runAsync(() async {
    final image = await boundary.toImage(pixelRatio: 3);
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    Directory(_out).createSync(recursive: true);
    File('$_out/$name.png').writeAsBytesSync(data!.buffer.asUint8List());
  });
  debugPrint('STORE: $_out/$name.png');
}

Finder _scroll() => find.byWidgetPredicate((w) => w is Scrollable && w.axisDirection == AxisDirection.down).last;

/// Element ekran tepasiga keltiriladi (dangasa ro'yxatda avval aylantirib topiladi).
Future<void> _toTop(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(f, 200, scrollable: _scroll());
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

void main() {
  final settings = Settings.fromJson(fixture('settings.json')).copyWith(onboardingDone: true, extraPlaces: []);

  setUpAll(_loadFonts);

  testWidgets('play store skrinshotlari', (tester) async {
    await _pump(tester, settings);
    await _shot(tester, '01_radar');

    await _toTop(tester, find.text('Bugun'));
    await _shot(tester, '02_today');

    await tester.tap(find.text('Issiqlik'));
    await tester.pumpAndSettle();
    expect(find.text('Harorat (soatlik)'), findsOneWidget);
    await _toTop(tester, find.text('Issiqlik'));
    await _shot(tester, '03_reasons');
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Prognoz'));
    await tester.pumpAndSettle();
    await _shot(tester, '04_forecast');

    await tester.tap(find.text("Ma'lumotnoma"));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Issiq urishi'));
    await tester.pumpAndSettle();
    await _shot(tester, '05_first_aid');
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Radar'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Sozlamalar'));
    await tester.pumpAndSettle();
    await _toTop(tester, find.text('Sezgir guruhlar'));
    await _shot(tester, '06_profile');
  });

  testWidgets('onboarding skrinshoti', (tester) async {
    await _pump(tester, const Settings());
    await _shot(tester, '07_onboarding');
  });
}
