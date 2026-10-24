import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:drift/drift.dart';

/// Lokal sana bazada `YYYY-MM-DD` matni sifatida.
class LocalDateConverter extends TypeConverter<LocalDate, String> {
  const LocalDateConverter();

  @override
  LocalDate fromSql(String fromDb) => LocalDate.parse(fromDb);

  @override
  String toSql(LocalDate value) => value.toString();
}
