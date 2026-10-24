// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'vault.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$Asset {

 SyncMeta get meta; AssetType get type; QuantityUnit get unit;/// UTC.
 DateTime get acquiredAt;/// Pul — minor birlik, oltin — milligramm.
 int get quantity; CurrencyCode? get currency; String? get name; VaultType? get vaultType;
/// Create a copy of Asset
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AssetCopyWith<Asset> get copyWith => _$AssetCopyWithImpl<Asset>(this as Asset, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Asset&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.type, type) || other.type == type)&&(identical(other.unit, unit) || other.unit == unit)&&(identical(other.acquiredAt, acquiredAt) || other.acquiredAt == acquiredAt)&&(identical(other.quantity, quantity) || other.quantity == quantity)&&(identical(other.currency, currency) || other.currency == currency)&&(identical(other.name, name) || other.name == name)&&(identical(other.vaultType, vaultType) || other.vaultType == vaultType));
}


@override
int get hashCode => Object.hash(runtimeType,meta,type,unit,acquiredAt,quantity,currency,name,vaultType);

@override
String toString() {
  return 'Asset(meta: $meta, type: $type, unit: $unit, acquiredAt: $acquiredAt, quantity: $quantity, currency: $currency, name: $name, vaultType: $vaultType)';
}


}

/// @nodoc
abstract mixin class $AssetCopyWith<$Res>  {
  factory $AssetCopyWith(Asset value, $Res Function(Asset) _then) = _$AssetCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, AssetType type, QuantityUnit unit, DateTime acquiredAt, int quantity, CurrencyCode? currency, String? name, VaultType? vaultType
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$AssetCopyWithImpl<$Res>
    implements $AssetCopyWith<$Res> {
  _$AssetCopyWithImpl(this._self, this._then);

  final Asset _self;
  final $Res Function(Asset) _then;

/// Create a copy of Asset
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? type = null,Object? unit = null,Object? acquiredAt = null,Object? quantity = null,Object? currency = freezed,Object? name = freezed,Object? vaultType = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as AssetType,unit: null == unit ? _self.unit : unit // ignore: cast_nullable_to_non_nullable
as QuantityUnit,acquiredAt: null == acquiredAt ? _self.acquiredAt : acquiredAt // ignore: cast_nullable_to_non_nullable
as DateTime,quantity: null == quantity ? _self.quantity : quantity // ignore: cast_nullable_to_non_nullable
as int,currency: freezed == currency ? _self.currency : currency // ignore: cast_nullable_to_non_nullable
as CurrencyCode?,name: freezed == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String?,vaultType: freezed == vaultType ? _self.vaultType : vaultType // ignore: cast_nullable_to_non_nullable
as VaultType?,
  ));
}
/// Create a copy of Asset
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Asset].
extension AssetPatterns on Asset {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Asset value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Asset() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Asset value)  $default,){
final _that = this;
switch (_that) {
case _Asset():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Asset value)?  $default,){
final _that = this;
switch (_that) {
case _Asset() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  AssetType type,  QuantityUnit unit,  DateTime acquiredAt,  int quantity,  CurrencyCode? currency,  String? name,  VaultType? vaultType)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Asset() when $default != null:
return $default(_that.meta,_that.type,_that.unit,_that.acquiredAt,_that.quantity,_that.currency,_that.name,_that.vaultType);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  AssetType type,  QuantityUnit unit,  DateTime acquiredAt,  int quantity,  CurrencyCode? currency,  String? name,  VaultType? vaultType)  $default,) {final _that = this;
switch (_that) {
case _Asset():
return $default(_that.meta,_that.type,_that.unit,_that.acquiredAt,_that.quantity,_that.currency,_that.name,_that.vaultType);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  AssetType type,  QuantityUnit unit,  DateTime acquiredAt,  int quantity,  CurrencyCode? currency,  String? name,  VaultType? vaultType)?  $default,) {final _that = this;
switch (_that) {
case _Asset() when $default != null:
return $default(_that.meta,_that.type,_that.unit,_that.acquiredAt,_that.quantity,_that.currency,_that.name,_that.vaultType);case _:
  return null;

}
}

}

/// @nodoc


class _Asset implements Asset {
  const _Asset({required this.meta, required this.type, required this.unit, required this.acquiredAt, this.quantity = 0, this.currency, this.name, this.vaultType});
  

@override final  SyncMeta meta;
@override final  AssetType type;
@override final  QuantityUnit unit;
/// UTC.
@override final  DateTime acquiredAt;
/// Pul — minor birlik, oltin — milligramm.
@override@JsonKey() final  int quantity;
@override final  CurrencyCode? currency;
@override final  String? name;
@override final  VaultType? vaultType;

/// Create a copy of Asset
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AssetCopyWith<_Asset> get copyWith => __$AssetCopyWithImpl<_Asset>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Asset&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.type, type) || other.type == type)&&(identical(other.unit, unit) || other.unit == unit)&&(identical(other.acquiredAt, acquiredAt) || other.acquiredAt == acquiredAt)&&(identical(other.quantity, quantity) || other.quantity == quantity)&&(identical(other.currency, currency) || other.currency == currency)&&(identical(other.name, name) || other.name == name)&&(identical(other.vaultType, vaultType) || other.vaultType == vaultType));
}


@override
int get hashCode => Object.hash(runtimeType,meta,type,unit,acquiredAt,quantity,currency,name,vaultType);

@override
String toString() {
  return 'Asset(meta: $meta, type: $type, unit: $unit, acquiredAt: $acquiredAt, quantity: $quantity, currency: $currency, name: $name, vaultType: $vaultType)';
}


}

/// @nodoc
abstract mixin class _$AssetCopyWith<$Res> implements $AssetCopyWith<$Res> {
  factory _$AssetCopyWith(_Asset value, $Res Function(_Asset) _then) = __$AssetCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, AssetType type, QuantityUnit unit, DateTime acquiredAt, int quantity, CurrencyCode? currency, String? name, VaultType? vaultType
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$AssetCopyWithImpl<$Res>
    implements _$AssetCopyWith<$Res> {
  __$AssetCopyWithImpl(this._self, this._then);

  final _Asset _self;
  final $Res Function(_Asset) _then;

/// Create a copy of Asset
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? type = null,Object? unit = null,Object? acquiredAt = null,Object? quantity = null,Object? currency = freezed,Object? name = freezed,Object? vaultType = freezed,}) {
  return _then(_Asset(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as AssetType,unit: null == unit ? _self.unit : unit // ignore: cast_nullable_to_non_nullable
as QuantityUnit,acquiredAt: null == acquiredAt ? _self.acquiredAt : acquiredAt // ignore: cast_nullable_to_non_nullable
as DateTime,quantity: null == quantity ? _self.quantity : quantity // ignore: cast_nullable_to_non_nullable
as int,currency: freezed == currency ? _self.currency : currency // ignore: cast_nullable_to_non_nullable
as CurrencyCode?,name: freezed == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String?,vaultType: freezed == vaultType ? _self.vaultType : vaultType // ignore: cast_nullable_to_non_nullable
as VaultType?,
  ));
}

/// Create a copy of Asset
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}

/// @nodoc
mixin _$AssetSnapshot {

 SyncMeta get meta; String get assetId; int get quantity;/// UTC.
 DateTime get takenAt;
/// Create a copy of AssetSnapshot
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AssetSnapshotCopyWith<AssetSnapshot> get copyWith => _$AssetSnapshotCopyWithImpl<AssetSnapshot>(this as AssetSnapshot, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is AssetSnapshot&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.assetId, assetId) || other.assetId == assetId)&&(identical(other.quantity, quantity) || other.quantity == quantity)&&(identical(other.takenAt, takenAt) || other.takenAt == takenAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,assetId,quantity,takenAt);

@override
String toString() {
  return 'AssetSnapshot(meta: $meta, assetId: $assetId, quantity: $quantity, takenAt: $takenAt)';
}


}

/// @nodoc
abstract mixin class $AssetSnapshotCopyWith<$Res>  {
  factory $AssetSnapshotCopyWith(AssetSnapshot value, $Res Function(AssetSnapshot) _then) = _$AssetSnapshotCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String assetId, int quantity, DateTime takenAt
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$AssetSnapshotCopyWithImpl<$Res>
    implements $AssetSnapshotCopyWith<$Res> {
  _$AssetSnapshotCopyWithImpl(this._self, this._then);

  final AssetSnapshot _self;
  final $Res Function(AssetSnapshot) _then;

/// Create a copy of AssetSnapshot
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? assetId = null,Object? quantity = null,Object? takenAt = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,assetId: null == assetId ? _self.assetId : assetId // ignore: cast_nullable_to_non_nullable
as String,quantity: null == quantity ? _self.quantity : quantity // ignore: cast_nullable_to_non_nullable
as int,takenAt: null == takenAt ? _self.takenAt : takenAt // ignore: cast_nullable_to_non_nullable
as DateTime,
  ));
}
/// Create a copy of AssetSnapshot
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [AssetSnapshot].
extension AssetSnapshotPatterns on AssetSnapshot {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _AssetSnapshot value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _AssetSnapshot() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _AssetSnapshot value)  $default,){
final _that = this;
switch (_that) {
case _AssetSnapshot():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _AssetSnapshot value)?  $default,){
final _that = this;
switch (_that) {
case _AssetSnapshot() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String assetId,  int quantity,  DateTime takenAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _AssetSnapshot() when $default != null:
return $default(_that.meta,_that.assetId,_that.quantity,_that.takenAt);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String assetId,  int quantity,  DateTime takenAt)  $default,) {final _that = this;
switch (_that) {
case _AssetSnapshot():
return $default(_that.meta,_that.assetId,_that.quantity,_that.takenAt);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String assetId,  int quantity,  DateTime takenAt)?  $default,) {final _that = this;
switch (_that) {
case _AssetSnapshot() when $default != null:
return $default(_that.meta,_that.assetId,_that.quantity,_that.takenAt);case _:
  return null;

}
}

}

/// @nodoc


class _AssetSnapshot implements AssetSnapshot {
  const _AssetSnapshot({required this.meta, required this.assetId, required this.quantity, required this.takenAt});
  

@override final  SyncMeta meta;
@override final  String assetId;
@override final  int quantity;
/// UTC.
@override final  DateTime takenAt;

/// Create a copy of AssetSnapshot
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AssetSnapshotCopyWith<_AssetSnapshot> get copyWith => __$AssetSnapshotCopyWithImpl<_AssetSnapshot>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _AssetSnapshot&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.assetId, assetId) || other.assetId == assetId)&&(identical(other.quantity, quantity) || other.quantity == quantity)&&(identical(other.takenAt, takenAt) || other.takenAt == takenAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,assetId,quantity,takenAt);

@override
String toString() {
  return 'AssetSnapshot(meta: $meta, assetId: $assetId, quantity: $quantity, takenAt: $takenAt)';
}


}

/// @nodoc
abstract mixin class _$AssetSnapshotCopyWith<$Res> implements $AssetSnapshotCopyWith<$Res> {
  factory _$AssetSnapshotCopyWith(_AssetSnapshot value, $Res Function(_AssetSnapshot) _then) = __$AssetSnapshotCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String assetId, int quantity, DateTime takenAt
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$AssetSnapshotCopyWithImpl<$Res>
    implements _$AssetSnapshotCopyWith<$Res> {
  __$AssetSnapshotCopyWithImpl(this._self, this._then);

  final _AssetSnapshot _self;
  final $Res Function(_AssetSnapshot) _then;

/// Create a copy of AssetSnapshot
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? assetId = null,Object? quantity = null,Object? takenAt = null,}) {
  return _then(_AssetSnapshot(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,assetId: null == assetId ? _self.assetId : assetId // ignore: cast_nullable_to_non_nullable
as String,quantity: null == quantity ? _self.quantity : quantity // ignore: cast_nullable_to_non_nullable
as int,takenAt: null == takenAt ? _self.takenAt : takenAt // ignore: cast_nullable_to_non_nullable
as DateTime,
  ));
}

/// Create a copy of AssetSnapshot
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}

/// @nodoc
mixin _$VaultTransaction {

 SyncMeta get meta; String get vaultAssetId; VaultTransactionType get type;/// Doim musbat; yo'nalish [type] da.
 Money get amount; VaultTransactionReason get reason;/// UTC.
 DateTime get occurredAt;/// Pul olishda majburiy.
 String? get reasonNote; String? get incomeId; String? get memberId;
/// Create a copy of VaultTransaction
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$VaultTransactionCopyWith<VaultTransaction> get copyWith => _$VaultTransactionCopyWithImpl<VaultTransaction>(this as VaultTransaction, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is VaultTransaction&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.vaultAssetId, vaultAssetId) || other.vaultAssetId == vaultAssetId)&&(identical(other.type, type) || other.type == type)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.reason, reason) || other.reason == reason)&&(identical(other.occurredAt, occurredAt) || other.occurredAt == occurredAt)&&(identical(other.reasonNote, reasonNote) || other.reasonNote == reasonNote)&&(identical(other.incomeId, incomeId) || other.incomeId == incomeId)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,vaultAssetId,type,amount,reason,occurredAt,reasonNote,incomeId,memberId);

@override
String toString() {
  return 'VaultTransaction(meta: $meta, vaultAssetId: $vaultAssetId, type: $type, amount: $amount, reason: $reason, occurredAt: $occurredAt, reasonNote: $reasonNote, incomeId: $incomeId, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class $VaultTransactionCopyWith<$Res>  {
  factory $VaultTransactionCopyWith(VaultTransaction value, $Res Function(VaultTransaction) _then) = _$VaultTransactionCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String vaultAssetId, VaultTransactionType type, Money amount, VaultTransactionReason reason, DateTime occurredAt, String? reasonNote, String? incomeId, String? memberId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$VaultTransactionCopyWithImpl<$Res>
    implements $VaultTransactionCopyWith<$Res> {
  _$VaultTransactionCopyWithImpl(this._self, this._then);

  final VaultTransaction _self;
  final $Res Function(VaultTransaction) _then;

/// Create a copy of VaultTransaction
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? vaultAssetId = null,Object? type = null,Object? amount = null,Object? reason = null,Object? occurredAt = null,Object? reasonNote = freezed,Object? incomeId = freezed,Object? memberId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,vaultAssetId: null == vaultAssetId ? _self.vaultAssetId : vaultAssetId // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as VaultTransactionType,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,reason: null == reason ? _self.reason : reason // ignore: cast_nullable_to_non_nullable
as VaultTransactionReason,occurredAt: null == occurredAt ? _self.occurredAt : occurredAt // ignore: cast_nullable_to_non_nullable
as DateTime,reasonNote: freezed == reasonNote ? _self.reasonNote : reasonNote // ignore: cast_nullable_to_non_nullable
as String?,incomeId: freezed == incomeId ? _self.incomeId : incomeId // ignore: cast_nullable_to_non_nullable
as String?,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of VaultTransaction
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [VaultTransaction].
extension VaultTransactionPatterns on VaultTransaction {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _VaultTransaction value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _VaultTransaction() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _VaultTransaction value)  $default,){
final _that = this;
switch (_that) {
case _VaultTransaction():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _VaultTransaction value)?  $default,){
final _that = this;
switch (_that) {
case _VaultTransaction() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String vaultAssetId,  VaultTransactionType type,  Money amount,  VaultTransactionReason reason,  DateTime occurredAt,  String? reasonNote,  String? incomeId,  String? memberId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _VaultTransaction() when $default != null:
return $default(_that.meta,_that.vaultAssetId,_that.type,_that.amount,_that.reason,_that.occurredAt,_that.reasonNote,_that.incomeId,_that.memberId);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String vaultAssetId,  VaultTransactionType type,  Money amount,  VaultTransactionReason reason,  DateTime occurredAt,  String? reasonNote,  String? incomeId,  String? memberId)  $default,) {final _that = this;
switch (_that) {
case _VaultTransaction():
return $default(_that.meta,_that.vaultAssetId,_that.type,_that.amount,_that.reason,_that.occurredAt,_that.reasonNote,_that.incomeId,_that.memberId);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String vaultAssetId,  VaultTransactionType type,  Money amount,  VaultTransactionReason reason,  DateTime occurredAt,  String? reasonNote,  String? incomeId,  String? memberId)?  $default,) {final _that = this;
switch (_that) {
case _VaultTransaction() when $default != null:
return $default(_that.meta,_that.vaultAssetId,_that.type,_that.amount,_that.reason,_that.occurredAt,_that.reasonNote,_that.incomeId,_that.memberId);case _:
  return null;

}
}

}

/// @nodoc


class _VaultTransaction implements VaultTransaction {
  const _VaultTransaction({required this.meta, required this.vaultAssetId, required this.type, required this.amount, required this.reason, required this.occurredAt, this.reasonNote, this.incomeId, this.memberId});
  

@override final  SyncMeta meta;
@override final  String vaultAssetId;
@override final  VaultTransactionType type;
/// Doim musbat; yo'nalish [type] da.
@override final  Money amount;
@override final  VaultTransactionReason reason;
/// UTC.
@override final  DateTime occurredAt;
/// Pul olishda majburiy.
@override final  String? reasonNote;
@override final  String? incomeId;
@override final  String? memberId;

/// Create a copy of VaultTransaction
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$VaultTransactionCopyWith<_VaultTransaction> get copyWith => __$VaultTransactionCopyWithImpl<_VaultTransaction>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _VaultTransaction&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.vaultAssetId, vaultAssetId) || other.vaultAssetId == vaultAssetId)&&(identical(other.type, type) || other.type == type)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.reason, reason) || other.reason == reason)&&(identical(other.occurredAt, occurredAt) || other.occurredAt == occurredAt)&&(identical(other.reasonNote, reasonNote) || other.reasonNote == reasonNote)&&(identical(other.incomeId, incomeId) || other.incomeId == incomeId)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,vaultAssetId,type,amount,reason,occurredAt,reasonNote,incomeId,memberId);

@override
String toString() {
  return 'VaultTransaction(meta: $meta, vaultAssetId: $vaultAssetId, type: $type, amount: $amount, reason: $reason, occurredAt: $occurredAt, reasonNote: $reasonNote, incomeId: $incomeId, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class _$VaultTransactionCopyWith<$Res> implements $VaultTransactionCopyWith<$Res> {
  factory _$VaultTransactionCopyWith(_VaultTransaction value, $Res Function(_VaultTransaction) _then) = __$VaultTransactionCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String vaultAssetId, VaultTransactionType type, Money amount, VaultTransactionReason reason, DateTime occurredAt, String? reasonNote, String? incomeId, String? memberId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$VaultTransactionCopyWithImpl<$Res>
    implements _$VaultTransactionCopyWith<$Res> {
  __$VaultTransactionCopyWithImpl(this._self, this._then);

  final _VaultTransaction _self;
  final $Res Function(_VaultTransaction) _then;

/// Create a copy of VaultTransaction
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? vaultAssetId = null,Object? type = null,Object? amount = null,Object? reason = null,Object? occurredAt = null,Object? reasonNote = freezed,Object? incomeId = freezed,Object? memberId = freezed,}) {
  return _then(_VaultTransaction(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,vaultAssetId: null == vaultAssetId ? _self.vaultAssetId : vaultAssetId // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as VaultTransactionType,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,reason: null == reason ? _self.reason : reason // ignore: cast_nullable_to_non_nullable
as VaultTransactionReason,occurredAt: null == occurredAt ? _self.occurredAt : occurredAt // ignore: cast_nullable_to_non_nullable
as DateTime,reasonNote: freezed == reasonNote ? _self.reasonNote : reasonNote // ignore: cast_nullable_to_non_nullable
as String?,incomeId: freezed == incomeId ? _self.incomeId : incomeId // ignore: cast_nullable_to_non_nullable
as String?,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of VaultTransaction
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}

/// @nodoc
mixin _$AllocationRule {

 SyncMeta get meta; String get vaultAssetId; AllocationMode get mode; CurrencyCode get currency; int? get basisPoints;/// Qat'iy summa — oyiga (masalan, 300 000 so'm).
 Money? get fixedAmount; bool get isActive;/// Progressiv rejimda oxirgi «+1 %» taklifi (UTC).
 DateTime? get progressionOfferedAt;
/// Create a copy of AllocationRule
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AllocationRuleCopyWith<AllocationRule> get copyWith => _$AllocationRuleCopyWithImpl<AllocationRule>(this as AllocationRule, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is AllocationRule&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.vaultAssetId, vaultAssetId) || other.vaultAssetId == vaultAssetId)&&(identical(other.mode, mode) || other.mode == mode)&&(identical(other.currency, currency) || other.currency == currency)&&(identical(other.basisPoints, basisPoints) || other.basisPoints == basisPoints)&&(identical(other.fixedAmount, fixedAmount) || other.fixedAmount == fixedAmount)&&(identical(other.isActive, isActive) || other.isActive == isActive)&&(identical(other.progressionOfferedAt, progressionOfferedAt) || other.progressionOfferedAt == progressionOfferedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,vaultAssetId,mode,currency,basisPoints,fixedAmount,isActive,progressionOfferedAt);

@override
String toString() {
  return 'AllocationRule(meta: $meta, vaultAssetId: $vaultAssetId, mode: $mode, currency: $currency, basisPoints: $basisPoints, fixedAmount: $fixedAmount, isActive: $isActive, progressionOfferedAt: $progressionOfferedAt)';
}


}

/// @nodoc
abstract mixin class $AllocationRuleCopyWith<$Res>  {
  factory $AllocationRuleCopyWith(AllocationRule value, $Res Function(AllocationRule) _then) = _$AllocationRuleCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String vaultAssetId, AllocationMode mode, CurrencyCode currency, int? basisPoints, Money? fixedAmount, bool isActive, DateTime? progressionOfferedAt
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$AllocationRuleCopyWithImpl<$Res>
    implements $AllocationRuleCopyWith<$Res> {
  _$AllocationRuleCopyWithImpl(this._self, this._then);

  final AllocationRule _self;
  final $Res Function(AllocationRule) _then;

/// Create a copy of AllocationRule
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? vaultAssetId = null,Object? mode = null,Object? currency = null,Object? basisPoints = freezed,Object? fixedAmount = freezed,Object? isActive = null,Object? progressionOfferedAt = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,vaultAssetId: null == vaultAssetId ? _self.vaultAssetId : vaultAssetId // ignore: cast_nullable_to_non_nullable
as String,mode: null == mode ? _self.mode : mode // ignore: cast_nullable_to_non_nullable
as AllocationMode,currency: null == currency ? _self.currency : currency // ignore: cast_nullable_to_non_nullable
as CurrencyCode,basisPoints: freezed == basisPoints ? _self.basisPoints : basisPoints // ignore: cast_nullable_to_non_nullable
as int?,fixedAmount: freezed == fixedAmount ? _self.fixedAmount : fixedAmount // ignore: cast_nullable_to_non_nullable
as Money?,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,progressionOfferedAt: freezed == progressionOfferedAt ? _self.progressionOfferedAt : progressionOfferedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}
/// Create a copy of AllocationRule
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [AllocationRule].
extension AllocationRulePatterns on AllocationRule {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _AllocationRule value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _AllocationRule() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _AllocationRule value)  $default,){
final _that = this;
switch (_that) {
case _AllocationRule():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _AllocationRule value)?  $default,){
final _that = this;
switch (_that) {
case _AllocationRule() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String vaultAssetId,  AllocationMode mode,  CurrencyCode currency,  int? basisPoints,  Money? fixedAmount,  bool isActive,  DateTime? progressionOfferedAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _AllocationRule() when $default != null:
return $default(_that.meta,_that.vaultAssetId,_that.mode,_that.currency,_that.basisPoints,_that.fixedAmount,_that.isActive,_that.progressionOfferedAt);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String vaultAssetId,  AllocationMode mode,  CurrencyCode currency,  int? basisPoints,  Money? fixedAmount,  bool isActive,  DateTime? progressionOfferedAt)  $default,) {final _that = this;
switch (_that) {
case _AllocationRule():
return $default(_that.meta,_that.vaultAssetId,_that.mode,_that.currency,_that.basisPoints,_that.fixedAmount,_that.isActive,_that.progressionOfferedAt);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String vaultAssetId,  AllocationMode mode,  CurrencyCode currency,  int? basisPoints,  Money? fixedAmount,  bool isActive,  DateTime? progressionOfferedAt)?  $default,) {final _that = this;
switch (_that) {
case _AllocationRule() when $default != null:
return $default(_that.meta,_that.vaultAssetId,_that.mode,_that.currency,_that.basisPoints,_that.fixedAmount,_that.isActive,_that.progressionOfferedAt);case _:
  return null;

}
}

}

/// @nodoc


class _AllocationRule implements AllocationRule {
  const _AllocationRule({required this.meta, required this.vaultAssetId, required this.mode, required this.currency, this.basisPoints, this.fixedAmount, this.isActive = true, this.progressionOfferedAt});
  

@override final  SyncMeta meta;
@override final  String vaultAssetId;
@override final  AllocationMode mode;
@override final  CurrencyCode currency;
@override final  int? basisPoints;
/// Qat'iy summa — oyiga (masalan, 300 000 so'm).
@override final  Money? fixedAmount;
@override@JsonKey() final  bool isActive;
/// Progressiv rejimda oxirgi «+1 %» taklifi (UTC).
@override final  DateTime? progressionOfferedAt;

/// Create a copy of AllocationRule
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AllocationRuleCopyWith<_AllocationRule> get copyWith => __$AllocationRuleCopyWithImpl<_AllocationRule>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _AllocationRule&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.vaultAssetId, vaultAssetId) || other.vaultAssetId == vaultAssetId)&&(identical(other.mode, mode) || other.mode == mode)&&(identical(other.currency, currency) || other.currency == currency)&&(identical(other.basisPoints, basisPoints) || other.basisPoints == basisPoints)&&(identical(other.fixedAmount, fixedAmount) || other.fixedAmount == fixedAmount)&&(identical(other.isActive, isActive) || other.isActive == isActive)&&(identical(other.progressionOfferedAt, progressionOfferedAt) || other.progressionOfferedAt == progressionOfferedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,vaultAssetId,mode,currency,basisPoints,fixedAmount,isActive,progressionOfferedAt);

@override
String toString() {
  return 'AllocationRule(meta: $meta, vaultAssetId: $vaultAssetId, mode: $mode, currency: $currency, basisPoints: $basisPoints, fixedAmount: $fixedAmount, isActive: $isActive, progressionOfferedAt: $progressionOfferedAt)';
}


}

/// @nodoc
abstract mixin class _$AllocationRuleCopyWith<$Res> implements $AllocationRuleCopyWith<$Res> {
  factory _$AllocationRuleCopyWith(_AllocationRule value, $Res Function(_AllocationRule) _then) = __$AllocationRuleCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String vaultAssetId, AllocationMode mode, CurrencyCode currency, int? basisPoints, Money? fixedAmount, bool isActive, DateTime? progressionOfferedAt
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$AllocationRuleCopyWithImpl<$Res>
    implements _$AllocationRuleCopyWith<$Res> {
  __$AllocationRuleCopyWithImpl(this._self, this._then);

  final _AllocationRule _self;
  final $Res Function(_AllocationRule) _then;

/// Create a copy of AllocationRule
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? vaultAssetId = null,Object? mode = null,Object? currency = null,Object? basisPoints = freezed,Object? fixedAmount = freezed,Object? isActive = null,Object? progressionOfferedAt = freezed,}) {
  return _then(_AllocationRule(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,vaultAssetId: null == vaultAssetId ? _self.vaultAssetId : vaultAssetId // ignore: cast_nullable_to_non_nullable
as String,mode: null == mode ? _self.mode : mode // ignore: cast_nullable_to_non_nullable
as AllocationMode,currency: null == currency ? _self.currency : currency // ignore: cast_nullable_to_non_nullable
as CurrencyCode,basisPoints: freezed == basisPoints ? _self.basisPoints : basisPoints // ignore: cast_nullable_to_non_nullable
as int?,fixedAmount: freezed == fixedAmount ? _self.fixedAmount : fixedAmount // ignore: cast_nullable_to_non_nullable
as Money?,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,progressionOfferedAt: freezed == progressionOfferedAt ? _self.progressionOfferedAt : progressionOfferedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}

/// Create a copy of AllocationRule
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}

// dart format on
