import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core.dart';

/// So'rov kaliti (desktop'dagi TanStack Query `keys.*` kabi): `parts` so'rovni noyob belgilaydi,
/// `run` — yadroni chaqiradi.
class QueryKey {
  QueryKey(this.parts, this.run);

  final List<Object?> parts;
  final Future<Object?> Function(BarakaCore core) run;

  @override
  bool operator ==(Object other) => other is QueryKey && _listEq(other.parts, parts);

  @override
  int get hashCode => Object.hashAll(parts);

  static bool _listEq(List<Object?> a, List<Object?> b) {
    if (a.length != b.length) return false;
    for (var i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }
}

/// Yadrodan o'qish. Yadrodagi har bir o'zgarishda (`changeTickProvider`) qayta o'qiladi;
/// ekran yopilganda (va qulflanganda) kesh tozalanadi. `riverpod_generator` ishlatilmaydi —
/// ADR-0002 (Android).
final AutoDisposeFutureProviderFamily<Object?, QueryKey> coreQueryProvider = FutureProvider.autoDispose
    .family<Object?, QueryKey>((ref, key) {
      ref.watch(changeTickProvider);
      return key.run(ref.watch(coreProvider));
    });

/// Tipli so'rov: `ref.watch(query(['vault', id], (c) => c.vault(spaceId: id)))`.
ProviderListenable<AsyncValue<T>> query<T>(List<Object?> key, Future<T> Function(BarakaCore core) run) =>
    coreQueryProvider(QueryKey(key, run)).select((v) => v.whenData((d) => d as T));
