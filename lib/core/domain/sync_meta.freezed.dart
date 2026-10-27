// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'sync_meta.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$SyncMeta {

/// UUIDv7.
 String get id; String get householdId;/// UTC.
 DateTime get createdAt;/// UTC.
 DateTime get updatedAt;/// Soft delete (UTC). `null` — faol yozuv.
 DateTime? get deletedAt;/// Optimistik versiya: har o'zgarishda +1.
 int get version;
/// Create a copy of SyncMeta
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<SyncMeta> get copyWith => _$SyncMetaCopyWithImpl<SyncMeta>(this as SyncMeta, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is SyncMeta&&(identical(other.id, id) || other.id == id)&&(identical(other.householdId, householdId) || other.householdId == householdId)&&(identical(other.createdAt, createdAt) || other.createdAt == createdAt)&&(identical(other.updatedAt, updatedAt) || other.updatedAt == updatedAt)&&(identical(other.deletedAt, deletedAt) || other.deletedAt == deletedAt)&&(identical(other.version, version) || other.version == version));
}


@override
int get hashCode => Object.hash(runtimeType,id,householdId,createdAt,updatedAt,deletedAt,version);

@override
String toString() {
  return 'SyncMeta(id: $id, householdId: $householdId, createdAt: $createdAt, updatedAt: $updatedAt, deletedAt: $deletedAt, version: $version)';
}


}

/// @nodoc
abstract mixin class $SyncMetaCopyWith<$Res>  {
  factory $SyncMetaCopyWith(SyncMeta value, $Res Function(SyncMeta) _then) = _$SyncMetaCopyWithImpl;
@useResult
$Res call({
 String id, String householdId, DateTime createdAt, DateTime updatedAt, DateTime? deletedAt, int version
});




}
/// @nodoc
class _$SyncMetaCopyWithImpl<$Res>
    implements $SyncMetaCopyWith<$Res> {
  _$SyncMetaCopyWithImpl(this._self, this._then);

  final SyncMeta _self;
  final $Res Function(SyncMeta) _then;

/// Create a copy of SyncMeta
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? householdId = null,Object? createdAt = null,Object? updatedAt = null,Object? deletedAt = freezed,Object? version = null,}) {
  return _then(_self.copyWith(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,householdId: null == householdId ? _self.householdId : householdId // ignore: cast_nullable_to_non_nullable
as String,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,updatedAt: null == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as DateTime,deletedAt: freezed == deletedAt ? _self.deletedAt : deletedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,version: null == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

}


/// Adds pattern-matching-related methods to [SyncMeta].
extension SyncMetaPatterns on SyncMeta {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _SyncMeta value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _SyncMeta() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _SyncMeta value)  $default,){
final _that = this;
switch (_that) {
case _SyncMeta():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _SyncMeta value)?  $default,){
final _that = this;
switch (_that) {
case _SyncMeta() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String householdId,  DateTime createdAt,  DateTime updatedAt,  DateTime? deletedAt,  int version)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _SyncMeta() when $default != null:
return $default(_that.id,_that.householdId,_that.createdAt,_that.updatedAt,_that.deletedAt,_that.version);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String householdId,  DateTime createdAt,  DateTime updatedAt,  DateTime? deletedAt,  int version)  $default,) {final _that = this;
switch (_that) {
case _SyncMeta():
return $default(_that.id,_that.householdId,_that.createdAt,_that.updatedAt,_that.deletedAt,_that.version);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String householdId,  DateTime createdAt,  DateTime updatedAt,  DateTime? deletedAt,  int version)?  $default,) {final _that = this;
switch (_that) {
case _SyncMeta() when $default != null:
return $default(_that.id,_that.householdId,_that.createdAt,_that.updatedAt,_that.deletedAt,_that.version);case _:
  return null;

}
}

}

/// @nodoc


class _SyncMeta extends SyncMeta {
  const _SyncMeta({required this.id, required this.householdId, required this.createdAt, required this.updatedAt, this.deletedAt, this.version = 1}): super._();
  

/// UUIDv7.
@override final  String id;
@override final  String householdId;
/// UTC.
@override final  DateTime createdAt;
/// UTC.
@override final  DateTime updatedAt;
/// Soft delete (UTC). `null` — faol yozuv.
@override final  DateTime? deletedAt;
/// Optimistik versiya: har o'zgarishda +1.
@override@JsonKey() final  int version;

/// Create a copy of SyncMeta
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$SyncMetaCopyWith<_SyncMeta> get copyWith => __$SyncMetaCopyWithImpl<_SyncMeta>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _SyncMeta&&(identical(other.id, id) || other.id == id)&&(identical(other.householdId, householdId) || other.householdId == householdId)&&(identical(other.createdAt, createdAt) || other.createdAt == createdAt)&&(identical(other.updatedAt, updatedAt) || other.updatedAt == updatedAt)&&(identical(other.deletedAt, deletedAt) || other.deletedAt == deletedAt)&&(identical(other.version, version) || other.version == version));
}


@override
int get hashCode => Object.hash(runtimeType,id,householdId,createdAt,updatedAt,deletedAt,version);

@override
String toString() {
  return 'SyncMeta(id: $id, householdId: $householdId, createdAt: $createdAt, updatedAt: $updatedAt, deletedAt: $deletedAt, version: $version)';
}


}

/// @nodoc
abstract mixin class _$SyncMetaCopyWith<$Res> implements $SyncMetaCopyWith<$Res> {
  factory _$SyncMetaCopyWith(_SyncMeta value, $Res Function(_SyncMeta) _then) = __$SyncMetaCopyWithImpl;
@override @useResult
$Res call({
 String id, String householdId, DateTime createdAt, DateTime updatedAt, DateTime? deletedAt, int version
});




}
/// @nodoc
class __$SyncMetaCopyWithImpl<$Res>
    implements _$SyncMetaCopyWith<$Res> {
  __$SyncMetaCopyWithImpl(this._self, this._then);

  final _SyncMeta _self;
  final $Res Function(_SyncMeta) _then;

/// Create a copy of SyncMeta
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? householdId = null,Object? createdAt = null,Object? updatedAt = null,Object? deletedAt = freezed,Object? version = null,}) {
  return _then(_SyncMeta(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,householdId: null == householdId ? _self.householdId : householdId // ignore: cast_nullable_to_non_nullable
as String,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,updatedAt: null == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as DateTime,deletedAt: freezed == deletedAt ? _self.deletedAt : deletedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,version: null == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as int,
  ));
}


}

// dart format on
