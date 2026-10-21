import 'dart:io';
import 'dart:math';

import 'package:baraka/app/app.dart';
import 'package:baraka/app/i18n.dart';
import 'package:baraka/bindings/frb_generated.dart';
import 'package:baraka/core/core.dart';
import 'package:baraka/core/platform.dart';
import 'package:baraka/core/prefs.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_rust_bridge/flutter_rust_bridge_for_generated.dart';
import 'package:flutter_test/flutter_test.dart';

/// Host'da yig'ilgan yadro (`cargo build -p baraka-bindings-flutter`): widget testlar haqiqiy
/// Rust yadro bilan ishlaydi — desktop E2E kabi, faqat emulyatorsiz.
String get coreLibPath => Platform.environment['BARAKA_CORE_LIB'] ?? '../../target/debug/libbaraka_bindings_flutter.so';

bool _rustReady = false;

Future<void> initRust() async {
  // Ekranda bo'lmagan elementni «bosish» — test xatosi.
  WidgetController.hitTestWarningShouldBeFatal = true;
  if (_rustReady) return;
  await RustLib.init(externalLibrary: ExternalLibrary.open(coreLibPath));
  _rustReady = true;
}

/// Ilova ichidagi shriftlar (skrinshotlar uchun; aks holda test shrifti — to'rtburchaklar).
Future<void> loadFonts() async {
  for (final (family, files) in [
    ('NotoSans', ['NotoSans-Regular.ttf', 'NotoSans-Bold.ttf']),
    ('NotoSerif', ['NotoSerif-Regular.ttf', 'NotoSerif-Bold.ttf']),
  ]) {
    final loader = FontLoader(family);
    for (final f in files) {
      loader.addFont(Future.value(ByteData.sublistView(File('../../shared/fonts/$f').readAsBytesSync())));
    }
    await loader.load();
  }
  await (FontLoader('MaterialIcons')..addFont(
        Future.value(
          ByteData.sublistView(
            File(
              '${Platform.environment['FLUTTER_ROOT'] ?? '/opt/flutter-sdk/flutter'}/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf',
            ).readAsBytesSync(),
          ),
        ),
      ))
      .load();
}

class MemorySecret implements SecretSource {
  Uint8List? _secret;

  @override
  Future<Uint8List> create() async =>
      _secret ??= Uint8List.fromList(List.generate(32, (_) => Random.secure().nextInt(256)));

  @override
  Future<Uint8List> load() async => _secret ?? (throw PlatformException(code: 'PLATFORM_SECRET_MISSING'));
}

class NoopWindow implements SecureWindow {
  @override
  Future<void> setSecure({required bool secure}) async {}
}

/// Bitta "qurilma": vaqtinchalik papka, xotiradagi platforma siri va yadro.
class Device {
  Device._(this.dir, this.services);

  static Future<Device> create([String? dir]) async {
    await initRust();
    final d = dir ?? Directory.systemTemp.createTempSync('baraka-android-').path;
    final core = await BarakaCore.newInstance(dataDir: d);
    return Device._(d, CoreServices(core: core, secrets: MemorySecret(), window: NoopWindow(), prefs: PrefsStore(d)));
  }

  final String dir;
  final CoreServices services;
  ProviderContainer? _container;

  ProviderContainer get container => _container ??= ProviderContainer(
    overrides: [
      servicesProvider.overrideWithValue(services),
      localeProvider.overrideWith((ref) => services.prefs.read().locale ?? 'uz'),
    ],
  );

  Widget app() => UncontrolledProviderScope(container: container, child: const BarakaApp());

  BarakaCore get core => services.core;

  /// Onboarding'siz tayyor xonadon (ochiq sessiya): `spaces` — `UY`, `KASBKOR`, `MUSOFIR`.
  Future<SetupResult> bootstrap({List<String> spaces = const ['UY'], String name = 'Anvar'}) async {
    final r = await container.read(sessionActionsProvider).setup(
      '135790',
      BootstrapInput(
        householdName: '$name oilasi',
        deviceName: 'Telefon',
        platform: 'android',
        locale: 'uz',
        baseCurrency: 'UZS',
        monthStartDay: 1,
        spaces: spaces,
        members: [NewMemberInput(displayName: name, role: 'ADULT')],
        incomeRhythm: 'MONTHLY',
        debtsDeclared: false,
      ),
    );
    container.read(sessionActionsProvider).finishSetup();
    return r;
  }

  String spaceId(SetupResult r, String kind) => r.household.spaces.firstWhere((s) => s.kind == kind).id;
}

/// Telefon ekrani (o'rta segment): 411×891 dp.
void phone(WidgetTester tester) {
  tester.view
    ..physicalSize = const Size(1080, 2340)
    ..devicePixelRatio = 2.625;
  addTearDown(tester.view.reset);
}

/// FFI chaqiruvlari haqiqiy oqimlarda bajariladi: vaqt soxta bo'lgani uchun `runAsync` bilan kutiladi.
Future<void> settle(WidgetTester tester, {int rounds = 30}) async {
  for (var i = 0; i < rounds; i++) {
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 15)));
    await tester.pump(const Duration(milliseconds: 16));
  }
}

/// Matn paydo bo'lguncha kutadi (yadro javobi).
Future<void> waitFor(WidgetTester tester, Finder finder, {int rounds = 200}) async {
  for (var i = 0; i < rounds; i++) {
    if (finder.evaluate().isNotEmpty) return;
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 20)));
    await tester.pump(const Duration(milliseconds: 16));
  }
  throw TestFailure('kutilgan element chiqmadi: $finder');
}

Future<void> tapText(WidgetTester tester, String text) async {
  // Oyna/sheet animatsiyalari tugasin (aks holda element hali ekrandan tashqarida).
  await tester.pump(const Duration(milliseconds: 400));
  final f = find.text(text);
  await tester.ensureVisible(f.last);
  await tester.tap(f.last);
  await settle(tester, rounds: 4);
}

/// Yorliq bo'yicha matn maydoniga yozish.
Future<void> enter(WidgetTester tester, String label, String value) async {
  await tester.pump(const Duration(milliseconds: 400));
  final f = find.widgetWithText(TextField, label);
  await tester.ensureVisible(f.first);
  await tester.enterText(f.first, value);
  await tester.pump();
}

/// Skrinshot (`docs/screenshots/android-*.png`) — haqiqiy shriftlar bilan. Faqat
/// `BARAKA_SHOTS=1 flutter test --update-goldens` da yoziladi (piksel taqqoslash CI'da emas).
Future<void> shot(WidgetTester tester, String name) async {
  if (Platform.environment['BARAKA_SHOTS'] != '1') return;
  // Animatsiyalar (yorliq, tugma holati) tugasin.
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
  await expectLater(find.byType(MaterialApp), matchesGoldenFile('../../../docs/screenshots/$name.png'));
}
