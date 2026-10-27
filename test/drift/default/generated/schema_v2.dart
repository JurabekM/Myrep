// dart format width=80
// GENERATED CODE, DO NOT EDIT BY HAND.
// ignore_for_file: type=lint
import 'package:drift/drift.dart';

class Households extends Table with TableInfo<Households, HouseholdsData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  Households(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<String> baseCurrency = GeneratedColumn<String>(
    'base_currency',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('\'uzs\''),
  );
  late final GeneratedColumn<int> weekAnchor = GeneratedColumn<int>(
    'week_anchor',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('5'),
  );
  late final GeneratedColumn<int> monthStartDay = GeneratedColumn<int>(
    'month_start_day',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    name,
    baseCurrency,
    weekAnchor,
    monthStartDay,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'households';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  HouseholdsData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return HouseholdsData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      name: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}name'],
      ),
      baseCurrency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}base_currency'],
      )!,
      weekAnchor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}week_anchor'],
      )!,
      monthStartDay: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}month_start_day'],
      )!,
    );
  }

  @override
  Households createAlias(String alias) {
    return Households(attachedDatabase, alias);
  }
}

class HouseholdsData extends DataClass implements Insertable<HouseholdsData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final String? name;
  final String baseCurrency;
  final int weekAnchor;
  final int monthStartDay;
  const HouseholdsData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    this.name,
    required this.baseCurrency,
    required this.weekAnchor,
    required this.monthStartDay,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    if (!nullToAbsent || name != null) {
      map['name'] = Variable<String>(name);
    }
    map['base_currency'] = Variable<String>(baseCurrency);
    map['week_anchor'] = Variable<int>(weekAnchor);
    map['month_start_day'] = Variable<int>(monthStartDay);
    return map;
  }

  HouseholdsCompanion toCompanion(bool nullToAbsent) {
    return HouseholdsCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      name: name == null && nullToAbsent ? const Value.absent() : Value(name),
      baseCurrency: Value(baseCurrency),
      weekAnchor: Value(weekAnchor),
      monthStartDay: Value(monthStartDay),
    );
  }

  factory HouseholdsData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return HouseholdsData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      name: serializer.fromJson<String?>(json['name']),
      baseCurrency: serializer.fromJson<String>(json['baseCurrency']),
      weekAnchor: serializer.fromJson<int>(json['weekAnchor']),
      monthStartDay: serializer.fromJson<int>(json['monthStartDay']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'name': serializer.toJson<String?>(name),
      'baseCurrency': serializer.toJson<String>(baseCurrency),
      'weekAnchor': serializer.toJson<int>(weekAnchor),
      'monthStartDay': serializer.toJson<int>(monthStartDay),
    };
  }

  HouseholdsData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    Value<String?> name = const Value.absent(),
    String? baseCurrency,
    int? weekAnchor,
    int? monthStartDay,
  }) => HouseholdsData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    name: name.present ? name.value : this.name,
    baseCurrency: baseCurrency ?? this.baseCurrency,
    weekAnchor: weekAnchor ?? this.weekAnchor,
    monthStartDay: monthStartDay ?? this.monthStartDay,
  );
  HouseholdsData copyWithCompanion(HouseholdsCompanion data) {
    return HouseholdsData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      name: data.name.present ? data.name.value : this.name,
      baseCurrency: data.baseCurrency.present
          ? data.baseCurrency.value
          : this.baseCurrency,
      weekAnchor: data.weekAnchor.present
          ? data.weekAnchor.value
          : this.weekAnchor,
      monthStartDay: data.monthStartDay.present
          ? data.monthStartDay.value
          : this.monthStartDay,
    );
  }

  @override
  String toString() {
    return (StringBuffer('HouseholdsData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('name: $name, ')
          ..write('baseCurrency: $baseCurrency, ')
          ..write('weekAnchor: $weekAnchor, ')
          ..write('monthStartDay: $monthStartDay')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    name,
    baseCurrency,
    weekAnchor,
    monthStartDay,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is HouseholdsData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.name == this.name &&
          other.baseCurrency == this.baseCurrency &&
          other.weekAnchor == this.weekAnchor &&
          other.monthStartDay == this.monthStartDay);
}

class HouseholdsCompanion extends UpdateCompanion<HouseholdsData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<String?> name;
  final Value<String> baseCurrency;
  final Value<int> weekAnchor;
  final Value<int> monthStartDay;
  final Value<int> rowid;
  const HouseholdsCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.name = const Value.absent(),
    this.baseCurrency = const Value.absent(),
    this.weekAnchor = const Value.absent(),
    this.monthStartDay = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  HouseholdsCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.name = const Value.absent(),
    this.baseCurrency = const Value.absent(),
    this.weekAnchor = const Value.absent(),
    this.monthStartDay = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt);
  static Insertable<HouseholdsData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<String>? name,
    Expression<String>? baseCurrency,
    Expression<int>? weekAnchor,
    Expression<int>? monthStartDay,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (name != null) 'name': name,
      if (baseCurrency != null) 'base_currency': baseCurrency,
      if (weekAnchor != null) 'week_anchor': weekAnchor,
      if (monthStartDay != null) 'month_start_day': monthStartDay,
      if (rowid != null) 'rowid': rowid,
    });
  }

  HouseholdsCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<String?>? name,
    Value<String>? baseCurrency,
    Value<int>? weekAnchor,
    Value<int>? monthStartDay,
    Value<int>? rowid,
  }) {
    return HouseholdsCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      name: name ?? this.name,
      baseCurrency: baseCurrency ?? this.baseCurrency,
      weekAnchor: weekAnchor ?? this.weekAnchor,
      monthStartDay: monthStartDay ?? this.monthStartDay,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (baseCurrency.present) {
      map['base_currency'] = Variable<String>(baseCurrency.value);
    }
    if (weekAnchor.present) {
      map['week_anchor'] = Variable<int>(weekAnchor.value);
    }
    if (monthStartDay.present) {
      map['month_start_day'] = Variable<int>(monthStartDay.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('HouseholdsCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('name: $name, ')
          ..write('baseCurrency: $baseCurrency, ')
          ..write('weekAnchor: $weekAnchor, ')
          ..write('monthStartDay: $monthStartDay, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class Members extends Table with TableInfo<Members, MembersData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  Members(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<String> displayName = GeneratedColumn<String>(
    'display_name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> role = GeneratedColumn<String>(
    'role',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<bool> isOwner = GeneratedColumn<bool>(
    'is_owner',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_owner" IN (0, 1))',
    ),
    defaultValue: const CustomExpression('0'),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    displayName,
    role,
    isOwner,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'members';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  MembersData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MembersData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      displayName: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}display_name'],
      )!,
      role: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}role'],
      )!,
      isOwner: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_owner'],
      )!,
    );
  }

  @override
  Members createAlias(String alias) {
    return Members(attachedDatabase, alias);
  }
}

class MembersData extends DataClass implements Insertable<MembersData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final String displayName;
  final String role;
  final bool isOwner;
  const MembersData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    required this.displayName,
    required this.role,
    required this.isOwner,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    map['display_name'] = Variable<String>(displayName);
    map['role'] = Variable<String>(role);
    map['is_owner'] = Variable<bool>(isOwner);
    return map;
  }

  MembersCompanion toCompanion(bool nullToAbsent) {
    return MembersCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      displayName: Value(displayName),
      role: Value(role),
      isOwner: Value(isOwner),
    );
  }

  factory MembersData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MembersData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      displayName: serializer.fromJson<String>(json['displayName']),
      role: serializer.fromJson<String>(json['role']),
      isOwner: serializer.fromJson<bool>(json['isOwner']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'displayName': serializer.toJson<String>(displayName),
      'role': serializer.toJson<String>(role),
      'isOwner': serializer.toJson<bool>(isOwner),
    };
  }

  MembersData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    String? displayName,
    String? role,
    bool? isOwner,
  }) => MembersData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    displayName: displayName ?? this.displayName,
    role: role ?? this.role,
    isOwner: isOwner ?? this.isOwner,
  );
  MembersData copyWithCompanion(MembersCompanion data) {
    return MembersData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      displayName: data.displayName.present
          ? data.displayName.value
          : this.displayName,
      role: data.role.present ? data.role.value : this.role,
      isOwner: data.isOwner.present ? data.isOwner.value : this.isOwner,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MembersData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('displayName: $displayName, ')
          ..write('role: $role, ')
          ..write('isOwner: $isOwner')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    displayName,
    role,
    isOwner,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MembersData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.displayName == this.displayName &&
          other.role == this.role &&
          other.isOwner == this.isOwner);
}

class MembersCompanion extends UpdateCompanion<MembersData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<String> displayName;
  final Value<String> role;
  final Value<bool> isOwner;
  final Value<int> rowid;
  const MembersCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.displayName = const Value.absent(),
    this.role = const Value.absent(),
    this.isOwner = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  MembersCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    required String displayName,
    required String role,
    this.isOwner = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       displayName = Value(displayName),
       role = Value(role);
  static Insertable<MembersData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<String>? displayName,
    Expression<String>? role,
    Expression<bool>? isOwner,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (displayName != null) 'display_name': displayName,
      if (role != null) 'role': role,
      if (isOwner != null) 'is_owner': isOwner,
      if (rowid != null) 'rowid': rowid,
    });
  }

  MembersCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<String>? displayName,
    Value<String>? role,
    Value<bool>? isOwner,
    Value<int>? rowid,
  }) {
    return MembersCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      displayName: displayName ?? this.displayName,
      role: role ?? this.role,
      isOwner: isOwner ?? this.isOwner,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (displayName.present) {
      map['display_name'] = Variable<String>(displayName.value);
    }
    if (role.present) {
      map['role'] = Variable<String>(role.value);
    }
    if (isOwner.present) {
      map['is_owner'] = Variable<bool>(isOwner.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('MembersCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('displayName: $displayName, ')
          ..write('role: $role, ')
          ..write('isOwner: $isOwner, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class Categories extends Table with TableInfo<Categories, CategoriesData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  Categories(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<String> systemKey = GeneratedColumn<String>(
    'system_key',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<String> defaultNecessity = GeneratedColumn<String>(
    'default_necessity',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> sortOrder = GeneratedColumn<int>(
    'sort_order',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('0'),
  );
  late final GeneratedColumn<bool> isArchived = GeneratedColumn<bool>(
    'is_archived',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_archived" IN (0, 1))',
    ),
    defaultValue: const CustomExpression('0'),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    systemKey,
    name,
    defaultNecessity,
    sortOrder,
    isArchived,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'categories';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  CategoriesData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CategoriesData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      systemKey: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}system_key'],
      ),
      name: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}name'],
      ),
      defaultNecessity: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}default_necessity'],
      ),
      sortOrder: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}sort_order'],
      )!,
      isArchived: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_archived'],
      )!,
    );
  }

  @override
  Categories createAlias(String alias) {
    return Categories(attachedDatabase, alias);
  }

  @override
  List<String> get customConstraints => const [
    'CHECK (system_key IS NOT NULL OR name IS NOT NULL)',
  ];
}

class CategoriesData extends DataClass implements Insertable<CategoriesData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final String? systemKey;
  final String? name;
  final String? defaultNecessity;
  final int sortOrder;
  final bool isArchived;
  const CategoriesData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    this.systemKey,
    this.name,
    this.defaultNecessity,
    required this.sortOrder,
    required this.isArchived,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    if (!nullToAbsent || systemKey != null) {
      map['system_key'] = Variable<String>(systemKey);
    }
    if (!nullToAbsent || name != null) {
      map['name'] = Variable<String>(name);
    }
    if (!nullToAbsent || defaultNecessity != null) {
      map['default_necessity'] = Variable<String>(defaultNecessity);
    }
    map['sort_order'] = Variable<int>(sortOrder);
    map['is_archived'] = Variable<bool>(isArchived);
    return map;
  }

  CategoriesCompanion toCompanion(bool nullToAbsent) {
    return CategoriesCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      systemKey: systemKey == null && nullToAbsent
          ? const Value.absent()
          : Value(systemKey),
      name: name == null && nullToAbsent ? const Value.absent() : Value(name),
      defaultNecessity: defaultNecessity == null && nullToAbsent
          ? const Value.absent()
          : Value(defaultNecessity),
      sortOrder: Value(sortOrder),
      isArchived: Value(isArchived),
    );
  }

  factory CategoriesData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CategoriesData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      systemKey: serializer.fromJson<String?>(json['systemKey']),
      name: serializer.fromJson<String?>(json['name']),
      defaultNecessity: serializer.fromJson<String?>(json['defaultNecessity']),
      sortOrder: serializer.fromJson<int>(json['sortOrder']),
      isArchived: serializer.fromJson<bool>(json['isArchived']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'systemKey': serializer.toJson<String?>(systemKey),
      'name': serializer.toJson<String?>(name),
      'defaultNecessity': serializer.toJson<String?>(defaultNecessity),
      'sortOrder': serializer.toJson<int>(sortOrder),
      'isArchived': serializer.toJson<bool>(isArchived),
    };
  }

  CategoriesData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    Value<String?> systemKey = const Value.absent(),
    Value<String?> name = const Value.absent(),
    Value<String?> defaultNecessity = const Value.absent(),
    int? sortOrder,
    bool? isArchived,
  }) => CategoriesData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    systemKey: systemKey.present ? systemKey.value : this.systemKey,
    name: name.present ? name.value : this.name,
    defaultNecessity: defaultNecessity.present
        ? defaultNecessity.value
        : this.defaultNecessity,
    sortOrder: sortOrder ?? this.sortOrder,
    isArchived: isArchived ?? this.isArchived,
  );
  CategoriesData copyWithCompanion(CategoriesCompanion data) {
    return CategoriesData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      systemKey: data.systemKey.present ? data.systemKey.value : this.systemKey,
      name: data.name.present ? data.name.value : this.name,
      defaultNecessity: data.defaultNecessity.present
          ? data.defaultNecessity.value
          : this.defaultNecessity,
      sortOrder: data.sortOrder.present ? data.sortOrder.value : this.sortOrder,
      isArchived: data.isArchived.present
          ? data.isArchived.value
          : this.isArchived,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CategoriesData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('systemKey: $systemKey, ')
          ..write('name: $name, ')
          ..write('defaultNecessity: $defaultNecessity, ')
          ..write('sortOrder: $sortOrder, ')
          ..write('isArchived: $isArchived')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    systemKey,
    name,
    defaultNecessity,
    sortOrder,
    isArchived,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CategoriesData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.systemKey == this.systemKey &&
          other.name == this.name &&
          other.defaultNecessity == this.defaultNecessity &&
          other.sortOrder == this.sortOrder &&
          other.isArchived == this.isArchived);
}

class CategoriesCompanion extends UpdateCompanion<CategoriesData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<String?> systemKey;
  final Value<String?> name;
  final Value<String?> defaultNecessity;
  final Value<int> sortOrder;
  final Value<bool> isArchived;
  final Value<int> rowid;
  const CategoriesCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.systemKey = const Value.absent(),
    this.name = const Value.absent(),
    this.defaultNecessity = const Value.absent(),
    this.sortOrder = const Value.absent(),
    this.isArchived = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CategoriesCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.systemKey = const Value.absent(),
    this.name = const Value.absent(),
    this.defaultNecessity = const Value.absent(),
    this.sortOrder = const Value.absent(),
    this.isArchived = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt);
  static Insertable<CategoriesData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<String>? systemKey,
    Expression<String>? name,
    Expression<String>? defaultNecessity,
    Expression<int>? sortOrder,
    Expression<bool>? isArchived,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (systemKey != null) 'system_key': systemKey,
      if (name != null) 'name': name,
      if (defaultNecessity != null) 'default_necessity': defaultNecessity,
      if (sortOrder != null) 'sort_order': sortOrder,
      if (isArchived != null) 'is_archived': isArchived,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CategoriesCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<String?>? systemKey,
    Value<String?>? name,
    Value<String?>? defaultNecessity,
    Value<int>? sortOrder,
    Value<bool>? isArchived,
    Value<int>? rowid,
  }) {
    return CategoriesCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      systemKey: systemKey ?? this.systemKey,
      name: name ?? this.name,
      defaultNecessity: defaultNecessity ?? this.defaultNecessity,
      sortOrder: sortOrder ?? this.sortOrder,
      isArchived: isArchived ?? this.isArchived,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (systemKey.present) {
      map['system_key'] = Variable<String>(systemKey.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (defaultNecessity.present) {
      map['default_necessity'] = Variable<String>(defaultNecessity.value);
    }
    if (sortOrder.present) {
      map['sort_order'] = Variable<int>(sortOrder.value);
    }
    if (isArchived.present) {
      map['is_archived'] = Variable<bool>(isArchived.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CategoriesCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('systemKey: $systemKey, ')
          ..write('name: $name, ')
          ..write('defaultNecessity: $defaultNecessity, ')
          ..write('sortOrder: $sortOrder, ')
          ..write('isArchived: $isArchived, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class Incomes extends Table with TableInfo<Incomes, IncomesData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  Incomes(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<int> amountMinor = GeneratedColumn<int>(
    'amount_minor',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> currency = GeneratedColumn<String>(
    'currency',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> source = GeneratedColumn<String>(
    'source',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> channel = GeneratedColumn<String>(
    'channel',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> memberId = GeneratedColumn<String>(
    'member_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES members (id)',
    ),
  );
  late final GeneratedColumn<String> sourceType = GeneratedColumn<String>(
    'source_type',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<DateTime> receivedAt = GeneratedColumn<DateTime>(
    'received_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> note = GeneratedColumn<String>(
    'note',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    amountMinor,
    currency,
    source,
    channel,
    memberId,
    sourceType,
    receivedAt,
    note,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'incomes';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  IncomesData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return IncomesData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      amountMinor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}amount_minor'],
      )!,
      currency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}currency'],
      )!,
      source: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source'],
      )!,
      channel: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}channel'],
      )!,
      memberId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}member_id'],
      ),
      sourceType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source_type'],
      ),
      receivedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}received_at'],
      )!,
      note: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}note'],
      ),
    );
  }

  @override
  Incomes createAlias(String alias) {
    return Incomes(attachedDatabase, alias);
  }

  @override
  List<String> get customConstraints => const ['CHECK (amount_minor > 0)'];
}

class IncomesData extends DataClass implements Insertable<IncomesData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final int amountMinor;
  final String currency;
  final String source;
  final String channel;
  final String? memberId;
  final String? sourceType;
  final DateTime receivedAt;
  final String? note;
  const IncomesData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    required this.amountMinor,
    required this.currency,
    required this.source,
    required this.channel,
    this.memberId,
    this.sourceType,
    required this.receivedAt,
    this.note,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    map['amount_minor'] = Variable<int>(amountMinor);
    map['currency'] = Variable<String>(currency);
    map['source'] = Variable<String>(source);
    map['channel'] = Variable<String>(channel);
    if (!nullToAbsent || memberId != null) {
      map['member_id'] = Variable<String>(memberId);
    }
    if (!nullToAbsent || sourceType != null) {
      map['source_type'] = Variable<String>(sourceType);
    }
    map['received_at'] = Variable<DateTime>(receivedAt);
    if (!nullToAbsent || note != null) {
      map['note'] = Variable<String>(note);
    }
    return map;
  }

  IncomesCompanion toCompanion(bool nullToAbsent) {
    return IncomesCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      amountMinor: Value(amountMinor),
      currency: Value(currency),
      source: Value(source),
      channel: Value(channel),
      memberId: memberId == null && nullToAbsent
          ? const Value.absent()
          : Value(memberId),
      sourceType: sourceType == null && nullToAbsent
          ? const Value.absent()
          : Value(sourceType),
      receivedAt: Value(receivedAt),
      note: note == null && nullToAbsent ? const Value.absent() : Value(note),
    );
  }

  factory IncomesData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return IncomesData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      amountMinor: serializer.fromJson<int>(json['amountMinor']),
      currency: serializer.fromJson<String>(json['currency']),
      source: serializer.fromJson<String>(json['source']),
      channel: serializer.fromJson<String>(json['channel']),
      memberId: serializer.fromJson<String?>(json['memberId']),
      sourceType: serializer.fromJson<String?>(json['sourceType']),
      receivedAt: serializer.fromJson<DateTime>(json['receivedAt']),
      note: serializer.fromJson<String?>(json['note']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'amountMinor': serializer.toJson<int>(amountMinor),
      'currency': serializer.toJson<String>(currency),
      'source': serializer.toJson<String>(source),
      'channel': serializer.toJson<String>(channel),
      'memberId': serializer.toJson<String?>(memberId),
      'sourceType': serializer.toJson<String?>(sourceType),
      'receivedAt': serializer.toJson<DateTime>(receivedAt),
      'note': serializer.toJson<String?>(note),
    };
  }

  IncomesData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    int? amountMinor,
    String? currency,
    String? source,
    String? channel,
    Value<String?> memberId = const Value.absent(),
    Value<String?> sourceType = const Value.absent(),
    DateTime? receivedAt,
    Value<String?> note = const Value.absent(),
  }) => IncomesData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    amountMinor: amountMinor ?? this.amountMinor,
    currency: currency ?? this.currency,
    source: source ?? this.source,
    channel: channel ?? this.channel,
    memberId: memberId.present ? memberId.value : this.memberId,
    sourceType: sourceType.present ? sourceType.value : this.sourceType,
    receivedAt: receivedAt ?? this.receivedAt,
    note: note.present ? note.value : this.note,
  );
  IncomesData copyWithCompanion(IncomesCompanion data) {
    return IncomesData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      amountMinor: data.amountMinor.present
          ? data.amountMinor.value
          : this.amountMinor,
      currency: data.currency.present ? data.currency.value : this.currency,
      source: data.source.present ? data.source.value : this.source,
      channel: data.channel.present ? data.channel.value : this.channel,
      memberId: data.memberId.present ? data.memberId.value : this.memberId,
      sourceType: data.sourceType.present
          ? data.sourceType.value
          : this.sourceType,
      receivedAt: data.receivedAt.present
          ? data.receivedAt.value
          : this.receivedAt,
      note: data.note.present ? data.note.value : this.note,
    );
  }

  @override
  String toString() {
    return (StringBuffer('IncomesData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('amountMinor: $amountMinor, ')
          ..write('currency: $currency, ')
          ..write('source: $source, ')
          ..write('channel: $channel, ')
          ..write('memberId: $memberId, ')
          ..write('sourceType: $sourceType, ')
          ..write('receivedAt: $receivedAt, ')
          ..write('note: $note')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    amountMinor,
    currency,
    source,
    channel,
    memberId,
    sourceType,
    receivedAt,
    note,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is IncomesData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.amountMinor == this.amountMinor &&
          other.currency == this.currency &&
          other.source == this.source &&
          other.channel == this.channel &&
          other.memberId == this.memberId &&
          other.sourceType == this.sourceType &&
          other.receivedAt == this.receivedAt &&
          other.note == this.note);
}

class IncomesCompanion extends UpdateCompanion<IncomesData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<int> amountMinor;
  final Value<String> currency;
  final Value<String> source;
  final Value<String> channel;
  final Value<String?> memberId;
  final Value<String?> sourceType;
  final Value<DateTime> receivedAt;
  final Value<String?> note;
  final Value<int> rowid;
  const IncomesCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.amountMinor = const Value.absent(),
    this.currency = const Value.absent(),
    this.source = const Value.absent(),
    this.channel = const Value.absent(),
    this.memberId = const Value.absent(),
    this.sourceType = const Value.absent(),
    this.receivedAt = const Value.absent(),
    this.note = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  IncomesCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    required int amountMinor,
    required String currency,
    required String source,
    required String channel,
    this.memberId = const Value.absent(),
    this.sourceType = const Value.absent(),
    required DateTime receivedAt,
    this.note = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       amountMinor = Value(amountMinor),
       currency = Value(currency),
       source = Value(source),
       channel = Value(channel),
       receivedAt = Value(receivedAt);
  static Insertable<IncomesData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<int>? amountMinor,
    Expression<String>? currency,
    Expression<String>? source,
    Expression<String>? channel,
    Expression<String>? memberId,
    Expression<String>? sourceType,
    Expression<DateTime>? receivedAt,
    Expression<String>? note,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (amountMinor != null) 'amount_minor': amountMinor,
      if (currency != null) 'currency': currency,
      if (source != null) 'source': source,
      if (channel != null) 'channel': channel,
      if (memberId != null) 'member_id': memberId,
      if (sourceType != null) 'source_type': sourceType,
      if (receivedAt != null) 'received_at': receivedAt,
      if (note != null) 'note': note,
      if (rowid != null) 'rowid': rowid,
    });
  }

  IncomesCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<int>? amountMinor,
    Value<String>? currency,
    Value<String>? source,
    Value<String>? channel,
    Value<String?>? memberId,
    Value<String?>? sourceType,
    Value<DateTime>? receivedAt,
    Value<String?>? note,
    Value<int>? rowid,
  }) {
    return IncomesCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      amountMinor: amountMinor ?? this.amountMinor,
      currency: currency ?? this.currency,
      source: source ?? this.source,
      channel: channel ?? this.channel,
      memberId: memberId ?? this.memberId,
      sourceType: sourceType ?? this.sourceType,
      receivedAt: receivedAt ?? this.receivedAt,
      note: note ?? this.note,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (amountMinor.present) {
      map['amount_minor'] = Variable<int>(amountMinor.value);
    }
    if (currency.present) {
      map['currency'] = Variable<String>(currency.value);
    }
    if (source.present) {
      map['source'] = Variable<String>(source.value);
    }
    if (channel.present) {
      map['channel'] = Variable<String>(channel.value);
    }
    if (memberId.present) {
      map['member_id'] = Variable<String>(memberId.value);
    }
    if (sourceType.present) {
      map['source_type'] = Variable<String>(sourceType.value);
    }
    if (receivedAt.present) {
      map['received_at'] = Variable<DateTime>(receivedAt.value);
    }
    if (note.present) {
      map['note'] = Variable<String>(note.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('IncomesCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('amountMinor: $amountMinor, ')
          ..write('currency: $currency, ')
          ..write('source: $source, ')
          ..write('channel: $channel, ')
          ..write('memberId: $memberId, ')
          ..write('sourceType: $sourceType, ')
          ..write('receivedAt: $receivedAt, ')
          ..write('note: $note, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class Expenses extends Table with TableInfo<Expenses, ExpensesData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  Expenses(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<int> amountMinor = GeneratedColumn<int>(
    'amount_minor',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> currency = GeneratedColumn<String>(
    'currency',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> categoryId = GeneratedColumn<String>(
    'category_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES categories (id)',
    ),
  );
  late final GeneratedColumn<String> channel = GeneratedColumn<String>(
    'channel',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> memberId = GeneratedColumn<String>(
    'member_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES members (id)',
    ),
  );
  late final GeneratedColumn<String> necessity = GeneratedColumn<String>(
    'necessity',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<String> envelopeId = GeneratedColumn<String>(
    'envelope_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<bool> isGift = GeneratedColumn<bool>(
    'is_gift',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_gift" IN (0, 1))',
    ),
    defaultValue: const CustomExpression('0'),
  );
  late final GeneratedColumn<bool> isOstentation = GeneratedColumn<bool>(
    'is_ostentation',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_ostentation" IN (0, 1))',
    ),
    defaultValue: const CustomExpression('0'),
  );
  late final GeneratedColumn<bool> fundedByDebt = GeneratedColumn<bool>(
    'funded_by_debt',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("funded_by_debt" IN (0, 1))',
    ),
    defaultValue: const CustomExpression('0'),
  );
  late final GeneratedColumn<DateTime> spentAt = GeneratedColumn<DateTime>(
    'spent_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> note = GeneratedColumn<String>(
    'note',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    amountMinor,
    currency,
    categoryId,
    channel,
    memberId,
    necessity,
    envelopeId,
    isGift,
    isOstentation,
    fundedByDebt,
    spentAt,
    note,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'expenses';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  ExpensesData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ExpensesData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      amountMinor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}amount_minor'],
      )!,
      currency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}currency'],
      )!,
      categoryId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}category_id'],
      )!,
      channel: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}channel'],
      )!,
      memberId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}member_id'],
      ),
      necessity: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}necessity'],
      ),
      envelopeId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}envelope_id'],
      ),
      isGift: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_gift'],
      )!,
      isOstentation: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_ostentation'],
      )!,
      fundedByDebt: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}funded_by_debt'],
      )!,
      spentAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}spent_at'],
      )!,
      note: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}note'],
      ),
    );
  }

  @override
  Expenses createAlias(String alias) {
    return Expenses(attachedDatabase, alias);
  }

  @override
  List<String> get customConstraints => const ['CHECK (amount_minor > 0)'];
}

class ExpensesData extends DataClass implements Insertable<ExpensesData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final int amountMinor;
  final String currency;
  final String categoryId;
  final String channel;
  final String? memberId;
  final String? necessity;
  final String? envelopeId;
  final bool isGift;
  final bool isOstentation;
  final bool fundedByDebt;
  final DateTime spentAt;
  final String? note;
  const ExpensesData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    required this.amountMinor,
    required this.currency,
    required this.categoryId,
    required this.channel,
    this.memberId,
    this.necessity,
    this.envelopeId,
    required this.isGift,
    required this.isOstentation,
    required this.fundedByDebt,
    required this.spentAt,
    this.note,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    map['amount_minor'] = Variable<int>(amountMinor);
    map['currency'] = Variable<String>(currency);
    map['category_id'] = Variable<String>(categoryId);
    map['channel'] = Variable<String>(channel);
    if (!nullToAbsent || memberId != null) {
      map['member_id'] = Variable<String>(memberId);
    }
    if (!nullToAbsent || necessity != null) {
      map['necessity'] = Variable<String>(necessity);
    }
    if (!nullToAbsent || envelopeId != null) {
      map['envelope_id'] = Variable<String>(envelopeId);
    }
    map['is_gift'] = Variable<bool>(isGift);
    map['is_ostentation'] = Variable<bool>(isOstentation);
    map['funded_by_debt'] = Variable<bool>(fundedByDebt);
    map['spent_at'] = Variable<DateTime>(spentAt);
    if (!nullToAbsent || note != null) {
      map['note'] = Variable<String>(note);
    }
    return map;
  }

  ExpensesCompanion toCompanion(bool nullToAbsent) {
    return ExpensesCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      amountMinor: Value(amountMinor),
      currency: Value(currency),
      categoryId: Value(categoryId),
      channel: Value(channel),
      memberId: memberId == null && nullToAbsent
          ? const Value.absent()
          : Value(memberId),
      necessity: necessity == null && nullToAbsent
          ? const Value.absent()
          : Value(necessity),
      envelopeId: envelopeId == null && nullToAbsent
          ? const Value.absent()
          : Value(envelopeId),
      isGift: Value(isGift),
      isOstentation: Value(isOstentation),
      fundedByDebt: Value(fundedByDebt),
      spentAt: Value(spentAt),
      note: note == null && nullToAbsent ? const Value.absent() : Value(note),
    );
  }

  factory ExpensesData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ExpensesData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      amountMinor: serializer.fromJson<int>(json['amountMinor']),
      currency: serializer.fromJson<String>(json['currency']),
      categoryId: serializer.fromJson<String>(json['categoryId']),
      channel: serializer.fromJson<String>(json['channel']),
      memberId: serializer.fromJson<String?>(json['memberId']),
      necessity: serializer.fromJson<String?>(json['necessity']),
      envelopeId: serializer.fromJson<String?>(json['envelopeId']),
      isGift: serializer.fromJson<bool>(json['isGift']),
      isOstentation: serializer.fromJson<bool>(json['isOstentation']),
      fundedByDebt: serializer.fromJson<bool>(json['fundedByDebt']),
      spentAt: serializer.fromJson<DateTime>(json['spentAt']),
      note: serializer.fromJson<String?>(json['note']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'amountMinor': serializer.toJson<int>(amountMinor),
      'currency': serializer.toJson<String>(currency),
      'categoryId': serializer.toJson<String>(categoryId),
      'channel': serializer.toJson<String>(channel),
      'memberId': serializer.toJson<String?>(memberId),
      'necessity': serializer.toJson<String?>(necessity),
      'envelopeId': serializer.toJson<String?>(envelopeId),
      'isGift': serializer.toJson<bool>(isGift),
      'isOstentation': serializer.toJson<bool>(isOstentation),
      'fundedByDebt': serializer.toJson<bool>(fundedByDebt),
      'spentAt': serializer.toJson<DateTime>(spentAt),
      'note': serializer.toJson<String?>(note),
    };
  }

  ExpensesData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    int? amountMinor,
    String? currency,
    String? categoryId,
    String? channel,
    Value<String?> memberId = const Value.absent(),
    Value<String?> necessity = const Value.absent(),
    Value<String?> envelopeId = const Value.absent(),
    bool? isGift,
    bool? isOstentation,
    bool? fundedByDebt,
    DateTime? spentAt,
    Value<String?> note = const Value.absent(),
  }) => ExpensesData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    amountMinor: amountMinor ?? this.amountMinor,
    currency: currency ?? this.currency,
    categoryId: categoryId ?? this.categoryId,
    channel: channel ?? this.channel,
    memberId: memberId.present ? memberId.value : this.memberId,
    necessity: necessity.present ? necessity.value : this.necessity,
    envelopeId: envelopeId.present ? envelopeId.value : this.envelopeId,
    isGift: isGift ?? this.isGift,
    isOstentation: isOstentation ?? this.isOstentation,
    fundedByDebt: fundedByDebt ?? this.fundedByDebt,
    spentAt: spentAt ?? this.spentAt,
    note: note.present ? note.value : this.note,
  );
  ExpensesData copyWithCompanion(ExpensesCompanion data) {
    return ExpensesData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      amountMinor: data.amountMinor.present
          ? data.amountMinor.value
          : this.amountMinor,
      currency: data.currency.present ? data.currency.value : this.currency,
      categoryId: data.categoryId.present
          ? data.categoryId.value
          : this.categoryId,
      channel: data.channel.present ? data.channel.value : this.channel,
      memberId: data.memberId.present ? data.memberId.value : this.memberId,
      necessity: data.necessity.present ? data.necessity.value : this.necessity,
      envelopeId: data.envelopeId.present
          ? data.envelopeId.value
          : this.envelopeId,
      isGift: data.isGift.present ? data.isGift.value : this.isGift,
      isOstentation: data.isOstentation.present
          ? data.isOstentation.value
          : this.isOstentation,
      fundedByDebt: data.fundedByDebt.present
          ? data.fundedByDebt.value
          : this.fundedByDebt,
      spentAt: data.spentAt.present ? data.spentAt.value : this.spentAt,
      note: data.note.present ? data.note.value : this.note,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ExpensesData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('amountMinor: $amountMinor, ')
          ..write('currency: $currency, ')
          ..write('categoryId: $categoryId, ')
          ..write('channel: $channel, ')
          ..write('memberId: $memberId, ')
          ..write('necessity: $necessity, ')
          ..write('envelopeId: $envelopeId, ')
          ..write('isGift: $isGift, ')
          ..write('isOstentation: $isOstentation, ')
          ..write('fundedByDebt: $fundedByDebt, ')
          ..write('spentAt: $spentAt, ')
          ..write('note: $note')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    amountMinor,
    currency,
    categoryId,
    channel,
    memberId,
    necessity,
    envelopeId,
    isGift,
    isOstentation,
    fundedByDebt,
    spentAt,
    note,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ExpensesData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.amountMinor == this.amountMinor &&
          other.currency == this.currency &&
          other.categoryId == this.categoryId &&
          other.channel == this.channel &&
          other.memberId == this.memberId &&
          other.necessity == this.necessity &&
          other.envelopeId == this.envelopeId &&
          other.isGift == this.isGift &&
          other.isOstentation == this.isOstentation &&
          other.fundedByDebt == this.fundedByDebt &&
          other.spentAt == this.spentAt &&
          other.note == this.note);
}

class ExpensesCompanion extends UpdateCompanion<ExpensesData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<int> amountMinor;
  final Value<String> currency;
  final Value<String> categoryId;
  final Value<String> channel;
  final Value<String?> memberId;
  final Value<String?> necessity;
  final Value<String?> envelopeId;
  final Value<bool> isGift;
  final Value<bool> isOstentation;
  final Value<bool> fundedByDebt;
  final Value<DateTime> spentAt;
  final Value<String?> note;
  final Value<int> rowid;
  const ExpensesCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.amountMinor = const Value.absent(),
    this.currency = const Value.absent(),
    this.categoryId = const Value.absent(),
    this.channel = const Value.absent(),
    this.memberId = const Value.absent(),
    this.necessity = const Value.absent(),
    this.envelopeId = const Value.absent(),
    this.isGift = const Value.absent(),
    this.isOstentation = const Value.absent(),
    this.fundedByDebt = const Value.absent(),
    this.spentAt = const Value.absent(),
    this.note = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  ExpensesCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    required int amountMinor,
    required String currency,
    required String categoryId,
    required String channel,
    this.memberId = const Value.absent(),
    this.necessity = const Value.absent(),
    this.envelopeId = const Value.absent(),
    this.isGift = const Value.absent(),
    this.isOstentation = const Value.absent(),
    this.fundedByDebt = const Value.absent(),
    required DateTime spentAt,
    this.note = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       amountMinor = Value(amountMinor),
       currency = Value(currency),
       categoryId = Value(categoryId),
       channel = Value(channel),
       spentAt = Value(spentAt);
  static Insertable<ExpensesData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<int>? amountMinor,
    Expression<String>? currency,
    Expression<String>? categoryId,
    Expression<String>? channel,
    Expression<String>? memberId,
    Expression<String>? necessity,
    Expression<String>? envelopeId,
    Expression<bool>? isGift,
    Expression<bool>? isOstentation,
    Expression<bool>? fundedByDebt,
    Expression<DateTime>? spentAt,
    Expression<String>? note,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (amountMinor != null) 'amount_minor': amountMinor,
      if (currency != null) 'currency': currency,
      if (categoryId != null) 'category_id': categoryId,
      if (channel != null) 'channel': channel,
      if (memberId != null) 'member_id': memberId,
      if (necessity != null) 'necessity': necessity,
      if (envelopeId != null) 'envelope_id': envelopeId,
      if (isGift != null) 'is_gift': isGift,
      if (isOstentation != null) 'is_ostentation': isOstentation,
      if (fundedByDebt != null) 'funded_by_debt': fundedByDebt,
      if (spentAt != null) 'spent_at': spentAt,
      if (note != null) 'note': note,
      if (rowid != null) 'rowid': rowid,
    });
  }

  ExpensesCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<int>? amountMinor,
    Value<String>? currency,
    Value<String>? categoryId,
    Value<String>? channel,
    Value<String?>? memberId,
    Value<String?>? necessity,
    Value<String?>? envelopeId,
    Value<bool>? isGift,
    Value<bool>? isOstentation,
    Value<bool>? fundedByDebt,
    Value<DateTime>? spentAt,
    Value<String?>? note,
    Value<int>? rowid,
  }) {
    return ExpensesCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      amountMinor: amountMinor ?? this.amountMinor,
      currency: currency ?? this.currency,
      categoryId: categoryId ?? this.categoryId,
      channel: channel ?? this.channel,
      memberId: memberId ?? this.memberId,
      necessity: necessity ?? this.necessity,
      envelopeId: envelopeId ?? this.envelopeId,
      isGift: isGift ?? this.isGift,
      isOstentation: isOstentation ?? this.isOstentation,
      fundedByDebt: fundedByDebt ?? this.fundedByDebt,
      spentAt: spentAt ?? this.spentAt,
      note: note ?? this.note,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (amountMinor.present) {
      map['amount_minor'] = Variable<int>(amountMinor.value);
    }
    if (currency.present) {
      map['currency'] = Variable<String>(currency.value);
    }
    if (categoryId.present) {
      map['category_id'] = Variable<String>(categoryId.value);
    }
    if (channel.present) {
      map['channel'] = Variable<String>(channel.value);
    }
    if (memberId.present) {
      map['member_id'] = Variable<String>(memberId.value);
    }
    if (necessity.present) {
      map['necessity'] = Variable<String>(necessity.value);
    }
    if (envelopeId.present) {
      map['envelope_id'] = Variable<String>(envelopeId.value);
    }
    if (isGift.present) {
      map['is_gift'] = Variable<bool>(isGift.value);
    }
    if (isOstentation.present) {
      map['is_ostentation'] = Variable<bool>(isOstentation.value);
    }
    if (fundedByDebt.present) {
      map['funded_by_debt'] = Variable<bool>(fundedByDebt.value);
    }
    if (spentAt.present) {
      map['spent_at'] = Variable<DateTime>(spentAt.value);
    }
    if (note.present) {
      map['note'] = Variable<String>(note.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ExpensesCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('amountMinor: $amountMinor, ')
          ..write('currency: $currency, ')
          ..write('categoryId: $categoryId, ')
          ..write('channel: $channel, ')
          ..write('memberId: $memberId, ')
          ..write('necessity: $necessity, ')
          ..write('envelopeId: $envelopeId, ')
          ..write('isGift: $isGift, ')
          ..write('isOstentation: $isOstentation, ')
          ..write('fundedByDebt: $fundedByDebt, ')
          ..write('spentAt: $spentAt, ')
          ..write('note: $note, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class Debts extends Table with TableInfo<Debts, DebtsData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  Debts(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<String> creditorType = GeneratedColumn<String>(
    'creditor_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> creditorName = GeneratedColumn<String>(
    'creditor_name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> currency = GeneratedColumn<String>(
    'currency',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<int> principalMinor = GeneratedColumn<int>(
    'principal_minor',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<int> remainingMinor = GeneratedColumn<int>(
    'remaining_minor',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<int> monthlyPaymentMinor = GeneratedColumn<int>(
    'monthly_payment_minor',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<String> dueDate = GeneratedColumn<String>(
    'due_date',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<String> reason = GeneratedColumn<String>(
    'reason',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<bool> hasMarkup = GeneratedColumn<bool>(
    'has_markup',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("has_markup" IN (0, 1))',
    ),
    defaultValue: const CustomExpression('0'),
  );
  late final GeneratedColumn<int> totalPaidMinor = GeneratedColumn<int>(
    'total_paid_minor',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> markupAmountMinor = GeneratedColumn<int>(
    'markup_amount_minor',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<String> earlyRepaymentTerms =
      GeneratedColumn<String>(
        'early_repayment_terms',
        aliasedName,
        true,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
      );
  late final GeneratedColumn<int> priority = GeneratedColumn<int>(
    'priority',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<String> note = GeneratedColumn<String>(
    'note',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    creditorType,
    creditorName,
    currency,
    principalMinor,
    remainingMinor,
    monthlyPaymentMinor,
    dueDate,
    reason,
    hasMarkup,
    totalPaidMinor,
    markupAmountMinor,
    earlyRepaymentTerms,
    priority,
    note,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'debts';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  DebtsData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return DebtsData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      creditorType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}creditor_type'],
      )!,
      creditorName: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}creditor_name'],
      )!,
      currency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}currency'],
      )!,
      principalMinor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}principal_minor'],
      )!,
      remainingMinor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}remaining_minor'],
      )!,
      monthlyPaymentMinor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}monthly_payment_minor'],
      ),
      dueDate: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}due_date'],
      ),
      reason: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}reason'],
      ),
      hasMarkup: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}has_markup'],
      )!,
      totalPaidMinor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}total_paid_minor'],
      ),
      markupAmountMinor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}markup_amount_minor'],
      ),
      earlyRepaymentTerms: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}early_repayment_terms'],
      ),
      priority: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}priority'],
      ),
      note: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}note'],
      ),
    );
  }

  @override
  Debts createAlias(String alias) {
    return Debts(attachedDatabase, alias);
  }

  @override
  List<String> get customConstraints => const [
    'CHECK (principal_minor >= 0 AND remaining_minor >= 0)',
  ];
}

class DebtsData extends DataClass implements Insertable<DebtsData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final String creditorType;
  final String creditorName;
  final String currency;
  final int principalMinor;
  final int remainingMinor;
  final int? monthlyPaymentMinor;
  final String? dueDate;
  final String? reason;
  final bool hasMarkup;
  final int? totalPaidMinor;
  final int? markupAmountMinor;
  final String? earlyRepaymentTerms;
  final int? priority;
  final String? note;
  const DebtsData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    required this.creditorType,
    required this.creditorName,
    required this.currency,
    required this.principalMinor,
    required this.remainingMinor,
    this.monthlyPaymentMinor,
    this.dueDate,
    this.reason,
    required this.hasMarkup,
    this.totalPaidMinor,
    this.markupAmountMinor,
    this.earlyRepaymentTerms,
    this.priority,
    this.note,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    map['creditor_type'] = Variable<String>(creditorType);
    map['creditor_name'] = Variable<String>(creditorName);
    map['currency'] = Variable<String>(currency);
    map['principal_minor'] = Variable<int>(principalMinor);
    map['remaining_minor'] = Variable<int>(remainingMinor);
    if (!nullToAbsent || monthlyPaymentMinor != null) {
      map['monthly_payment_minor'] = Variable<int>(monthlyPaymentMinor);
    }
    if (!nullToAbsent || dueDate != null) {
      map['due_date'] = Variable<String>(dueDate);
    }
    if (!nullToAbsent || reason != null) {
      map['reason'] = Variable<String>(reason);
    }
    map['has_markup'] = Variable<bool>(hasMarkup);
    if (!nullToAbsent || totalPaidMinor != null) {
      map['total_paid_minor'] = Variable<int>(totalPaidMinor);
    }
    if (!nullToAbsent || markupAmountMinor != null) {
      map['markup_amount_minor'] = Variable<int>(markupAmountMinor);
    }
    if (!nullToAbsent || earlyRepaymentTerms != null) {
      map['early_repayment_terms'] = Variable<String>(earlyRepaymentTerms);
    }
    if (!nullToAbsent || priority != null) {
      map['priority'] = Variable<int>(priority);
    }
    if (!nullToAbsent || note != null) {
      map['note'] = Variable<String>(note);
    }
    return map;
  }

  DebtsCompanion toCompanion(bool nullToAbsent) {
    return DebtsCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      creditorType: Value(creditorType),
      creditorName: Value(creditorName),
      currency: Value(currency),
      principalMinor: Value(principalMinor),
      remainingMinor: Value(remainingMinor),
      monthlyPaymentMinor: monthlyPaymentMinor == null && nullToAbsent
          ? const Value.absent()
          : Value(monthlyPaymentMinor),
      dueDate: dueDate == null && nullToAbsent
          ? const Value.absent()
          : Value(dueDate),
      reason: reason == null && nullToAbsent
          ? const Value.absent()
          : Value(reason),
      hasMarkup: Value(hasMarkup),
      totalPaidMinor: totalPaidMinor == null && nullToAbsent
          ? const Value.absent()
          : Value(totalPaidMinor),
      markupAmountMinor: markupAmountMinor == null && nullToAbsent
          ? const Value.absent()
          : Value(markupAmountMinor),
      earlyRepaymentTerms: earlyRepaymentTerms == null && nullToAbsent
          ? const Value.absent()
          : Value(earlyRepaymentTerms),
      priority: priority == null && nullToAbsent
          ? const Value.absent()
          : Value(priority),
      note: note == null && nullToAbsent ? const Value.absent() : Value(note),
    );
  }

  factory DebtsData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return DebtsData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      creditorType: serializer.fromJson<String>(json['creditorType']),
      creditorName: serializer.fromJson<String>(json['creditorName']),
      currency: serializer.fromJson<String>(json['currency']),
      principalMinor: serializer.fromJson<int>(json['principalMinor']),
      remainingMinor: serializer.fromJson<int>(json['remainingMinor']),
      monthlyPaymentMinor: serializer.fromJson<int?>(
        json['monthlyPaymentMinor'],
      ),
      dueDate: serializer.fromJson<String?>(json['dueDate']),
      reason: serializer.fromJson<String?>(json['reason']),
      hasMarkup: serializer.fromJson<bool>(json['hasMarkup']),
      totalPaidMinor: serializer.fromJson<int?>(json['totalPaidMinor']),
      markupAmountMinor: serializer.fromJson<int?>(json['markupAmountMinor']),
      earlyRepaymentTerms: serializer.fromJson<String?>(
        json['earlyRepaymentTerms'],
      ),
      priority: serializer.fromJson<int?>(json['priority']),
      note: serializer.fromJson<String?>(json['note']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'creditorType': serializer.toJson<String>(creditorType),
      'creditorName': serializer.toJson<String>(creditorName),
      'currency': serializer.toJson<String>(currency),
      'principalMinor': serializer.toJson<int>(principalMinor),
      'remainingMinor': serializer.toJson<int>(remainingMinor),
      'monthlyPaymentMinor': serializer.toJson<int?>(monthlyPaymentMinor),
      'dueDate': serializer.toJson<String?>(dueDate),
      'reason': serializer.toJson<String?>(reason),
      'hasMarkup': serializer.toJson<bool>(hasMarkup),
      'totalPaidMinor': serializer.toJson<int?>(totalPaidMinor),
      'markupAmountMinor': serializer.toJson<int?>(markupAmountMinor),
      'earlyRepaymentTerms': serializer.toJson<String?>(earlyRepaymentTerms),
      'priority': serializer.toJson<int?>(priority),
      'note': serializer.toJson<String?>(note),
    };
  }

  DebtsData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    String? creditorType,
    String? creditorName,
    String? currency,
    int? principalMinor,
    int? remainingMinor,
    Value<int?> monthlyPaymentMinor = const Value.absent(),
    Value<String?> dueDate = const Value.absent(),
    Value<String?> reason = const Value.absent(),
    bool? hasMarkup,
    Value<int?> totalPaidMinor = const Value.absent(),
    Value<int?> markupAmountMinor = const Value.absent(),
    Value<String?> earlyRepaymentTerms = const Value.absent(),
    Value<int?> priority = const Value.absent(),
    Value<String?> note = const Value.absent(),
  }) => DebtsData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    creditorType: creditorType ?? this.creditorType,
    creditorName: creditorName ?? this.creditorName,
    currency: currency ?? this.currency,
    principalMinor: principalMinor ?? this.principalMinor,
    remainingMinor: remainingMinor ?? this.remainingMinor,
    monthlyPaymentMinor: monthlyPaymentMinor.present
        ? monthlyPaymentMinor.value
        : this.monthlyPaymentMinor,
    dueDate: dueDate.present ? dueDate.value : this.dueDate,
    reason: reason.present ? reason.value : this.reason,
    hasMarkup: hasMarkup ?? this.hasMarkup,
    totalPaidMinor: totalPaidMinor.present
        ? totalPaidMinor.value
        : this.totalPaidMinor,
    markupAmountMinor: markupAmountMinor.present
        ? markupAmountMinor.value
        : this.markupAmountMinor,
    earlyRepaymentTerms: earlyRepaymentTerms.present
        ? earlyRepaymentTerms.value
        : this.earlyRepaymentTerms,
    priority: priority.present ? priority.value : this.priority,
    note: note.present ? note.value : this.note,
  );
  DebtsData copyWithCompanion(DebtsCompanion data) {
    return DebtsData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      creditorType: data.creditorType.present
          ? data.creditorType.value
          : this.creditorType,
      creditorName: data.creditorName.present
          ? data.creditorName.value
          : this.creditorName,
      currency: data.currency.present ? data.currency.value : this.currency,
      principalMinor: data.principalMinor.present
          ? data.principalMinor.value
          : this.principalMinor,
      remainingMinor: data.remainingMinor.present
          ? data.remainingMinor.value
          : this.remainingMinor,
      monthlyPaymentMinor: data.monthlyPaymentMinor.present
          ? data.monthlyPaymentMinor.value
          : this.monthlyPaymentMinor,
      dueDate: data.dueDate.present ? data.dueDate.value : this.dueDate,
      reason: data.reason.present ? data.reason.value : this.reason,
      hasMarkup: data.hasMarkup.present ? data.hasMarkup.value : this.hasMarkup,
      totalPaidMinor: data.totalPaidMinor.present
          ? data.totalPaidMinor.value
          : this.totalPaidMinor,
      markupAmountMinor: data.markupAmountMinor.present
          ? data.markupAmountMinor.value
          : this.markupAmountMinor,
      earlyRepaymentTerms: data.earlyRepaymentTerms.present
          ? data.earlyRepaymentTerms.value
          : this.earlyRepaymentTerms,
      priority: data.priority.present ? data.priority.value : this.priority,
      note: data.note.present ? data.note.value : this.note,
    );
  }

  @override
  String toString() {
    return (StringBuffer('DebtsData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('creditorType: $creditorType, ')
          ..write('creditorName: $creditorName, ')
          ..write('currency: $currency, ')
          ..write('principalMinor: $principalMinor, ')
          ..write('remainingMinor: $remainingMinor, ')
          ..write('monthlyPaymentMinor: $monthlyPaymentMinor, ')
          ..write('dueDate: $dueDate, ')
          ..write('reason: $reason, ')
          ..write('hasMarkup: $hasMarkup, ')
          ..write('totalPaidMinor: $totalPaidMinor, ')
          ..write('markupAmountMinor: $markupAmountMinor, ')
          ..write('earlyRepaymentTerms: $earlyRepaymentTerms, ')
          ..write('priority: $priority, ')
          ..write('note: $note')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    creditorType,
    creditorName,
    currency,
    principalMinor,
    remainingMinor,
    monthlyPaymentMinor,
    dueDate,
    reason,
    hasMarkup,
    totalPaidMinor,
    markupAmountMinor,
    earlyRepaymentTerms,
    priority,
    note,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is DebtsData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.creditorType == this.creditorType &&
          other.creditorName == this.creditorName &&
          other.currency == this.currency &&
          other.principalMinor == this.principalMinor &&
          other.remainingMinor == this.remainingMinor &&
          other.monthlyPaymentMinor == this.monthlyPaymentMinor &&
          other.dueDate == this.dueDate &&
          other.reason == this.reason &&
          other.hasMarkup == this.hasMarkup &&
          other.totalPaidMinor == this.totalPaidMinor &&
          other.markupAmountMinor == this.markupAmountMinor &&
          other.earlyRepaymentTerms == this.earlyRepaymentTerms &&
          other.priority == this.priority &&
          other.note == this.note);
}

class DebtsCompanion extends UpdateCompanion<DebtsData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<String> creditorType;
  final Value<String> creditorName;
  final Value<String> currency;
  final Value<int> principalMinor;
  final Value<int> remainingMinor;
  final Value<int?> monthlyPaymentMinor;
  final Value<String?> dueDate;
  final Value<String?> reason;
  final Value<bool> hasMarkup;
  final Value<int?> totalPaidMinor;
  final Value<int?> markupAmountMinor;
  final Value<String?> earlyRepaymentTerms;
  final Value<int?> priority;
  final Value<String?> note;
  final Value<int> rowid;
  const DebtsCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.creditorType = const Value.absent(),
    this.creditorName = const Value.absent(),
    this.currency = const Value.absent(),
    this.principalMinor = const Value.absent(),
    this.remainingMinor = const Value.absent(),
    this.monthlyPaymentMinor = const Value.absent(),
    this.dueDate = const Value.absent(),
    this.reason = const Value.absent(),
    this.hasMarkup = const Value.absent(),
    this.totalPaidMinor = const Value.absent(),
    this.markupAmountMinor = const Value.absent(),
    this.earlyRepaymentTerms = const Value.absent(),
    this.priority = const Value.absent(),
    this.note = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  DebtsCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    required String creditorType,
    required String creditorName,
    required String currency,
    required int principalMinor,
    required int remainingMinor,
    this.monthlyPaymentMinor = const Value.absent(),
    this.dueDate = const Value.absent(),
    this.reason = const Value.absent(),
    this.hasMarkup = const Value.absent(),
    this.totalPaidMinor = const Value.absent(),
    this.markupAmountMinor = const Value.absent(),
    this.earlyRepaymentTerms = const Value.absent(),
    this.priority = const Value.absent(),
    this.note = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       creditorType = Value(creditorType),
       creditorName = Value(creditorName),
       currency = Value(currency),
       principalMinor = Value(principalMinor),
       remainingMinor = Value(remainingMinor);
  static Insertable<DebtsData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<String>? creditorType,
    Expression<String>? creditorName,
    Expression<String>? currency,
    Expression<int>? principalMinor,
    Expression<int>? remainingMinor,
    Expression<int>? monthlyPaymentMinor,
    Expression<String>? dueDate,
    Expression<String>? reason,
    Expression<bool>? hasMarkup,
    Expression<int>? totalPaidMinor,
    Expression<int>? markupAmountMinor,
    Expression<String>? earlyRepaymentTerms,
    Expression<int>? priority,
    Expression<String>? note,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (creditorType != null) 'creditor_type': creditorType,
      if (creditorName != null) 'creditor_name': creditorName,
      if (currency != null) 'currency': currency,
      if (principalMinor != null) 'principal_minor': principalMinor,
      if (remainingMinor != null) 'remaining_minor': remainingMinor,
      if (monthlyPaymentMinor != null)
        'monthly_payment_minor': monthlyPaymentMinor,
      if (dueDate != null) 'due_date': dueDate,
      if (reason != null) 'reason': reason,
      if (hasMarkup != null) 'has_markup': hasMarkup,
      if (totalPaidMinor != null) 'total_paid_minor': totalPaidMinor,
      if (markupAmountMinor != null) 'markup_amount_minor': markupAmountMinor,
      if (earlyRepaymentTerms != null)
        'early_repayment_terms': earlyRepaymentTerms,
      if (priority != null) 'priority': priority,
      if (note != null) 'note': note,
      if (rowid != null) 'rowid': rowid,
    });
  }

  DebtsCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<String>? creditorType,
    Value<String>? creditorName,
    Value<String>? currency,
    Value<int>? principalMinor,
    Value<int>? remainingMinor,
    Value<int?>? monthlyPaymentMinor,
    Value<String?>? dueDate,
    Value<String?>? reason,
    Value<bool>? hasMarkup,
    Value<int?>? totalPaidMinor,
    Value<int?>? markupAmountMinor,
    Value<String?>? earlyRepaymentTerms,
    Value<int?>? priority,
    Value<String?>? note,
    Value<int>? rowid,
  }) {
    return DebtsCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      creditorType: creditorType ?? this.creditorType,
      creditorName: creditorName ?? this.creditorName,
      currency: currency ?? this.currency,
      principalMinor: principalMinor ?? this.principalMinor,
      remainingMinor: remainingMinor ?? this.remainingMinor,
      monthlyPaymentMinor: monthlyPaymentMinor ?? this.monthlyPaymentMinor,
      dueDate: dueDate ?? this.dueDate,
      reason: reason ?? this.reason,
      hasMarkup: hasMarkup ?? this.hasMarkup,
      totalPaidMinor: totalPaidMinor ?? this.totalPaidMinor,
      markupAmountMinor: markupAmountMinor ?? this.markupAmountMinor,
      earlyRepaymentTerms: earlyRepaymentTerms ?? this.earlyRepaymentTerms,
      priority: priority ?? this.priority,
      note: note ?? this.note,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (creditorType.present) {
      map['creditor_type'] = Variable<String>(creditorType.value);
    }
    if (creditorName.present) {
      map['creditor_name'] = Variable<String>(creditorName.value);
    }
    if (currency.present) {
      map['currency'] = Variable<String>(currency.value);
    }
    if (principalMinor.present) {
      map['principal_minor'] = Variable<int>(principalMinor.value);
    }
    if (remainingMinor.present) {
      map['remaining_minor'] = Variable<int>(remainingMinor.value);
    }
    if (monthlyPaymentMinor.present) {
      map['monthly_payment_minor'] = Variable<int>(monthlyPaymentMinor.value);
    }
    if (dueDate.present) {
      map['due_date'] = Variable<String>(dueDate.value);
    }
    if (reason.present) {
      map['reason'] = Variable<String>(reason.value);
    }
    if (hasMarkup.present) {
      map['has_markup'] = Variable<bool>(hasMarkup.value);
    }
    if (totalPaidMinor.present) {
      map['total_paid_minor'] = Variable<int>(totalPaidMinor.value);
    }
    if (markupAmountMinor.present) {
      map['markup_amount_minor'] = Variable<int>(markupAmountMinor.value);
    }
    if (earlyRepaymentTerms.present) {
      map['early_repayment_terms'] = Variable<String>(
        earlyRepaymentTerms.value,
      );
    }
    if (priority.present) {
      map['priority'] = Variable<int>(priority.value);
    }
    if (note.present) {
      map['note'] = Variable<String>(note.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('DebtsCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('creditorType: $creditorType, ')
          ..write('creditorName: $creditorName, ')
          ..write('currency: $currency, ')
          ..write('principalMinor: $principalMinor, ')
          ..write('remainingMinor: $remainingMinor, ')
          ..write('monthlyPaymentMinor: $monthlyPaymentMinor, ')
          ..write('dueDate: $dueDate, ')
          ..write('reason: $reason, ')
          ..write('hasMarkup: $hasMarkup, ')
          ..write('totalPaidMinor: $totalPaidMinor, ')
          ..write('markupAmountMinor: $markupAmountMinor, ')
          ..write('earlyRepaymentTerms: $earlyRepaymentTerms, ')
          ..write('priority: $priority, ')
          ..write('note: $note, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class Obligations extends Table with TableInfo<Obligations, ObligationsData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  Obligations(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
    'title',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> kind = GeneratedColumn<String>(
    'kind',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<int> amountMinor = GeneratedColumn<int>(
    'amount_minor',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> currency = GeneratedColumn<String>(
    'currency',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<int> dayOfMonth = GeneratedColumn<int>(
    'day_of_month',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> categoryId = GeneratedColumn<String>(
    'category_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES categories (id)',
    ),
  );
  late final GeneratedColumn<String> debtId = GeneratedColumn<String>(
    'debt_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES debts (id)',
    ),
  );
  late final GeneratedColumn<bool> isActive = GeneratedColumn<bool>(
    'is_active',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_active" IN (0, 1))',
    ),
    defaultValue: const CustomExpression('1'),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    title,
    kind,
    amountMinor,
    currency,
    dayOfMonth,
    categoryId,
    debtId,
    isActive,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'obligations';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  ObligationsData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ObligationsData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      title: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}title'],
      )!,
      kind: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}kind'],
      )!,
      amountMinor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}amount_minor'],
      )!,
      currency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}currency'],
      )!,
      dayOfMonth: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}day_of_month'],
      )!,
      categoryId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}category_id'],
      ),
      debtId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}debt_id'],
      ),
      isActive: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_active'],
      )!,
    );
  }

  @override
  Obligations createAlias(String alias) {
    return Obligations(attachedDatabase, alias);
  }

  @override
  List<String> get customConstraints => const [
    'CHECK (day_of_month BETWEEN 1 AND 31)',
    'CHECK (amount_minor > 0)',
  ];
}

class ObligationsData extends DataClass implements Insertable<ObligationsData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final String title;
  final String kind;
  final int amountMinor;
  final String currency;
  final int dayOfMonth;
  final String? categoryId;
  final String? debtId;
  final bool isActive;
  const ObligationsData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    required this.title,
    required this.kind,
    required this.amountMinor,
    required this.currency,
    required this.dayOfMonth,
    this.categoryId,
    this.debtId,
    required this.isActive,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    map['title'] = Variable<String>(title);
    map['kind'] = Variable<String>(kind);
    map['amount_minor'] = Variable<int>(amountMinor);
    map['currency'] = Variable<String>(currency);
    map['day_of_month'] = Variable<int>(dayOfMonth);
    if (!nullToAbsent || categoryId != null) {
      map['category_id'] = Variable<String>(categoryId);
    }
    if (!nullToAbsent || debtId != null) {
      map['debt_id'] = Variable<String>(debtId);
    }
    map['is_active'] = Variable<bool>(isActive);
    return map;
  }

  ObligationsCompanion toCompanion(bool nullToAbsent) {
    return ObligationsCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      title: Value(title),
      kind: Value(kind),
      amountMinor: Value(amountMinor),
      currency: Value(currency),
      dayOfMonth: Value(dayOfMonth),
      categoryId: categoryId == null && nullToAbsent
          ? const Value.absent()
          : Value(categoryId),
      debtId: debtId == null && nullToAbsent
          ? const Value.absent()
          : Value(debtId),
      isActive: Value(isActive),
    );
  }

  factory ObligationsData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ObligationsData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      title: serializer.fromJson<String>(json['title']),
      kind: serializer.fromJson<String>(json['kind']),
      amountMinor: serializer.fromJson<int>(json['amountMinor']),
      currency: serializer.fromJson<String>(json['currency']),
      dayOfMonth: serializer.fromJson<int>(json['dayOfMonth']),
      categoryId: serializer.fromJson<String?>(json['categoryId']),
      debtId: serializer.fromJson<String?>(json['debtId']),
      isActive: serializer.fromJson<bool>(json['isActive']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'title': serializer.toJson<String>(title),
      'kind': serializer.toJson<String>(kind),
      'amountMinor': serializer.toJson<int>(amountMinor),
      'currency': serializer.toJson<String>(currency),
      'dayOfMonth': serializer.toJson<int>(dayOfMonth),
      'categoryId': serializer.toJson<String?>(categoryId),
      'debtId': serializer.toJson<String?>(debtId),
      'isActive': serializer.toJson<bool>(isActive),
    };
  }

  ObligationsData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    String? title,
    String? kind,
    int? amountMinor,
    String? currency,
    int? dayOfMonth,
    Value<String?> categoryId = const Value.absent(),
    Value<String?> debtId = const Value.absent(),
    bool? isActive,
  }) => ObligationsData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    title: title ?? this.title,
    kind: kind ?? this.kind,
    amountMinor: amountMinor ?? this.amountMinor,
    currency: currency ?? this.currency,
    dayOfMonth: dayOfMonth ?? this.dayOfMonth,
    categoryId: categoryId.present ? categoryId.value : this.categoryId,
    debtId: debtId.present ? debtId.value : this.debtId,
    isActive: isActive ?? this.isActive,
  );
  ObligationsData copyWithCompanion(ObligationsCompanion data) {
    return ObligationsData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      title: data.title.present ? data.title.value : this.title,
      kind: data.kind.present ? data.kind.value : this.kind,
      amountMinor: data.amountMinor.present
          ? data.amountMinor.value
          : this.amountMinor,
      currency: data.currency.present ? data.currency.value : this.currency,
      dayOfMonth: data.dayOfMonth.present
          ? data.dayOfMonth.value
          : this.dayOfMonth,
      categoryId: data.categoryId.present
          ? data.categoryId.value
          : this.categoryId,
      debtId: data.debtId.present ? data.debtId.value : this.debtId,
      isActive: data.isActive.present ? data.isActive.value : this.isActive,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ObligationsData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('title: $title, ')
          ..write('kind: $kind, ')
          ..write('amountMinor: $amountMinor, ')
          ..write('currency: $currency, ')
          ..write('dayOfMonth: $dayOfMonth, ')
          ..write('categoryId: $categoryId, ')
          ..write('debtId: $debtId, ')
          ..write('isActive: $isActive')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    title,
    kind,
    amountMinor,
    currency,
    dayOfMonth,
    categoryId,
    debtId,
    isActive,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ObligationsData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.title == this.title &&
          other.kind == this.kind &&
          other.amountMinor == this.amountMinor &&
          other.currency == this.currency &&
          other.dayOfMonth == this.dayOfMonth &&
          other.categoryId == this.categoryId &&
          other.debtId == this.debtId &&
          other.isActive == this.isActive);
}

class ObligationsCompanion extends UpdateCompanion<ObligationsData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<String> title;
  final Value<String> kind;
  final Value<int> amountMinor;
  final Value<String> currency;
  final Value<int> dayOfMonth;
  final Value<String?> categoryId;
  final Value<String?> debtId;
  final Value<bool> isActive;
  final Value<int> rowid;
  const ObligationsCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.title = const Value.absent(),
    this.kind = const Value.absent(),
    this.amountMinor = const Value.absent(),
    this.currency = const Value.absent(),
    this.dayOfMonth = const Value.absent(),
    this.categoryId = const Value.absent(),
    this.debtId = const Value.absent(),
    this.isActive = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  ObligationsCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    required String title,
    required String kind,
    required int amountMinor,
    required String currency,
    required int dayOfMonth,
    this.categoryId = const Value.absent(),
    this.debtId = const Value.absent(),
    this.isActive = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       title = Value(title),
       kind = Value(kind),
       amountMinor = Value(amountMinor),
       currency = Value(currency),
       dayOfMonth = Value(dayOfMonth);
  static Insertable<ObligationsData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<String>? title,
    Expression<String>? kind,
    Expression<int>? amountMinor,
    Expression<String>? currency,
    Expression<int>? dayOfMonth,
    Expression<String>? categoryId,
    Expression<String>? debtId,
    Expression<bool>? isActive,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (title != null) 'title': title,
      if (kind != null) 'kind': kind,
      if (amountMinor != null) 'amount_minor': amountMinor,
      if (currency != null) 'currency': currency,
      if (dayOfMonth != null) 'day_of_month': dayOfMonth,
      if (categoryId != null) 'category_id': categoryId,
      if (debtId != null) 'debt_id': debtId,
      if (isActive != null) 'is_active': isActive,
      if (rowid != null) 'rowid': rowid,
    });
  }

  ObligationsCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<String>? title,
    Value<String>? kind,
    Value<int>? amountMinor,
    Value<String>? currency,
    Value<int>? dayOfMonth,
    Value<String?>? categoryId,
    Value<String?>? debtId,
    Value<bool>? isActive,
    Value<int>? rowid,
  }) {
    return ObligationsCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      title: title ?? this.title,
      kind: kind ?? this.kind,
      amountMinor: amountMinor ?? this.amountMinor,
      currency: currency ?? this.currency,
      dayOfMonth: dayOfMonth ?? this.dayOfMonth,
      categoryId: categoryId ?? this.categoryId,
      debtId: debtId ?? this.debtId,
      isActive: isActive ?? this.isActive,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (kind.present) {
      map['kind'] = Variable<String>(kind.value);
    }
    if (amountMinor.present) {
      map['amount_minor'] = Variable<int>(amountMinor.value);
    }
    if (currency.present) {
      map['currency'] = Variable<String>(currency.value);
    }
    if (dayOfMonth.present) {
      map['day_of_month'] = Variable<int>(dayOfMonth.value);
    }
    if (categoryId.present) {
      map['category_id'] = Variable<String>(categoryId.value);
    }
    if (debtId.present) {
      map['debt_id'] = Variable<String>(debtId.value);
    }
    if (isActive.present) {
      map['is_active'] = Variable<bool>(isActive.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ObligationsCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('title: $title, ')
          ..write('kind: $kind, ')
          ..write('amountMinor: $amountMinor, ')
          ..write('currency: $currency, ')
          ..write('dayOfMonth: $dayOfMonth, ')
          ..write('categoryId: $categoryId, ')
          ..write('debtId: $debtId, ')
          ..write('isActive: $isActive, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class Assets extends Table with TableInfo<Assets, AssetsData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  Assets(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<String> type = GeneratedColumn<String>(
    'type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> quantity = GeneratedColumn<int>(
    'quantity',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('0'),
  );
  late final GeneratedColumn<String> unit = GeneratedColumn<String>(
    'unit',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> currency = GeneratedColumn<String>(
    'currency',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<DateTime> acquiredAt = GeneratedColumn<DateTime>(
    'acquired_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> vaultType = GeneratedColumn<String>(
    'vault_type',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    type,
    name,
    quantity,
    unit,
    currency,
    acquiredAt,
    vaultType,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'assets';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  AssetsData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return AssetsData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      type: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}type'],
      )!,
      name: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}name'],
      ),
      quantity: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}quantity'],
      )!,
      unit: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}unit'],
      )!,
      currency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}currency'],
      ),
      acquiredAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}acquired_at'],
      )!,
      vaultType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}vault_type'],
      ),
    );
  }

  @override
  Assets createAlias(String alias) {
    return Assets(attachedDatabase, alias);
  }
}

class AssetsData extends DataClass implements Insertable<AssetsData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final String type;
  final String? name;
  final int quantity;
  final String unit;
  final String? currency;
  final DateTime acquiredAt;
  final String? vaultType;
  const AssetsData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    required this.type,
    this.name,
    required this.quantity,
    required this.unit,
    this.currency,
    required this.acquiredAt,
    this.vaultType,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    map['type'] = Variable<String>(type);
    if (!nullToAbsent || name != null) {
      map['name'] = Variable<String>(name);
    }
    map['quantity'] = Variable<int>(quantity);
    map['unit'] = Variable<String>(unit);
    if (!nullToAbsent || currency != null) {
      map['currency'] = Variable<String>(currency);
    }
    map['acquired_at'] = Variable<DateTime>(acquiredAt);
    if (!nullToAbsent || vaultType != null) {
      map['vault_type'] = Variable<String>(vaultType);
    }
    return map;
  }

  AssetsCompanion toCompanion(bool nullToAbsent) {
    return AssetsCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      type: Value(type),
      name: name == null && nullToAbsent ? const Value.absent() : Value(name),
      quantity: Value(quantity),
      unit: Value(unit),
      currency: currency == null && nullToAbsent
          ? const Value.absent()
          : Value(currency),
      acquiredAt: Value(acquiredAt),
      vaultType: vaultType == null && nullToAbsent
          ? const Value.absent()
          : Value(vaultType),
    );
  }

  factory AssetsData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return AssetsData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      type: serializer.fromJson<String>(json['type']),
      name: serializer.fromJson<String?>(json['name']),
      quantity: serializer.fromJson<int>(json['quantity']),
      unit: serializer.fromJson<String>(json['unit']),
      currency: serializer.fromJson<String?>(json['currency']),
      acquiredAt: serializer.fromJson<DateTime>(json['acquiredAt']),
      vaultType: serializer.fromJson<String?>(json['vaultType']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'type': serializer.toJson<String>(type),
      'name': serializer.toJson<String?>(name),
      'quantity': serializer.toJson<int>(quantity),
      'unit': serializer.toJson<String>(unit),
      'currency': serializer.toJson<String?>(currency),
      'acquiredAt': serializer.toJson<DateTime>(acquiredAt),
      'vaultType': serializer.toJson<String?>(vaultType),
    };
  }

  AssetsData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    String? type,
    Value<String?> name = const Value.absent(),
    int? quantity,
    String? unit,
    Value<String?> currency = const Value.absent(),
    DateTime? acquiredAt,
    Value<String?> vaultType = const Value.absent(),
  }) => AssetsData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    type: type ?? this.type,
    name: name.present ? name.value : this.name,
    quantity: quantity ?? this.quantity,
    unit: unit ?? this.unit,
    currency: currency.present ? currency.value : this.currency,
    acquiredAt: acquiredAt ?? this.acquiredAt,
    vaultType: vaultType.present ? vaultType.value : this.vaultType,
  );
  AssetsData copyWithCompanion(AssetsCompanion data) {
    return AssetsData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      type: data.type.present ? data.type.value : this.type,
      name: data.name.present ? data.name.value : this.name,
      quantity: data.quantity.present ? data.quantity.value : this.quantity,
      unit: data.unit.present ? data.unit.value : this.unit,
      currency: data.currency.present ? data.currency.value : this.currency,
      acquiredAt: data.acquiredAt.present
          ? data.acquiredAt.value
          : this.acquiredAt,
      vaultType: data.vaultType.present ? data.vaultType.value : this.vaultType,
    );
  }

  @override
  String toString() {
    return (StringBuffer('AssetsData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('type: $type, ')
          ..write('name: $name, ')
          ..write('quantity: $quantity, ')
          ..write('unit: $unit, ')
          ..write('currency: $currency, ')
          ..write('acquiredAt: $acquiredAt, ')
          ..write('vaultType: $vaultType')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    type,
    name,
    quantity,
    unit,
    currency,
    acquiredAt,
    vaultType,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is AssetsData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.type == this.type &&
          other.name == this.name &&
          other.quantity == this.quantity &&
          other.unit == this.unit &&
          other.currency == this.currency &&
          other.acquiredAt == this.acquiredAt &&
          other.vaultType == this.vaultType);
}

class AssetsCompanion extends UpdateCompanion<AssetsData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<String> type;
  final Value<String?> name;
  final Value<int> quantity;
  final Value<String> unit;
  final Value<String?> currency;
  final Value<DateTime> acquiredAt;
  final Value<String?> vaultType;
  final Value<int> rowid;
  const AssetsCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.type = const Value.absent(),
    this.name = const Value.absent(),
    this.quantity = const Value.absent(),
    this.unit = const Value.absent(),
    this.currency = const Value.absent(),
    this.acquiredAt = const Value.absent(),
    this.vaultType = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  AssetsCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    required String type,
    this.name = const Value.absent(),
    this.quantity = const Value.absent(),
    required String unit,
    this.currency = const Value.absent(),
    required DateTime acquiredAt,
    this.vaultType = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       type = Value(type),
       unit = Value(unit),
       acquiredAt = Value(acquiredAt);
  static Insertable<AssetsData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<String>? type,
    Expression<String>? name,
    Expression<int>? quantity,
    Expression<String>? unit,
    Expression<String>? currency,
    Expression<DateTime>? acquiredAt,
    Expression<String>? vaultType,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (type != null) 'type': type,
      if (name != null) 'name': name,
      if (quantity != null) 'quantity': quantity,
      if (unit != null) 'unit': unit,
      if (currency != null) 'currency': currency,
      if (acquiredAt != null) 'acquired_at': acquiredAt,
      if (vaultType != null) 'vault_type': vaultType,
      if (rowid != null) 'rowid': rowid,
    });
  }

  AssetsCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<String>? type,
    Value<String?>? name,
    Value<int>? quantity,
    Value<String>? unit,
    Value<String?>? currency,
    Value<DateTime>? acquiredAt,
    Value<String?>? vaultType,
    Value<int>? rowid,
  }) {
    return AssetsCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      type: type ?? this.type,
      name: name ?? this.name,
      quantity: quantity ?? this.quantity,
      unit: unit ?? this.unit,
      currency: currency ?? this.currency,
      acquiredAt: acquiredAt ?? this.acquiredAt,
      vaultType: vaultType ?? this.vaultType,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (type.present) {
      map['type'] = Variable<String>(type.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (quantity.present) {
      map['quantity'] = Variable<int>(quantity.value);
    }
    if (unit.present) {
      map['unit'] = Variable<String>(unit.value);
    }
    if (currency.present) {
      map['currency'] = Variable<String>(currency.value);
    }
    if (acquiredAt.present) {
      map['acquired_at'] = Variable<DateTime>(acquiredAt.value);
    }
    if (vaultType.present) {
      map['vault_type'] = Variable<String>(vaultType.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('AssetsCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('type: $type, ')
          ..write('name: $name, ')
          ..write('quantity: $quantity, ')
          ..write('unit: $unit, ')
          ..write('currency: $currency, ')
          ..write('acquiredAt: $acquiredAt, ')
          ..write('vaultType: $vaultType, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class AssetSnapshots extends Table
    with TableInfo<AssetSnapshots, AssetSnapshotsData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  AssetSnapshots(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<String> assetId = GeneratedColumn<String>(
    'asset_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES assets (id)',
    ),
  );
  late final GeneratedColumn<int> quantity = GeneratedColumn<int>(
    'quantity',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> takenAt = GeneratedColumn<DateTime>(
    'taken_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    assetId,
    quantity,
    takenAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'asset_snapshots';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  AssetSnapshotsData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return AssetSnapshotsData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      assetId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}asset_id'],
      )!,
      quantity: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}quantity'],
      )!,
      takenAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}taken_at'],
      )!,
    );
  }

  @override
  AssetSnapshots createAlias(String alias) {
    return AssetSnapshots(attachedDatabase, alias);
  }
}

class AssetSnapshotsData extends DataClass
    implements Insertable<AssetSnapshotsData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final String assetId;
  final int quantity;
  final DateTime takenAt;
  const AssetSnapshotsData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    required this.assetId,
    required this.quantity,
    required this.takenAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    map['asset_id'] = Variable<String>(assetId);
    map['quantity'] = Variable<int>(quantity);
    map['taken_at'] = Variable<DateTime>(takenAt);
    return map;
  }

  AssetSnapshotsCompanion toCompanion(bool nullToAbsent) {
    return AssetSnapshotsCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      assetId: Value(assetId),
      quantity: Value(quantity),
      takenAt: Value(takenAt),
    );
  }

  factory AssetSnapshotsData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return AssetSnapshotsData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      assetId: serializer.fromJson<String>(json['assetId']),
      quantity: serializer.fromJson<int>(json['quantity']),
      takenAt: serializer.fromJson<DateTime>(json['takenAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'assetId': serializer.toJson<String>(assetId),
      'quantity': serializer.toJson<int>(quantity),
      'takenAt': serializer.toJson<DateTime>(takenAt),
    };
  }

  AssetSnapshotsData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    String? assetId,
    int? quantity,
    DateTime? takenAt,
  }) => AssetSnapshotsData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    assetId: assetId ?? this.assetId,
    quantity: quantity ?? this.quantity,
    takenAt: takenAt ?? this.takenAt,
  );
  AssetSnapshotsData copyWithCompanion(AssetSnapshotsCompanion data) {
    return AssetSnapshotsData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      assetId: data.assetId.present ? data.assetId.value : this.assetId,
      quantity: data.quantity.present ? data.quantity.value : this.quantity,
      takenAt: data.takenAt.present ? data.takenAt.value : this.takenAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('AssetSnapshotsData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('assetId: $assetId, ')
          ..write('quantity: $quantity, ')
          ..write('takenAt: $takenAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    assetId,
    quantity,
    takenAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is AssetSnapshotsData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.assetId == this.assetId &&
          other.quantity == this.quantity &&
          other.takenAt == this.takenAt);
}

class AssetSnapshotsCompanion extends UpdateCompanion<AssetSnapshotsData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<String> assetId;
  final Value<int> quantity;
  final Value<DateTime> takenAt;
  final Value<int> rowid;
  const AssetSnapshotsCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.assetId = const Value.absent(),
    this.quantity = const Value.absent(),
    this.takenAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  AssetSnapshotsCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    required String assetId,
    required int quantity,
    required DateTime takenAt,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       assetId = Value(assetId),
       quantity = Value(quantity),
       takenAt = Value(takenAt);
  static Insertable<AssetSnapshotsData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<String>? assetId,
    Expression<int>? quantity,
    Expression<DateTime>? takenAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (assetId != null) 'asset_id': assetId,
      if (quantity != null) 'quantity': quantity,
      if (takenAt != null) 'taken_at': takenAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  AssetSnapshotsCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<String>? assetId,
    Value<int>? quantity,
    Value<DateTime>? takenAt,
    Value<int>? rowid,
  }) {
    return AssetSnapshotsCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      assetId: assetId ?? this.assetId,
      quantity: quantity ?? this.quantity,
      takenAt: takenAt ?? this.takenAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (assetId.present) {
      map['asset_id'] = Variable<String>(assetId.value);
    }
    if (quantity.present) {
      map['quantity'] = Variable<int>(quantity.value);
    }
    if (takenAt.present) {
      map['taken_at'] = Variable<DateTime>(takenAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('AssetSnapshotsCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('assetId: $assetId, ')
          ..write('quantity: $quantity, ')
          ..write('takenAt: $takenAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class VaultTransactions extends Table
    with TableInfo<VaultTransactions, VaultTransactionsData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  VaultTransactions(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<String> vaultAssetId = GeneratedColumn<String>(
    'vault_asset_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES assets (id)',
    ),
  );
  late final GeneratedColumn<String> type = GeneratedColumn<String>(
    'type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<int> amountMinor = GeneratedColumn<int>(
    'amount_minor',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> currency = GeneratedColumn<String>(
    'currency',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> reason = GeneratedColumn<String>(
    'reason',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> reasonNote = GeneratedColumn<String>(
    'reason_note',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<String> incomeId = GeneratedColumn<String>(
    'income_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES incomes (id)',
    ),
  );
  late final GeneratedColumn<String> memberId = GeneratedColumn<String>(
    'member_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES members (id)',
    ),
  );
  late final GeneratedColumn<DateTime> occurredAt = GeneratedColumn<DateTime>(
    'occurred_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    vaultAssetId,
    type,
    amountMinor,
    currency,
    reason,
    reasonNote,
    incomeId,
    memberId,
    occurredAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'vault_transactions';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  VaultTransactionsData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return VaultTransactionsData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      vaultAssetId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}vault_asset_id'],
      )!,
      type: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}type'],
      )!,
      amountMinor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}amount_minor'],
      )!,
      currency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}currency'],
      )!,
      reason: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}reason'],
      )!,
      reasonNote: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}reason_note'],
      ),
      incomeId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}income_id'],
      ),
      memberId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}member_id'],
      ),
      occurredAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}occurred_at'],
      )!,
    );
  }

  @override
  VaultTransactions createAlias(String alias) {
    return VaultTransactions(attachedDatabase, alias);
  }

  @override
  List<String> get customConstraints => const [
    'CHECK (amount_minor > 0)',
    'CHECK (type <> \'withdraw\' OR (reason_note IS NOT NULL AND length(trim(reason_note)) > 0))',
  ];
}

class VaultTransactionsData extends DataClass
    implements Insertable<VaultTransactionsData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final String vaultAssetId;
  final String type;
  final int amountMinor;
  final String currency;
  final String reason;
  final String? reasonNote;
  final String? incomeId;
  final String? memberId;
  final DateTime occurredAt;
  const VaultTransactionsData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    required this.vaultAssetId,
    required this.type,
    required this.amountMinor,
    required this.currency,
    required this.reason,
    this.reasonNote,
    this.incomeId,
    this.memberId,
    required this.occurredAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    map['vault_asset_id'] = Variable<String>(vaultAssetId);
    map['type'] = Variable<String>(type);
    map['amount_minor'] = Variable<int>(amountMinor);
    map['currency'] = Variable<String>(currency);
    map['reason'] = Variable<String>(reason);
    if (!nullToAbsent || reasonNote != null) {
      map['reason_note'] = Variable<String>(reasonNote);
    }
    if (!nullToAbsent || incomeId != null) {
      map['income_id'] = Variable<String>(incomeId);
    }
    if (!nullToAbsent || memberId != null) {
      map['member_id'] = Variable<String>(memberId);
    }
    map['occurred_at'] = Variable<DateTime>(occurredAt);
    return map;
  }

  VaultTransactionsCompanion toCompanion(bool nullToAbsent) {
    return VaultTransactionsCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      vaultAssetId: Value(vaultAssetId),
      type: Value(type),
      amountMinor: Value(amountMinor),
      currency: Value(currency),
      reason: Value(reason),
      reasonNote: reasonNote == null && nullToAbsent
          ? const Value.absent()
          : Value(reasonNote),
      incomeId: incomeId == null && nullToAbsent
          ? const Value.absent()
          : Value(incomeId),
      memberId: memberId == null && nullToAbsent
          ? const Value.absent()
          : Value(memberId),
      occurredAt: Value(occurredAt),
    );
  }

  factory VaultTransactionsData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return VaultTransactionsData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      vaultAssetId: serializer.fromJson<String>(json['vaultAssetId']),
      type: serializer.fromJson<String>(json['type']),
      amountMinor: serializer.fromJson<int>(json['amountMinor']),
      currency: serializer.fromJson<String>(json['currency']),
      reason: serializer.fromJson<String>(json['reason']),
      reasonNote: serializer.fromJson<String?>(json['reasonNote']),
      incomeId: serializer.fromJson<String?>(json['incomeId']),
      memberId: serializer.fromJson<String?>(json['memberId']),
      occurredAt: serializer.fromJson<DateTime>(json['occurredAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'vaultAssetId': serializer.toJson<String>(vaultAssetId),
      'type': serializer.toJson<String>(type),
      'amountMinor': serializer.toJson<int>(amountMinor),
      'currency': serializer.toJson<String>(currency),
      'reason': serializer.toJson<String>(reason),
      'reasonNote': serializer.toJson<String?>(reasonNote),
      'incomeId': serializer.toJson<String?>(incomeId),
      'memberId': serializer.toJson<String?>(memberId),
      'occurredAt': serializer.toJson<DateTime>(occurredAt),
    };
  }

  VaultTransactionsData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    String? vaultAssetId,
    String? type,
    int? amountMinor,
    String? currency,
    String? reason,
    Value<String?> reasonNote = const Value.absent(),
    Value<String?> incomeId = const Value.absent(),
    Value<String?> memberId = const Value.absent(),
    DateTime? occurredAt,
  }) => VaultTransactionsData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    vaultAssetId: vaultAssetId ?? this.vaultAssetId,
    type: type ?? this.type,
    amountMinor: amountMinor ?? this.amountMinor,
    currency: currency ?? this.currency,
    reason: reason ?? this.reason,
    reasonNote: reasonNote.present ? reasonNote.value : this.reasonNote,
    incomeId: incomeId.present ? incomeId.value : this.incomeId,
    memberId: memberId.present ? memberId.value : this.memberId,
    occurredAt: occurredAt ?? this.occurredAt,
  );
  VaultTransactionsData copyWithCompanion(VaultTransactionsCompanion data) {
    return VaultTransactionsData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      vaultAssetId: data.vaultAssetId.present
          ? data.vaultAssetId.value
          : this.vaultAssetId,
      type: data.type.present ? data.type.value : this.type,
      amountMinor: data.amountMinor.present
          ? data.amountMinor.value
          : this.amountMinor,
      currency: data.currency.present ? data.currency.value : this.currency,
      reason: data.reason.present ? data.reason.value : this.reason,
      reasonNote: data.reasonNote.present
          ? data.reasonNote.value
          : this.reasonNote,
      incomeId: data.incomeId.present ? data.incomeId.value : this.incomeId,
      memberId: data.memberId.present ? data.memberId.value : this.memberId,
      occurredAt: data.occurredAt.present
          ? data.occurredAt.value
          : this.occurredAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('VaultTransactionsData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('vaultAssetId: $vaultAssetId, ')
          ..write('type: $type, ')
          ..write('amountMinor: $amountMinor, ')
          ..write('currency: $currency, ')
          ..write('reason: $reason, ')
          ..write('reasonNote: $reasonNote, ')
          ..write('incomeId: $incomeId, ')
          ..write('memberId: $memberId, ')
          ..write('occurredAt: $occurredAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    vaultAssetId,
    type,
    amountMinor,
    currency,
    reason,
    reasonNote,
    incomeId,
    memberId,
    occurredAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is VaultTransactionsData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.vaultAssetId == this.vaultAssetId &&
          other.type == this.type &&
          other.amountMinor == this.amountMinor &&
          other.currency == this.currency &&
          other.reason == this.reason &&
          other.reasonNote == this.reasonNote &&
          other.incomeId == this.incomeId &&
          other.memberId == this.memberId &&
          other.occurredAt == this.occurredAt);
}

class VaultTransactionsCompanion
    extends UpdateCompanion<VaultTransactionsData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<String> vaultAssetId;
  final Value<String> type;
  final Value<int> amountMinor;
  final Value<String> currency;
  final Value<String> reason;
  final Value<String?> reasonNote;
  final Value<String?> incomeId;
  final Value<String?> memberId;
  final Value<DateTime> occurredAt;
  final Value<int> rowid;
  const VaultTransactionsCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.vaultAssetId = const Value.absent(),
    this.type = const Value.absent(),
    this.amountMinor = const Value.absent(),
    this.currency = const Value.absent(),
    this.reason = const Value.absent(),
    this.reasonNote = const Value.absent(),
    this.incomeId = const Value.absent(),
    this.memberId = const Value.absent(),
    this.occurredAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  VaultTransactionsCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    required String vaultAssetId,
    required String type,
    required int amountMinor,
    required String currency,
    required String reason,
    this.reasonNote = const Value.absent(),
    this.incomeId = const Value.absent(),
    this.memberId = const Value.absent(),
    required DateTime occurredAt,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       vaultAssetId = Value(vaultAssetId),
       type = Value(type),
       amountMinor = Value(amountMinor),
       currency = Value(currency),
       reason = Value(reason),
       occurredAt = Value(occurredAt);
  static Insertable<VaultTransactionsData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<String>? vaultAssetId,
    Expression<String>? type,
    Expression<int>? amountMinor,
    Expression<String>? currency,
    Expression<String>? reason,
    Expression<String>? reasonNote,
    Expression<String>? incomeId,
    Expression<String>? memberId,
    Expression<DateTime>? occurredAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (vaultAssetId != null) 'vault_asset_id': vaultAssetId,
      if (type != null) 'type': type,
      if (amountMinor != null) 'amount_minor': amountMinor,
      if (currency != null) 'currency': currency,
      if (reason != null) 'reason': reason,
      if (reasonNote != null) 'reason_note': reasonNote,
      if (incomeId != null) 'income_id': incomeId,
      if (memberId != null) 'member_id': memberId,
      if (occurredAt != null) 'occurred_at': occurredAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  VaultTransactionsCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<String>? vaultAssetId,
    Value<String>? type,
    Value<int>? amountMinor,
    Value<String>? currency,
    Value<String>? reason,
    Value<String?>? reasonNote,
    Value<String?>? incomeId,
    Value<String?>? memberId,
    Value<DateTime>? occurredAt,
    Value<int>? rowid,
  }) {
    return VaultTransactionsCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      vaultAssetId: vaultAssetId ?? this.vaultAssetId,
      type: type ?? this.type,
      amountMinor: amountMinor ?? this.amountMinor,
      currency: currency ?? this.currency,
      reason: reason ?? this.reason,
      reasonNote: reasonNote ?? this.reasonNote,
      incomeId: incomeId ?? this.incomeId,
      memberId: memberId ?? this.memberId,
      occurredAt: occurredAt ?? this.occurredAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (vaultAssetId.present) {
      map['vault_asset_id'] = Variable<String>(vaultAssetId.value);
    }
    if (type.present) {
      map['type'] = Variable<String>(type.value);
    }
    if (amountMinor.present) {
      map['amount_minor'] = Variable<int>(amountMinor.value);
    }
    if (currency.present) {
      map['currency'] = Variable<String>(currency.value);
    }
    if (reason.present) {
      map['reason'] = Variable<String>(reason.value);
    }
    if (reasonNote.present) {
      map['reason_note'] = Variable<String>(reasonNote.value);
    }
    if (incomeId.present) {
      map['income_id'] = Variable<String>(incomeId.value);
    }
    if (memberId.present) {
      map['member_id'] = Variable<String>(memberId.value);
    }
    if (occurredAt.present) {
      map['occurred_at'] = Variable<DateTime>(occurredAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('VaultTransactionsCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('vaultAssetId: $vaultAssetId, ')
          ..write('type: $type, ')
          ..write('amountMinor: $amountMinor, ')
          ..write('currency: $currency, ')
          ..write('reason: $reason, ')
          ..write('reasonNote: $reasonNote, ')
          ..write('incomeId: $incomeId, ')
          ..write('memberId: $memberId, ')
          ..write('occurredAt: $occurredAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class AllocationRules extends Table
    with TableInfo<AllocationRules, AllocationRulesData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  AllocationRules(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<String> vaultAssetId = GeneratedColumn<String>(
    'vault_asset_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES assets (id)',
    ),
  );
  late final GeneratedColumn<String> mode = GeneratedColumn<String>(
    'mode',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<int> basisPoints = GeneratedColumn<int>(
    'basis_points',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> fixedAmountMinor = GeneratedColumn<int>(
    'fixed_amount_minor',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<String> currency = GeneratedColumn<String>(
    'currency',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<bool> isActive = GeneratedColumn<bool>(
    'is_active',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_active" IN (0, 1))',
    ),
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<DateTime> progressionOfferedAt =
      GeneratedColumn<DateTime>(
        'progression_offered_at',
        aliasedName,
        true,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: false,
      );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    vaultAssetId,
    mode,
    basisPoints,
    fixedAmountMinor,
    currency,
    isActive,
    progressionOfferedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'allocation_rules';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  AllocationRulesData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return AllocationRulesData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      vaultAssetId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}vault_asset_id'],
      )!,
      mode: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}mode'],
      )!,
      basisPoints: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}basis_points'],
      ),
      fixedAmountMinor: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}fixed_amount_minor'],
      ),
      currency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}currency'],
      )!,
      isActive: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_active'],
      )!,
      progressionOfferedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}progression_offered_at'],
      ),
    );
  }

  @override
  AllocationRules createAlias(String alias) {
    return AllocationRules(attachedDatabase, alias);
  }

  @override
  List<String> get customConstraints => const [
    'CHECK (basis_points IS NOT NULL OR fixed_amount_minor IS NOT NULL)',
    'CHECK (basis_points IS NULL OR basis_points BETWEEN 0 AND 10000)',
  ];
}

class AllocationRulesData extends DataClass
    implements Insertable<AllocationRulesData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final String vaultAssetId;
  final String mode;
  final int? basisPoints;
  final int? fixedAmountMinor;
  final String currency;
  final bool isActive;
  final DateTime? progressionOfferedAt;
  const AllocationRulesData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    required this.vaultAssetId,
    required this.mode,
    this.basisPoints,
    this.fixedAmountMinor,
    required this.currency,
    required this.isActive,
    this.progressionOfferedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    map['vault_asset_id'] = Variable<String>(vaultAssetId);
    map['mode'] = Variable<String>(mode);
    if (!nullToAbsent || basisPoints != null) {
      map['basis_points'] = Variable<int>(basisPoints);
    }
    if (!nullToAbsent || fixedAmountMinor != null) {
      map['fixed_amount_minor'] = Variable<int>(fixedAmountMinor);
    }
    map['currency'] = Variable<String>(currency);
    map['is_active'] = Variable<bool>(isActive);
    if (!nullToAbsent || progressionOfferedAt != null) {
      map['progression_offered_at'] = Variable<DateTime>(progressionOfferedAt);
    }
    return map;
  }

  AllocationRulesCompanion toCompanion(bool nullToAbsent) {
    return AllocationRulesCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      vaultAssetId: Value(vaultAssetId),
      mode: Value(mode),
      basisPoints: basisPoints == null && nullToAbsent
          ? const Value.absent()
          : Value(basisPoints),
      fixedAmountMinor: fixedAmountMinor == null && nullToAbsent
          ? const Value.absent()
          : Value(fixedAmountMinor),
      currency: Value(currency),
      isActive: Value(isActive),
      progressionOfferedAt: progressionOfferedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(progressionOfferedAt),
    );
  }

  factory AllocationRulesData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return AllocationRulesData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      vaultAssetId: serializer.fromJson<String>(json['vaultAssetId']),
      mode: serializer.fromJson<String>(json['mode']),
      basisPoints: serializer.fromJson<int?>(json['basisPoints']),
      fixedAmountMinor: serializer.fromJson<int?>(json['fixedAmountMinor']),
      currency: serializer.fromJson<String>(json['currency']),
      isActive: serializer.fromJson<bool>(json['isActive']),
      progressionOfferedAt: serializer.fromJson<DateTime?>(
        json['progressionOfferedAt'],
      ),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'vaultAssetId': serializer.toJson<String>(vaultAssetId),
      'mode': serializer.toJson<String>(mode),
      'basisPoints': serializer.toJson<int?>(basisPoints),
      'fixedAmountMinor': serializer.toJson<int?>(fixedAmountMinor),
      'currency': serializer.toJson<String>(currency),
      'isActive': serializer.toJson<bool>(isActive),
      'progressionOfferedAt': serializer.toJson<DateTime?>(
        progressionOfferedAt,
      ),
    };
  }

  AllocationRulesData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    String? vaultAssetId,
    String? mode,
    Value<int?> basisPoints = const Value.absent(),
    Value<int?> fixedAmountMinor = const Value.absent(),
    String? currency,
    bool? isActive,
    Value<DateTime?> progressionOfferedAt = const Value.absent(),
  }) => AllocationRulesData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    vaultAssetId: vaultAssetId ?? this.vaultAssetId,
    mode: mode ?? this.mode,
    basisPoints: basisPoints.present ? basisPoints.value : this.basisPoints,
    fixedAmountMinor: fixedAmountMinor.present
        ? fixedAmountMinor.value
        : this.fixedAmountMinor,
    currency: currency ?? this.currency,
    isActive: isActive ?? this.isActive,
    progressionOfferedAt: progressionOfferedAt.present
        ? progressionOfferedAt.value
        : this.progressionOfferedAt,
  );
  AllocationRulesData copyWithCompanion(AllocationRulesCompanion data) {
    return AllocationRulesData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      vaultAssetId: data.vaultAssetId.present
          ? data.vaultAssetId.value
          : this.vaultAssetId,
      mode: data.mode.present ? data.mode.value : this.mode,
      basisPoints: data.basisPoints.present
          ? data.basisPoints.value
          : this.basisPoints,
      fixedAmountMinor: data.fixedAmountMinor.present
          ? data.fixedAmountMinor.value
          : this.fixedAmountMinor,
      currency: data.currency.present ? data.currency.value : this.currency,
      isActive: data.isActive.present ? data.isActive.value : this.isActive,
      progressionOfferedAt: data.progressionOfferedAt.present
          ? data.progressionOfferedAt.value
          : this.progressionOfferedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('AllocationRulesData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('vaultAssetId: $vaultAssetId, ')
          ..write('mode: $mode, ')
          ..write('basisPoints: $basisPoints, ')
          ..write('fixedAmountMinor: $fixedAmountMinor, ')
          ..write('currency: $currency, ')
          ..write('isActive: $isActive, ')
          ..write('progressionOfferedAt: $progressionOfferedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    vaultAssetId,
    mode,
    basisPoints,
    fixedAmountMinor,
    currency,
    isActive,
    progressionOfferedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is AllocationRulesData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.vaultAssetId == this.vaultAssetId &&
          other.mode == this.mode &&
          other.basisPoints == this.basisPoints &&
          other.fixedAmountMinor == this.fixedAmountMinor &&
          other.currency == this.currency &&
          other.isActive == this.isActive &&
          other.progressionOfferedAt == this.progressionOfferedAt);
}

class AllocationRulesCompanion extends UpdateCompanion<AllocationRulesData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<String> vaultAssetId;
  final Value<String> mode;
  final Value<int?> basisPoints;
  final Value<int?> fixedAmountMinor;
  final Value<String> currency;
  final Value<bool> isActive;
  final Value<DateTime?> progressionOfferedAt;
  final Value<int> rowid;
  const AllocationRulesCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.vaultAssetId = const Value.absent(),
    this.mode = const Value.absent(),
    this.basisPoints = const Value.absent(),
    this.fixedAmountMinor = const Value.absent(),
    this.currency = const Value.absent(),
    this.isActive = const Value.absent(),
    this.progressionOfferedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  AllocationRulesCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    required String vaultAssetId,
    required String mode,
    this.basisPoints = const Value.absent(),
    this.fixedAmountMinor = const Value.absent(),
    required String currency,
    this.isActive = const Value.absent(),
    this.progressionOfferedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       vaultAssetId = Value(vaultAssetId),
       mode = Value(mode),
       currency = Value(currency);
  static Insertable<AllocationRulesData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<String>? vaultAssetId,
    Expression<String>? mode,
    Expression<int>? basisPoints,
    Expression<int>? fixedAmountMinor,
    Expression<String>? currency,
    Expression<bool>? isActive,
    Expression<DateTime>? progressionOfferedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (vaultAssetId != null) 'vault_asset_id': vaultAssetId,
      if (mode != null) 'mode': mode,
      if (basisPoints != null) 'basis_points': basisPoints,
      if (fixedAmountMinor != null) 'fixed_amount_minor': fixedAmountMinor,
      if (currency != null) 'currency': currency,
      if (isActive != null) 'is_active': isActive,
      if (progressionOfferedAt != null)
        'progression_offered_at': progressionOfferedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  AllocationRulesCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<String>? vaultAssetId,
    Value<String>? mode,
    Value<int?>? basisPoints,
    Value<int?>? fixedAmountMinor,
    Value<String>? currency,
    Value<bool>? isActive,
    Value<DateTime?>? progressionOfferedAt,
    Value<int>? rowid,
  }) {
    return AllocationRulesCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      vaultAssetId: vaultAssetId ?? this.vaultAssetId,
      mode: mode ?? this.mode,
      basisPoints: basisPoints ?? this.basisPoints,
      fixedAmountMinor: fixedAmountMinor ?? this.fixedAmountMinor,
      currency: currency ?? this.currency,
      isActive: isActive ?? this.isActive,
      progressionOfferedAt: progressionOfferedAt ?? this.progressionOfferedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (vaultAssetId.present) {
      map['vault_asset_id'] = Variable<String>(vaultAssetId.value);
    }
    if (mode.present) {
      map['mode'] = Variable<String>(mode.value);
    }
    if (basisPoints.present) {
      map['basis_points'] = Variable<int>(basisPoints.value);
    }
    if (fixedAmountMinor.present) {
      map['fixed_amount_minor'] = Variable<int>(fixedAmountMinor.value);
    }
    if (currency.present) {
      map['currency'] = Variable<String>(currency.value);
    }
    if (isActive.present) {
      map['is_active'] = Variable<bool>(isActive.value);
    }
    if (progressionOfferedAt.present) {
      map['progression_offered_at'] = Variable<DateTime>(
        progressionOfferedAt.value,
      );
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('AllocationRulesCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('vaultAssetId: $vaultAssetId, ')
          ..write('mode: $mode, ')
          ..write('basisPoints: $basisPoints, ')
          ..write('fixedAmountMinor: $fixedAmountMinor, ')
          ..write('currency: $currency, ')
          ..write('isActive: $isActive, ')
          ..write('progressionOfferedAt: $progressionOfferedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class FxRates extends Table with TableInfo<FxRates, FxRatesData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  FxRates(this.attachedDatabase, [this._alias]);
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> householdId = GeneratedColumn<String>(
    'household_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('1'),
  );
  late final GeneratedColumn<String> fromCurrency = GeneratedColumn<String>(
    'from_currency',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> toCurrency = GeneratedColumn<String>(
    'to_currency',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<int> rateNumerator = GeneratedColumn<int>(
    'rate_numerator',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<int> rateDenominator = GeneratedColumn<int>(
    'rate_denominator',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> rateDate = GeneratedColumn<String>(
    'rate_date',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  late final GeneratedColumn<String> source = GeneratedColumn<String>(
    'source',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const CustomExpression('\'manual\''),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    fromCurrency,
    toCurrency,
    rateNumerator,
    rateDenominator,
    rateDate,
    source,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'fx_rates';
  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  FxRatesData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return FxRatesData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      householdId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}household_id'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      fromCurrency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}from_currency'],
      )!,
      toCurrency: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}to_currency'],
      )!,
      rateNumerator: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}rate_numerator'],
      )!,
      rateDenominator: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}rate_denominator'],
      )!,
      rateDate: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}rate_date'],
      )!,
      source: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source'],
      )!,
    );
  }

  @override
  FxRates createAlias(String alias) {
    return FxRates(attachedDatabase, alias);
  }

  @override
  List<String> get customConstraints => const [
    'CHECK (rate_numerator > 0 AND rate_denominator > 0)',
  ];
}

class FxRatesData extends DataClass implements Insertable<FxRatesData> {
  final String id;
  final String householdId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final int version;
  final String fromCurrency;
  final String toCurrency;
  final int rateNumerator;
  final int rateDenominator;
  final String rateDate;
  final String source;
  const FxRatesData({
    required this.id,
    required this.householdId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.version,
    required this.fromCurrency,
    required this.toCurrency,
    required this.rateNumerator,
    required this.rateDenominator,
    required this.rateDate,
    required this.source,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['household_id'] = Variable<String>(householdId);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    map['version'] = Variable<int>(version);
    map['from_currency'] = Variable<String>(fromCurrency);
    map['to_currency'] = Variable<String>(toCurrency);
    map['rate_numerator'] = Variable<int>(rateNumerator);
    map['rate_denominator'] = Variable<int>(rateDenominator);
    map['rate_date'] = Variable<String>(rateDate);
    map['source'] = Variable<String>(source);
    return map;
  }

  FxRatesCompanion toCompanion(bool nullToAbsent) {
    return FxRatesCompanion(
      id: Value(id),
      householdId: Value(householdId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      version: Value(version),
      fromCurrency: Value(fromCurrency),
      toCurrency: Value(toCurrency),
      rateNumerator: Value(rateNumerator),
      rateDenominator: Value(rateDenominator),
      rateDate: Value(rateDate),
      source: Value(source),
    );
  }

  factory FxRatesData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return FxRatesData(
      id: serializer.fromJson<String>(json['id']),
      householdId: serializer.fromJson<String>(json['householdId']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      version: serializer.fromJson<int>(json['version']),
      fromCurrency: serializer.fromJson<String>(json['fromCurrency']),
      toCurrency: serializer.fromJson<String>(json['toCurrency']),
      rateNumerator: serializer.fromJson<int>(json['rateNumerator']),
      rateDenominator: serializer.fromJson<int>(json['rateDenominator']),
      rateDate: serializer.fromJson<String>(json['rateDate']),
      source: serializer.fromJson<String>(json['source']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'householdId': serializer.toJson<String>(householdId),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'version': serializer.toJson<int>(version),
      'fromCurrency': serializer.toJson<String>(fromCurrency),
      'toCurrency': serializer.toJson<String>(toCurrency),
      'rateNumerator': serializer.toJson<int>(rateNumerator),
      'rateDenominator': serializer.toJson<int>(rateDenominator),
      'rateDate': serializer.toJson<String>(rateDate),
      'source': serializer.toJson<String>(source),
    };
  }

  FxRatesData copyWith({
    String? id,
    String? householdId,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    int? version,
    String? fromCurrency,
    String? toCurrency,
    int? rateNumerator,
    int? rateDenominator,
    String? rateDate,
    String? source,
  }) => FxRatesData(
    id: id ?? this.id,
    householdId: householdId ?? this.householdId,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    version: version ?? this.version,
    fromCurrency: fromCurrency ?? this.fromCurrency,
    toCurrency: toCurrency ?? this.toCurrency,
    rateNumerator: rateNumerator ?? this.rateNumerator,
    rateDenominator: rateDenominator ?? this.rateDenominator,
    rateDate: rateDate ?? this.rateDate,
    source: source ?? this.source,
  );
  FxRatesData copyWithCompanion(FxRatesCompanion data) {
    return FxRatesData(
      id: data.id.present ? data.id.value : this.id,
      householdId: data.householdId.present
          ? data.householdId.value
          : this.householdId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      version: data.version.present ? data.version.value : this.version,
      fromCurrency: data.fromCurrency.present
          ? data.fromCurrency.value
          : this.fromCurrency,
      toCurrency: data.toCurrency.present
          ? data.toCurrency.value
          : this.toCurrency,
      rateNumerator: data.rateNumerator.present
          ? data.rateNumerator.value
          : this.rateNumerator,
      rateDenominator: data.rateDenominator.present
          ? data.rateDenominator.value
          : this.rateDenominator,
      rateDate: data.rateDate.present ? data.rateDate.value : this.rateDate,
      source: data.source.present ? data.source.value : this.source,
    );
  }

  @override
  String toString() {
    return (StringBuffer('FxRatesData(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('fromCurrency: $fromCurrency, ')
          ..write('toCurrency: $toCurrency, ')
          ..write('rateNumerator: $rateNumerator, ')
          ..write('rateDenominator: $rateDenominator, ')
          ..write('rateDate: $rateDate, ')
          ..write('source: $source')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    householdId,
    createdAt,
    updatedAt,
    deletedAt,
    version,
    fromCurrency,
    toCurrency,
    rateNumerator,
    rateDenominator,
    rateDate,
    source,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is FxRatesData &&
          other.id == this.id &&
          other.householdId == this.householdId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.version == this.version &&
          other.fromCurrency == this.fromCurrency &&
          other.toCurrency == this.toCurrency &&
          other.rateNumerator == this.rateNumerator &&
          other.rateDenominator == this.rateDenominator &&
          other.rateDate == this.rateDate &&
          other.source == this.source);
}

class FxRatesCompanion extends UpdateCompanion<FxRatesData> {
  final Value<String> id;
  final Value<String> householdId;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<int> version;
  final Value<String> fromCurrency;
  final Value<String> toCurrency;
  final Value<int> rateNumerator;
  final Value<int> rateDenominator;
  final Value<String> rateDate;
  final Value<String> source;
  final Value<int> rowid;
  const FxRatesCompanion({
    this.id = const Value.absent(),
    this.householdId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    this.fromCurrency = const Value.absent(),
    this.toCurrency = const Value.absent(),
    this.rateNumerator = const Value.absent(),
    this.rateDenominator = const Value.absent(),
    this.rateDate = const Value.absent(),
    this.source = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  FxRatesCompanion.insert({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    this.version = const Value.absent(),
    required String fromCurrency,
    required String toCurrency,
    required int rateNumerator,
    required int rateDenominator,
    required String rateDate,
    this.source = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       householdId = Value(householdId),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       fromCurrency = Value(fromCurrency),
       toCurrency = Value(toCurrency),
       rateNumerator = Value(rateNumerator),
       rateDenominator = Value(rateDenominator),
       rateDate = Value(rateDate);
  static Insertable<FxRatesData> custom({
    Expression<String>? id,
    Expression<String>? householdId,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? version,
    Expression<String>? fromCurrency,
    Expression<String>? toCurrency,
    Expression<int>? rateNumerator,
    Expression<int>? rateDenominator,
    Expression<String>? rateDate,
    Expression<String>? source,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (householdId != null) 'household_id': householdId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (version != null) 'version': version,
      if (fromCurrency != null) 'from_currency': fromCurrency,
      if (toCurrency != null) 'to_currency': toCurrency,
      if (rateNumerator != null) 'rate_numerator': rateNumerator,
      if (rateDenominator != null) 'rate_denominator': rateDenominator,
      if (rateDate != null) 'rate_date': rateDate,
      if (source != null) 'source': source,
      if (rowid != null) 'rowid': rowid,
    });
  }

  FxRatesCompanion copyWith({
    Value<String>? id,
    Value<String>? householdId,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<int>? version,
    Value<String>? fromCurrency,
    Value<String>? toCurrency,
    Value<int>? rateNumerator,
    Value<int>? rateDenominator,
    Value<String>? rateDate,
    Value<String>? source,
    Value<int>? rowid,
  }) {
    return FxRatesCompanion(
      id: id ?? this.id,
      householdId: householdId ?? this.householdId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      version: version ?? this.version,
      fromCurrency: fromCurrency ?? this.fromCurrency,
      toCurrency: toCurrency ?? this.toCurrency,
      rateNumerator: rateNumerator ?? this.rateNumerator,
      rateDenominator: rateDenominator ?? this.rateDenominator,
      rateDate: rateDate ?? this.rateDate,
      source: source ?? this.source,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (householdId.present) {
      map['household_id'] = Variable<String>(householdId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (fromCurrency.present) {
      map['from_currency'] = Variable<String>(fromCurrency.value);
    }
    if (toCurrency.present) {
      map['to_currency'] = Variable<String>(toCurrency.value);
    }
    if (rateNumerator.present) {
      map['rate_numerator'] = Variable<int>(rateNumerator.value);
    }
    if (rateDenominator.present) {
      map['rate_denominator'] = Variable<int>(rateDenominator.value);
    }
    if (rateDate.present) {
      map['rate_date'] = Variable<String>(rateDate.value);
    }
    if (source.present) {
      map['source'] = Variable<String>(source.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('FxRatesCompanion(')
          ..write('id: $id, ')
          ..write('householdId: $householdId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('version: $version, ')
          ..write('fromCurrency: $fromCurrency, ')
          ..write('toCurrency: $toCurrency, ')
          ..write('rateNumerator: $rateNumerator, ')
          ..write('rateDenominator: $rateDenominator, ')
          ..write('rateDate: $rateDate, ')
          ..write('source: $source, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class DatabaseAtV2 extends GeneratedDatabase {
  DatabaseAtV2(QueryExecutor e) : super(e);
  late final Households households = Households(this);
  late final Members members = Members(this);
  late final Categories categories = Categories(this);
  late final Incomes incomes = Incomes(this);
  late final Expenses expenses = Expenses(this);
  late final Debts debts = Debts(this);
  late final Obligations obligations = Obligations(this);
  late final Assets assets = Assets(this);
  late final AssetSnapshots assetSnapshots = AssetSnapshots(this);
  late final VaultTransactions vaultTransactions = VaultTransactions(this);
  late final AllocationRules allocationRules = AllocationRules(this);
  late final FxRates fxRates = FxRates(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    households,
    members,
    categories,
    incomes,
    expenses,
    debts,
    obligations,
    assets,
    assetSnapshots,
    vaultTransactions,
    allocationRules,
    fxRates,
  ];
  @override
  int get schemaVersion => 2;
  @override
  DriftDatabaseOptions get options =>
      const DriftDatabaseOptions(storeDateTimeAsText: true);
}
