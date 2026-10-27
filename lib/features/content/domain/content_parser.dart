import 'dart:convert';

import 'package:baraka_daftari/features/content/domain/content.dart';

/// `assets/content/chapters.json` ni o'qiydi va tekshiradi. Sxema:
/// `docs/content_schema.json`.
///
/// Qoida: hech qachon istisno tashlamaydi. Buzuq bob o'tkazib yuboriladi
/// va sababi [ContentLoadResult.errors] ga yoziladi; butun fayl buzuq
/// bo'lsa — bo'sh natija.
abstract final class ContentParser {
  static const supportedSchemaVersion = 1;
  static final _id = RegExp(r'^[a-z0-9]+$');
  static final _taskId = RegExp(r'^[a-z0-9]+\.t[1-3]$');

  static ContentLoadResult parse(String source) {
    final Object? root;
    try {
      root = jsonDecode(source);
    } on FormatException catch (e) {
      return ContentLoadResult(
        chapters: const [],
        errors: ['json: ${e.message}'],
      );
    }
    if (root is! Map<String, dynamic>) {
      return const ContentLoadResult(
        chapters: [],
        errors: ['root: obyekt emas'],
      );
    }
    final version = root['schemaVersion'];
    if (version != supportedSchemaVersion) {
      return ContentLoadResult(
        chapters: const [],
        errors: ["schemaVersion: $version qo'llanmaydi"],
      );
    }
    final list = root['chapters'];
    if (list is! List) {
      return const ContentLoadResult(
        chapters: [],
        errors: ["chapters: ro'yxat emas"],
      );
    }

    final errors = <String>[];
    final chapters = <Chapter>[];
    final ids = <String>{};
    final orders = <int>{};
    final taskIds = <String>{};
    for (final (i, raw) in list.indexed) {
      try {
        final c = _chapter(raw);
        if (!ids.add(c.id)) throw FormatException('id takrorlangan: ${c.id}');
        if (!orders.add(c.order)) {
          throw FormatException('order takrorlangan: ${c.order}');
        }
        for (final t in c.weeklyTasks) {
          if (!taskIds.add(t.id)) {
            throw FormatException('vazifa id takrorlangan: ${t.id}');
          }
        }
        chapters.add(c);
      } on FormatException catch (e) {
        errors.add('chapters[$i]: ${e.message}');
      } on Object catch (e) {
        errors.add('chapters[$i]: ${e.runtimeType}');
      }
    }
    chapters.sort((a, b) => a.order.compareTo(b.order));
    return ContentLoadResult(chapters: chapters, errors: errors);
  }

  static Chapter _chapter(Object? raw) {
    final m = _map(raw, 'bob');
    final id = _string(m, 'id');
    if (!_id.hasMatch(id)) throw FormatException("id noto'g'ri: $id");
    final order = _int(m, 'order');
    if (order < 1) throw const FormatException("order ≥ 1 bo'lishi kerak");
    final blocks = _list(m, 'blocks').map(_block).toList();
    if (blocks.isEmpty) throw const FormatException("blocks bo'sh");
    final tasks = _list(m, 'weeklyTasks').map(_task).toList();
    if (tasks.length != 3) {
      throw FormatException(
        "weeklyTasks aniq 3 ta bo'lishi kerak: ${tasks.length}",
      );
    }
    for (final t in tasks) {
      if (!t.id.startsWith('$id.')) {
        throw FormatException(
          'vazifa id bob id bilan boshlanishi kerak: ${t.id}',
        );
      }
    }
    final audio = m['audioUrl'];
    if (audio != null &&
        (audio is! String ||
            !(Uri.tryParse(audio)?.isScheme('https') ?? false))) {
      throw const FormatException("audioUrl https bo'lishi kerak");
    }
    final lawMap = _map(m['law'], 'law');
    return Chapter(
      id: id,
      order: order,
      title: _text(m['title'], 'title'),
      blocks: blocks,
      law: Law(
        number: _int(lawMap, 'number'),
        text: _text(lawMap['text'], 'law.text'),
      ),
      weeklyTasks: tasks,
      audioUrl: audio as String?,
    );
  }

  static ContentBlock _block(Object? raw) {
    final m = _map(raw, 'blok');
    return switch (m['type']) {
      'paragraph' => ParagraphBlock(_text(m['text'], 'paragraph.text')),
      'quote' => QuoteBlock(_text(m['text'], 'quote.text')),
      'religious' => ReligiousBlock(
        text: _text(m['text'], 'religious.text'),
        source: _text(m['source'], 'religious.source'),
        status: switch (m['religiousReviewStatus']) {
          'APPROVED' => ReligiousReviewStatus.approved,
          'PENDING' => ReligiousReviewStatus.pending,
          final other => throw FormatException(
            "religiousReviewStatus noto'g'ri: $other",
          ),
        },
      ),
      final other => throw FormatException("blok turi noma'lum: $other"),
    };
  }

  static WeeklyTask _task(Object? raw) {
    final m = _map(raw, 'vazifa');
    final id = _string(m, 'id');
    if (!_taskId.hasMatch(id)) {
      throw FormatException("vazifa id noto'g'ri: $id");
    }
    final trigger = m['autoComplete'];
    return WeeklyTask(
      id: id,
      text: _text(m['text'], 'task.text'),
      trigger: switch (trigger) {
        null => null,
        final String code when TaskTrigger.fromCode(code) != null =>
          TaskTrigger.fromCode(code),
        final other => throw FormatException("autoComplete noma'lum: $other"),
      },
    );
  }

  static LocalizedText _text(Object? raw, String field) {
    final m = _map(raw, field);
    final values = <String, String>{};
    for (final MapEntry(:key, :value) in m.entries) {
      if (key != 'uz' && key != 'ru') {
        throw FormatException("$field: til noma'lum: $key");
      }
      if (value is! String || value.trim().isEmpty) {
        throw FormatException("$field.$key: bo'sh");
      }
      values[key] = value;
    }
    if (!values.containsKey('uz')) throw FormatException('$field: uz majburiy');
    return LocalizedText(values);
  }

  static Map<String, dynamic> _map(Object? raw, String field) {
    if (raw is Map<String, dynamic>) return raw;
    throw FormatException('$field: obyekt emas');
  }

  static List<Object?> _list(Map<String, dynamic> m, String key) {
    final v = m[key];
    if (v is List) return v;
    throw FormatException("$key: ro'yxat emas");
  }

  static String _string(Map<String, dynamic> m, String key) {
    final v = m[key];
    if (v is String && v.isNotEmpty) return v;
    throw FormatException('$key: matn emas');
  }

  static int _int(Map<String, dynamic> m, String key) {
    final v = m[key];
    if (v is int) return v;
    throw FormatException('$key: butun son emas');
  }
}
