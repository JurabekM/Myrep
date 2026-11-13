/// JSON'ga o'xshash qiymatning o'zgarmas chuqur nusxasi (Map/List ichma-ich).
Object? deepFreeze(Object? v) => switch (v) {
  final Map<Object?, Object?> m => Map<String, Object?>.unmodifiable({
    for (final e in m.entries) e.key.toString(): deepFreeze(e.value),
  }),
  final List<Object?> l => List<Object?>.unmodifiable(l.map(deepFreeze)),
  _ => v,
};

Map<String, Object?> freezeMap(Map<String, Object?> m) => deepFreeze(m)! as Map<String, Object?>;
