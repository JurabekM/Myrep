// Tushmagan testni tahlil qilish uchun: ekrandagi matnlar va maydonlar qiymati.
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

void dumpTexts(WidgetTester tester) {
  final texts = tester.widgetList<Text>(find.byType(Text)).map((t) => t.data ?? t.textSpan?.toPlainText()).toList();
  debugPrint('TEXTS: $texts');
  final fields = tester.widgetList<EditableText>(find.byType(EditableText)).map((e) => e.controller.text).toList();
  debugPrint('FIELDS: $fields');
}
