import 'dart:async';

import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/widget/widget_api.pigeon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

export 'package:baraka_daftari/core/widget/widget_api.pigeon.dart';

part 'widget_bridge.g.dart';

@Riverpod(keepAlive: true)
WidgetApi widgetApi(Ref ref) => WidgetApi();

/// Vidjet summalari ko'rinish muddatini Kotlin'ga uzatadi (SPEC 2B.1:
/// ilova qulfli bo'lsa vidjet summa ko'rsatmaydi). Platforma xatosi asosiy
/// oqimni to'xtatmaydi.
class WidgetVisibility {
  WidgetVisibility(this._api);

  final WidgetApi _api;

  void set(int epochMillis) => unawaited(
    _api.setVisibleUntil(epochMillis).catchError((Object _) {
      AppLog.event('widget_visibility_failed');
    }),
  );

  void locked() => set(0);

  /// Qulf ochildi, ilovaga qaytildi yoki fonga o'tdi: qulf vaqti tugaguncha
  /// ko'rinadi. «Cheksiz» holat atayin yo'q — jarayon kutilmaganda o'lsa
  /// ham summalar ko'pi bilan [lockTimeout] davomida ko'rinadi.
  void openFor(DateTime nowUtc, Duration lockTimeout) =>
      set(nowUtc.add(lockTimeout).millisecondsSinceEpoch);
}

@Riverpod(keepAlive: true)
WidgetVisibility widgetVisibility(Ref ref) =>
    WidgetVisibility(ref.watch(widgetApiProvider));
