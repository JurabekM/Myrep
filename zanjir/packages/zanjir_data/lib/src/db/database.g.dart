// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'database.dart';

// ignore_for_file: type=lint
class $OrganizationsTable extends Organizations with TableInfo<$OrganizationsTable, OrganizationRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $OrganizationsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _deletedMeta = const VerificationMeta('deleted');
  @override
  late final GeneratedColumn<bool> deleted = GeneratedColumn<bool>(
    'deleted',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("deleted" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _licenseNoMeta = const VerificationMeta('licenseNo');
  @override
  late final GeneratedColumn<String> licenseNo = GeneratedColumn<String>(
    'license_no',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _licenseValidUntilMeta = const VerificationMeta('licenseValidUntil');
  @override
  late final GeneratedColumn<DateTime> licenseValidUntil = GeneratedColumn<DateTime>(
    'license_valid_until',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [id, createdAt, updatedAt, rev, deleted, name, licenseNo, licenseValidUntil];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'organization';
  @override
  VerificationContext validateIntegrity(Insertable<OrganizationRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('deleted')) {
      context.handle(_deletedMeta, deleted.isAcceptableOrUnknown(data['deleted']!, _deletedMeta));
    }
    if (data.containsKey('name')) {
      context.handle(_nameMeta, name.isAcceptableOrUnknown(data['name']!, _nameMeta));
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('license_no')) {
      context.handle(_licenseNoMeta, licenseNo.isAcceptableOrUnknown(data['license_no']!, _licenseNoMeta));
    }
    if (data.containsKey('license_valid_until')) {
      context.handle(
        _licenseValidUntilMeta,
        licenseValidUntil.isAcceptableOrUnknown(data['license_valid_until']!, _licenseValidUntilMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  OrganizationRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return OrganizationRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      deleted: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}deleted'])!,
      name: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}name'])!,
      licenseNo: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}license_no']),
      licenseValidUntil: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}license_valid_until'],
      ),
    );
  }

  @override
  $OrganizationsTable createAlias(String alias) {
    return $OrganizationsTable(attachedDatabase, alias);
  }
}

class OrganizationRow extends DataClass implements Insertable<OrganizationRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final bool deleted;
  final String name;
  final String? licenseNo;
  final DateTime? licenseValidUntil;
  const OrganizationRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.deleted,
    required this.name,
    this.licenseNo,
    this.licenseValidUntil,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['deleted'] = Variable<bool>(deleted);
    map['name'] = Variable<String>(name);
    if (!nullToAbsent || licenseNo != null) {
      map['license_no'] = Variable<String>(licenseNo);
    }
    if (!nullToAbsent || licenseValidUntil != null) {
      map['license_valid_until'] = Variable<DateTime>(licenseValidUntil);
    }
    return map;
  }

  OrganizationsCompanion toCompanion(bool nullToAbsent) {
    return OrganizationsCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      deleted: Value(deleted),
      name: Value(name),
      licenseNo: licenseNo == null && nullToAbsent ? const Value.absent() : Value(licenseNo),
      licenseValidUntil: licenseValidUntil == null && nullToAbsent ? const Value.absent() : Value(licenseValidUntil),
    );
  }

  factory OrganizationRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return OrganizationRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      deleted: serializer.fromJson<bool>(json['deleted']),
      name: serializer.fromJson<String>(json['name']),
      licenseNo: serializer.fromJson<String?>(json['licenseNo']),
      licenseValidUntil: serializer.fromJson<DateTime?>(json['licenseValidUntil']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'deleted': serializer.toJson<bool>(deleted),
      'name': serializer.toJson<String>(name),
      'licenseNo': serializer.toJson<String?>(licenseNo),
      'licenseValidUntil': serializer.toJson<DateTime?>(licenseValidUntil),
    };
  }

  OrganizationRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    bool? deleted,
    String? name,
    Value<String?> licenseNo = const Value.absent(),
    Value<DateTime?> licenseValidUntil = const Value.absent(),
  }) => OrganizationRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    deleted: deleted ?? this.deleted,
    name: name ?? this.name,
    licenseNo: licenseNo.present ? licenseNo.value : this.licenseNo,
    licenseValidUntil: licenseValidUntil.present ? licenseValidUntil.value : this.licenseValidUntil,
  );
  OrganizationRow copyWithCompanion(OrganizationsCompanion data) {
    return OrganizationRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      deleted: data.deleted.present ? data.deleted.value : this.deleted,
      name: data.name.present ? data.name.value : this.name,
      licenseNo: data.licenseNo.present ? data.licenseNo.value : this.licenseNo,
      licenseValidUntil: data.licenseValidUntil.present ? data.licenseValidUntil.value : this.licenseValidUntil,
    );
  }

  @override
  String toString() {
    return (StringBuffer('OrganizationRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('deleted: $deleted, ')
          ..write('name: $name, ')
          ..write('licenseNo: $licenseNo, ')
          ..write('licenseValidUntil: $licenseValidUntil')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, createdAt, updatedAt, rev, deleted, name, licenseNo, licenseValidUntil);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is OrganizationRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.deleted == this.deleted &&
          other.name == this.name &&
          other.licenseNo == this.licenseNo &&
          other.licenseValidUntil == this.licenseValidUntil);
}

class OrganizationsCompanion extends UpdateCompanion<OrganizationRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<bool> deleted;
  final Value<String> name;
  final Value<String?> licenseNo;
  final Value<DateTime?> licenseValidUntil;
  final Value<int> rowid;
  const OrganizationsCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.deleted = const Value.absent(),
    this.name = const Value.absent(),
    this.licenseNo = const Value.absent(),
    this.licenseValidUntil = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  OrganizationsCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    this.deleted = const Value.absent(),
    required String name,
    this.licenseNo = const Value.absent(),
    this.licenseValidUntil = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       name = Value(name);
  static Insertable<OrganizationRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<bool>? deleted,
    Expression<String>? name,
    Expression<String>? licenseNo,
    Expression<DateTime>? licenseValidUntil,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (deleted != null) 'deleted': deleted,
      if (name != null) 'name': name,
      if (licenseNo != null) 'license_no': licenseNo,
      if (licenseValidUntil != null) 'license_valid_until': licenseValidUntil,
      if (rowid != null) 'rowid': rowid,
    });
  }

  OrganizationsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<bool>? deleted,
    Value<String>? name,
    Value<String?>? licenseNo,
    Value<DateTime?>? licenseValidUntil,
    Value<int>? rowid,
  }) {
    return OrganizationsCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      deleted: deleted ?? this.deleted,
      name: name ?? this.name,
      licenseNo: licenseNo ?? this.licenseNo,
      licenseValidUntil: licenseValidUntil ?? this.licenseValidUntil,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (deleted.present) {
      map['deleted'] = Variable<bool>(deleted.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (licenseNo.present) {
      map['license_no'] = Variable<String>(licenseNo.value);
    }
    if (licenseValidUntil.present) {
      map['license_valid_until'] = Variable<DateTime>(licenseValidUntil.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('OrganizationsCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('deleted: $deleted, ')
          ..write('name: $name, ')
          ..write('licenseNo: $licenseNo, ')
          ..write('licenseValidUntil: $licenseValidUntil, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $SitesTable extends Sites with TableInfo<$SitesTable, SiteRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SitesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _deletedMeta = const VerificationMeta('deleted');
  @override
  late final GeneratedColumn<bool> deleted = GeneratedColumn<bool>(
    'deleted',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("deleted" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _addressMeta = const VerificationMeta('address');
  @override
  late final GeneratedColumn<String> address = GeneratedColumn<String>(
    'address',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _customerMeta = const VerificationMeta('customer');
  @override
  late final GeneratedColumn<String> customer = GeneratedColumn<String>(
    'customer',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  late final GeneratedColumnWithTypeConverter<EarthingSystem?, String> earthingSystem = GeneratedColumn<String>(
    'earthing_system',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  ).withConverter<EarthingSystem?>($SitesTable.$converterearthingSystemn);
  static const VerificationMeta _u0VoltsMeta = const VerificationMeta('u0Volts');
  @override
  late final GeneratedColumn<double> u0Volts = GeneratedColumn<double>(
    'u0_volts',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    name,
    address,
    customer,
    earthingSystem,
    u0Volts,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'site';
  @override
  VerificationContext validateIntegrity(Insertable<SiteRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('deleted')) {
      context.handle(_deletedMeta, deleted.isAcceptableOrUnknown(data['deleted']!, _deletedMeta));
    }
    if (data.containsKey('name')) {
      context.handle(_nameMeta, name.isAcceptableOrUnknown(data['name']!, _nameMeta));
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('address')) {
      context.handle(_addressMeta, address.isAcceptableOrUnknown(data['address']!, _addressMeta));
    }
    if (data.containsKey('customer')) {
      context.handle(_customerMeta, customer.isAcceptableOrUnknown(data['customer']!, _customerMeta));
    }
    if (data.containsKey('u0_volts')) {
      context.handle(_u0VoltsMeta, u0Volts.isAcceptableOrUnknown(data['u0_volts']!, _u0VoltsMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  SiteRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SiteRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      deleted: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}deleted'])!,
      name: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}name'])!,
      address: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}address']),
      customer: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}customer']),
      earthingSystem: $SitesTable.$converterearthingSystemn.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}earthing_system']),
      ),
      u0Volts: attachedDatabase.typeMapping.read(DriftSqlType.double, data['${effectivePrefix}u0_volts']),
    );
  }

  @override
  $SitesTable createAlias(String alias) {
    return $SitesTable(attachedDatabase, alias);
  }

  static TypeConverter<EarthingSystem, String> $converterearthingSystem = earthingConverter;
  static TypeConverter<EarthingSystem?, String?> $converterearthingSystemn = NullAwareTypeConverter.wrap(
    $converterearthingSystem,
  );
}

class SiteRow extends DataClass implements Insertable<SiteRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final bool deleted;
  final String name;
  final String? address;
  final String? customer;
  final EarthingSystem? earthingSystem;
  final double? u0Volts;
  const SiteRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.deleted,
    required this.name,
    this.address,
    this.customer,
    this.earthingSystem,
    this.u0Volts,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['deleted'] = Variable<bool>(deleted);
    map['name'] = Variable<String>(name);
    if (!nullToAbsent || address != null) {
      map['address'] = Variable<String>(address);
    }
    if (!nullToAbsent || customer != null) {
      map['customer'] = Variable<String>(customer);
    }
    if (!nullToAbsent || earthingSystem != null) {
      map['earthing_system'] = Variable<String>($SitesTable.$converterearthingSystemn.toSql(earthingSystem));
    }
    if (!nullToAbsent || u0Volts != null) {
      map['u0_volts'] = Variable<double>(u0Volts);
    }
    return map;
  }

  SitesCompanion toCompanion(bool nullToAbsent) {
    return SitesCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      deleted: Value(deleted),
      name: Value(name),
      address: address == null && nullToAbsent ? const Value.absent() : Value(address),
      customer: customer == null && nullToAbsent ? const Value.absent() : Value(customer),
      earthingSystem: earthingSystem == null && nullToAbsent ? const Value.absent() : Value(earthingSystem),
      u0Volts: u0Volts == null && nullToAbsent ? const Value.absent() : Value(u0Volts),
    );
  }

  factory SiteRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SiteRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      deleted: serializer.fromJson<bool>(json['deleted']),
      name: serializer.fromJson<String>(json['name']),
      address: serializer.fromJson<String?>(json['address']),
      customer: serializer.fromJson<String?>(json['customer']),
      earthingSystem: serializer.fromJson<EarthingSystem?>(json['earthingSystem']),
      u0Volts: serializer.fromJson<double?>(json['u0Volts']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'deleted': serializer.toJson<bool>(deleted),
      'name': serializer.toJson<String>(name),
      'address': serializer.toJson<String?>(address),
      'customer': serializer.toJson<String?>(customer),
      'earthingSystem': serializer.toJson<EarthingSystem?>(earthingSystem),
      'u0Volts': serializer.toJson<double?>(u0Volts),
    };
  }

  SiteRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    bool? deleted,
    String? name,
    Value<String?> address = const Value.absent(),
    Value<String?> customer = const Value.absent(),
    Value<EarthingSystem?> earthingSystem = const Value.absent(),
    Value<double?> u0Volts = const Value.absent(),
  }) => SiteRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    deleted: deleted ?? this.deleted,
    name: name ?? this.name,
    address: address.present ? address.value : this.address,
    customer: customer.present ? customer.value : this.customer,
    earthingSystem: earthingSystem.present ? earthingSystem.value : this.earthingSystem,
    u0Volts: u0Volts.present ? u0Volts.value : this.u0Volts,
  );
  SiteRow copyWithCompanion(SitesCompanion data) {
    return SiteRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      deleted: data.deleted.present ? data.deleted.value : this.deleted,
      name: data.name.present ? data.name.value : this.name,
      address: data.address.present ? data.address.value : this.address,
      customer: data.customer.present ? data.customer.value : this.customer,
      earthingSystem: data.earthingSystem.present ? data.earthingSystem.value : this.earthingSystem,
      u0Volts: data.u0Volts.present ? data.u0Volts.value : this.u0Volts,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SiteRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('name: $name, ')
          ..write('address: $address, ')
          ..write('customer: $customer, ')
          ..write('earthingSystem: $earthingSystem, ')
          ..write('u0Volts: $u0Volts')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, createdAt, updatedAt, rev, orgId, deleted, name, address, customer, earthingSystem, u0Volts);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SiteRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.deleted == this.deleted &&
          other.name == this.name &&
          other.address == this.address &&
          other.customer == this.customer &&
          other.earthingSystem == this.earthingSystem &&
          other.u0Volts == this.u0Volts);
}

class SitesCompanion extends UpdateCompanion<SiteRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<bool> deleted;
  final Value<String> name;
  final Value<String?> address;
  final Value<String?> customer;
  final Value<EarthingSystem?> earthingSystem;
  final Value<double?> u0Volts;
  final Value<int> rowid;
  const SitesCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.deleted = const Value.absent(),
    this.name = const Value.absent(),
    this.address = const Value.absent(),
    this.customer = const Value.absent(),
    this.earthingSystem = const Value.absent(),
    this.u0Volts = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  SitesCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    this.deleted = const Value.absent(),
    required String name,
    this.address = const Value.absent(),
    this.customer = const Value.absent(),
    this.earthingSystem = const Value.absent(),
    this.u0Volts = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       name = Value(name);
  static Insertable<SiteRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<bool>? deleted,
    Expression<String>? name,
    Expression<String>? address,
    Expression<String>? customer,
    Expression<String>? earthingSystem,
    Expression<double>? u0Volts,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (deleted != null) 'deleted': deleted,
      if (name != null) 'name': name,
      if (address != null) 'address': address,
      if (customer != null) 'customer': customer,
      if (earthingSystem != null) 'earthing_system': earthingSystem,
      if (u0Volts != null) 'u0_volts': u0Volts,
      if (rowid != null) 'rowid': rowid,
    });
  }

  SitesCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<bool>? deleted,
    Value<String>? name,
    Value<String?>? address,
    Value<String?>? customer,
    Value<EarthingSystem?>? earthingSystem,
    Value<double?>? u0Volts,
    Value<int>? rowid,
  }) {
    return SitesCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      deleted: deleted ?? this.deleted,
      name: name ?? this.name,
      address: address ?? this.address,
      customer: customer ?? this.customer,
      earthingSystem: earthingSystem ?? this.earthingSystem,
      u0Volts: u0Volts ?? this.u0Volts,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (deleted.present) {
      map['deleted'] = Variable<bool>(deleted.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (address.present) {
      map['address'] = Variable<String>(address.value);
    }
    if (customer.present) {
      map['customer'] = Variable<String>(customer.value);
    }
    if (earthingSystem.present) {
      map['earthing_system'] = Variable<String>($SitesTable.$converterearthingSystemn.toSql(earthingSystem.value));
    }
    if (u0Volts.present) {
      map['u0_volts'] = Variable<double>(u0Volts.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SitesCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('name: $name, ')
          ..write('address: $address, ')
          ..write('customer: $customer, ')
          ..write('earthingSystem: $earthingSystem, ')
          ..write('u0Volts: $u0Volts, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $AppUsersTable extends AppUsers with TableInfo<$AppUsersTable, AppUserRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $AppUsersTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _deletedMeta = const VerificationMeta('deleted');
  @override
  late final GeneratedColumn<bool> deleted = GeneratedColumn<bool>(
    'deleted',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("deleted" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _fullNameMeta = const VerificationMeta('fullName');
  @override
  late final GeneratedColumn<String> fullName = GeneratedColumn<String>(
    'full_name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _phoneMeta = const VerificationMeta('phone');
  @override
  late final GeneratedColumn<String> phone = GeneratedColumn<String>(
    'phone',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _roleMeta = const VerificationMeta('role');
  @override
  late final GeneratedColumn<String> role = GeneratedColumn<String>(
    'role',
    aliasedName,
    false,
    check: () => role.isIn(const ['ADMIN', 'LEAD', 'ENGINEER', 'VIEWER']),
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _safetyGroupMeta = const VerificationMeta('safetyGroup');
  @override
  late final GeneratedColumn<String> safetyGroup = GeneratedColumn<String>(
    'safety_group',
    aliasedName,
    true,
    check: () => safetyGroup.isIn(const ['I', 'II', 'III', 'IV', 'V']),
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    fullName,
    phone,
    role,
    safetyGroup,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'app_user';
  @override
  VerificationContext validateIntegrity(Insertable<AppUserRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('deleted')) {
      context.handle(_deletedMeta, deleted.isAcceptableOrUnknown(data['deleted']!, _deletedMeta));
    }
    if (data.containsKey('full_name')) {
      context.handle(_fullNameMeta, fullName.isAcceptableOrUnknown(data['full_name']!, _fullNameMeta));
    } else if (isInserting) {
      context.missing(_fullNameMeta);
    }
    if (data.containsKey('phone')) {
      context.handle(_phoneMeta, phone.isAcceptableOrUnknown(data['phone']!, _phoneMeta));
    } else if (isInserting) {
      context.missing(_phoneMeta);
    }
    if (data.containsKey('role')) {
      context.handle(_roleMeta, role.isAcceptableOrUnknown(data['role']!, _roleMeta));
    } else if (isInserting) {
      context.missing(_roleMeta);
    }
    if (data.containsKey('safety_group')) {
      context.handle(_safetyGroupMeta, safetyGroup.isAcceptableOrUnknown(data['safety_group']!, _safetyGroupMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  AppUserRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return AppUserRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      deleted: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}deleted'])!,
      fullName: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}full_name'])!,
      phone: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}phone'])!,
      role: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}role'])!,
      safetyGroup: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}safety_group']),
    );
  }

  @override
  $AppUsersTable createAlias(String alias) {
    return $AppUsersTable(attachedDatabase, alias);
  }
}

class AppUserRow extends DataClass implements Insertable<AppUserRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final bool deleted;
  final String fullName;
  final String phone;
  final String role;
  final String? safetyGroup;
  const AppUserRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.deleted,
    required this.fullName,
    required this.phone,
    required this.role,
    this.safetyGroup,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['deleted'] = Variable<bool>(deleted);
    map['full_name'] = Variable<String>(fullName);
    map['phone'] = Variable<String>(phone);
    map['role'] = Variable<String>(role);
    if (!nullToAbsent || safetyGroup != null) {
      map['safety_group'] = Variable<String>(safetyGroup);
    }
    return map;
  }

  AppUsersCompanion toCompanion(bool nullToAbsent) {
    return AppUsersCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      deleted: Value(deleted),
      fullName: Value(fullName),
      phone: Value(phone),
      role: Value(role),
      safetyGroup: safetyGroup == null && nullToAbsent ? const Value.absent() : Value(safetyGroup),
    );
  }

  factory AppUserRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return AppUserRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      deleted: serializer.fromJson<bool>(json['deleted']),
      fullName: serializer.fromJson<String>(json['fullName']),
      phone: serializer.fromJson<String>(json['phone']),
      role: serializer.fromJson<String>(json['role']),
      safetyGroup: serializer.fromJson<String?>(json['safetyGroup']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'deleted': serializer.toJson<bool>(deleted),
      'fullName': serializer.toJson<String>(fullName),
      'phone': serializer.toJson<String>(phone),
      'role': serializer.toJson<String>(role),
      'safetyGroup': serializer.toJson<String?>(safetyGroup),
    };
  }

  AppUserRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    bool? deleted,
    String? fullName,
    String? phone,
    String? role,
    Value<String?> safetyGroup = const Value.absent(),
  }) => AppUserRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    deleted: deleted ?? this.deleted,
    fullName: fullName ?? this.fullName,
    phone: phone ?? this.phone,
    role: role ?? this.role,
    safetyGroup: safetyGroup.present ? safetyGroup.value : this.safetyGroup,
  );
  AppUserRow copyWithCompanion(AppUsersCompanion data) {
    return AppUserRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      deleted: data.deleted.present ? data.deleted.value : this.deleted,
      fullName: data.fullName.present ? data.fullName.value : this.fullName,
      phone: data.phone.present ? data.phone.value : this.phone,
      role: data.role.present ? data.role.value : this.role,
      safetyGroup: data.safetyGroup.present ? data.safetyGroup.value : this.safetyGroup,
    );
  }

  @override
  String toString() {
    return (StringBuffer('AppUserRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('fullName: $fullName, ')
          ..write('phone: $phone, ')
          ..write('role: $role, ')
          ..write('safetyGroup: $safetyGroup')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, createdAt, updatedAt, rev, orgId, deleted, fullName, phone, role, safetyGroup);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is AppUserRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.deleted == this.deleted &&
          other.fullName == this.fullName &&
          other.phone == this.phone &&
          other.role == this.role &&
          other.safetyGroup == this.safetyGroup);
}

class AppUsersCompanion extends UpdateCompanion<AppUserRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<bool> deleted;
  final Value<String> fullName;
  final Value<String> phone;
  final Value<String> role;
  final Value<String?> safetyGroup;
  final Value<int> rowid;
  const AppUsersCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.deleted = const Value.absent(),
    this.fullName = const Value.absent(),
    this.phone = const Value.absent(),
    this.role = const Value.absent(),
    this.safetyGroup = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  AppUsersCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    this.deleted = const Value.absent(),
    required String fullName,
    required String phone,
    required String role,
    this.safetyGroup = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       fullName = Value(fullName),
       phone = Value(phone),
       role = Value(role);
  static Insertable<AppUserRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<bool>? deleted,
    Expression<String>? fullName,
    Expression<String>? phone,
    Expression<String>? role,
    Expression<String>? safetyGroup,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (deleted != null) 'deleted': deleted,
      if (fullName != null) 'full_name': fullName,
      if (phone != null) 'phone': phone,
      if (role != null) 'role': role,
      if (safetyGroup != null) 'safety_group': safetyGroup,
      if (rowid != null) 'rowid': rowid,
    });
  }

  AppUsersCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<bool>? deleted,
    Value<String>? fullName,
    Value<String>? phone,
    Value<String>? role,
    Value<String?>? safetyGroup,
    Value<int>? rowid,
  }) {
    return AppUsersCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      deleted: deleted ?? this.deleted,
      fullName: fullName ?? this.fullName,
      phone: phone ?? this.phone,
      role: role ?? this.role,
      safetyGroup: safetyGroup ?? this.safetyGroup,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (deleted.present) {
      map['deleted'] = Variable<bool>(deleted.value);
    }
    if (fullName.present) {
      map['full_name'] = Variable<String>(fullName.value);
    }
    if (phone.present) {
      map['phone'] = Variable<String>(phone.value);
    }
    if (role.present) {
      map['role'] = Variable<String>(role.value);
    }
    if (safetyGroup.present) {
      map['safety_group'] = Variable<String>(safetyGroup.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('AppUsersCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('fullName: $fullName, ')
          ..write('phone: $phone, ')
          ..write('role: $role, ')
          ..write('safetyGroup: $safetyGroup, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $MeasurementSessionsTable extends MeasurementSessions
    with TableInfo<$MeasurementSessionsTable, MeasurementSessionRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $MeasurementSessionsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _deletedMeta = const VerificationMeta('deleted');
  @override
  late final GeneratedColumn<bool> deleted = GeneratedColumn<bool>(
    'deleted',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("deleted" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _siteIdMeta = const VerificationMeta('siteId');
  @override
  late final GeneratedColumn<String> siteId = GeneratedColumn<String>(
    'site_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES site (id)'),
  );
  @override
  late final GeneratedColumnWithTypeConverter<SessionKind, String> kind = GeneratedColumn<String>(
    'kind',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  ).withConverter<SessionKind>($MeasurementSessionsTable.$converterkind);
  static const VerificationMeta _engineerIdMeta = const VerificationMeta('engineerId');
  @override
  late final GeneratedColumn<String> engineerId = GeneratedColumn<String>(
    'engineer_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES app_user (id)'),
  );
  static const VerificationMeta _ambientTempCMeta = const VerificationMeta('ambientTempC');
  @override
  late final GeneratedColumn<double> ambientTempC = GeneratedColumn<double>(
    'ambient_temp_c',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _humidityPctMeta = const VerificationMeta('humidityPct');
  @override
  late final GeneratedColumn<double> humidityPct = GeneratedColumn<double>(
    'humidity_pct',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _startedAtMeta = const VerificationMeta('startedAt');
  @override
  late final GeneratedColumn<DateTime> startedAt = GeneratedColumn<DateTime>(
    'started_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _closedAtMeta = const VerificationMeta('closedAt');
  @override
  late final GeneratedColumn<DateTime> closedAt = GeneratedColumn<DateTime>(
    'closed_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    siteId,
    kind,
    engineerId,
    ambientTempC,
    humidityPct,
    startedAt,
    closedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'measurement_session';
  @override
  VerificationContext validateIntegrity(Insertable<MeasurementSessionRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('deleted')) {
      context.handle(_deletedMeta, deleted.isAcceptableOrUnknown(data['deleted']!, _deletedMeta));
    }
    if (data.containsKey('site_id')) {
      context.handle(_siteIdMeta, siteId.isAcceptableOrUnknown(data['site_id']!, _siteIdMeta));
    } else if (isInserting) {
      context.missing(_siteIdMeta);
    }
    if (data.containsKey('engineer_id')) {
      context.handle(_engineerIdMeta, engineerId.isAcceptableOrUnknown(data['engineer_id']!, _engineerIdMeta));
    } else if (isInserting) {
      context.missing(_engineerIdMeta);
    }
    if (data.containsKey('ambient_temp_c')) {
      context.handle(_ambientTempCMeta, ambientTempC.isAcceptableOrUnknown(data['ambient_temp_c']!, _ambientTempCMeta));
    }
    if (data.containsKey('humidity_pct')) {
      context.handle(_humidityPctMeta, humidityPct.isAcceptableOrUnknown(data['humidity_pct']!, _humidityPctMeta));
    }
    if (data.containsKey('started_at')) {
      context.handle(_startedAtMeta, startedAt.isAcceptableOrUnknown(data['started_at']!, _startedAtMeta));
    } else if (isInserting) {
      context.missing(_startedAtMeta);
    }
    if (data.containsKey('closed_at')) {
      context.handle(_closedAtMeta, closedAt.isAcceptableOrUnknown(data['closed_at']!, _closedAtMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  MeasurementSessionRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MeasurementSessionRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      deleted: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}deleted'])!,
      siteId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}site_id'])!,
      kind: $MeasurementSessionsTable.$converterkind.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}kind'])!,
      ),
      engineerId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}engineer_id'])!,
      ambientTempC: attachedDatabase.typeMapping.read(DriftSqlType.double, data['${effectivePrefix}ambient_temp_c']),
      humidityPct: attachedDatabase.typeMapping.read(DriftSqlType.double, data['${effectivePrefix}humidity_pct']),
      startedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}started_at'])!,
      closedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}closed_at']),
    );
  }

  @override
  $MeasurementSessionsTable createAlias(String alias) {
    return $MeasurementSessionsTable(attachedDatabase, alias);
  }

  static TypeConverter<SessionKind, String> $converterkind = sessionKindConverter;
}

class MeasurementSessionRow extends DataClass implements Insertable<MeasurementSessionRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final bool deleted;
  final String siteId;
  final SessionKind kind;
  final String engineerId;
  final double? ambientTempC;
  final double? humidityPct;
  final DateTime startedAt;
  final DateTime? closedAt;
  const MeasurementSessionRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.deleted,
    required this.siteId,
    required this.kind,
    required this.engineerId,
    this.ambientTempC,
    this.humidityPct,
    required this.startedAt,
    this.closedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['deleted'] = Variable<bool>(deleted);
    map['site_id'] = Variable<String>(siteId);
    {
      map['kind'] = Variable<String>($MeasurementSessionsTable.$converterkind.toSql(kind));
    }
    map['engineer_id'] = Variable<String>(engineerId);
    if (!nullToAbsent || ambientTempC != null) {
      map['ambient_temp_c'] = Variable<double>(ambientTempC);
    }
    if (!nullToAbsent || humidityPct != null) {
      map['humidity_pct'] = Variable<double>(humidityPct);
    }
    map['started_at'] = Variable<DateTime>(startedAt);
    if (!nullToAbsent || closedAt != null) {
      map['closed_at'] = Variable<DateTime>(closedAt);
    }
    return map;
  }

  MeasurementSessionsCompanion toCompanion(bool nullToAbsent) {
    return MeasurementSessionsCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      deleted: Value(deleted),
      siteId: Value(siteId),
      kind: Value(kind),
      engineerId: Value(engineerId),
      ambientTempC: ambientTempC == null && nullToAbsent ? const Value.absent() : Value(ambientTempC),
      humidityPct: humidityPct == null && nullToAbsent ? const Value.absent() : Value(humidityPct),
      startedAt: Value(startedAt),
      closedAt: closedAt == null && nullToAbsent ? const Value.absent() : Value(closedAt),
    );
  }

  factory MeasurementSessionRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MeasurementSessionRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      deleted: serializer.fromJson<bool>(json['deleted']),
      siteId: serializer.fromJson<String>(json['siteId']),
      kind: serializer.fromJson<SessionKind>(json['kind']),
      engineerId: serializer.fromJson<String>(json['engineerId']),
      ambientTempC: serializer.fromJson<double?>(json['ambientTempC']),
      humidityPct: serializer.fromJson<double?>(json['humidityPct']),
      startedAt: serializer.fromJson<DateTime>(json['startedAt']),
      closedAt: serializer.fromJson<DateTime?>(json['closedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'deleted': serializer.toJson<bool>(deleted),
      'siteId': serializer.toJson<String>(siteId),
      'kind': serializer.toJson<SessionKind>(kind),
      'engineerId': serializer.toJson<String>(engineerId),
      'ambientTempC': serializer.toJson<double?>(ambientTempC),
      'humidityPct': serializer.toJson<double?>(humidityPct),
      'startedAt': serializer.toJson<DateTime>(startedAt),
      'closedAt': serializer.toJson<DateTime?>(closedAt),
    };
  }

  MeasurementSessionRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    bool? deleted,
    String? siteId,
    SessionKind? kind,
    String? engineerId,
    Value<double?> ambientTempC = const Value.absent(),
    Value<double?> humidityPct = const Value.absent(),
    DateTime? startedAt,
    Value<DateTime?> closedAt = const Value.absent(),
  }) => MeasurementSessionRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    deleted: deleted ?? this.deleted,
    siteId: siteId ?? this.siteId,
    kind: kind ?? this.kind,
    engineerId: engineerId ?? this.engineerId,
    ambientTempC: ambientTempC.present ? ambientTempC.value : this.ambientTempC,
    humidityPct: humidityPct.present ? humidityPct.value : this.humidityPct,
    startedAt: startedAt ?? this.startedAt,
    closedAt: closedAt.present ? closedAt.value : this.closedAt,
  );
  MeasurementSessionRow copyWithCompanion(MeasurementSessionsCompanion data) {
    return MeasurementSessionRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      deleted: data.deleted.present ? data.deleted.value : this.deleted,
      siteId: data.siteId.present ? data.siteId.value : this.siteId,
      kind: data.kind.present ? data.kind.value : this.kind,
      engineerId: data.engineerId.present ? data.engineerId.value : this.engineerId,
      ambientTempC: data.ambientTempC.present ? data.ambientTempC.value : this.ambientTempC,
      humidityPct: data.humidityPct.present ? data.humidityPct.value : this.humidityPct,
      startedAt: data.startedAt.present ? data.startedAt.value : this.startedAt,
      closedAt: data.closedAt.present ? data.closedAt.value : this.closedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MeasurementSessionRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('siteId: $siteId, ')
          ..write('kind: $kind, ')
          ..write('engineerId: $engineerId, ')
          ..write('ambientTempC: $ambientTempC, ')
          ..write('humidityPct: $humidityPct, ')
          ..write('startedAt: $startedAt, ')
          ..write('closedAt: $closedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    siteId,
    kind,
    engineerId,
    ambientTempC,
    humidityPct,
    startedAt,
    closedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MeasurementSessionRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.deleted == this.deleted &&
          other.siteId == this.siteId &&
          other.kind == this.kind &&
          other.engineerId == this.engineerId &&
          other.ambientTempC == this.ambientTempC &&
          other.humidityPct == this.humidityPct &&
          other.startedAt == this.startedAt &&
          other.closedAt == this.closedAt);
}

class MeasurementSessionsCompanion extends UpdateCompanion<MeasurementSessionRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<bool> deleted;
  final Value<String> siteId;
  final Value<SessionKind> kind;
  final Value<String> engineerId;
  final Value<double?> ambientTempC;
  final Value<double?> humidityPct;
  final Value<DateTime> startedAt;
  final Value<DateTime?> closedAt;
  final Value<int> rowid;
  const MeasurementSessionsCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.deleted = const Value.absent(),
    this.siteId = const Value.absent(),
    this.kind = const Value.absent(),
    this.engineerId = const Value.absent(),
    this.ambientTempC = const Value.absent(),
    this.humidityPct = const Value.absent(),
    this.startedAt = const Value.absent(),
    this.closedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  MeasurementSessionsCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    this.deleted = const Value.absent(),
    required String siteId,
    required SessionKind kind,
    required String engineerId,
    this.ambientTempC = const Value.absent(),
    this.humidityPct = const Value.absent(),
    required DateTime startedAt,
    this.closedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       siteId = Value(siteId),
       kind = Value(kind),
       engineerId = Value(engineerId),
       startedAt = Value(startedAt);
  static Insertable<MeasurementSessionRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<bool>? deleted,
    Expression<String>? siteId,
    Expression<String>? kind,
    Expression<String>? engineerId,
    Expression<double>? ambientTempC,
    Expression<double>? humidityPct,
    Expression<DateTime>? startedAt,
    Expression<DateTime>? closedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (deleted != null) 'deleted': deleted,
      if (siteId != null) 'site_id': siteId,
      if (kind != null) 'kind': kind,
      if (engineerId != null) 'engineer_id': engineerId,
      if (ambientTempC != null) 'ambient_temp_c': ambientTempC,
      if (humidityPct != null) 'humidity_pct': humidityPct,
      if (startedAt != null) 'started_at': startedAt,
      if (closedAt != null) 'closed_at': closedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  MeasurementSessionsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<bool>? deleted,
    Value<String>? siteId,
    Value<SessionKind>? kind,
    Value<String>? engineerId,
    Value<double?>? ambientTempC,
    Value<double?>? humidityPct,
    Value<DateTime>? startedAt,
    Value<DateTime?>? closedAt,
    Value<int>? rowid,
  }) {
    return MeasurementSessionsCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      deleted: deleted ?? this.deleted,
      siteId: siteId ?? this.siteId,
      kind: kind ?? this.kind,
      engineerId: engineerId ?? this.engineerId,
      ambientTempC: ambientTempC ?? this.ambientTempC,
      humidityPct: humidityPct ?? this.humidityPct,
      startedAt: startedAt ?? this.startedAt,
      closedAt: closedAt ?? this.closedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (deleted.present) {
      map['deleted'] = Variable<bool>(deleted.value);
    }
    if (siteId.present) {
      map['site_id'] = Variable<String>(siteId.value);
    }
    if (kind.present) {
      map['kind'] = Variable<String>($MeasurementSessionsTable.$converterkind.toSql(kind.value));
    }
    if (engineerId.present) {
      map['engineer_id'] = Variable<String>(engineerId.value);
    }
    if (ambientTempC.present) {
      map['ambient_temp_c'] = Variable<double>(ambientTempC.value);
    }
    if (humidityPct.present) {
      map['humidity_pct'] = Variable<double>(humidityPct.value);
    }
    if (startedAt.present) {
      map['started_at'] = Variable<DateTime>(startedAt.value);
    }
    if (closedAt.present) {
      map['closed_at'] = Variable<DateTime>(closedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('MeasurementSessionsCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('siteId: $siteId, ')
          ..write('kind: $kind, ')
          ..write('engineerId: $engineerId, ')
          ..write('ambientTempC: $ambientTempC, ')
          ..write('humidityPct: $humidityPct, ')
          ..write('startedAt: $startedAt, ')
          ..write('closedAt: $closedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $NodesTable extends Nodes with TableInfo<$NodesTable, NodeRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $NodesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _deletedMeta = const VerificationMeta('deleted');
  @override
  late final GeneratedColumn<bool> deleted = GeneratedColumn<bool>(
    'deleted',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("deleted" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _siteIdMeta = const VerificationMeta('siteId');
  @override
  late final GeneratedColumn<String> siteId = GeneratedColumn<String>(
    'site_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES site (id)'),
  );
  @override
  late final GeneratedColumnWithTypeConverter<NodeKind, String> kind = GeneratedColumn<String>(
    'kind',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  ).withConverter<NodeKind>($NodesTable.$converterkind);
  static const VerificationMeta _labelMeta = const VerificationMeta('label');
  @override
  late final GeneratedColumn<String> label = GeneratedColumn<String>(
    'label',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _panelIdMeta = const VerificationMeta('panelId');
  @override
  late final GeneratedColumn<String> panelId = GeneratedColumn<String>(
    'panel_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES node (id)'),
  );
  @override
  late final GeneratedColumnWithTypeConverter<SwitchState?, String> state = GeneratedColumn<String>(
    'state',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  ).withConverter<SwitchState?>($NodesTable.$converterstaten);
  @override
  late final GeneratedColumnWithTypeConverter<Map<String, Object?>, String> attrs = GeneratedColumn<String>(
    'attrs',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('{}'),
  ).withConverter<Map<String, Object?>>($NodesTable.$converterattrs);
  static const VerificationMeta _verifiedMeta = const VerificationMeta('verified');
  @override
  late final GeneratedColumn<bool> verified = GeneratedColumn<bool>(
    'verified',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("verified" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _xMeta = const VerificationMeta('x');
  @override
  late final GeneratedColumn<double> x = GeneratedColumn<double>(
    'x',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _yMeta = const VerificationMeta('y');
  @override
  late final GeneratedColumn<double> y = GeneratedColumn<double>(
    'y',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    siteId,
    kind,
    label,
    panelId,
    state,
    attrs,
    verified,
    x,
    y,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'node';
  @override
  VerificationContext validateIntegrity(Insertable<NodeRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('deleted')) {
      context.handle(_deletedMeta, deleted.isAcceptableOrUnknown(data['deleted']!, _deletedMeta));
    }
    if (data.containsKey('site_id')) {
      context.handle(_siteIdMeta, siteId.isAcceptableOrUnknown(data['site_id']!, _siteIdMeta));
    } else if (isInserting) {
      context.missing(_siteIdMeta);
    }
    if (data.containsKey('label')) {
      context.handle(_labelMeta, label.isAcceptableOrUnknown(data['label']!, _labelMeta));
    } else if (isInserting) {
      context.missing(_labelMeta);
    }
    if (data.containsKey('panel_id')) {
      context.handle(_panelIdMeta, panelId.isAcceptableOrUnknown(data['panel_id']!, _panelIdMeta));
    }
    if (data.containsKey('verified')) {
      context.handle(_verifiedMeta, verified.isAcceptableOrUnknown(data['verified']!, _verifiedMeta));
    }
    if (data.containsKey('x')) {
      context.handle(_xMeta, x.isAcceptableOrUnknown(data['x']!, _xMeta));
    }
    if (data.containsKey('y')) {
      context.handle(_yMeta, y.isAcceptableOrUnknown(data['y']!, _yMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  NodeRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return NodeRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      deleted: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}deleted'])!,
      siteId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}site_id'])!,
      kind: $NodesTable.$converterkind.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}kind'])!,
      ),
      label: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}label'])!,
      panelId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}panel_id']),
      state: $NodesTable.$converterstaten.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}state']),
      ),
      attrs: $NodesTable.$converterattrs.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}attrs'])!,
      ),
      verified: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}verified'])!,
      x: attachedDatabase.typeMapping.read(DriftSqlType.double, data['${effectivePrefix}x']),
      y: attachedDatabase.typeMapping.read(DriftSqlType.double, data['${effectivePrefix}y']),
    );
  }

  @override
  $NodesTable createAlias(String alias) {
    return $NodesTable(attachedDatabase, alias);
  }

  static TypeConverter<NodeKind, String> $converterkind = nodeKindConverter;
  static TypeConverter<SwitchState, String> $converterstate = switchStateConverter;
  static TypeConverter<SwitchState?, String?> $converterstaten = NullAwareTypeConverter.wrap($converterstate);
  static TypeConverter<Map<String, Object?>, String> $converterattrs = const JsonMapConverter();
}

class NodeRow extends DataClass implements Insertable<NodeRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final bool deleted;
  final String siteId;
  final NodeKind kind;
  final String label;
  final String? panelId;

  /// Faqat kommutatsiya apparatlarida (CLOSED/OPEN).
  final SwitchState? state;
  final Map<String, Object?> attrs;
  final bool verified;
  final double? x;
  final double? y;
  const NodeRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.deleted,
    required this.siteId,
    required this.kind,
    required this.label,
    this.panelId,
    this.state,
    required this.attrs,
    required this.verified,
    this.x,
    this.y,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['deleted'] = Variable<bool>(deleted);
    map['site_id'] = Variable<String>(siteId);
    {
      map['kind'] = Variable<String>($NodesTable.$converterkind.toSql(kind));
    }
    map['label'] = Variable<String>(label);
    if (!nullToAbsent || panelId != null) {
      map['panel_id'] = Variable<String>(panelId);
    }
    if (!nullToAbsent || state != null) {
      map['state'] = Variable<String>($NodesTable.$converterstaten.toSql(state));
    }
    {
      map['attrs'] = Variable<String>($NodesTable.$converterattrs.toSql(attrs));
    }
    map['verified'] = Variable<bool>(verified);
    if (!nullToAbsent || x != null) {
      map['x'] = Variable<double>(x);
    }
    if (!nullToAbsent || y != null) {
      map['y'] = Variable<double>(y);
    }
    return map;
  }

  NodesCompanion toCompanion(bool nullToAbsent) {
    return NodesCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      deleted: Value(deleted),
      siteId: Value(siteId),
      kind: Value(kind),
      label: Value(label),
      panelId: panelId == null && nullToAbsent ? const Value.absent() : Value(panelId),
      state: state == null && nullToAbsent ? const Value.absent() : Value(state),
      attrs: Value(attrs),
      verified: Value(verified),
      x: x == null && nullToAbsent ? const Value.absent() : Value(x),
      y: y == null && nullToAbsent ? const Value.absent() : Value(y),
    );
  }

  factory NodeRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return NodeRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      deleted: serializer.fromJson<bool>(json['deleted']),
      siteId: serializer.fromJson<String>(json['siteId']),
      kind: serializer.fromJson<NodeKind>(json['kind']),
      label: serializer.fromJson<String>(json['label']),
      panelId: serializer.fromJson<String?>(json['panelId']),
      state: serializer.fromJson<SwitchState?>(json['state']),
      attrs: serializer.fromJson<Map<String, Object?>>(json['attrs']),
      verified: serializer.fromJson<bool>(json['verified']),
      x: serializer.fromJson<double?>(json['x']),
      y: serializer.fromJson<double?>(json['y']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'deleted': serializer.toJson<bool>(deleted),
      'siteId': serializer.toJson<String>(siteId),
      'kind': serializer.toJson<NodeKind>(kind),
      'label': serializer.toJson<String>(label),
      'panelId': serializer.toJson<String?>(panelId),
      'state': serializer.toJson<SwitchState?>(state),
      'attrs': serializer.toJson<Map<String, Object?>>(attrs),
      'verified': serializer.toJson<bool>(verified),
      'x': serializer.toJson<double?>(x),
      'y': serializer.toJson<double?>(y),
    };
  }

  NodeRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    bool? deleted,
    String? siteId,
    NodeKind? kind,
    String? label,
    Value<String?> panelId = const Value.absent(),
    Value<SwitchState?> state = const Value.absent(),
    Map<String, Object?>? attrs,
    bool? verified,
    Value<double?> x = const Value.absent(),
    Value<double?> y = const Value.absent(),
  }) => NodeRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    deleted: deleted ?? this.deleted,
    siteId: siteId ?? this.siteId,
    kind: kind ?? this.kind,
    label: label ?? this.label,
    panelId: panelId.present ? panelId.value : this.panelId,
    state: state.present ? state.value : this.state,
    attrs: attrs ?? this.attrs,
    verified: verified ?? this.verified,
    x: x.present ? x.value : this.x,
    y: y.present ? y.value : this.y,
  );
  NodeRow copyWithCompanion(NodesCompanion data) {
    return NodeRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      deleted: data.deleted.present ? data.deleted.value : this.deleted,
      siteId: data.siteId.present ? data.siteId.value : this.siteId,
      kind: data.kind.present ? data.kind.value : this.kind,
      label: data.label.present ? data.label.value : this.label,
      panelId: data.panelId.present ? data.panelId.value : this.panelId,
      state: data.state.present ? data.state.value : this.state,
      attrs: data.attrs.present ? data.attrs.value : this.attrs,
      verified: data.verified.present ? data.verified.value : this.verified,
      x: data.x.present ? data.x.value : this.x,
      y: data.y.present ? data.y.value : this.y,
    );
  }

  @override
  String toString() {
    return (StringBuffer('NodeRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('siteId: $siteId, ')
          ..write('kind: $kind, ')
          ..write('label: $label, ')
          ..write('panelId: $panelId, ')
          ..write('state: $state, ')
          ..write('attrs: $attrs, ')
          ..write('verified: $verified, ')
          ..write('x: $x, ')
          ..write('y: $y')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    siteId,
    kind,
    label,
    panelId,
    state,
    attrs,
    verified,
    x,
    y,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is NodeRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.deleted == this.deleted &&
          other.siteId == this.siteId &&
          other.kind == this.kind &&
          other.label == this.label &&
          other.panelId == this.panelId &&
          other.state == this.state &&
          other.attrs == this.attrs &&
          other.verified == this.verified &&
          other.x == this.x &&
          other.y == this.y);
}

class NodesCompanion extends UpdateCompanion<NodeRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<bool> deleted;
  final Value<String> siteId;
  final Value<NodeKind> kind;
  final Value<String> label;
  final Value<String?> panelId;
  final Value<SwitchState?> state;
  final Value<Map<String, Object?>> attrs;
  final Value<bool> verified;
  final Value<double?> x;
  final Value<double?> y;
  final Value<int> rowid;
  const NodesCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.deleted = const Value.absent(),
    this.siteId = const Value.absent(),
    this.kind = const Value.absent(),
    this.label = const Value.absent(),
    this.panelId = const Value.absent(),
    this.state = const Value.absent(),
    this.attrs = const Value.absent(),
    this.verified = const Value.absent(),
    this.x = const Value.absent(),
    this.y = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  NodesCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    this.deleted = const Value.absent(),
    required String siteId,
    required NodeKind kind,
    required String label,
    this.panelId = const Value.absent(),
    this.state = const Value.absent(),
    this.attrs = const Value.absent(),
    this.verified = const Value.absent(),
    this.x = const Value.absent(),
    this.y = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       siteId = Value(siteId),
       kind = Value(kind),
       label = Value(label);
  static Insertable<NodeRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<bool>? deleted,
    Expression<String>? siteId,
    Expression<String>? kind,
    Expression<String>? label,
    Expression<String>? panelId,
    Expression<String>? state,
    Expression<String>? attrs,
    Expression<bool>? verified,
    Expression<double>? x,
    Expression<double>? y,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (deleted != null) 'deleted': deleted,
      if (siteId != null) 'site_id': siteId,
      if (kind != null) 'kind': kind,
      if (label != null) 'label': label,
      if (panelId != null) 'panel_id': panelId,
      if (state != null) 'state': state,
      if (attrs != null) 'attrs': attrs,
      if (verified != null) 'verified': verified,
      if (x != null) 'x': x,
      if (y != null) 'y': y,
      if (rowid != null) 'rowid': rowid,
    });
  }

  NodesCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<bool>? deleted,
    Value<String>? siteId,
    Value<NodeKind>? kind,
    Value<String>? label,
    Value<String?>? panelId,
    Value<SwitchState?>? state,
    Value<Map<String, Object?>>? attrs,
    Value<bool>? verified,
    Value<double?>? x,
    Value<double?>? y,
    Value<int>? rowid,
  }) {
    return NodesCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      deleted: deleted ?? this.deleted,
      siteId: siteId ?? this.siteId,
      kind: kind ?? this.kind,
      label: label ?? this.label,
      panelId: panelId ?? this.panelId,
      state: state ?? this.state,
      attrs: attrs ?? this.attrs,
      verified: verified ?? this.verified,
      x: x ?? this.x,
      y: y ?? this.y,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (deleted.present) {
      map['deleted'] = Variable<bool>(deleted.value);
    }
    if (siteId.present) {
      map['site_id'] = Variable<String>(siteId.value);
    }
    if (kind.present) {
      map['kind'] = Variable<String>($NodesTable.$converterkind.toSql(kind.value));
    }
    if (label.present) {
      map['label'] = Variable<String>(label.value);
    }
    if (panelId.present) {
      map['panel_id'] = Variable<String>(panelId.value);
    }
    if (state.present) {
      map['state'] = Variable<String>($NodesTable.$converterstaten.toSql(state.value));
    }
    if (attrs.present) {
      map['attrs'] = Variable<String>($NodesTable.$converterattrs.toSql(attrs.value));
    }
    if (verified.present) {
      map['verified'] = Variable<bool>(verified.value);
    }
    if (x.present) {
      map['x'] = Variable<double>(x.value);
    }
    if (y.present) {
      map['y'] = Variable<double>(y.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('NodesCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('siteId: $siteId, ')
          ..write('kind: $kind, ')
          ..write('label: $label, ')
          ..write('panelId: $panelId, ')
          ..write('state: $state, ')
          ..write('attrs: $attrs, ')
          ..write('verified: $verified, ')
          ..write('x: $x, ')
          ..write('y: $y, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $InstrumentsTable extends Instruments with TableInfo<$InstrumentsTable, InstrumentRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $InstrumentsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _deletedMeta = const VerificationMeta('deleted');
  @override
  late final GeneratedColumn<bool> deleted = GeneratedColumn<bool>(
    'deleted',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("deleted" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _kindMeta = const VerificationMeta('kind');
  @override
  late final GeneratedColumn<String> kind = GeneratedColumn<String>(
    'kind',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _modelMeta = const VerificationMeta('model');
  @override
  late final GeneratedColumn<String> model = GeneratedColumn<String>(
    'model',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _serialNoMeta = const VerificationMeta('serialNo');
  @override
  late final GeneratedColumn<String> serialNo = GeneratedColumn<String>(
    'serial_no',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _verificationCertNoMeta = const VerificationMeta('verificationCertNo');
  @override
  late final GeneratedColumn<String> verificationCertNo = GeneratedColumn<String>(
    'verification_cert_no',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _verifiedUntilMeta = const VerificationMeta('verifiedUntil');
  @override
  late final GeneratedColumn<DateTime> verifiedUntil = GeneratedColumn<DateTime>(
    'verified_until',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    kind,
    model,
    serialNo,
    verificationCertNo,
    verifiedUntil,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'instrument';
  @override
  VerificationContext validateIntegrity(Insertable<InstrumentRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('deleted')) {
      context.handle(_deletedMeta, deleted.isAcceptableOrUnknown(data['deleted']!, _deletedMeta));
    }
    if (data.containsKey('kind')) {
      context.handle(_kindMeta, kind.isAcceptableOrUnknown(data['kind']!, _kindMeta));
    } else if (isInserting) {
      context.missing(_kindMeta);
    }
    if (data.containsKey('model')) {
      context.handle(_modelMeta, model.isAcceptableOrUnknown(data['model']!, _modelMeta));
    } else if (isInserting) {
      context.missing(_modelMeta);
    }
    if (data.containsKey('serial_no')) {
      context.handle(_serialNoMeta, serialNo.isAcceptableOrUnknown(data['serial_no']!, _serialNoMeta));
    } else if (isInserting) {
      context.missing(_serialNoMeta);
    }
    if (data.containsKey('verification_cert_no')) {
      context.handle(
        _verificationCertNoMeta,
        verificationCertNo.isAcceptableOrUnknown(data['verification_cert_no']!, _verificationCertNoMeta),
      );
    }
    if (data.containsKey('verified_until')) {
      context.handle(
        _verifiedUntilMeta,
        verifiedUntil.isAcceptableOrUnknown(data['verified_until']!, _verifiedUntilMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  InstrumentRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return InstrumentRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      deleted: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}deleted'])!,
      kind: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}kind'])!,
      model: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}model'])!,
      serialNo: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}serial_no'])!,
      verificationCertNo: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}verification_cert_no'],
      ),
      verifiedUntil: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}verified_until']),
    );
  }

  @override
  $InstrumentsTable createAlias(String alias) {
    return $InstrumentsTable(attachedDatabase, alias);
  }
}

class InstrumentRow extends DataClass implements Insertable<InstrumentRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final bool deleted;
  final String kind;
  final String model;
  final String serialNo;
  final String? verificationCertNo;
  final DateTime? verifiedUntil;
  const InstrumentRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.deleted,
    required this.kind,
    required this.model,
    required this.serialNo,
    this.verificationCertNo,
    this.verifiedUntil,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['deleted'] = Variable<bool>(deleted);
    map['kind'] = Variable<String>(kind);
    map['model'] = Variable<String>(model);
    map['serial_no'] = Variable<String>(serialNo);
    if (!nullToAbsent || verificationCertNo != null) {
      map['verification_cert_no'] = Variable<String>(verificationCertNo);
    }
    if (!nullToAbsent || verifiedUntil != null) {
      map['verified_until'] = Variable<DateTime>(verifiedUntil);
    }
    return map;
  }

  InstrumentsCompanion toCompanion(bool nullToAbsent) {
    return InstrumentsCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      deleted: Value(deleted),
      kind: Value(kind),
      model: Value(model),
      serialNo: Value(serialNo),
      verificationCertNo: verificationCertNo == null && nullToAbsent ? const Value.absent() : Value(verificationCertNo),
      verifiedUntil: verifiedUntil == null && nullToAbsent ? const Value.absent() : Value(verifiedUntil),
    );
  }

  factory InstrumentRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return InstrumentRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      deleted: serializer.fromJson<bool>(json['deleted']),
      kind: serializer.fromJson<String>(json['kind']),
      model: serializer.fromJson<String>(json['model']),
      serialNo: serializer.fromJson<String>(json['serialNo']),
      verificationCertNo: serializer.fromJson<String?>(json['verificationCertNo']),
      verifiedUntil: serializer.fromJson<DateTime?>(json['verifiedUntil']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'deleted': serializer.toJson<bool>(deleted),
      'kind': serializer.toJson<String>(kind),
      'model': serializer.toJson<String>(model),
      'serialNo': serializer.toJson<String>(serialNo),
      'verificationCertNo': serializer.toJson<String?>(verificationCertNo),
      'verifiedUntil': serializer.toJson<DateTime?>(verifiedUntil),
    };
  }

  InstrumentRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    bool? deleted,
    String? kind,
    String? model,
    String? serialNo,
    Value<String?> verificationCertNo = const Value.absent(),
    Value<DateTime?> verifiedUntil = const Value.absent(),
  }) => InstrumentRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    deleted: deleted ?? this.deleted,
    kind: kind ?? this.kind,
    model: model ?? this.model,
    serialNo: serialNo ?? this.serialNo,
    verificationCertNo: verificationCertNo.present ? verificationCertNo.value : this.verificationCertNo,
    verifiedUntil: verifiedUntil.present ? verifiedUntil.value : this.verifiedUntil,
  );
  InstrumentRow copyWithCompanion(InstrumentsCompanion data) {
    return InstrumentRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      deleted: data.deleted.present ? data.deleted.value : this.deleted,
      kind: data.kind.present ? data.kind.value : this.kind,
      model: data.model.present ? data.model.value : this.model,
      serialNo: data.serialNo.present ? data.serialNo.value : this.serialNo,
      verificationCertNo: data.verificationCertNo.present ? data.verificationCertNo.value : this.verificationCertNo,
      verifiedUntil: data.verifiedUntil.present ? data.verifiedUntil.value : this.verifiedUntil,
    );
  }

  @override
  String toString() {
    return (StringBuffer('InstrumentRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('kind: $kind, ')
          ..write('model: $model, ')
          ..write('serialNo: $serialNo, ')
          ..write('verificationCertNo: $verificationCertNo, ')
          ..write('verifiedUntil: $verifiedUntil')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    kind,
    model,
    serialNo,
    verificationCertNo,
    verifiedUntil,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is InstrumentRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.deleted == this.deleted &&
          other.kind == this.kind &&
          other.model == this.model &&
          other.serialNo == this.serialNo &&
          other.verificationCertNo == this.verificationCertNo &&
          other.verifiedUntil == this.verifiedUntil);
}

class InstrumentsCompanion extends UpdateCompanion<InstrumentRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<bool> deleted;
  final Value<String> kind;
  final Value<String> model;
  final Value<String> serialNo;
  final Value<String?> verificationCertNo;
  final Value<DateTime?> verifiedUntil;
  final Value<int> rowid;
  const InstrumentsCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.deleted = const Value.absent(),
    this.kind = const Value.absent(),
    this.model = const Value.absent(),
    this.serialNo = const Value.absent(),
    this.verificationCertNo = const Value.absent(),
    this.verifiedUntil = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  InstrumentsCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    this.deleted = const Value.absent(),
    required String kind,
    required String model,
    required String serialNo,
    this.verificationCertNo = const Value.absent(),
    this.verifiedUntil = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       kind = Value(kind),
       model = Value(model),
       serialNo = Value(serialNo);
  static Insertable<InstrumentRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<bool>? deleted,
    Expression<String>? kind,
    Expression<String>? model,
    Expression<String>? serialNo,
    Expression<String>? verificationCertNo,
    Expression<DateTime>? verifiedUntil,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (deleted != null) 'deleted': deleted,
      if (kind != null) 'kind': kind,
      if (model != null) 'model': model,
      if (serialNo != null) 'serial_no': serialNo,
      if (verificationCertNo != null) 'verification_cert_no': verificationCertNo,
      if (verifiedUntil != null) 'verified_until': verifiedUntil,
      if (rowid != null) 'rowid': rowid,
    });
  }

  InstrumentsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<bool>? deleted,
    Value<String>? kind,
    Value<String>? model,
    Value<String>? serialNo,
    Value<String?>? verificationCertNo,
    Value<DateTime?>? verifiedUntil,
    Value<int>? rowid,
  }) {
    return InstrumentsCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      deleted: deleted ?? this.deleted,
      kind: kind ?? this.kind,
      model: model ?? this.model,
      serialNo: serialNo ?? this.serialNo,
      verificationCertNo: verificationCertNo ?? this.verificationCertNo,
      verifiedUntil: verifiedUntil ?? this.verifiedUntil,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (deleted.present) {
      map['deleted'] = Variable<bool>(deleted.value);
    }
    if (kind.present) {
      map['kind'] = Variable<String>(kind.value);
    }
    if (model.present) {
      map['model'] = Variable<String>(model.value);
    }
    if (serialNo.present) {
      map['serial_no'] = Variable<String>(serialNo.value);
    }
    if (verificationCertNo.present) {
      map['verification_cert_no'] = Variable<String>(verificationCertNo.value);
    }
    if (verifiedUntil.present) {
      map['verified_until'] = Variable<DateTime>(verifiedUntil.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('InstrumentsCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('kind: $kind, ')
          ..write('model: $model, ')
          ..write('serialNo: $serialNo, ')
          ..write('verificationCertNo: $verificationCertNo, ')
          ..write('verifiedUntil: $verifiedUntil, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $MeasurementsTable extends Measurements with TableInfo<$MeasurementsTable, MeasurementRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $MeasurementsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _sessionIdMeta = const VerificationMeta('sessionId');
  @override
  late final GeneratedColumn<String> sessionId = GeneratedColumn<String>(
    'session_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES measurement_session (id)'),
  );
  static const VerificationMeta _nodeIdMeta = const VerificationMeta('nodeId');
  @override
  late final GeneratedColumn<String> nodeId = GeneratedColumn<String>(
    'node_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES node (id)'),
  );
  @override
  late final GeneratedColumnWithTypeConverter<MeasurementType, String> type = GeneratedColumn<String>(
    'type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  ).withConverter<MeasurementType>($MeasurementsTable.$convertertype);
  static const VerificationMeta _instrumentIdMeta = const VerificationMeta('instrumentId');
  @override
  late final GeneratedColumn<String> instrumentId = GeneratedColumn<String>(
    'instrument_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES instrument (id)'),
  );
  @override
  late final GeneratedColumnWithTypeConverter<Map<String, Object?>, String> values = GeneratedColumn<String>(
    'values',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  ).withConverter<Map<String, Object?>>($MeasurementsTable.$convertervalues);
  @override
  late final GeneratedColumnWithTypeConverter<EnteredVia, String> enteredVia = GeneratedColumn<String>(
    'entered_via',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  ).withConverter<EnteredVia>($MeasurementsTable.$converterenteredVia);
  @override
  late final GeneratedColumnWithTypeConverter<Verdict, String> verdict = GeneratedColumn<String>(
    'verdict',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  ).withConverter<Verdict>($MeasurementsTable.$converterverdict);
  static const VerificationMeta _normIdMeta = const VerificationMeta('normId');
  @override
  late final GeneratedColumn<String> normId = GeneratedColumn<String>(
    'norm_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _normSetVersionMeta = const VerificationMeta('normSetVersion');
  @override
  late final GeneratedColumn<String> normSetVersion = GeneratedColumn<String>(
    'norm_set_version',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  late final GeneratedColumnWithTypeConverter<Map<String, Object?>, String> evalDetail = GeneratedColumn<String>(
    'eval_detail',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  ).withConverter<Map<String, Object?>>($MeasurementsTable.$converterevalDetail);
  static const VerificationMeta _supersedesIdMeta = const VerificationMeta('supersedesId');
  @override
  late final GeneratedColumn<String> supersedesId = GeneratedColumn<String>(
    'supersedes_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('UNIQUE REFERENCES measurement (id)'),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    sessionId,
    nodeId,
    type,
    instrumentId,
    values,
    enteredVia,
    verdict,
    normId,
    normSetVersion,
    evalDetail,
    supersedesId,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'measurement';
  @override
  VerificationContext validateIntegrity(Insertable<MeasurementRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('session_id')) {
      context.handle(_sessionIdMeta, sessionId.isAcceptableOrUnknown(data['session_id']!, _sessionIdMeta));
    } else if (isInserting) {
      context.missing(_sessionIdMeta);
    }
    if (data.containsKey('node_id')) {
      context.handle(_nodeIdMeta, nodeId.isAcceptableOrUnknown(data['node_id']!, _nodeIdMeta));
    } else if (isInserting) {
      context.missing(_nodeIdMeta);
    }
    if (data.containsKey('instrument_id')) {
      context.handle(_instrumentIdMeta, instrumentId.isAcceptableOrUnknown(data['instrument_id']!, _instrumentIdMeta));
    } else if (isInserting) {
      context.missing(_instrumentIdMeta);
    }
    if (data.containsKey('norm_id')) {
      context.handle(_normIdMeta, normId.isAcceptableOrUnknown(data['norm_id']!, _normIdMeta));
    }
    if (data.containsKey('norm_set_version')) {
      context.handle(
        _normSetVersionMeta,
        normSetVersion.isAcceptableOrUnknown(data['norm_set_version']!, _normSetVersionMeta),
      );
    } else if (isInserting) {
      context.missing(_normSetVersionMeta);
    }
    if (data.containsKey('supersedes_id')) {
      context.handle(_supersedesIdMeta, supersedesId.isAcceptableOrUnknown(data['supersedes_id']!, _supersedesIdMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  MeasurementRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MeasurementRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      sessionId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}session_id'])!,
      nodeId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}node_id'])!,
      type: $MeasurementsTable.$convertertype.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}type'])!,
      ),
      instrumentId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}instrument_id'])!,
      values: $MeasurementsTable.$convertervalues.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}values'])!,
      ),
      enteredVia: $MeasurementsTable.$converterenteredVia.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}entered_via'])!,
      ),
      verdict: $MeasurementsTable.$converterverdict.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}verdict'])!,
      ),
      normId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}norm_id']),
      normSetVersion: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}norm_set_version'],
      )!,
      evalDetail: $MeasurementsTable.$converterevalDetail.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}eval_detail'])!,
      ),
      supersedesId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}supersedes_id']),
    );
  }

  @override
  $MeasurementsTable createAlias(String alias) {
    return $MeasurementsTable(attachedDatabase, alias);
  }

  static TypeConverter<MeasurementType, String> $convertertype = measurementTypeConverter;
  static TypeConverter<Map<String, Object?>, String> $convertervalues = const JsonMapConverter();
  static TypeConverter<EnteredVia, String> $converterenteredVia = enteredViaConverter;
  static TypeConverter<Verdict, String> $converterverdict = verdictConverter;
  static TypeConverter<Map<String, Object?>, String> $converterevalDetail = const JsonMapConverter();
}

class MeasurementRow extends DataClass implements Insertable<MeasurementRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final String sessionId;
  final String nodeId;
  final MeasurementType type;
  final String instrumentId;
  final Map<String, Object?> values;
  final EnteredVia enteredVia;
  final Verdict verdict;
  final String? normId;
  final String normSetVersion;
  final Map<String, Object?> evalDetail;

  /// Xato o'lchov o'chirilmaydi — yangisi `supersedes_id` bilan qo'shiladi; har bir o'lchov ko'pi bilan bir marta almashtiriladi.
  final String? supersedesId;
  const MeasurementRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.sessionId,
    required this.nodeId,
    required this.type,
    required this.instrumentId,
    required this.values,
    required this.enteredVia,
    required this.verdict,
    this.normId,
    required this.normSetVersion,
    required this.evalDetail,
    this.supersedesId,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['session_id'] = Variable<String>(sessionId);
    map['node_id'] = Variable<String>(nodeId);
    {
      map['type'] = Variable<String>($MeasurementsTable.$convertertype.toSql(type));
    }
    map['instrument_id'] = Variable<String>(instrumentId);
    {
      map['values'] = Variable<String>($MeasurementsTable.$convertervalues.toSql(values));
    }
    {
      map['entered_via'] = Variable<String>($MeasurementsTable.$converterenteredVia.toSql(enteredVia));
    }
    {
      map['verdict'] = Variable<String>($MeasurementsTable.$converterverdict.toSql(verdict));
    }
    if (!nullToAbsent || normId != null) {
      map['norm_id'] = Variable<String>(normId);
    }
    map['norm_set_version'] = Variable<String>(normSetVersion);
    {
      map['eval_detail'] = Variable<String>($MeasurementsTable.$converterevalDetail.toSql(evalDetail));
    }
    if (!nullToAbsent || supersedesId != null) {
      map['supersedes_id'] = Variable<String>(supersedesId);
    }
    return map;
  }

  MeasurementsCompanion toCompanion(bool nullToAbsent) {
    return MeasurementsCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      sessionId: Value(sessionId),
      nodeId: Value(nodeId),
      type: Value(type),
      instrumentId: Value(instrumentId),
      values: Value(values),
      enteredVia: Value(enteredVia),
      verdict: Value(verdict),
      normId: normId == null && nullToAbsent ? const Value.absent() : Value(normId),
      normSetVersion: Value(normSetVersion),
      evalDetail: Value(evalDetail),
      supersedesId: supersedesId == null && nullToAbsent ? const Value.absent() : Value(supersedesId),
    );
  }

  factory MeasurementRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MeasurementRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      sessionId: serializer.fromJson<String>(json['sessionId']),
      nodeId: serializer.fromJson<String>(json['nodeId']),
      type: serializer.fromJson<MeasurementType>(json['type']),
      instrumentId: serializer.fromJson<String>(json['instrumentId']),
      values: serializer.fromJson<Map<String, Object?>>(json['values']),
      enteredVia: serializer.fromJson<EnteredVia>(json['enteredVia']),
      verdict: serializer.fromJson<Verdict>(json['verdict']),
      normId: serializer.fromJson<String?>(json['normId']),
      normSetVersion: serializer.fromJson<String>(json['normSetVersion']),
      evalDetail: serializer.fromJson<Map<String, Object?>>(json['evalDetail']),
      supersedesId: serializer.fromJson<String?>(json['supersedesId']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'sessionId': serializer.toJson<String>(sessionId),
      'nodeId': serializer.toJson<String>(nodeId),
      'type': serializer.toJson<MeasurementType>(type),
      'instrumentId': serializer.toJson<String>(instrumentId),
      'values': serializer.toJson<Map<String, Object?>>(values),
      'enteredVia': serializer.toJson<EnteredVia>(enteredVia),
      'verdict': serializer.toJson<Verdict>(verdict),
      'normId': serializer.toJson<String?>(normId),
      'normSetVersion': serializer.toJson<String>(normSetVersion),
      'evalDetail': serializer.toJson<Map<String, Object?>>(evalDetail),
      'supersedesId': serializer.toJson<String?>(supersedesId),
    };
  }

  MeasurementRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    String? sessionId,
    String? nodeId,
    MeasurementType? type,
    String? instrumentId,
    Map<String, Object?>? values,
    EnteredVia? enteredVia,
    Verdict? verdict,
    Value<String?> normId = const Value.absent(),
    String? normSetVersion,
    Map<String, Object?>? evalDetail,
    Value<String?> supersedesId = const Value.absent(),
  }) => MeasurementRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    sessionId: sessionId ?? this.sessionId,
    nodeId: nodeId ?? this.nodeId,
    type: type ?? this.type,
    instrumentId: instrumentId ?? this.instrumentId,
    values: values ?? this.values,
    enteredVia: enteredVia ?? this.enteredVia,
    verdict: verdict ?? this.verdict,
    normId: normId.present ? normId.value : this.normId,
    normSetVersion: normSetVersion ?? this.normSetVersion,
    evalDetail: evalDetail ?? this.evalDetail,
    supersedesId: supersedesId.present ? supersedesId.value : this.supersedesId,
  );
  MeasurementRow copyWithCompanion(MeasurementsCompanion data) {
    return MeasurementRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      sessionId: data.sessionId.present ? data.sessionId.value : this.sessionId,
      nodeId: data.nodeId.present ? data.nodeId.value : this.nodeId,
      type: data.type.present ? data.type.value : this.type,
      instrumentId: data.instrumentId.present ? data.instrumentId.value : this.instrumentId,
      values: data.values.present ? data.values.value : this.values,
      enteredVia: data.enteredVia.present ? data.enteredVia.value : this.enteredVia,
      verdict: data.verdict.present ? data.verdict.value : this.verdict,
      normId: data.normId.present ? data.normId.value : this.normId,
      normSetVersion: data.normSetVersion.present ? data.normSetVersion.value : this.normSetVersion,
      evalDetail: data.evalDetail.present ? data.evalDetail.value : this.evalDetail,
      supersedesId: data.supersedesId.present ? data.supersedesId.value : this.supersedesId,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MeasurementRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('sessionId: $sessionId, ')
          ..write('nodeId: $nodeId, ')
          ..write('type: $type, ')
          ..write('instrumentId: $instrumentId, ')
          ..write('values: $values, ')
          ..write('enteredVia: $enteredVia, ')
          ..write('verdict: $verdict, ')
          ..write('normId: $normId, ')
          ..write('normSetVersion: $normSetVersion, ')
          ..write('evalDetail: $evalDetail, ')
          ..write('supersedesId: $supersedesId')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    sessionId,
    nodeId,
    type,
    instrumentId,
    values,
    enteredVia,
    verdict,
    normId,
    normSetVersion,
    evalDetail,
    supersedesId,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MeasurementRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.sessionId == this.sessionId &&
          other.nodeId == this.nodeId &&
          other.type == this.type &&
          other.instrumentId == this.instrumentId &&
          other.values == this.values &&
          other.enteredVia == this.enteredVia &&
          other.verdict == this.verdict &&
          other.normId == this.normId &&
          other.normSetVersion == this.normSetVersion &&
          other.evalDetail == this.evalDetail &&
          other.supersedesId == this.supersedesId);
}

class MeasurementsCompanion extends UpdateCompanion<MeasurementRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<String> sessionId;
  final Value<String> nodeId;
  final Value<MeasurementType> type;
  final Value<String> instrumentId;
  final Value<Map<String, Object?>> values;
  final Value<EnteredVia> enteredVia;
  final Value<Verdict> verdict;
  final Value<String?> normId;
  final Value<String> normSetVersion;
  final Value<Map<String, Object?>> evalDetail;
  final Value<String?> supersedesId;
  final Value<int> rowid;
  const MeasurementsCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.sessionId = const Value.absent(),
    this.nodeId = const Value.absent(),
    this.type = const Value.absent(),
    this.instrumentId = const Value.absent(),
    this.values = const Value.absent(),
    this.enteredVia = const Value.absent(),
    this.verdict = const Value.absent(),
    this.normId = const Value.absent(),
    this.normSetVersion = const Value.absent(),
    this.evalDetail = const Value.absent(),
    this.supersedesId = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  MeasurementsCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    required String sessionId,
    required String nodeId,
    required MeasurementType type,
    required String instrumentId,
    required Map<String, Object?> values,
    required EnteredVia enteredVia,
    required Verdict verdict,
    this.normId = const Value.absent(),
    required String normSetVersion,
    required Map<String, Object?> evalDetail,
    this.supersedesId = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       sessionId = Value(sessionId),
       nodeId = Value(nodeId),
       type = Value(type),
       instrumentId = Value(instrumentId),
       values = Value(values),
       enteredVia = Value(enteredVia),
       verdict = Value(verdict),
       normSetVersion = Value(normSetVersion),
       evalDetail = Value(evalDetail);
  static Insertable<MeasurementRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<String>? sessionId,
    Expression<String>? nodeId,
    Expression<String>? type,
    Expression<String>? instrumentId,
    Expression<String>? values,
    Expression<String>? enteredVia,
    Expression<String>? verdict,
    Expression<String>? normId,
    Expression<String>? normSetVersion,
    Expression<String>? evalDetail,
    Expression<String>? supersedesId,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (sessionId != null) 'session_id': sessionId,
      if (nodeId != null) 'node_id': nodeId,
      if (type != null) 'type': type,
      if (instrumentId != null) 'instrument_id': instrumentId,
      if (values != null) 'values': values,
      if (enteredVia != null) 'entered_via': enteredVia,
      if (verdict != null) 'verdict': verdict,
      if (normId != null) 'norm_id': normId,
      if (normSetVersion != null) 'norm_set_version': normSetVersion,
      if (evalDetail != null) 'eval_detail': evalDetail,
      if (supersedesId != null) 'supersedes_id': supersedesId,
      if (rowid != null) 'rowid': rowid,
    });
  }

  MeasurementsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<String>? sessionId,
    Value<String>? nodeId,
    Value<MeasurementType>? type,
    Value<String>? instrumentId,
    Value<Map<String, Object?>>? values,
    Value<EnteredVia>? enteredVia,
    Value<Verdict>? verdict,
    Value<String?>? normId,
    Value<String>? normSetVersion,
    Value<Map<String, Object?>>? evalDetail,
    Value<String?>? supersedesId,
    Value<int>? rowid,
  }) {
    return MeasurementsCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      sessionId: sessionId ?? this.sessionId,
      nodeId: nodeId ?? this.nodeId,
      type: type ?? this.type,
      instrumentId: instrumentId ?? this.instrumentId,
      values: values ?? this.values,
      enteredVia: enteredVia ?? this.enteredVia,
      verdict: verdict ?? this.verdict,
      normId: normId ?? this.normId,
      normSetVersion: normSetVersion ?? this.normSetVersion,
      evalDetail: evalDetail ?? this.evalDetail,
      supersedesId: supersedesId ?? this.supersedesId,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (sessionId.present) {
      map['session_id'] = Variable<String>(sessionId.value);
    }
    if (nodeId.present) {
      map['node_id'] = Variable<String>(nodeId.value);
    }
    if (type.present) {
      map['type'] = Variable<String>($MeasurementsTable.$convertertype.toSql(type.value));
    }
    if (instrumentId.present) {
      map['instrument_id'] = Variable<String>(instrumentId.value);
    }
    if (values.present) {
      map['values'] = Variable<String>($MeasurementsTable.$convertervalues.toSql(values.value));
    }
    if (enteredVia.present) {
      map['entered_via'] = Variable<String>($MeasurementsTable.$converterenteredVia.toSql(enteredVia.value));
    }
    if (verdict.present) {
      map['verdict'] = Variable<String>($MeasurementsTable.$converterverdict.toSql(verdict.value));
    }
    if (normId.present) {
      map['norm_id'] = Variable<String>(normId.value);
    }
    if (normSetVersion.present) {
      map['norm_set_version'] = Variable<String>(normSetVersion.value);
    }
    if (evalDetail.present) {
      map['eval_detail'] = Variable<String>($MeasurementsTable.$converterevalDetail.toSql(evalDetail.value));
    }
    if (supersedesId.present) {
      map['supersedes_id'] = Variable<String>(supersedesId.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('MeasurementsCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('sessionId: $sessionId, ')
          ..write('nodeId: $nodeId, ')
          ..write('type: $type, ')
          ..write('instrumentId: $instrumentId, ')
          ..write('values: $values, ')
          ..write('enteredVia: $enteredVia, ')
          ..write('verdict: $verdict, ')
          ..write('normId: $normId, ')
          ..write('normSetVersion: $normSetVersion, ')
          ..write('evalDetail: $evalDetail, ')
          ..write('supersedesId: $supersedesId, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $DevicesTable extends Devices with TableInfo<$DevicesTable, DeviceRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $DevicesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _deletedMeta = const VerificationMeta('deleted');
  @override
  late final GeneratedColumn<bool> deleted = GeneratedColumn<bool>(
    'deleted',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("deleted" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _userIdMeta = const VerificationMeta('userId');
  @override
  late final GeneratedColumn<String> userId = GeneratedColumn<String>(
    'user_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES app_user (id)'),
  );
  static const VerificationMeta _publicKeyEd25519Meta = const VerificationMeta('publicKeyEd25519');
  @override
  late final GeneratedColumn<String> publicKeyEd25519 = GeneratedColumn<String>(
    'public_key_ed25519',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sigAlgMeta = const VerificationMeta('sigAlg');
  @override
  late final GeneratedColumn<String> sigAlg = GeneratedColumn<String>(
    'sig_alg',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _registeredAtMeta = const VerificationMeta('registeredAt');
  @override
  late final GeneratedColumn<DateTime> registeredAt = GeneratedColumn<DateTime>(
    'registered_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revokedAtMeta = const VerificationMeta('revokedAt');
  @override
  late final GeneratedColumn<DateTime> revokedAt = GeneratedColumn<DateTime>(
    'revoked_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    userId,
    publicKeyEd25519,
    sigAlg,
    registeredAt,
    revokedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'device';
  @override
  VerificationContext validateIntegrity(Insertable<DeviceRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('deleted')) {
      context.handle(_deletedMeta, deleted.isAcceptableOrUnknown(data['deleted']!, _deletedMeta));
    }
    if (data.containsKey('user_id')) {
      context.handle(_userIdMeta, userId.isAcceptableOrUnknown(data['user_id']!, _userIdMeta));
    } else if (isInserting) {
      context.missing(_userIdMeta);
    }
    if (data.containsKey('public_key_ed25519')) {
      context.handle(
        _publicKeyEd25519Meta,
        publicKeyEd25519.isAcceptableOrUnknown(data['public_key_ed25519']!, _publicKeyEd25519Meta),
      );
    } else if (isInserting) {
      context.missing(_publicKeyEd25519Meta);
    }
    if (data.containsKey('sig_alg')) {
      context.handle(_sigAlgMeta, sigAlg.isAcceptableOrUnknown(data['sig_alg']!, _sigAlgMeta));
    } else if (isInserting) {
      context.missing(_sigAlgMeta);
    }
    if (data.containsKey('registered_at')) {
      context.handle(_registeredAtMeta, registeredAt.isAcceptableOrUnknown(data['registered_at']!, _registeredAtMeta));
    } else if (isInserting) {
      context.missing(_registeredAtMeta);
    }
    if (data.containsKey('revoked_at')) {
      context.handle(_revokedAtMeta, revokedAt.isAcceptableOrUnknown(data['revoked_at']!, _revokedAtMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  DeviceRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return DeviceRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      deleted: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}deleted'])!,
      userId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}user_id'])!,
      publicKeyEd25519: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}public_key_ed25519'],
      )!,
      sigAlg: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}sig_alg'])!,
      registeredAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}registered_at'])!,
      revokedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}revoked_at']),
    );
  }

  @override
  $DevicesTable createAlias(String alias) {
    return $DevicesTable(attachedDatabase, alias);
  }
}

class DeviceRow extends DataClass implements Insertable<DeviceRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final bool deleted;
  final String userId;
  final String publicKeyEd25519;
  final String sigAlg;
  final DateTime registeredAt;
  final DateTime? revokedAt;
  const DeviceRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.deleted,
    required this.userId,
    required this.publicKeyEd25519,
    required this.sigAlg,
    required this.registeredAt,
    this.revokedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['deleted'] = Variable<bool>(deleted);
    map['user_id'] = Variable<String>(userId);
    map['public_key_ed25519'] = Variable<String>(publicKeyEd25519);
    map['sig_alg'] = Variable<String>(sigAlg);
    map['registered_at'] = Variable<DateTime>(registeredAt);
    if (!nullToAbsent || revokedAt != null) {
      map['revoked_at'] = Variable<DateTime>(revokedAt);
    }
    return map;
  }

  DevicesCompanion toCompanion(bool nullToAbsent) {
    return DevicesCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      deleted: Value(deleted),
      userId: Value(userId),
      publicKeyEd25519: Value(publicKeyEd25519),
      sigAlg: Value(sigAlg),
      registeredAt: Value(registeredAt),
      revokedAt: revokedAt == null && nullToAbsent ? const Value.absent() : Value(revokedAt),
    );
  }

  factory DeviceRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return DeviceRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      deleted: serializer.fromJson<bool>(json['deleted']),
      userId: serializer.fromJson<String>(json['userId']),
      publicKeyEd25519: serializer.fromJson<String>(json['publicKeyEd25519']),
      sigAlg: serializer.fromJson<String>(json['sigAlg']),
      registeredAt: serializer.fromJson<DateTime>(json['registeredAt']),
      revokedAt: serializer.fromJson<DateTime?>(json['revokedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'deleted': serializer.toJson<bool>(deleted),
      'userId': serializer.toJson<String>(userId),
      'publicKeyEd25519': serializer.toJson<String>(publicKeyEd25519),
      'sigAlg': serializer.toJson<String>(sigAlg),
      'registeredAt': serializer.toJson<DateTime>(registeredAt),
      'revokedAt': serializer.toJson<DateTime?>(revokedAt),
    };
  }

  DeviceRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    bool? deleted,
    String? userId,
    String? publicKeyEd25519,
    String? sigAlg,
    DateTime? registeredAt,
    Value<DateTime?> revokedAt = const Value.absent(),
  }) => DeviceRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    deleted: deleted ?? this.deleted,
    userId: userId ?? this.userId,
    publicKeyEd25519: publicKeyEd25519 ?? this.publicKeyEd25519,
    sigAlg: sigAlg ?? this.sigAlg,
    registeredAt: registeredAt ?? this.registeredAt,
    revokedAt: revokedAt.present ? revokedAt.value : this.revokedAt,
  );
  DeviceRow copyWithCompanion(DevicesCompanion data) {
    return DeviceRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      deleted: data.deleted.present ? data.deleted.value : this.deleted,
      userId: data.userId.present ? data.userId.value : this.userId,
      publicKeyEd25519: data.publicKeyEd25519.present ? data.publicKeyEd25519.value : this.publicKeyEd25519,
      sigAlg: data.sigAlg.present ? data.sigAlg.value : this.sigAlg,
      registeredAt: data.registeredAt.present ? data.registeredAt.value : this.registeredAt,
      revokedAt: data.revokedAt.present ? data.revokedAt.value : this.revokedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('DeviceRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('userId: $userId, ')
          ..write('publicKeyEd25519: $publicKeyEd25519, ')
          ..write('sigAlg: $sigAlg, ')
          ..write('registeredAt: $registeredAt, ')
          ..write('revokedAt: $revokedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    userId,
    publicKeyEd25519,
    sigAlg,
    registeredAt,
    revokedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is DeviceRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.deleted == this.deleted &&
          other.userId == this.userId &&
          other.publicKeyEd25519 == this.publicKeyEd25519 &&
          other.sigAlg == this.sigAlg &&
          other.registeredAt == this.registeredAt &&
          other.revokedAt == this.revokedAt);
}

class DevicesCompanion extends UpdateCompanion<DeviceRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<bool> deleted;
  final Value<String> userId;
  final Value<String> publicKeyEd25519;
  final Value<String> sigAlg;
  final Value<DateTime> registeredAt;
  final Value<DateTime?> revokedAt;
  final Value<int> rowid;
  const DevicesCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.deleted = const Value.absent(),
    this.userId = const Value.absent(),
    this.publicKeyEd25519 = const Value.absent(),
    this.sigAlg = const Value.absent(),
    this.registeredAt = const Value.absent(),
    this.revokedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  DevicesCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    this.deleted = const Value.absent(),
    required String userId,
    required String publicKeyEd25519,
    required String sigAlg,
    required DateTime registeredAt,
    this.revokedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       userId = Value(userId),
       publicKeyEd25519 = Value(publicKeyEd25519),
       sigAlg = Value(sigAlg),
       registeredAt = Value(registeredAt);
  static Insertable<DeviceRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<bool>? deleted,
    Expression<String>? userId,
    Expression<String>? publicKeyEd25519,
    Expression<String>? sigAlg,
    Expression<DateTime>? registeredAt,
    Expression<DateTime>? revokedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (deleted != null) 'deleted': deleted,
      if (userId != null) 'user_id': userId,
      if (publicKeyEd25519 != null) 'public_key_ed25519': publicKeyEd25519,
      if (sigAlg != null) 'sig_alg': sigAlg,
      if (registeredAt != null) 'registered_at': registeredAt,
      if (revokedAt != null) 'revoked_at': revokedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  DevicesCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<bool>? deleted,
    Value<String>? userId,
    Value<String>? publicKeyEd25519,
    Value<String>? sigAlg,
    Value<DateTime>? registeredAt,
    Value<DateTime?>? revokedAt,
    Value<int>? rowid,
  }) {
    return DevicesCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      deleted: deleted ?? this.deleted,
      userId: userId ?? this.userId,
      publicKeyEd25519: publicKeyEd25519 ?? this.publicKeyEd25519,
      sigAlg: sigAlg ?? this.sigAlg,
      registeredAt: registeredAt ?? this.registeredAt,
      revokedAt: revokedAt ?? this.revokedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (deleted.present) {
      map['deleted'] = Variable<bool>(deleted.value);
    }
    if (userId.present) {
      map['user_id'] = Variable<String>(userId.value);
    }
    if (publicKeyEd25519.present) {
      map['public_key_ed25519'] = Variable<String>(publicKeyEd25519.value);
    }
    if (sigAlg.present) {
      map['sig_alg'] = Variable<String>(sigAlg.value);
    }
    if (registeredAt.present) {
      map['registered_at'] = Variable<DateTime>(registeredAt.value);
    }
    if (revokedAt.present) {
      map['revoked_at'] = Variable<DateTime>(revokedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('DevicesCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('userId: $userId, ')
          ..write('publicKeyEd25519: $publicKeyEd25519, ')
          ..write('sigAlg: $sigAlg, ')
          ..write('registeredAt: $registeredAt, ')
          ..write('revokedAt: $revokedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $ProtocolsTable extends Protocols with TableInfo<$ProtocolsTable, ProtocolRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ProtocolsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _sessionIdMeta = const VerificationMeta('sessionId');
  @override
  late final GeneratedColumn<String> sessionId = GeneratedColumn<String>(
    'session_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES measurement_session (id)'),
  );
  static const VerificationMeta _numberMeta = const VerificationMeta('number');
  @override
  late final GeneratedColumn<String> number = GeneratedColumn<String>(
    'number',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _payloadSha256Meta = const VerificationMeta('payloadSha256');
  @override
  late final GeneratedColumn<String> payloadSha256 = GeneratedColumn<String>(
    'payload_sha256',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _pdfSha256Meta = const VerificationMeta('pdfSha256');
  @override
  late final GeneratedColumn<String> pdfSha256 = GeneratedColumn<String>(
    'pdf_sha256',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _signedByMeta = const VerificationMeta('signedBy');
  @override
  late final GeneratedColumn<String> signedBy = GeneratedColumn<String>(
    'signed_by',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES app_user (id)'),
  );
  static const VerificationMeta _deviceIdMeta = const VerificationMeta('deviceId');
  @override
  late final GeneratedColumn<String> deviceId = GeneratedColumn<String>(
    'device_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES device (id)'),
  );
  static const VerificationMeta _signatureMeta = const VerificationMeta('signature');
  @override
  late final GeneratedColumn<String> signature = GeneratedColumn<String>(
    'signature',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sigAlgMeta = const VerificationMeta('sigAlg');
  @override
  late final GeneratedColumn<String> sigAlg = GeneratedColumn<String>(
    'sig_alg',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _qrTokenMeta = const VerificationMeta('qrToken');
  @override
  late final GeneratedColumn<String> qrToken = GeneratedColumn<String>(
    'qr_token',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('UNIQUE'),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    sessionId,
    number,
    payloadSha256,
    pdfSha256,
    signedBy,
    deviceId,
    signature,
    sigAlg,
    qrToken,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'protocol';
  @override
  VerificationContext validateIntegrity(Insertable<ProtocolRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('session_id')) {
      context.handle(_sessionIdMeta, sessionId.isAcceptableOrUnknown(data['session_id']!, _sessionIdMeta));
    } else if (isInserting) {
      context.missing(_sessionIdMeta);
    }
    if (data.containsKey('number')) {
      context.handle(_numberMeta, number.isAcceptableOrUnknown(data['number']!, _numberMeta));
    } else if (isInserting) {
      context.missing(_numberMeta);
    }
    if (data.containsKey('payload_sha256')) {
      context.handle(
        _payloadSha256Meta,
        payloadSha256.isAcceptableOrUnknown(data['payload_sha256']!, _payloadSha256Meta),
      );
    } else if (isInserting) {
      context.missing(_payloadSha256Meta);
    }
    if (data.containsKey('pdf_sha256')) {
      context.handle(_pdfSha256Meta, pdfSha256.isAcceptableOrUnknown(data['pdf_sha256']!, _pdfSha256Meta));
    } else if (isInserting) {
      context.missing(_pdfSha256Meta);
    }
    if (data.containsKey('signed_by')) {
      context.handle(_signedByMeta, signedBy.isAcceptableOrUnknown(data['signed_by']!, _signedByMeta));
    } else if (isInserting) {
      context.missing(_signedByMeta);
    }
    if (data.containsKey('device_id')) {
      context.handle(_deviceIdMeta, deviceId.isAcceptableOrUnknown(data['device_id']!, _deviceIdMeta));
    } else if (isInserting) {
      context.missing(_deviceIdMeta);
    }
    if (data.containsKey('signature')) {
      context.handle(_signatureMeta, signature.isAcceptableOrUnknown(data['signature']!, _signatureMeta));
    } else if (isInserting) {
      context.missing(_signatureMeta);
    }
    if (data.containsKey('sig_alg')) {
      context.handle(_sigAlgMeta, sigAlg.isAcceptableOrUnknown(data['sig_alg']!, _sigAlgMeta));
    } else if (isInserting) {
      context.missing(_sigAlgMeta);
    }
    if (data.containsKey('qr_token')) {
      context.handle(_qrTokenMeta, qrToken.isAcceptableOrUnknown(data['qr_token']!, _qrTokenMeta));
    } else if (isInserting) {
      context.missing(_qrTokenMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {orgId, number},
  ];
  @override
  ProtocolRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ProtocolRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      sessionId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}session_id'])!,
      number: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}number'])!,
      payloadSha256: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}payload_sha256'])!,
      pdfSha256: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}pdf_sha256'])!,
      signedBy: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}signed_by'])!,
      deviceId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}device_id'])!,
      signature: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}signature'])!,
      sigAlg: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}sig_alg'])!,
      qrToken: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}qr_token'])!,
    );
  }

  @override
  $ProtocolsTable createAlias(String alias) {
    return $ProtocolsTable(attachedDatabase, alias);
  }
}

class ProtocolRow extends DataClass implements Insertable<ProtocolRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final String sessionId;
  final String number;
  final String payloadSha256;
  final String pdfSha256;
  final String signedBy;
  final String deviceId;
  final String signature;
  final String sigAlg;
  final String qrToken;
  const ProtocolRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.sessionId,
    required this.number,
    required this.payloadSha256,
    required this.pdfSha256,
    required this.signedBy,
    required this.deviceId,
    required this.signature,
    required this.sigAlg,
    required this.qrToken,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['session_id'] = Variable<String>(sessionId);
    map['number'] = Variable<String>(number);
    map['payload_sha256'] = Variable<String>(payloadSha256);
    map['pdf_sha256'] = Variable<String>(pdfSha256);
    map['signed_by'] = Variable<String>(signedBy);
    map['device_id'] = Variable<String>(deviceId);
    map['signature'] = Variable<String>(signature);
    map['sig_alg'] = Variable<String>(sigAlg);
    map['qr_token'] = Variable<String>(qrToken);
    return map;
  }

  ProtocolsCompanion toCompanion(bool nullToAbsent) {
    return ProtocolsCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      sessionId: Value(sessionId),
      number: Value(number),
      payloadSha256: Value(payloadSha256),
      pdfSha256: Value(pdfSha256),
      signedBy: Value(signedBy),
      deviceId: Value(deviceId),
      signature: Value(signature),
      sigAlg: Value(sigAlg),
      qrToken: Value(qrToken),
    );
  }

  factory ProtocolRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ProtocolRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      sessionId: serializer.fromJson<String>(json['sessionId']),
      number: serializer.fromJson<String>(json['number']),
      payloadSha256: serializer.fromJson<String>(json['payloadSha256']),
      pdfSha256: serializer.fromJson<String>(json['pdfSha256']),
      signedBy: serializer.fromJson<String>(json['signedBy']),
      deviceId: serializer.fromJson<String>(json['deviceId']),
      signature: serializer.fromJson<String>(json['signature']),
      sigAlg: serializer.fromJson<String>(json['sigAlg']),
      qrToken: serializer.fromJson<String>(json['qrToken']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'sessionId': serializer.toJson<String>(sessionId),
      'number': serializer.toJson<String>(number),
      'payloadSha256': serializer.toJson<String>(payloadSha256),
      'pdfSha256': serializer.toJson<String>(pdfSha256),
      'signedBy': serializer.toJson<String>(signedBy),
      'deviceId': serializer.toJson<String>(deviceId),
      'signature': serializer.toJson<String>(signature),
      'sigAlg': serializer.toJson<String>(sigAlg),
      'qrToken': serializer.toJson<String>(qrToken),
    };
  }

  ProtocolRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    String? sessionId,
    String? number,
    String? payloadSha256,
    String? pdfSha256,
    String? signedBy,
    String? deviceId,
    String? signature,
    String? sigAlg,
    String? qrToken,
  }) => ProtocolRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    sessionId: sessionId ?? this.sessionId,
    number: number ?? this.number,
    payloadSha256: payloadSha256 ?? this.payloadSha256,
    pdfSha256: pdfSha256 ?? this.pdfSha256,
    signedBy: signedBy ?? this.signedBy,
    deviceId: deviceId ?? this.deviceId,
    signature: signature ?? this.signature,
    sigAlg: sigAlg ?? this.sigAlg,
    qrToken: qrToken ?? this.qrToken,
  );
  ProtocolRow copyWithCompanion(ProtocolsCompanion data) {
    return ProtocolRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      sessionId: data.sessionId.present ? data.sessionId.value : this.sessionId,
      number: data.number.present ? data.number.value : this.number,
      payloadSha256: data.payloadSha256.present ? data.payloadSha256.value : this.payloadSha256,
      pdfSha256: data.pdfSha256.present ? data.pdfSha256.value : this.pdfSha256,
      signedBy: data.signedBy.present ? data.signedBy.value : this.signedBy,
      deviceId: data.deviceId.present ? data.deviceId.value : this.deviceId,
      signature: data.signature.present ? data.signature.value : this.signature,
      sigAlg: data.sigAlg.present ? data.sigAlg.value : this.sigAlg,
      qrToken: data.qrToken.present ? data.qrToken.value : this.qrToken,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ProtocolRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('sessionId: $sessionId, ')
          ..write('number: $number, ')
          ..write('payloadSha256: $payloadSha256, ')
          ..write('pdfSha256: $pdfSha256, ')
          ..write('signedBy: $signedBy, ')
          ..write('deviceId: $deviceId, ')
          ..write('signature: $signature, ')
          ..write('sigAlg: $sigAlg, ')
          ..write('qrToken: $qrToken')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    sessionId,
    number,
    payloadSha256,
    pdfSha256,
    signedBy,
    deviceId,
    signature,
    sigAlg,
    qrToken,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ProtocolRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.sessionId == this.sessionId &&
          other.number == this.number &&
          other.payloadSha256 == this.payloadSha256 &&
          other.pdfSha256 == this.pdfSha256 &&
          other.signedBy == this.signedBy &&
          other.deviceId == this.deviceId &&
          other.signature == this.signature &&
          other.sigAlg == this.sigAlg &&
          other.qrToken == this.qrToken);
}

class ProtocolsCompanion extends UpdateCompanion<ProtocolRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<String> sessionId;
  final Value<String> number;
  final Value<String> payloadSha256;
  final Value<String> pdfSha256;
  final Value<String> signedBy;
  final Value<String> deviceId;
  final Value<String> signature;
  final Value<String> sigAlg;
  final Value<String> qrToken;
  final Value<int> rowid;
  const ProtocolsCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.sessionId = const Value.absent(),
    this.number = const Value.absent(),
    this.payloadSha256 = const Value.absent(),
    this.pdfSha256 = const Value.absent(),
    this.signedBy = const Value.absent(),
    this.deviceId = const Value.absent(),
    this.signature = const Value.absent(),
    this.sigAlg = const Value.absent(),
    this.qrToken = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  ProtocolsCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    required String sessionId,
    required String number,
    required String payloadSha256,
    required String pdfSha256,
    required String signedBy,
    required String deviceId,
    required String signature,
    required String sigAlg,
    required String qrToken,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       sessionId = Value(sessionId),
       number = Value(number),
       payloadSha256 = Value(payloadSha256),
       pdfSha256 = Value(pdfSha256),
       signedBy = Value(signedBy),
       deviceId = Value(deviceId),
       signature = Value(signature),
       sigAlg = Value(sigAlg),
       qrToken = Value(qrToken);
  static Insertable<ProtocolRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<String>? sessionId,
    Expression<String>? number,
    Expression<String>? payloadSha256,
    Expression<String>? pdfSha256,
    Expression<String>? signedBy,
    Expression<String>? deviceId,
    Expression<String>? signature,
    Expression<String>? sigAlg,
    Expression<String>? qrToken,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (sessionId != null) 'session_id': sessionId,
      if (number != null) 'number': number,
      if (payloadSha256 != null) 'payload_sha256': payloadSha256,
      if (pdfSha256 != null) 'pdf_sha256': pdfSha256,
      if (signedBy != null) 'signed_by': signedBy,
      if (deviceId != null) 'device_id': deviceId,
      if (signature != null) 'signature': signature,
      if (sigAlg != null) 'sig_alg': sigAlg,
      if (qrToken != null) 'qr_token': qrToken,
      if (rowid != null) 'rowid': rowid,
    });
  }

  ProtocolsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<String>? sessionId,
    Value<String>? number,
    Value<String>? payloadSha256,
    Value<String>? pdfSha256,
    Value<String>? signedBy,
    Value<String>? deviceId,
    Value<String>? signature,
    Value<String>? sigAlg,
    Value<String>? qrToken,
    Value<int>? rowid,
  }) {
    return ProtocolsCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      sessionId: sessionId ?? this.sessionId,
      number: number ?? this.number,
      payloadSha256: payloadSha256 ?? this.payloadSha256,
      pdfSha256: pdfSha256 ?? this.pdfSha256,
      signedBy: signedBy ?? this.signedBy,
      deviceId: deviceId ?? this.deviceId,
      signature: signature ?? this.signature,
      sigAlg: sigAlg ?? this.sigAlg,
      qrToken: qrToken ?? this.qrToken,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (sessionId.present) {
      map['session_id'] = Variable<String>(sessionId.value);
    }
    if (number.present) {
      map['number'] = Variable<String>(number.value);
    }
    if (payloadSha256.present) {
      map['payload_sha256'] = Variable<String>(payloadSha256.value);
    }
    if (pdfSha256.present) {
      map['pdf_sha256'] = Variable<String>(pdfSha256.value);
    }
    if (signedBy.present) {
      map['signed_by'] = Variable<String>(signedBy.value);
    }
    if (deviceId.present) {
      map['device_id'] = Variable<String>(deviceId.value);
    }
    if (signature.present) {
      map['signature'] = Variable<String>(signature.value);
    }
    if (sigAlg.present) {
      map['sig_alg'] = Variable<String>(sigAlg.value);
    }
    if (qrToken.present) {
      map['qr_token'] = Variable<String>(qrToken.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ProtocolsCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('sessionId: $sessionId, ')
          ..write('number: $number, ')
          ..write('payloadSha256: $payloadSha256, ')
          ..write('pdfSha256: $pdfSha256, ')
          ..write('signedBy: $signedBy, ')
          ..write('deviceId: $deviceId, ')
          ..write('signature: $signature, ')
          ..write('sigAlg: $sigAlg, ')
          ..write('qrToken: $qrToken, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $ProtocolDocumentsTable extends ProtocolDocuments with TableInfo<$ProtocolDocumentsTable, ProtocolDocumentRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ProtocolDocumentsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _protocolIdMeta = const VerificationMeta('protocolId');
  @override
  late final GeneratedColumn<String> protocolId = GeneratedColumn<String>(
    'protocol_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('UNIQUE REFERENCES protocol (id)'),
  );
  static const VerificationMeta _payloadJsonMeta = const VerificationMeta('payloadJson');
  @override
  late final GeneratedColumn<String> payloadJson = GeneratedColumn<String>(
    'payload_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _pdfMeta = const VerificationMeta('pdf');
  @override
  late final GeneratedColumn<Uint8List> pdf = GeneratedColumn<Uint8List>(
    'pdf',
    aliasedName,
    false,
    type: DriftSqlType.blob,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [id, createdAt, updatedAt, rev, orgId, protocolId, payloadJson, pdf];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'protocol_document';
  @override
  VerificationContext validateIntegrity(Insertable<ProtocolDocumentRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('protocol_id')) {
      context.handle(_protocolIdMeta, protocolId.isAcceptableOrUnknown(data['protocol_id']!, _protocolIdMeta));
    } else if (isInserting) {
      context.missing(_protocolIdMeta);
    }
    if (data.containsKey('payload_json')) {
      context.handle(_payloadJsonMeta, payloadJson.isAcceptableOrUnknown(data['payload_json']!, _payloadJsonMeta));
    } else if (isInserting) {
      context.missing(_payloadJsonMeta);
    }
    if (data.containsKey('pdf')) {
      context.handle(_pdfMeta, pdf.isAcceptableOrUnknown(data['pdf']!, _pdfMeta));
    } else if (isInserting) {
      context.missing(_pdfMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  ProtocolDocumentRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ProtocolDocumentRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      protocolId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}protocol_id'])!,
      payloadJson: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}payload_json'])!,
      pdf: attachedDatabase.typeMapping.read(DriftSqlType.blob, data['${effectivePrefix}pdf'])!,
    );
  }

  @override
  $ProtocolDocumentsTable createAlias(String alias) {
    return $ProtocolDocumentsTable(attachedDatabase, alias);
  }
}

class ProtocolDocumentRow extends DataClass implements Insertable<ProtocolDocumentRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final String protocolId;
  final String payloadJson;
  final Uint8List pdf;
  const ProtocolDocumentRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.protocolId,
    required this.payloadJson,
    required this.pdf,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['protocol_id'] = Variable<String>(protocolId);
    map['payload_json'] = Variable<String>(payloadJson);
    map['pdf'] = Variable<Uint8List>(pdf);
    return map;
  }

  ProtocolDocumentsCompanion toCompanion(bool nullToAbsent) {
    return ProtocolDocumentsCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      protocolId: Value(protocolId),
      payloadJson: Value(payloadJson),
      pdf: Value(pdf),
    );
  }

  factory ProtocolDocumentRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ProtocolDocumentRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      protocolId: serializer.fromJson<String>(json['protocolId']),
      payloadJson: serializer.fromJson<String>(json['payloadJson']),
      pdf: serializer.fromJson<Uint8List>(json['pdf']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'protocolId': serializer.toJson<String>(protocolId),
      'payloadJson': serializer.toJson<String>(payloadJson),
      'pdf': serializer.toJson<Uint8List>(pdf),
    };
  }

  ProtocolDocumentRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    String? protocolId,
    String? payloadJson,
    Uint8List? pdf,
  }) => ProtocolDocumentRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    protocolId: protocolId ?? this.protocolId,
    payloadJson: payloadJson ?? this.payloadJson,
    pdf: pdf ?? this.pdf,
  );
  ProtocolDocumentRow copyWithCompanion(ProtocolDocumentsCompanion data) {
    return ProtocolDocumentRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      protocolId: data.protocolId.present ? data.protocolId.value : this.protocolId,
      payloadJson: data.payloadJson.present ? data.payloadJson.value : this.payloadJson,
      pdf: data.pdf.present ? data.pdf.value : this.pdf,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ProtocolDocumentRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('protocolId: $protocolId, ')
          ..write('payloadJson: $payloadJson, ')
          ..write('pdf: $pdf')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, createdAt, updatedAt, rev, orgId, protocolId, payloadJson, $driftBlobEquality.hash(pdf));
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ProtocolDocumentRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.protocolId == this.protocolId &&
          other.payloadJson == this.payloadJson &&
          $driftBlobEquality.equals(other.pdf, this.pdf));
}

class ProtocolDocumentsCompanion extends UpdateCompanion<ProtocolDocumentRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<String> protocolId;
  final Value<String> payloadJson;
  final Value<Uint8List> pdf;
  final Value<int> rowid;
  const ProtocolDocumentsCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.protocolId = const Value.absent(),
    this.payloadJson = const Value.absent(),
    this.pdf = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  ProtocolDocumentsCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    required String protocolId,
    required String payloadJson,
    required Uint8List pdf,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       protocolId = Value(protocolId),
       payloadJson = Value(payloadJson),
       pdf = Value(pdf);
  static Insertable<ProtocolDocumentRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<String>? protocolId,
    Expression<String>? payloadJson,
    Expression<Uint8List>? pdf,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (protocolId != null) 'protocol_id': protocolId,
      if (payloadJson != null) 'payload_json': payloadJson,
      if (pdf != null) 'pdf': pdf,
      if (rowid != null) 'rowid': rowid,
    });
  }

  ProtocolDocumentsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<String>? protocolId,
    Value<String>? payloadJson,
    Value<Uint8List>? pdf,
    Value<int>? rowid,
  }) {
    return ProtocolDocumentsCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      protocolId: protocolId ?? this.protocolId,
      payloadJson: payloadJson ?? this.payloadJson,
      pdf: pdf ?? this.pdf,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (protocolId.present) {
      map['protocol_id'] = Variable<String>(protocolId.value);
    }
    if (payloadJson.present) {
      map['payload_json'] = Variable<String>(payloadJson.value);
    }
    if (pdf.present) {
      map['pdf'] = Variable<Uint8List>(pdf.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ProtocolDocumentsCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('protocolId: $protocolId, ')
          ..write('payloadJson: $payloadJson, ')
          ..write('pdf: $pdf, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $AuditEventsTable extends AuditEvents with TableInfo<$AuditEventsTable, AuditEventRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $AuditEventsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _deviceIdMeta = const VerificationMeta('deviceId');
  @override
  late final GeneratedColumn<String> deviceId = GeneratedColumn<String>(
    'device_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES device (id)'),
  );
  static const VerificationMeta _seqMeta = const VerificationMeta('seq');
  @override
  late final GeneratedColumn<int> seq = GeneratedColumn<int>(
    'seq',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _prevHashMeta = const VerificationMeta('prevHash');
  @override
  late final GeneratedColumn<String> prevHash = GeneratedColumn<String>(
    'prev_hash',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _eventHashMeta = const VerificationMeta('eventHash');
  @override
  late final GeneratedColumn<String> eventHash = GeneratedColumn<String>(
    'event_hash',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('UNIQUE'),
  );
  static const VerificationMeta _actorIdMeta = const VerificationMeta('actorId');
  @override
  late final GeneratedColumn<String> actorId = GeneratedColumn<String>(
    'actor_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES app_user (id)'),
  );
  static const VerificationMeta _eventTypeMeta = const VerificationMeta('eventType');
  @override
  late final GeneratedColumn<String> eventType = GeneratedColumn<String>(
    'event_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _entityIdMeta = const VerificationMeta('entityId');
  @override
  late final GeneratedColumn<String> entityId = GeneratedColumn<String>(
    'entity_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _payloadHashMeta = const VerificationMeta('payloadHash');
  @override
  late final GeneratedColumn<String> payloadHash = GeneratedColumn<String>(
    'payload_hash',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _deviceSigMeta = const VerificationMeta('deviceSig');
  @override
  late final GeneratedColumn<String> deviceSig = GeneratedColumn<String>(
    'device_sig',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sigAlgMeta = const VerificationMeta('sigAlg');
  @override
  late final GeneratedColumn<String> sigAlg = GeneratedColumn<String>(
    'sig_alg',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _eventAtMeta = const VerificationMeta('eventAt');
  @override
  late final GeneratedColumn<String> eventAt = GeneratedColumn<String>(
    'event_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deviceId,
    seq,
    prevHash,
    eventHash,
    actorId,
    eventType,
    entityId,
    payloadHash,
    deviceSig,
    sigAlg,
    eventAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'audit_event';
  @override
  VerificationContext validateIntegrity(Insertable<AuditEventRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('device_id')) {
      context.handle(_deviceIdMeta, deviceId.isAcceptableOrUnknown(data['device_id']!, _deviceIdMeta));
    } else if (isInserting) {
      context.missing(_deviceIdMeta);
    }
    if (data.containsKey('seq')) {
      context.handle(_seqMeta, seq.isAcceptableOrUnknown(data['seq']!, _seqMeta));
    } else if (isInserting) {
      context.missing(_seqMeta);
    }
    if (data.containsKey('prev_hash')) {
      context.handle(_prevHashMeta, prevHash.isAcceptableOrUnknown(data['prev_hash']!, _prevHashMeta));
    } else if (isInserting) {
      context.missing(_prevHashMeta);
    }
    if (data.containsKey('event_hash')) {
      context.handle(_eventHashMeta, eventHash.isAcceptableOrUnknown(data['event_hash']!, _eventHashMeta));
    } else if (isInserting) {
      context.missing(_eventHashMeta);
    }
    if (data.containsKey('actor_id')) {
      context.handle(_actorIdMeta, actorId.isAcceptableOrUnknown(data['actor_id']!, _actorIdMeta));
    } else if (isInserting) {
      context.missing(_actorIdMeta);
    }
    if (data.containsKey('event_type')) {
      context.handle(_eventTypeMeta, eventType.isAcceptableOrUnknown(data['event_type']!, _eventTypeMeta));
    } else if (isInserting) {
      context.missing(_eventTypeMeta);
    }
    if (data.containsKey('entity_id')) {
      context.handle(_entityIdMeta, entityId.isAcceptableOrUnknown(data['entity_id']!, _entityIdMeta));
    }
    if (data.containsKey('payload_hash')) {
      context.handle(_payloadHashMeta, payloadHash.isAcceptableOrUnknown(data['payload_hash']!, _payloadHashMeta));
    } else if (isInserting) {
      context.missing(_payloadHashMeta);
    }
    if (data.containsKey('device_sig')) {
      context.handle(_deviceSigMeta, deviceSig.isAcceptableOrUnknown(data['device_sig']!, _deviceSigMeta));
    } else if (isInserting) {
      context.missing(_deviceSigMeta);
    }
    if (data.containsKey('sig_alg')) {
      context.handle(_sigAlgMeta, sigAlg.isAcceptableOrUnknown(data['sig_alg']!, _sigAlgMeta));
    } else if (isInserting) {
      context.missing(_sigAlgMeta);
    }
    if (data.containsKey('event_at')) {
      context.handle(_eventAtMeta, eventAt.isAcceptableOrUnknown(data['event_at']!, _eventAtMeta));
    } else if (isInserting) {
      context.missing(_eventAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {deviceId, seq},
  ];
  @override
  AuditEventRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return AuditEventRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      deviceId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}device_id'])!,
      seq: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}seq'])!,
      prevHash: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}prev_hash'])!,
      eventHash: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}event_hash'])!,
      actorId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}actor_id'])!,
      eventType: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}event_type'])!,
      entityId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}entity_id']),
      payloadHash: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}payload_hash'])!,
      deviceSig: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}device_sig'])!,
      sigAlg: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}sig_alg'])!,
      eventAt: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}event_at'])!,
    );
  }

  @override
  $AuditEventsTable createAlias(String alias) {
    return $AuditEventsTable(attachedDatabase, alias);
  }
}

class AuditEventRow extends DataClass implements Insertable<AuditEventRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final String deviceId;
  final int seq;
  final String prevHash;
  final String eventHash;
  final String actorId;
  final String eventType;
  final String? entityId;
  final String payloadHash;
  final String deviceSig;
  final String sigAlg;

  /// Zanjirdagi kanonik vaqt (`2026-10-26T07:05:03.120Z`) — hash shu satrdan hisoblanadi.
  final String eventAt;
  const AuditEventRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.deviceId,
    required this.seq,
    required this.prevHash,
    required this.eventHash,
    required this.actorId,
    required this.eventType,
    this.entityId,
    required this.payloadHash,
    required this.deviceSig,
    required this.sigAlg,
    required this.eventAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['device_id'] = Variable<String>(deviceId);
    map['seq'] = Variable<int>(seq);
    map['prev_hash'] = Variable<String>(prevHash);
    map['event_hash'] = Variable<String>(eventHash);
    map['actor_id'] = Variable<String>(actorId);
    map['event_type'] = Variable<String>(eventType);
    if (!nullToAbsent || entityId != null) {
      map['entity_id'] = Variable<String>(entityId);
    }
    map['payload_hash'] = Variable<String>(payloadHash);
    map['device_sig'] = Variable<String>(deviceSig);
    map['sig_alg'] = Variable<String>(sigAlg);
    map['event_at'] = Variable<String>(eventAt);
    return map;
  }

  AuditEventsCompanion toCompanion(bool nullToAbsent) {
    return AuditEventsCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      deviceId: Value(deviceId),
      seq: Value(seq),
      prevHash: Value(prevHash),
      eventHash: Value(eventHash),
      actorId: Value(actorId),
      eventType: Value(eventType),
      entityId: entityId == null && nullToAbsent ? const Value.absent() : Value(entityId),
      payloadHash: Value(payloadHash),
      deviceSig: Value(deviceSig),
      sigAlg: Value(sigAlg),
      eventAt: Value(eventAt),
    );
  }

  factory AuditEventRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return AuditEventRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      deviceId: serializer.fromJson<String>(json['deviceId']),
      seq: serializer.fromJson<int>(json['seq']),
      prevHash: serializer.fromJson<String>(json['prevHash']),
      eventHash: serializer.fromJson<String>(json['eventHash']),
      actorId: serializer.fromJson<String>(json['actorId']),
      eventType: serializer.fromJson<String>(json['eventType']),
      entityId: serializer.fromJson<String?>(json['entityId']),
      payloadHash: serializer.fromJson<String>(json['payloadHash']),
      deviceSig: serializer.fromJson<String>(json['deviceSig']),
      sigAlg: serializer.fromJson<String>(json['sigAlg']),
      eventAt: serializer.fromJson<String>(json['eventAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'deviceId': serializer.toJson<String>(deviceId),
      'seq': serializer.toJson<int>(seq),
      'prevHash': serializer.toJson<String>(prevHash),
      'eventHash': serializer.toJson<String>(eventHash),
      'actorId': serializer.toJson<String>(actorId),
      'eventType': serializer.toJson<String>(eventType),
      'entityId': serializer.toJson<String?>(entityId),
      'payloadHash': serializer.toJson<String>(payloadHash),
      'deviceSig': serializer.toJson<String>(deviceSig),
      'sigAlg': serializer.toJson<String>(sigAlg),
      'eventAt': serializer.toJson<String>(eventAt),
    };
  }

  AuditEventRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    String? deviceId,
    int? seq,
    String? prevHash,
    String? eventHash,
    String? actorId,
    String? eventType,
    Value<String?> entityId = const Value.absent(),
    String? payloadHash,
    String? deviceSig,
    String? sigAlg,
    String? eventAt,
  }) => AuditEventRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    deviceId: deviceId ?? this.deviceId,
    seq: seq ?? this.seq,
    prevHash: prevHash ?? this.prevHash,
    eventHash: eventHash ?? this.eventHash,
    actorId: actorId ?? this.actorId,
    eventType: eventType ?? this.eventType,
    entityId: entityId.present ? entityId.value : this.entityId,
    payloadHash: payloadHash ?? this.payloadHash,
    deviceSig: deviceSig ?? this.deviceSig,
    sigAlg: sigAlg ?? this.sigAlg,
    eventAt: eventAt ?? this.eventAt,
  );
  AuditEventRow copyWithCompanion(AuditEventsCompanion data) {
    return AuditEventRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      deviceId: data.deviceId.present ? data.deviceId.value : this.deviceId,
      seq: data.seq.present ? data.seq.value : this.seq,
      prevHash: data.prevHash.present ? data.prevHash.value : this.prevHash,
      eventHash: data.eventHash.present ? data.eventHash.value : this.eventHash,
      actorId: data.actorId.present ? data.actorId.value : this.actorId,
      eventType: data.eventType.present ? data.eventType.value : this.eventType,
      entityId: data.entityId.present ? data.entityId.value : this.entityId,
      payloadHash: data.payloadHash.present ? data.payloadHash.value : this.payloadHash,
      deviceSig: data.deviceSig.present ? data.deviceSig.value : this.deviceSig,
      sigAlg: data.sigAlg.present ? data.sigAlg.value : this.sigAlg,
      eventAt: data.eventAt.present ? data.eventAt.value : this.eventAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('AuditEventRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deviceId: $deviceId, ')
          ..write('seq: $seq, ')
          ..write('prevHash: $prevHash, ')
          ..write('eventHash: $eventHash, ')
          ..write('actorId: $actorId, ')
          ..write('eventType: $eventType, ')
          ..write('entityId: $entityId, ')
          ..write('payloadHash: $payloadHash, ')
          ..write('deviceSig: $deviceSig, ')
          ..write('sigAlg: $sigAlg, ')
          ..write('eventAt: $eventAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deviceId,
    seq,
    prevHash,
    eventHash,
    actorId,
    eventType,
    entityId,
    payloadHash,
    deviceSig,
    sigAlg,
    eventAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is AuditEventRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.deviceId == this.deviceId &&
          other.seq == this.seq &&
          other.prevHash == this.prevHash &&
          other.eventHash == this.eventHash &&
          other.actorId == this.actorId &&
          other.eventType == this.eventType &&
          other.entityId == this.entityId &&
          other.payloadHash == this.payloadHash &&
          other.deviceSig == this.deviceSig &&
          other.sigAlg == this.sigAlg &&
          other.eventAt == this.eventAt);
}

class AuditEventsCompanion extends UpdateCompanion<AuditEventRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<String> deviceId;
  final Value<int> seq;
  final Value<String> prevHash;
  final Value<String> eventHash;
  final Value<String> actorId;
  final Value<String> eventType;
  final Value<String?> entityId;
  final Value<String> payloadHash;
  final Value<String> deviceSig;
  final Value<String> sigAlg;
  final Value<String> eventAt;
  final Value<int> rowid;
  const AuditEventsCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.deviceId = const Value.absent(),
    this.seq = const Value.absent(),
    this.prevHash = const Value.absent(),
    this.eventHash = const Value.absent(),
    this.actorId = const Value.absent(),
    this.eventType = const Value.absent(),
    this.entityId = const Value.absent(),
    this.payloadHash = const Value.absent(),
    this.deviceSig = const Value.absent(),
    this.sigAlg = const Value.absent(),
    this.eventAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  AuditEventsCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    required String deviceId,
    required int seq,
    required String prevHash,
    required String eventHash,
    required String actorId,
    required String eventType,
    this.entityId = const Value.absent(),
    required String payloadHash,
    required String deviceSig,
    required String sigAlg,
    required String eventAt,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       deviceId = Value(deviceId),
       seq = Value(seq),
       prevHash = Value(prevHash),
       eventHash = Value(eventHash),
       actorId = Value(actorId),
       eventType = Value(eventType),
       payloadHash = Value(payloadHash),
       deviceSig = Value(deviceSig),
       sigAlg = Value(sigAlg),
       eventAt = Value(eventAt);
  static Insertable<AuditEventRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<String>? deviceId,
    Expression<int>? seq,
    Expression<String>? prevHash,
    Expression<String>? eventHash,
    Expression<String>? actorId,
    Expression<String>? eventType,
    Expression<String>? entityId,
    Expression<String>? payloadHash,
    Expression<String>? deviceSig,
    Expression<String>? sigAlg,
    Expression<String>? eventAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (deviceId != null) 'device_id': deviceId,
      if (seq != null) 'seq': seq,
      if (prevHash != null) 'prev_hash': prevHash,
      if (eventHash != null) 'event_hash': eventHash,
      if (actorId != null) 'actor_id': actorId,
      if (eventType != null) 'event_type': eventType,
      if (entityId != null) 'entity_id': entityId,
      if (payloadHash != null) 'payload_hash': payloadHash,
      if (deviceSig != null) 'device_sig': deviceSig,
      if (sigAlg != null) 'sig_alg': sigAlg,
      if (eventAt != null) 'event_at': eventAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  AuditEventsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<String>? deviceId,
    Value<int>? seq,
    Value<String>? prevHash,
    Value<String>? eventHash,
    Value<String>? actorId,
    Value<String>? eventType,
    Value<String?>? entityId,
    Value<String>? payloadHash,
    Value<String>? deviceSig,
    Value<String>? sigAlg,
    Value<String>? eventAt,
    Value<int>? rowid,
  }) {
    return AuditEventsCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      deviceId: deviceId ?? this.deviceId,
      seq: seq ?? this.seq,
      prevHash: prevHash ?? this.prevHash,
      eventHash: eventHash ?? this.eventHash,
      actorId: actorId ?? this.actorId,
      eventType: eventType ?? this.eventType,
      entityId: entityId ?? this.entityId,
      payloadHash: payloadHash ?? this.payloadHash,
      deviceSig: deviceSig ?? this.deviceSig,
      sigAlg: sigAlg ?? this.sigAlg,
      eventAt: eventAt ?? this.eventAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (deviceId.present) {
      map['device_id'] = Variable<String>(deviceId.value);
    }
    if (seq.present) {
      map['seq'] = Variable<int>(seq.value);
    }
    if (prevHash.present) {
      map['prev_hash'] = Variable<String>(prevHash.value);
    }
    if (eventHash.present) {
      map['event_hash'] = Variable<String>(eventHash.value);
    }
    if (actorId.present) {
      map['actor_id'] = Variable<String>(actorId.value);
    }
    if (eventType.present) {
      map['event_type'] = Variable<String>(eventType.value);
    }
    if (entityId.present) {
      map['entity_id'] = Variable<String>(entityId.value);
    }
    if (payloadHash.present) {
      map['payload_hash'] = Variable<String>(payloadHash.value);
    }
    if (deviceSig.present) {
      map['device_sig'] = Variable<String>(deviceSig.value);
    }
    if (sigAlg.present) {
      map['sig_alg'] = Variable<String>(sigAlg.value);
    }
    if (eventAt.present) {
      map['event_at'] = Variable<String>(eventAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('AuditEventsCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deviceId: $deviceId, ')
          ..write('seq: $seq, ')
          ..write('prevHash: $prevHash, ')
          ..write('eventHash: $eventHash, ')
          ..write('actorId: $actorId, ')
          ..write('eventType: $eventType, ')
          ..write('entityId: $entityId, ')
          ..write('payloadHash: $payloadHash, ')
          ..write('deviceSig: $deviceSig, ')
          ..write('sigAlg: $sigAlg, ')
          ..write('eventAt: $eventAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $EdgesTable extends Edges with TableInfo<$EdgesTable, EdgeRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $EdgesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _deletedMeta = const VerificationMeta('deleted');
  @override
  late final GeneratedColumn<bool> deleted = GeneratedColumn<bool>(
    'deleted',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("deleted" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _siteIdMeta = const VerificationMeta('siteId');
  @override
  late final GeneratedColumn<String> siteId = GeneratedColumn<String>(
    'site_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES site (id)'),
  );
  static const VerificationMeta _aNodeIdMeta = const VerificationMeta('aNodeId');
  @override
  late final GeneratedColumn<String> aNodeId = GeneratedColumn<String>(
    'a_node_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES node (id)'),
  );
  static const VerificationMeta _bNodeIdMeta = const VerificationMeta('bNodeId');
  @override
  late final GeneratedColumn<String> bNodeId = GeneratedColumn<String>(
    'b_node_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES node (id)'),
  );
  static const VerificationMeta _conductorsMeta = const VerificationMeta('conductors');
  @override
  late final GeneratedColumn<String> conductors = GeneratedColumn<String>(
    'conductors',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    siteId,
    aNodeId,
    bNodeId,
    conductors,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'edge';
  @override
  VerificationContext validateIntegrity(Insertable<EdgeRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('deleted')) {
      context.handle(_deletedMeta, deleted.isAcceptableOrUnknown(data['deleted']!, _deletedMeta));
    }
    if (data.containsKey('site_id')) {
      context.handle(_siteIdMeta, siteId.isAcceptableOrUnknown(data['site_id']!, _siteIdMeta));
    } else if (isInserting) {
      context.missing(_siteIdMeta);
    }
    if (data.containsKey('a_node_id')) {
      context.handle(_aNodeIdMeta, aNodeId.isAcceptableOrUnknown(data['a_node_id']!, _aNodeIdMeta));
    } else if (isInserting) {
      context.missing(_aNodeIdMeta);
    }
    if (data.containsKey('b_node_id')) {
      context.handle(_bNodeIdMeta, bNodeId.isAcceptableOrUnknown(data['b_node_id']!, _bNodeIdMeta));
    } else if (isInserting) {
      context.missing(_bNodeIdMeta);
    }
    if (data.containsKey('conductors')) {
      context.handle(_conductorsMeta, conductors.isAcceptableOrUnknown(data['conductors']!, _conductorsMeta));
    } else if (isInserting) {
      context.missing(_conductorsMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  EdgeRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return EdgeRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      deleted: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}deleted'])!,
      siteId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}site_id'])!,
      aNodeId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}a_node_id'])!,
      bNodeId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}b_node_id'])!,
      conductors: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}conductors'])!,
    );
  }

  @override
  $EdgesTable createAlias(String alias) {
    return $EdgesTable(attachedDatabase, alias);
  }
}

class EdgeRow extends DataClass implements Insertable<EdgeRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final bool deleted;
  final String siteId;
  final String aNodeId;
  final String bNodeId;
  final String conductors;
  const EdgeRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.deleted,
    required this.siteId,
    required this.aNodeId,
    required this.bNodeId,
    required this.conductors,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['deleted'] = Variable<bool>(deleted);
    map['site_id'] = Variable<String>(siteId);
    map['a_node_id'] = Variable<String>(aNodeId);
    map['b_node_id'] = Variable<String>(bNodeId);
    map['conductors'] = Variable<String>(conductors);
    return map;
  }

  EdgesCompanion toCompanion(bool nullToAbsent) {
    return EdgesCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      deleted: Value(deleted),
      siteId: Value(siteId),
      aNodeId: Value(aNodeId),
      bNodeId: Value(bNodeId),
      conductors: Value(conductors),
    );
  }

  factory EdgeRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return EdgeRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      deleted: serializer.fromJson<bool>(json['deleted']),
      siteId: serializer.fromJson<String>(json['siteId']),
      aNodeId: serializer.fromJson<String>(json['aNodeId']),
      bNodeId: serializer.fromJson<String>(json['bNodeId']),
      conductors: serializer.fromJson<String>(json['conductors']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'deleted': serializer.toJson<bool>(deleted),
      'siteId': serializer.toJson<String>(siteId),
      'aNodeId': serializer.toJson<String>(aNodeId),
      'bNodeId': serializer.toJson<String>(bNodeId),
      'conductors': serializer.toJson<String>(conductors),
    };
  }

  EdgeRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    bool? deleted,
    String? siteId,
    String? aNodeId,
    String? bNodeId,
    String? conductors,
  }) => EdgeRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    deleted: deleted ?? this.deleted,
    siteId: siteId ?? this.siteId,
    aNodeId: aNodeId ?? this.aNodeId,
    bNodeId: bNodeId ?? this.bNodeId,
    conductors: conductors ?? this.conductors,
  );
  EdgeRow copyWithCompanion(EdgesCompanion data) {
    return EdgeRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      deleted: data.deleted.present ? data.deleted.value : this.deleted,
      siteId: data.siteId.present ? data.siteId.value : this.siteId,
      aNodeId: data.aNodeId.present ? data.aNodeId.value : this.aNodeId,
      bNodeId: data.bNodeId.present ? data.bNodeId.value : this.bNodeId,
      conductors: data.conductors.present ? data.conductors.value : this.conductors,
    );
  }

  @override
  String toString() {
    return (StringBuffer('EdgeRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('siteId: $siteId, ')
          ..write('aNodeId: $aNodeId, ')
          ..write('bNodeId: $bNodeId, ')
          ..write('conductors: $conductors')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, createdAt, updatedAt, rev, orgId, deleted, siteId, aNodeId, bNodeId, conductors);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is EdgeRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.deleted == this.deleted &&
          other.siteId == this.siteId &&
          other.aNodeId == this.aNodeId &&
          other.bNodeId == this.bNodeId &&
          other.conductors == this.conductors);
}

class EdgesCompanion extends UpdateCompanion<EdgeRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<bool> deleted;
  final Value<String> siteId;
  final Value<String> aNodeId;
  final Value<String> bNodeId;
  final Value<String> conductors;
  final Value<int> rowid;
  const EdgesCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.deleted = const Value.absent(),
    this.siteId = const Value.absent(),
    this.aNodeId = const Value.absent(),
    this.bNodeId = const Value.absent(),
    this.conductors = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  EdgesCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    this.deleted = const Value.absent(),
    required String siteId,
    required String aNodeId,
    required String bNodeId,
    required String conductors,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       siteId = Value(siteId),
       aNodeId = Value(aNodeId),
       bNodeId = Value(bNodeId),
       conductors = Value(conductors);
  static Insertable<EdgeRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<bool>? deleted,
    Expression<String>? siteId,
    Expression<String>? aNodeId,
    Expression<String>? bNodeId,
    Expression<String>? conductors,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (deleted != null) 'deleted': deleted,
      if (siteId != null) 'site_id': siteId,
      if (aNodeId != null) 'a_node_id': aNodeId,
      if (bNodeId != null) 'b_node_id': bNodeId,
      if (conductors != null) 'conductors': conductors,
      if (rowid != null) 'rowid': rowid,
    });
  }

  EdgesCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<bool>? deleted,
    Value<String>? siteId,
    Value<String>? aNodeId,
    Value<String>? bNodeId,
    Value<String>? conductors,
    Value<int>? rowid,
  }) {
    return EdgesCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      deleted: deleted ?? this.deleted,
      siteId: siteId ?? this.siteId,
      aNodeId: aNodeId ?? this.aNodeId,
      bNodeId: bNodeId ?? this.bNodeId,
      conductors: conductors ?? this.conductors,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (deleted.present) {
      map['deleted'] = Variable<bool>(deleted.value);
    }
    if (siteId.present) {
      map['site_id'] = Variable<String>(siteId.value);
    }
    if (aNodeId.present) {
      map['a_node_id'] = Variable<String>(aNodeId.value);
    }
    if (bNodeId.present) {
      map['b_node_id'] = Variable<String>(bNodeId.value);
    }
    if (conductors.present) {
      map['conductors'] = Variable<String>(conductors.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('EdgesCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('siteId: $siteId, ')
          ..write('aNodeId: $aNodeId, ')
          ..write('bNodeId: $bNodeId, ')
          ..write('conductors: $conductors, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $LocalPrefsTable extends LocalPrefs with TableInfo<$LocalPrefsTable, LocalPrefRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LocalPrefsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _keyMeta = const VerificationMeta('key');
  @override
  late final GeneratedColumn<String> key = GeneratedColumn<String>(
    'key',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _valueMeta = const VerificationMeta('value');
  @override
  late final GeneratedColumn<String> value = GeneratedColumn<String>(
    'value',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [key, value];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'local_pref';
  @override
  VerificationContext validateIntegrity(Insertable<LocalPrefRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('key')) {
      context.handle(_keyMeta, key.isAcceptableOrUnknown(data['key']!, _keyMeta));
    } else if (isInserting) {
      context.missing(_keyMeta);
    }
    if (data.containsKey('value')) {
      context.handle(_valueMeta, value.isAcceptableOrUnknown(data['value']!, _valueMeta));
    } else if (isInserting) {
      context.missing(_valueMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {key};
  @override
  LocalPrefRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LocalPrefRow(
      key: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}key'])!,
      value: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}value'])!,
    );
  }

  @override
  $LocalPrefsTable createAlias(String alias) {
    return $LocalPrefsTable(attachedDatabase, alias);
  }
}

class LocalPrefRow extends DataClass implements Insertable<LocalPrefRow> {
  final String key;
  final String value;
  const LocalPrefRow({required this.key, required this.value});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['key'] = Variable<String>(key);
    map['value'] = Variable<String>(value);
    return map;
  }

  LocalPrefsCompanion toCompanion(bool nullToAbsent) {
    return LocalPrefsCompanion(key: Value(key), value: Value(value));
  }

  factory LocalPrefRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LocalPrefRow(
      key: serializer.fromJson<String>(json['key']),
      value: serializer.fromJson<String>(json['value']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{'key': serializer.toJson<String>(key), 'value': serializer.toJson<String>(value)};
  }

  LocalPrefRow copyWith({String? key, String? value}) => LocalPrefRow(key: key ?? this.key, value: value ?? this.value);
  LocalPrefRow copyWithCompanion(LocalPrefsCompanion data) {
    return LocalPrefRow(
      key: data.key.present ? data.key.value : this.key,
      value: data.value.present ? data.value.value : this.value,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LocalPrefRow(')
          ..write('key: $key, ')
          ..write('value: $value')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(key, value);
  @override
  bool operator ==(Object other) =>
      identical(this, other) || (other is LocalPrefRow && other.key == this.key && other.value == this.value);
}

class LocalPrefsCompanion extends UpdateCompanion<LocalPrefRow> {
  final Value<String> key;
  final Value<String> value;
  final Value<int> rowid;
  const LocalPrefsCompanion({
    this.key = const Value.absent(),
    this.value = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  LocalPrefsCompanion.insert({required String key, required String value, this.rowid = const Value.absent()})
    : key = Value(key),
      value = Value(value);
  static Insertable<LocalPrefRow> custom({Expression<String>? key, Expression<String>? value, Expression<int>? rowid}) {
    return RawValuesInsertable({
      if (key != null) 'key': key,
      if (value != null) 'value': value,
      if (rowid != null) 'rowid': rowid,
    });
  }

  LocalPrefsCompanion copyWith({Value<String>? key, Value<String>? value, Value<int>? rowid}) {
    return LocalPrefsCompanion(key: key ?? this.key, value: value ?? this.value, rowid: rowid ?? this.rowid);
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (key.present) {
      map['key'] = Variable<String>(key.value);
    }
    if (value.present) {
      map['value'] = Variable<String>(value.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LocalPrefsCompanion(')
          ..write('key: $key, ')
          ..write('value: $value, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $SyncOutboxTable extends SyncOutbox with TableInfo<$SyncOutboxTable, SyncOutboxRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SyncOutboxTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'),
  );
  static const VerificationMeta _tableName_Meta = const VerificationMeta('tableName_');
  @override
  late final GeneratedColumn<String> tableName_ = GeneratedColumn<String>(
    'table_name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _rowIdMeta = const VerificationMeta('rowId');
  @override
  late final GeneratedColumn<String> rowId = GeneratedColumn<String>(
    'row_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _opIdMeta = const VerificationMeta('opId');
  @override
  late final GeneratedColumn<String> opId = GeneratedColumn<String>(
    'op_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [id, tableName_, rowId, opId];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'sync_outbox';
  @override
  VerificationContext validateIntegrity(Insertable<SyncOutboxRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('table_name')) {
      context.handle(_tableName_Meta, tableName_.isAcceptableOrUnknown(data['table_name']!, _tableName_Meta));
    } else if (isInserting) {
      context.missing(_tableName_Meta);
    }
    if (data.containsKey('row_id')) {
      context.handle(_rowIdMeta, rowId.isAcceptableOrUnknown(data['row_id']!, _rowIdMeta));
    } else if (isInserting) {
      context.missing(_rowIdMeta);
    }
    if (data.containsKey('op_id')) {
      context.handle(_opIdMeta, opId.isAcceptableOrUnknown(data['op_id']!, _opIdMeta));
    } else if (isInserting) {
      context.missing(_opIdMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {tableName_, rowId},
  ];
  @override
  SyncOutboxRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SyncOutboxRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      tableName_: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}table_name'])!,
      rowId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}row_id'])!,
      opId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}op_id'])!,
    );
  }

  @override
  $SyncOutboxTable createAlias(String alias) {
    return $SyncOutboxTable(attachedDatabase, alias);
  }
}

class SyncOutboxRow extends DataClass implements Insertable<SyncOutboxRow> {
  final int id;
  final String tableName_;
  final String rowId;
  final String opId;
  const SyncOutboxRow({required this.id, required this.tableName_, required this.rowId, required this.opId});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['table_name'] = Variable<String>(tableName_);
    map['row_id'] = Variable<String>(rowId);
    map['op_id'] = Variable<String>(opId);
    return map;
  }

  SyncOutboxCompanion toCompanion(bool nullToAbsent) {
    return SyncOutboxCompanion(id: Value(id), tableName_: Value(tableName_), rowId: Value(rowId), opId: Value(opId));
  }

  factory SyncOutboxRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SyncOutboxRow(
      id: serializer.fromJson<int>(json['id']),
      tableName_: serializer.fromJson<String>(json['tableName_']),
      rowId: serializer.fromJson<String>(json['rowId']),
      opId: serializer.fromJson<String>(json['opId']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'tableName_': serializer.toJson<String>(tableName_),
      'rowId': serializer.toJson<String>(rowId),
      'opId': serializer.toJson<String>(opId),
    };
  }

  SyncOutboxRow copyWith({int? id, String? tableName_, String? rowId, String? opId}) => SyncOutboxRow(
    id: id ?? this.id,
    tableName_: tableName_ ?? this.tableName_,
    rowId: rowId ?? this.rowId,
    opId: opId ?? this.opId,
  );
  SyncOutboxRow copyWithCompanion(SyncOutboxCompanion data) {
    return SyncOutboxRow(
      id: data.id.present ? data.id.value : this.id,
      tableName_: data.tableName_.present ? data.tableName_.value : this.tableName_,
      rowId: data.rowId.present ? data.rowId.value : this.rowId,
      opId: data.opId.present ? data.opId.value : this.opId,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SyncOutboxRow(')
          ..write('id: $id, ')
          ..write('tableName_: $tableName_, ')
          ..write('rowId: $rowId, ')
          ..write('opId: $opId')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, tableName_, rowId, opId);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SyncOutboxRow &&
          other.id == this.id &&
          other.tableName_ == this.tableName_ &&
          other.rowId == this.rowId &&
          other.opId == this.opId);
}

class SyncOutboxCompanion extends UpdateCompanion<SyncOutboxRow> {
  final Value<int> id;
  final Value<String> tableName_;
  final Value<String> rowId;
  final Value<String> opId;
  const SyncOutboxCompanion({
    this.id = const Value.absent(),
    this.tableName_ = const Value.absent(),
    this.rowId = const Value.absent(),
    this.opId = const Value.absent(),
  });
  SyncOutboxCompanion.insert({
    this.id = const Value.absent(),
    required String tableName_,
    required String rowId,
    required String opId,
  }) : tableName_ = Value(tableName_),
       rowId = Value(rowId),
       opId = Value(opId);
  static Insertable<SyncOutboxRow> custom({
    Expression<int>? id,
    Expression<String>? tableName_,
    Expression<String>? rowId,
    Expression<String>? opId,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (tableName_ != null) 'table_name': tableName_,
      if (rowId != null) 'row_id': rowId,
      if (opId != null) 'op_id': opId,
    });
  }

  SyncOutboxCompanion copyWith({Value<int>? id, Value<String>? tableName_, Value<String>? rowId, Value<String>? opId}) {
    return SyncOutboxCompanion(
      id: id ?? this.id,
      tableName_: tableName_ ?? this.tableName_,
      rowId: rowId ?? this.rowId,
      opId: opId ?? this.opId,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (tableName_.present) {
      map['table_name'] = Variable<String>(tableName_.value);
    }
    if (rowId.present) {
      map['row_id'] = Variable<String>(rowId.value);
    }
    if (opId.present) {
      map['op_id'] = Variable<String>(opId.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SyncOutboxCompanion(')
          ..write('id: $id, ')
          ..write('tableName_: $tableName_, ')
          ..write('rowId: $rowId, ')
          ..write('opId: $opId')
          ..write(')'))
        .toString();
  }
}

class $IsolationPlansTable extends IsolationPlans with TableInfo<$IsolationPlansTable, IsolationPlanRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $IsolationPlansTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _deletedMeta = const VerificationMeta('deleted');
  @override
  late final GeneratedColumn<bool> deleted = GeneratedColumn<bool>(
    'deleted',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("deleted" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _siteIdMeta = const VerificationMeta('siteId');
  @override
  late final GeneratedColumn<String> siteId = GeneratedColumn<String>(
    'site_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES site (id)'),
  );
  @override
  late final GeneratedColumnWithTypeConverter<List<Object?>, String> targetNodeIds = GeneratedColumn<String>(
    'target_node_ids',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  ).withConverter<List<Object?>>($IsolationPlansTable.$convertertargetNodeIds);
  static const VerificationMeta _solverVersionMeta = const VerificationMeta('solverVersion');
  @override
  late final GeneratedColumn<String> solverVersion = GeneratedColumn<String>(
    'solver_version',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _graphSnapshotHashMeta = const VerificationMeta('graphSnapshotHash');
  @override
  late final GeneratedColumn<String> graphSnapshotHash = GeneratedColumn<String>(
    'graph_snapshot_hash',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  late final GeneratedColumnWithTypeConverter<List<Object?>, String> steps = GeneratedColumn<String>(
    'steps',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  ).withConverter<List<Object?>>($IsolationPlansTable.$convertersteps);
  @override
  late final GeneratedColumnWithTypeConverter<List<Object?>, String> warnings = GeneratedColumn<String>(
    'warnings',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  ).withConverter<List<Object?>>($IsolationPlansTable.$converterwarnings);
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
    'status',
    aliasedName,
    false,
    check: () => status.isIn(const ['DRAFT', 'APPROVED', 'EXECUTED', 'CANCELLED', 'STALE']),
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _approvedByMeta = const VerificationMeta('approvedBy');
  @override
  late final GeneratedColumn<String> approvedBy = GeneratedColumn<String>(
    'approved_by',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES app_user (id)'),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    siteId,
    targetNodeIds,
    solverVersion,
    graphSnapshotHash,
    steps,
    warnings,
    status,
    approvedBy,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'isolation_plan';
  @override
  VerificationContext validateIntegrity(Insertable<IsolationPlanRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('deleted')) {
      context.handle(_deletedMeta, deleted.isAcceptableOrUnknown(data['deleted']!, _deletedMeta));
    }
    if (data.containsKey('site_id')) {
      context.handle(_siteIdMeta, siteId.isAcceptableOrUnknown(data['site_id']!, _siteIdMeta));
    } else if (isInserting) {
      context.missing(_siteIdMeta);
    }
    if (data.containsKey('solver_version')) {
      context.handle(
        _solverVersionMeta,
        solverVersion.isAcceptableOrUnknown(data['solver_version']!, _solverVersionMeta),
      );
    } else if (isInserting) {
      context.missing(_solverVersionMeta);
    }
    if (data.containsKey('graph_snapshot_hash')) {
      context.handle(
        _graphSnapshotHashMeta,
        graphSnapshotHash.isAcceptableOrUnknown(data['graph_snapshot_hash']!, _graphSnapshotHashMeta),
      );
    } else if (isInserting) {
      context.missing(_graphSnapshotHashMeta);
    }
    if (data.containsKey('status')) {
      context.handle(_statusMeta, status.isAcceptableOrUnknown(data['status']!, _statusMeta));
    } else if (isInserting) {
      context.missing(_statusMeta);
    }
    if (data.containsKey('approved_by')) {
      context.handle(_approvedByMeta, approvedBy.isAcceptableOrUnknown(data['approved_by']!, _approvedByMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  IsolationPlanRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return IsolationPlanRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      deleted: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}deleted'])!,
      siteId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}site_id'])!,
      targetNodeIds: $IsolationPlansTable.$convertertargetNodeIds.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}target_node_ids'])!,
      ),
      solverVersion: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}solver_version'])!,
      graphSnapshotHash: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}graph_snapshot_hash'],
      )!,
      steps: $IsolationPlansTable.$convertersteps.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}steps'])!,
      ),
      warnings: $IsolationPlansTable.$converterwarnings.fromSql(
        attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}warnings'])!,
      ),
      status: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}status'])!,
      approvedBy: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}approved_by']),
    );
  }

  @override
  $IsolationPlansTable createAlias(String alias) {
    return $IsolationPlansTable(attachedDatabase, alias);
  }

  static TypeConverter<List<Object?>, String> $convertertargetNodeIds = const JsonListConverter();
  static TypeConverter<List<Object?>, String> $convertersteps = const JsonListConverter();
  static TypeConverter<List<Object?>, String> $converterwarnings = const JsonListConverter();
}

class IsolationPlanRow extends DataClass implements Insertable<IsolationPlanRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final bool deleted;
  final String siteId;
  final List<Object?> targetNodeIds;
  final String solverVersion;
  final String graphSnapshotHash;
  final List<Object?> steps;
  final List<Object?> warnings;
  final String status;
  final String? approvedBy;
  const IsolationPlanRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.deleted,
    required this.siteId,
    required this.targetNodeIds,
    required this.solverVersion,
    required this.graphSnapshotHash,
    required this.steps,
    required this.warnings,
    required this.status,
    this.approvedBy,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['deleted'] = Variable<bool>(deleted);
    map['site_id'] = Variable<String>(siteId);
    {
      map['target_node_ids'] = Variable<String>($IsolationPlansTable.$convertertargetNodeIds.toSql(targetNodeIds));
    }
    map['solver_version'] = Variable<String>(solverVersion);
    map['graph_snapshot_hash'] = Variable<String>(graphSnapshotHash);
    {
      map['steps'] = Variable<String>($IsolationPlansTable.$convertersteps.toSql(steps));
    }
    {
      map['warnings'] = Variable<String>($IsolationPlansTable.$converterwarnings.toSql(warnings));
    }
    map['status'] = Variable<String>(status);
    if (!nullToAbsent || approvedBy != null) {
      map['approved_by'] = Variable<String>(approvedBy);
    }
    return map;
  }

  IsolationPlansCompanion toCompanion(bool nullToAbsent) {
    return IsolationPlansCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      deleted: Value(deleted),
      siteId: Value(siteId),
      targetNodeIds: Value(targetNodeIds),
      solverVersion: Value(solverVersion),
      graphSnapshotHash: Value(graphSnapshotHash),
      steps: Value(steps),
      warnings: Value(warnings),
      status: Value(status),
      approvedBy: approvedBy == null && nullToAbsent ? const Value.absent() : Value(approvedBy),
    );
  }

  factory IsolationPlanRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return IsolationPlanRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      deleted: serializer.fromJson<bool>(json['deleted']),
      siteId: serializer.fromJson<String>(json['siteId']),
      targetNodeIds: serializer.fromJson<List<Object?>>(json['targetNodeIds']),
      solverVersion: serializer.fromJson<String>(json['solverVersion']),
      graphSnapshotHash: serializer.fromJson<String>(json['graphSnapshotHash']),
      steps: serializer.fromJson<List<Object?>>(json['steps']),
      warnings: serializer.fromJson<List<Object?>>(json['warnings']),
      status: serializer.fromJson<String>(json['status']),
      approvedBy: serializer.fromJson<String?>(json['approvedBy']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'deleted': serializer.toJson<bool>(deleted),
      'siteId': serializer.toJson<String>(siteId),
      'targetNodeIds': serializer.toJson<List<Object?>>(targetNodeIds),
      'solverVersion': serializer.toJson<String>(solverVersion),
      'graphSnapshotHash': serializer.toJson<String>(graphSnapshotHash),
      'steps': serializer.toJson<List<Object?>>(steps),
      'warnings': serializer.toJson<List<Object?>>(warnings),
      'status': serializer.toJson<String>(status),
      'approvedBy': serializer.toJson<String?>(approvedBy),
    };
  }

  IsolationPlanRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    bool? deleted,
    String? siteId,
    List<Object?>? targetNodeIds,
    String? solverVersion,
    String? graphSnapshotHash,
    List<Object?>? steps,
    List<Object?>? warnings,
    String? status,
    Value<String?> approvedBy = const Value.absent(),
  }) => IsolationPlanRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    deleted: deleted ?? this.deleted,
    siteId: siteId ?? this.siteId,
    targetNodeIds: targetNodeIds ?? this.targetNodeIds,
    solverVersion: solverVersion ?? this.solverVersion,
    graphSnapshotHash: graphSnapshotHash ?? this.graphSnapshotHash,
    steps: steps ?? this.steps,
    warnings: warnings ?? this.warnings,
    status: status ?? this.status,
    approvedBy: approvedBy.present ? approvedBy.value : this.approvedBy,
  );
  IsolationPlanRow copyWithCompanion(IsolationPlansCompanion data) {
    return IsolationPlanRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      deleted: data.deleted.present ? data.deleted.value : this.deleted,
      siteId: data.siteId.present ? data.siteId.value : this.siteId,
      targetNodeIds: data.targetNodeIds.present ? data.targetNodeIds.value : this.targetNodeIds,
      solverVersion: data.solverVersion.present ? data.solverVersion.value : this.solverVersion,
      graphSnapshotHash: data.graphSnapshotHash.present ? data.graphSnapshotHash.value : this.graphSnapshotHash,
      steps: data.steps.present ? data.steps.value : this.steps,
      warnings: data.warnings.present ? data.warnings.value : this.warnings,
      status: data.status.present ? data.status.value : this.status,
      approvedBy: data.approvedBy.present ? data.approvedBy.value : this.approvedBy,
    );
  }

  @override
  String toString() {
    return (StringBuffer('IsolationPlanRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('siteId: $siteId, ')
          ..write('targetNodeIds: $targetNodeIds, ')
          ..write('solverVersion: $solverVersion, ')
          ..write('graphSnapshotHash: $graphSnapshotHash, ')
          ..write('steps: $steps, ')
          ..write('warnings: $warnings, ')
          ..write('status: $status, ')
          ..write('approvedBy: $approvedBy')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    siteId,
    targetNodeIds,
    solverVersion,
    graphSnapshotHash,
    steps,
    warnings,
    status,
    approvedBy,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is IsolationPlanRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.deleted == this.deleted &&
          other.siteId == this.siteId &&
          other.targetNodeIds == this.targetNodeIds &&
          other.solverVersion == this.solverVersion &&
          other.graphSnapshotHash == this.graphSnapshotHash &&
          other.steps == this.steps &&
          other.warnings == this.warnings &&
          other.status == this.status &&
          other.approvedBy == this.approvedBy);
}

class IsolationPlansCompanion extends UpdateCompanion<IsolationPlanRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<bool> deleted;
  final Value<String> siteId;
  final Value<List<Object?>> targetNodeIds;
  final Value<String> solverVersion;
  final Value<String> graphSnapshotHash;
  final Value<List<Object?>> steps;
  final Value<List<Object?>> warnings;
  final Value<String> status;
  final Value<String?> approvedBy;
  final Value<int> rowid;
  const IsolationPlansCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.deleted = const Value.absent(),
    this.siteId = const Value.absent(),
    this.targetNodeIds = const Value.absent(),
    this.solverVersion = const Value.absent(),
    this.graphSnapshotHash = const Value.absent(),
    this.steps = const Value.absent(),
    this.warnings = const Value.absent(),
    this.status = const Value.absent(),
    this.approvedBy = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  IsolationPlansCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    this.deleted = const Value.absent(),
    required String siteId,
    required List<Object?> targetNodeIds,
    required String solverVersion,
    required String graphSnapshotHash,
    required List<Object?> steps,
    required List<Object?> warnings,
    required String status,
    this.approvedBy = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       siteId = Value(siteId),
       targetNodeIds = Value(targetNodeIds),
       solverVersion = Value(solverVersion),
       graphSnapshotHash = Value(graphSnapshotHash),
       steps = Value(steps),
       warnings = Value(warnings),
       status = Value(status);
  static Insertable<IsolationPlanRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<bool>? deleted,
    Expression<String>? siteId,
    Expression<String>? targetNodeIds,
    Expression<String>? solverVersion,
    Expression<String>? graphSnapshotHash,
    Expression<String>? steps,
    Expression<String>? warnings,
    Expression<String>? status,
    Expression<String>? approvedBy,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (deleted != null) 'deleted': deleted,
      if (siteId != null) 'site_id': siteId,
      if (targetNodeIds != null) 'target_node_ids': targetNodeIds,
      if (solverVersion != null) 'solver_version': solverVersion,
      if (graphSnapshotHash != null) 'graph_snapshot_hash': graphSnapshotHash,
      if (steps != null) 'steps': steps,
      if (warnings != null) 'warnings': warnings,
      if (status != null) 'status': status,
      if (approvedBy != null) 'approved_by': approvedBy,
      if (rowid != null) 'rowid': rowid,
    });
  }

  IsolationPlansCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<bool>? deleted,
    Value<String>? siteId,
    Value<List<Object?>>? targetNodeIds,
    Value<String>? solverVersion,
    Value<String>? graphSnapshotHash,
    Value<List<Object?>>? steps,
    Value<List<Object?>>? warnings,
    Value<String>? status,
    Value<String?>? approvedBy,
    Value<int>? rowid,
  }) {
    return IsolationPlansCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      deleted: deleted ?? this.deleted,
      siteId: siteId ?? this.siteId,
      targetNodeIds: targetNodeIds ?? this.targetNodeIds,
      solverVersion: solverVersion ?? this.solverVersion,
      graphSnapshotHash: graphSnapshotHash ?? this.graphSnapshotHash,
      steps: steps ?? this.steps,
      warnings: warnings ?? this.warnings,
      status: status ?? this.status,
      approvedBy: approvedBy ?? this.approvedBy,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (deleted.present) {
      map['deleted'] = Variable<bool>(deleted.value);
    }
    if (siteId.present) {
      map['site_id'] = Variable<String>(siteId.value);
    }
    if (targetNodeIds.present) {
      map['target_node_ids'] = Variable<String>(
        $IsolationPlansTable.$convertertargetNodeIds.toSql(targetNodeIds.value),
      );
    }
    if (solverVersion.present) {
      map['solver_version'] = Variable<String>(solverVersion.value);
    }
    if (graphSnapshotHash.present) {
      map['graph_snapshot_hash'] = Variable<String>(graphSnapshotHash.value);
    }
    if (steps.present) {
      map['steps'] = Variable<String>($IsolationPlansTable.$convertersteps.toSql(steps.value));
    }
    if (warnings.present) {
      map['warnings'] = Variable<String>($IsolationPlansTable.$converterwarnings.toSql(warnings.value));
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (approvedBy.present) {
      map['approved_by'] = Variable<String>(approvedBy.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('IsolationPlansCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('siteId: $siteId, ')
          ..write('targetNodeIds: $targetNodeIds, ')
          ..write('solverVersion: $solverVersion, ')
          ..write('graphSnapshotHash: $graphSnapshotHash, ')
          ..write('steps: $steps, ')
          ..write('warnings: $warnings, ')
          ..write('status: $status, ')
          ..write('approvedBy: $approvedBy, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $NormSetsTable extends NormSets with TableInfo<$NormSetsTable, NormSetRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $NormSetsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _deletedMeta = const VerificationMeta('deleted');
  @override
  late final GeneratedColumn<bool> deleted = GeneratedColumn<bool>(
    'deleted',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways('CHECK ("deleted" IN (0, 1))'),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _versionMeta = const VerificationMeta('version');
  @override
  late final GeneratedColumn<String> version = GeneratedColumn<String>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sha256Meta = const VerificationMeta('sha256');
  @override
  late final GeneratedColumn<String> sha256 = GeneratedColumn<String>(
    'sha256',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _yamlMeta = const VerificationMeta('yaml');
  @override
  late final GeneratedColumn<String> yaml = GeneratedColumn<String>(
    'yaml',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _reviewedByMeta = const VerificationMeta('reviewedBy');
  @override
  late final GeneratedColumn<String> reviewedBy = GeneratedColumn<String>(
    'reviewed_by',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _reviewedAtMeta = const VerificationMeta('reviewedAt');
  @override
  late final GeneratedColumn<String> reviewedAt = GeneratedColumn<String>(
    'reviewed_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    createdAt,
    updatedAt,
    rev,
    orgId,
    deleted,
    version,
    sha256,
    yaml,
    reviewedBy,
    reviewedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'norm_set';
  @override
  VerificationContext validateIntegrity(Insertable<NormSetRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('deleted')) {
      context.handle(_deletedMeta, deleted.isAcceptableOrUnknown(data['deleted']!, _deletedMeta));
    }
    if (data.containsKey('version')) {
      context.handle(_versionMeta, version.isAcceptableOrUnknown(data['version']!, _versionMeta));
    } else if (isInserting) {
      context.missing(_versionMeta);
    }
    if (data.containsKey('sha256')) {
      context.handle(_sha256Meta, sha256.isAcceptableOrUnknown(data['sha256']!, _sha256Meta));
    } else if (isInserting) {
      context.missing(_sha256Meta);
    }
    if (data.containsKey('yaml')) {
      context.handle(_yamlMeta, yaml.isAcceptableOrUnknown(data['yaml']!, _yamlMeta));
    } else if (isInserting) {
      context.missing(_yamlMeta);
    }
    if (data.containsKey('reviewed_by')) {
      context.handle(_reviewedByMeta, reviewedBy.isAcceptableOrUnknown(data['reviewed_by']!, _reviewedByMeta));
    }
    if (data.containsKey('reviewed_at')) {
      context.handle(_reviewedAtMeta, reviewedAt.isAcceptableOrUnknown(data['reviewed_at']!, _reviewedAtMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {orgId, version},
  ];
  @override
  NormSetRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return NormSetRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      deleted: attachedDatabase.typeMapping.read(DriftSqlType.bool, data['${effectivePrefix}deleted'])!,
      version: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}version'])!,
      sha256: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}sha256'])!,
      yaml: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}yaml'])!,
      reviewedBy: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}reviewed_by']),
      reviewedAt: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}reviewed_at']),
    );
  }

  @override
  $NormSetsTable createAlias(String alias) {
    return $NormSetsTable(attachedDatabase, alias);
  }
}

class NormSetRow extends DataClass implements Insertable<NormSetRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;
  final bool deleted;
  final String version;
  final String sha256;
  final String yaml;
  final String? reviewedBy;
  final String? reviewedAt;
  const NormSetRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.deleted,
    required this.version,
    required this.sha256,
    required this.yaml,
    this.reviewedBy,
    this.reviewedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['deleted'] = Variable<bool>(deleted);
    map['version'] = Variable<String>(version);
    map['sha256'] = Variable<String>(sha256);
    map['yaml'] = Variable<String>(yaml);
    if (!nullToAbsent || reviewedBy != null) {
      map['reviewed_by'] = Variable<String>(reviewedBy);
    }
    if (!nullToAbsent || reviewedAt != null) {
      map['reviewed_at'] = Variable<String>(reviewedAt);
    }
    return map;
  }

  NormSetsCompanion toCompanion(bool nullToAbsent) {
    return NormSetsCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      deleted: Value(deleted),
      version: Value(version),
      sha256: Value(sha256),
      yaml: Value(yaml),
      reviewedBy: reviewedBy == null && nullToAbsent ? const Value.absent() : Value(reviewedBy),
      reviewedAt: reviewedAt == null && nullToAbsent ? const Value.absent() : Value(reviewedAt),
    );
  }

  factory NormSetRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return NormSetRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      deleted: serializer.fromJson<bool>(json['deleted']),
      version: serializer.fromJson<String>(json['version']),
      sha256: serializer.fromJson<String>(json['sha256']),
      yaml: serializer.fromJson<String>(json['yaml']),
      reviewedBy: serializer.fromJson<String?>(json['reviewedBy']),
      reviewedAt: serializer.fromJson<String?>(json['reviewedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'deleted': serializer.toJson<bool>(deleted),
      'version': serializer.toJson<String>(version),
      'sha256': serializer.toJson<String>(sha256),
      'yaml': serializer.toJson<String>(yaml),
      'reviewedBy': serializer.toJson<String?>(reviewedBy),
      'reviewedAt': serializer.toJson<String?>(reviewedAt),
    };
  }

  NormSetRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    bool? deleted,
    String? version,
    String? sha256,
    String? yaml,
    Value<String?> reviewedBy = const Value.absent(),
    Value<String?> reviewedAt = const Value.absent(),
  }) => NormSetRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    deleted: deleted ?? this.deleted,
    version: version ?? this.version,
    sha256: sha256 ?? this.sha256,
    yaml: yaml ?? this.yaml,
    reviewedBy: reviewedBy.present ? reviewedBy.value : this.reviewedBy,
    reviewedAt: reviewedAt.present ? reviewedAt.value : this.reviewedAt,
  );
  NormSetRow copyWithCompanion(NormSetsCompanion data) {
    return NormSetRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      deleted: data.deleted.present ? data.deleted.value : this.deleted,
      version: data.version.present ? data.version.value : this.version,
      sha256: data.sha256.present ? data.sha256.value : this.sha256,
      yaml: data.yaml.present ? data.yaml.value : this.yaml,
      reviewedBy: data.reviewedBy.present ? data.reviewedBy.value : this.reviewedBy,
      reviewedAt: data.reviewedAt.present ? data.reviewedAt.value : this.reviewedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('NormSetRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('version: $version, ')
          ..write('sha256: $sha256, ')
          ..write('yaml: $yaml, ')
          ..write('reviewedBy: $reviewedBy, ')
          ..write('reviewedAt: $reviewedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, createdAt, updatedAt, rev, orgId, deleted, version, sha256, yaml, reviewedBy, reviewedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is NormSetRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.deleted == this.deleted &&
          other.version == this.version &&
          other.sha256 == this.sha256 &&
          other.yaml == this.yaml &&
          other.reviewedBy == this.reviewedBy &&
          other.reviewedAt == this.reviewedAt);
}

class NormSetsCompanion extends UpdateCompanion<NormSetRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<bool> deleted;
  final Value<String> version;
  final Value<String> sha256;
  final Value<String> yaml;
  final Value<String?> reviewedBy;
  final Value<String?> reviewedAt;
  final Value<int> rowid;
  const NormSetsCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.deleted = const Value.absent(),
    this.version = const Value.absent(),
    this.sha256 = const Value.absent(),
    this.yaml = const Value.absent(),
    this.reviewedBy = const Value.absent(),
    this.reviewedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  NormSetsCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    this.deleted = const Value.absent(),
    required String version,
    required String sha256,
    required String yaml,
    this.reviewedBy = const Value.absent(),
    this.reviewedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId),
       version = Value(version),
       sha256 = Value(sha256),
       yaml = Value(yaml);
  static Insertable<NormSetRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<bool>? deleted,
    Expression<String>? version,
    Expression<String>? sha256,
    Expression<String>? yaml,
    Expression<String>? reviewedBy,
    Expression<String>? reviewedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (deleted != null) 'deleted': deleted,
      if (version != null) 'version': version,
      if (sha256 != null) 'sha256': sha256,
      if (yaml != null) 'yaml': yaml,
      if (reviewedBy != null) 'reviewed_by': reviewedBy,
      if (reviewedAt != null) 'reviewed_at': reviewedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  NormSetsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<bool>? deleted,
    Value<String>? version,
    Value<String>? sha256,
    Value<String>? yaml,
    Value<String?>? reviewedBy,
    Value<String?>? reviewedAt,
    Value<int>? rowid,
  }) {
    return NormSetsCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      deleted: deleted ?? this.deleted,
      version: version ?? this.version,
      sha256: sha256 ?? this.sha256,
      yaml: yaml ?? this.yaml,
      reviewedBy: reviewedBy ?? this.reviewedBy,
      reviewedAt: reviewedAt ?? this.reviewedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (deleted.present) {
      map['deleted'] = Variable<bool>(deleted.value);
    }
    if (version.present) {
      map['version'] = Variable<String>(version.value);
    }
    if (sha256.present) {
      map['sha256'] = Variable<String>(sha256.value);
    }
    if (yaml.present) {
      map['yaml'] = Variable<String>(yaml.value);
    }
    if (reviewedBy.present) {
      map['reviewed_by'] = Variable<String>(reviewedBy.value);
    }
    if (reviewedAt.present) {
      map['reviewed_at'] = Variable<String>(reviewedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('NormSetsCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('deleted: $deleted, ')
          ..write('version: $version, ')
          ..write('sha256: $sha256, ')
          ..write('yaml: $yaml, ')
          ..write('reviewedBy: $reviewedBy, ')
          ..write('reviewedAt: $reviewedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $OrgSettingsTable extends OrgSettings with TableInfo<$OrgSettingsTable, OrgSettingRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $OrgSettingsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _revMeta = const VerificationMeta('rev');
  @override
  late final GeneratedColumn<int> rev = GeneratedColumn<int>(
    'rev',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _orgIdMeta = const VerificationMeta('orgId');
  @override
  late final GeneratedColumn<String> orgId = GeneratedColumn<String>(
    'org_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('REFERENCES organization (id)'),
  );
  static const VerificationMeta _kCorrMeta = const VerificationMeta('kCorr');
  @override
  late final GeneratedColumn<double> kCorr = GeneratedColumn<double>(
    'k_corr',
    aliasedName,
    false,
    check: () => ComparableExpr(kCorr).isBiggerThanValue(0) & ComparableExpr(kCorr).isSmallerOrEqualValue(1),
    type: DriftSqlType.double,
    requiredDuringInsert: false,
    defaultValue: const Constant(1.0),
  );
  static const VerificationMeta _marginPctMeta = const VerificationMeta('marginPct');
  @override
  late final GeneratedColumn<double> marginPct = GeneratedColumn<double>(
    'margin_pct',
    aliasedName,
    false,
    check: () => ComparableExpr(marginPct).isBetweenValues(0, 50),
    type: DriftSqlType.double,
    requiredDuringInsert: false,
    defaultValue: const Constant(0.0),
  );
  static const VerificationMeta _activeNormSetVersionMeta = const VerificationMeta('activeNormSetVersion');
  @override
  late final GeneratedColumn<String> activeNormSetVersion = GeneratedColumn<String>(
    'active_norm_set_version',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [id, createdAt, updatedAt, rev, orgId, kCorr, marginPct, activeNormSetVersion];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'org_setting';
  @override
  VerificationContext validateIntegrity(Insertable<OrgSettingRow> instance, {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta, createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta, updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('rev')) {
      context.handle(_revMeta, rev.isAcceptableOrUnknown(data['rev']!, _revMeta));
    }
    if (data.containsKey('org_id')) {
      context.handle(_orgIdMeta, orgId.isAcceptableOrUnknown(data['org_id']!, _orgIdMeta));
    } else if (isInserting) {
      context.missing(_orgIdMeta);
    }
    if (data.containsKey('k_corr')) {
      context.handle(_kCorrMeta, kCorr.isAcceptableOrUnknown(data['k_corr']!, _kCorrMeta));
    }
    if (data.containsKey('margin_pct')) {
      context.handle(_marginPctMeta, marginPct.isAcceptableOrUnknown(data['margin_pct']!, _marginPctMeta));
    }
    if (data.containsKey('active_norm_set_version')) {
      context.handle(
        _activeNormSetVersionMeta,
        activeNormSetVersion.isAcceptableOrUnknown(data['active_norm_set_version']!, _activeNormSetVersionMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {orgId},
  ];
  @override
  OrgSettingRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return OrgSettingRow(
      id: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      createdAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping.read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
      rev: attachedDatabase.typeMapping.read(DriftSqlType.int, data['${effectivePrefix}rev'])!,
      orgId: attachedDatabase.typeMapping.read(DriftSqlType.string, data['${effectivePrefix}org_id'])!,
      kCorr: attachedDatabase.typeMapping.read(DriftSqlType.double, data['${effectivePrefix}k_corr'])!,
      marginPct: attachedDatabase.typeMapping.read(DriftSqlType.double, data['${effectivePrefix}margin_pct'])!,
      activeNormSetVersion: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}active_norm_set_version'],
      ),
    );
  }

  @override
  $OrgSettingsTable createAlias(String alias) {
    return $OrgSettingsTable(attachedDatabase, alias);
  }
}

class OrgSettingRow extends DataClass implements Insertable<OrgSettingRow> {
  final String id;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Mahalliy o'zgarish hisoblagichi (sinxronlash uchun; server reviziyasi alohida saqlanadi — 8-faza).
  final int rev;
  final String orgId;

  /// Sirtmoq koeffitsienti, (0; 1].
  final double kCorr;

  /// Laboratoriya zaxirasi, % [0; 50]; effektiv = max(normalar to'plami, laboratoriya).
  final double marginPct;
  final String? activeNormSetVersion;
  const OrgSettingRow({
    required this.id,
    required this.createdAt,
    required this.updatedAt,
    required this.rev,
    required this.orgId,
    required this.kCorr,
    required this.marginPct,
    this.activeNormSetVersion,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    map['rev'] = Variable<int>(rev);
    map['org_id'] = Variable<String>(orgId);
    map['k_corr'] = Variable<double>(kCorr);
    map['margin_pct'] = Variable<double>(marginPct);
    if (!nullToAbsent || activeNormSetVersion != null) {
      map['active_norm_set_version'] = Variable<String>(activeNormSetVersion);
    }
    return map;
  }

  OrgSettingsCompanion toCompanion(bool nullToAbsent) {
    return OrgSettingsCompanion(
      id: Value(id),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      rev: Value(rev),
      orgId: Value(orgId),
      kCorr: Value(kCorr),
      marginPct: Value(marginPct),
      activeNormSetVersion: activeNormSetVersion == null && nullToAbsent
          ? const Value.absent()
          : Value(activeNormSetVersion),
    );
  }

  factory OrgSettingRow.fromJson(Map<String, dynamic> json, {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return OrgSettingRow(
      id: serializer.fromJson<String>(json['id']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      rev: serializer.fromJson<int>(json['rev']),
      orgId: serializer.fromJson<String>(json['orgId']),
      kCorr: serializer.fromJson<double>(json['kCorr']),
      marginPct: serializer.fromJson<double>(json['marginPct']),
      activeNormSetVersion: serializer.fromJson<String?>(json['activeNormSetVersion']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'rev': serializer.toJson<int>(rev),
      'orgId': serializer.toJson<String>(orgId),
      'kCorr': serializer.toJson<double>(kCorr),
      'marginPct': serializer.toJson<double>(marginPct),
      'activeNormSetVersion': serializer.toJson<String?>(activeNormSetVersion),
    };
  }

  OrgSettingRow copyWith({
    String? id,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? rev,
    String? orgId,
    double? kCorr,
    double? marginPct,
    Value<String?> activeNormSetVersion = const Value.absent(),
  }) => OrgSettingRow(
    id: id ?? this.id,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    rev: rev ?? this.rev,
    orgId: orgId ?? this.orgId,
    kCorr: kCorr ?? this.kCorr,
    marginPct: marginPct ?? this.marginPct,
    activeNormSetVersion: activeNormSetVersion.present ? activeNormSetVersion.value : this.activeNormSetVersion,
  );
  OrgSettingRow copyWithCompanion(OrgSettingsCompanion data) {
    return OrgSettingRow(
      id: data.id.present ? data.id.value : this.id,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      rev: data.rev.present ? data.rev.value : this.rev,
      orgId: data.orgId.present ? data.orgId.value : this.orgId,
      kCorr: data.kCorr.present ? data.kCorr.value : this.kCorr,
      marginPct: data.marginPct.present ? data.marginPct.value : this.marginPct,
      activeNormSetVersion: data.activeNormSetVersion.present
          ? data.activeNormSetVersion.value
          : this.activeNormSetVersion,
    );
  }

  @override
  String toString() {
    return (StringBuffer('OrgSettingRow(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('kCorr: $kCorr, ')
          ..write('marginPct: $marginPct, ')
          ..write('activeNormSetVersion: $activeNormSetVersion')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, createdAt, updatedAt, rev, orgId, kCorr, marginPct, activeNormSetVersion);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is OrgSettingRow &&
          other.id == this.id &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.rev == this.rev &&
          other.orgId == this.orgId &&
          other.kCorr == this.kCorr &&
          other.marginPct == this.marginPct &&
          other.activeNormSetVersion == this.activeNormSetVersion);
}

class OrgSettingsCompanion extends UpdateCompanion<OrgSettingRow> {
  final Value<String> id;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<int> rev;
  final Value<String> orgId;
  final Value<double> kCorr;
  final Value<double> marginPct;
  final Value<String?> activeNormSetVersion;
  final Value<int> rowid;
  const OrgSettingsCompanion({
    this.id = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rev = const Value.absent(),
    this.orgId = const Value.absent(),
    this.kCorr = const Value.absent(),
    this.marginPct = const Value.absent(),
    this.activeNormSetVersion = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  OrgSettingsCompanion.insert({
    required String id,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.rev = const Value.absent(),
    required String orgId,
    this.kCorr = const Value.absent(),
    this.marginPct = const Value.absent(),
    this.activeNormSetVersion = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       orgId = Value(orgId);
  static Insertable<OrgSettingRow> custom({
    Expression<String>? id,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rev,
    Expression<String>? orgId,
    Expression<double>? kCorr,
    Expression<double>? marginPct,
    Expression<String>? activeNormSetVersion,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rev != null) 'rev': rev,
      if (orgId != null) 'org_id': orgId,
      if (kCorr != null) 'k_corr': kCorr,
      if (marginPct != null) 'margin_pct': marginPct,
      if (activeNormSetVersion != null) 'active_norm_set_version': activeNormSetVersion,
      if (rowid != null) 'rowid': rowid,
    });
  }

  OrgSettingsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<int>? rev,
    Value<String>? orgId,
    Value<double>? kCorr,
    Value<double>? marginPct,
    Value<String?>? activeNormSetVersion,
    Value<int>? rowid,
  }) {
    return OrgSettingsCompanion(
      id: id ?? this.id,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rev: rev ?? this.rev,
      orgId: orgId ?? this.orgId,
      kCorr: kCorr ?? this.kCorr,
      marginPct: marginPct ?? this.marginPct,
      activeNormSetVersion: activeNormSetVersion ?? this.activeNormSetVersion,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rev.present) {
      map['rev'] = Variable<int>(rev.value);
    }
    if (orgId.present) {
      map['org_id'] = Variable<String>(orgId.value);
    }
    if (kCorr.present) {
      map['k_corr'] = Variable<double>(kCorr.value);
    }
    if (marginPct.present) {
      map['margin_pct'] = Variable<double>(marginPct.value);
    }
    if (activeNormSetVersion.present) {
      map['active_norm_set_version'] = Variable<String>(activeNormSetVersion.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('OrgSettingsCompanion(')
          ..write('id: $id, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rev: $rev, ')
          ..write('orgId: $orgId, ')
          ..write('kCorr: $kCorr, ')
          ..write('marginPct: $marginPct, ')
          ..write('activeNormSetVersion: $activeNormSetVersion, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$ZanjirDatabase extends GeneratedDatabase {
  _$ZanjirDatabase(QueryExecutor e) : super(e);
  late final $OrganizationsTable organizations = $OrganizationsTable(this);
  late final $SitesTable sites = $SitesTable(this);
  late final $AppUsersTable appUsers = $AppUsersTable(this);
  late final $MeasurementSessionsTable measurementSessions = $MeasurementSessionsTable(this);
  late final $NodesTable nodes = $NodesTable(this);
  late final $InstrumentsTable instruments = $InstrumentsTable(this);
  late final $MeasurementsTable measurements = $MeasurementsTable(this);
  late final Trigger measurementAppendOnlyUpdate = Trigger(
    'CREATE TRIGGER measurement_append_only_update BEFORE UPDATE ON measurement BEGIN SELECT RAISE (ABORT, \'append_only: measurement\');END',
    'measurement_append_only_update',
  );
  late final Trigger measurementAppendOnlyDelete = Trigger(
    'CREATE TRIGGER measurement_append_only_delete BEFORE DELETE ON measurement BEGIN SELECT RAISE (ABORT, \'append_only: measurement\');END',
    'measurement_append_only_delete',
  );
  late final $DevicesTable devices = $DevicesTable(this);
  late final $ProtocolsTable protocols = $ProtocolsTable(this);
  late final Trigger protocolAppendOnlyUpdate = Trigger(
    'CREATE TRIGGER protocol_append_only_update BEFORE UPDATE ON protocol BEGIN SELECT RAISE (ABORT, \'append_only: protocol\');END',
    'protocol_append_only_update',
  );
  late final Trigger protocolAppendOnlyDelete = Trigger(
    'CREATE TRIGGER protocol_append_only_delete BEFORE DELETE ON protocol BEGIN SELECT RAISE (ABORT, \'append_only: protocol\');END',
    'protocol_append_only_delete',
  );
  late final $ProtocolDocumentsTable protocolDocuments = $ProtocolDocumentsTable(this);
  late final Trigger protocolDocumentAppendOnlyUpdate = Trigger(
    'CREATE TRIGGER protocol_document_append_only_update BEFORE UPDATE ON protocol_document BEGIN SELECT RAISE (ABORT, \'append_only: protocol_document\');END',
    'protocol_document_append_only_update',
  );
  late final Trigger protocolDocumentAppendOnlyDelete = Trigger(
    'CREATE TRIGGER protocol_document_append_only_delete BEFORE DELETE ON protocol_document BEGIN SELECT RAISE (ABORT, \'append_only: protocol_document\');END',
    'protocol_document_append_only_delete',
  );
  late final $AuditEventsTable auditEvents = $AuditEventsTable(this);
  late final Trigger auditEventAppendOnlyUpdate = Trigger(
    'CREATE TRIGGER audit_event_append_only_update BEFORE UPDATE ON audit_event BEGIN SELECT RAISE (ABORT, \'append_only: audit_event\');END',
    'audit_event_append_only_update',
  );
  late final Trigger auditEventAppendOnlyDelete = Trigger(
    'CREATE TRIGGER audit_event_append_only_delete BEFORE DELETE ON audit_event BEGIN SELECT RAISE (ABORT, \'append_only: audit_event\');END',
    'audit_event_append_only_delete',
  );
  late final Index nodeSiteIdx = Index('node_site_idx', 'CREATE INDEX node_site_idx ON node (site_id)');
  late final $EdgesTable edges = $EdgesTable(this);
  late final Index edgeSiteIdx = Index('edge_site_idx', 'CREATE INDEX edge_site_idx ON edge (site_id)');
  late final Index measurementSessionIdx = Index(
    'measurement_session_idx',
    'CREATE INDEX measurement_session_idx ON measurement (session_id)',
  );
  late final Index auditEventEntityIdx = Index(
    'audit_event_entity_idx',
    'CREATE INDEX audit_event_entity_idx ON audit_event (entity_id)',
  );
  late final $LocalPrefsTable localPrefs = $LocalPrefsTable(this);
  late final $SyncOutboxTable syncOutbox = $SyncOutboxTable(this);
  late final Trigger organizationOutboxIns = Trigger(
    'CREATE TRIGGER organization_outbox_ins AFTER INSERT ON organization WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'organization\', NEW.id, lower(hex(randomblob(16))));END',
    'organization_outbox_ins',
  );
  late final Trigger organizationOutboxUpd = Trigger(
    'CREATE TRIGGER organization_outbox_upd AFTER UPDATE ON organization WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'organization\', NEW.id, lower(hex(randomblob(16))));END',
    'organization_outbox_upd',
  );
  late final Trigger instrumentOutboxIns = Trigger(
    'CREATE TRIGGER instrument_outbox_ins AFTER INSERT ON instrument WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'instrument\', NEW.id, lower(hex(randomblob(16))));END',
    'instrument_outbox_ins',
  );
  late final Trigger instrumentOutboxUpd = Trigger(
    'CREATE TRIGGER instrument_outbox_upd AFTER UPDATE ON instrument WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'instrument\', NEW.id, lower(hex(randomblob(16))));END',
    'instrument_outbox_upd',
  );
  late final Trigger siteOutboxIns = Trigger(
    'CREATE TRIGGER site_outbox_ins AFTER INSERT ON site WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'site\', NEW.id, lower(hex(randomblob(16))));END',
    'site_outbox_ins',
  );
  late final Trigger siteOutboxUpd = Trigger(
    'CREATE TRIGGER site_outbox_upd AFTER UPDATE ON site WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'site\', NEW.id, lower(hex(randomblob(16))));END',
    'site_outbox_upd',
  );
  late final Trigger nodeOutboxIns = Trigger(
    'CREATE TRIGGER node_outbox_ins AFTER INSERT ON node WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'node\', NEW.id, lower(hex(randomblob(16))));END',
    'node_outbox_ins',
  );
  late final Trigger nodeOutboxUpd = Trigger(
    'CREATE TRIGGER node_outbox_upd AFTER UPDATE ON node WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'node\', NEW.id, lower(hex(randomblob(16))));END',
    'node_outbox_upd',
  );
  late final Trigger edgeOutboxIns = Trigger(
    'CREATE TRIGGER edge_outbox_ins AFTER INSERT ON edge WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'edge\', NEW.id, lower(hex(randomblob(16))));END',
    'edge_outbox_ins',
  );
  late final Trigger edgeOutboxUpd = Trigger(
    'CREATE TRIGGER edge_outbox_upd AFTER UPDATE ON edge WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'edge\', NEW.id, lower(hex(randomblob(16))));END',
    'edge_outbox_upd',
  );
  late final Trigger measurementSessionOutboxIns = Trigger(
    'CREATE TRIGGER measurement_session_outbox_ins AFTER INSERT ON measurement_session WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'measurement_session\', NEW.id, lower(hex(randomblob(16))));END',
    'measurement_session_outbox_ins',
  );
  late final Trigger measurementSessionOutboxUpd = Trigger(
    'CREATE TRIGGER measurement_session_outbox_upd AFTER UPDATE ON measurement_session WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'measurement_session\', NEW.id, lower(hex(randomblob(16))));END',
    'measurement_session_outbox_upd',
  );
  late final Trigger measurementOutboxIns = Trigger(
    'CREATE TRIGGER measurement_outbox_ins AFTER INSERT ON measurement WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'measurement\', NEW.id, lower(hex(randomblob(16))));END',
    'measurement_outbox_ins',
  );
  late final Trigger protocolOutboxIns = Trigger(
    'CREATE TRIGGER protocol_outbox_ins AFTER INSERT ON protocol WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'protocol\', NEW.id, lower(hex(randomblob(16))));END',
    'protocol_outbox_ins',
  );
  late final Trigger protocolDocumentOutboxIns = Trigger(
    'CREATE TRIGGER protocol_document_outbox_ins AFTER INSERT ON protocol_document WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'protocol_document\', NEW.id, lower(hex(randomblob(16))));END',
    'protocol_document_outbox_ins',
  );
  late final Trigger auditEventOutboxIns = Trigger(
    'CREATE TRIGGER audit_event_outbox_ins AFTER INSERT ON audit_event WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'audit_event\', NEW.id, lower(hex(randomblob(16))));END',
    'audit_event_outbox_ins',
  );
  late final $IsolationPlansTable isolationPlans = $IsolationPlansTable(this);
  late final Trigger isolationPlanOutboxIns = Trigger(
    'CREATE TRIGGER isolation_plan_outbox_ins AFTER INSERT ON isolation_plan WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'isolation_plan\', NEW.id, lower(hex(randomblob(16))));END',
    'isolation_plan_outbox_ins',
  );
  late final Trigger isolationPlanOutboxUpd = Trigger(
    'CREATE TRIGGER isolation_plan_outbox_upd AFTER UPDATE ON isolation_plan WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'isolation_plan\', NEW.id, lower(hex(randomblob(16))));END',
    'isolation_plan_outbox_upd',
  );
  late final $NormSetsTable normSets = $NormSetsTable(this);
  late final Trigger normSetOutboxIns = Trigger(
    'CREATE TRIGGER norm_set_outbox_ins AFTER INSERT ON norm_set WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'norm_set\', NEW.id, lower(hex(randomblob(16))));END',
    'norm_set_outbox_ins',
  );
  late final Trigger normSetOutboxUpd = Trigger(
    'CREATE TRIGGER norm_set_outbox_upd AFTER UPDATE ON norm_set WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'norm_set\', NEW.id, lower(hex(randomblob(16))));END',
    'norm_set_outbox_upd',
  );
  late final $OrgSettingsTable orgSettings = $OrgSettingsTable(this);
  late final Trigger orgSettingOutboxIns = Trigger(
    'CREATE TRIGGER org_setting_outbox_ins AFTER INSERT ON org_setting WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'org_setting\', NEW.id, lower(hex(randomblob(16))));END',
    'org_setting_outbox_ins',
  );
  late final Trigger orgSettingOutboxUpd = Trigger(
    'CREATE TRIGGER org_setting_outbox_upd AFTER UPDATE ON org_setting WHEN NOT EXISTS (SELECT 1 FROM local_pref WHERE "key" = \'sync.applying\') BEGIN INSERT OR REPLACE INTO sync_outbox (table_name, row_id, op_id) VALUES (\'org_setting\', NEW.id, lower(hex(randomblob(16))));END',
    'org_setting_outbox_upd',
  );
  @override
  Iterable<TableInfo<Table, Object?>> get allTables => allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    organizations,
    sites,
    appUsers,
    measurementSessions,
    nodes,
    instruments,
    measurements,
    measurementAppendOnlyUpdate,
    measurementAppendOnlyDelete,
    devices,
    protocols,
    protocolAppendOnlyUpdate,
    protocolAppendOnlyDelete,
    protocolDocuments,
    protocolDocumentAppendOnlyUpdate,
    protocolDocumentAppendOnlyDelete,
    auditEvents,
    auditEventAppendOnlyUpdate,
    auditEventAppendOnlyDelete,
    nodeSiteIdx,
    edges,
    edgeSiteIdx,
    measurementSessionIdx,
    auditEventEntityIdx,
    localPrefs,
    syncOutbox,
    organizationOutboxIns,
    organizationOutboxUpd,
    instrumentOutboxIns,
    instrumentOutboxUpd,
    siteOutboxIns,
    siteOutboxUpd,
    nodeOutboxIns,
    nodeOutboxUpd,
    edgeOutboxIns,
    edgeOutboxUpd,
    measurementSessionOutboxIns,
    measurementSessionOutboxUpd,
    measurementOutboxIns,
    protocolOutboxIns,
    protocolDocumentOutboxIns,
    auditEventOutboxIns,
    isolationPlans,
    isolationPlanOutboxIns,
    isolationPlanOutboxUpd,
    normSets,
    normSetOutboxIns,
    normSetOutboxUpd,
    orgSettings,
    orgSettingOutboxIns,
    orgSettingOutboxUpd,
  ];
  @override
  StreamQueryUpdateRules get streamUpdateRules => const StreamQueryUpdateRules([
    WritePropagation(
      on: TableUpdateQuery.onTableName('measurement', limitUpdateKind: UpdateKind.update),
      result: [],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('measurement', limitUpdateKind: UpdateKind.delete),
      result: [],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('protocol', limitUpdateKind: UpdateKind.update),
      result: [],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('protocol', limitUpdateKind: UpdateKind.delete),
      result: [],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('protocol_document', limitUpdateKind: UpdateKind.update),
      result: [],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('protocol_document', limitUpdateKind: UpdateKind.delete),
      result: [],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('audit_event', limitUpdateKind: UpdateKind.update),
      result: [],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('audit_event', limitUpdateKind: UpdateKind.delete),
      result: [],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('organization', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('organization', limitUpdateKind: UpdateKind.update),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('instrument', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('instrument', limitUpdateKind: UpdateKind.update),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('site', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('site', limitUpdateKind: UpdateKind.update),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('node', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('node', limitUpdateKind: UpdateKind.update),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('edge', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('edge', limitUpdateKind: UpdateKind.update),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('measurement_session', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('measurement_session', limitUpdateKind: UpdateKind.update),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('measurement', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('protocol', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('protocol_document', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('audit_event', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('isolation_plan', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('isolation_plan', limitUpdateKind: UpdateKind.update),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('norm_set', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('norm_set', limitUpdateKind: UpdateKind.update),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('org_setting', limitUpdateKind: UpdateKind.insert),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
    WritePropagation(
      on: TableUpdateQuery.onTableName('org_setting', limitUpdateKind: UpdateKind.update),
      result: [TableUpdate('sync_outbox', kind: UpdateKind.insert)],
    ),
  ]);
  @override
  DriftDatabaseOptions get options => const DriftDatabaseOptions(storeDateTimeAsText: true);
}
