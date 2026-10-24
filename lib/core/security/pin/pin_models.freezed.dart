// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'pin_models.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$PinRecord {

 int get version; String get algorithm; int get iterations;/// base64
 String get salt;/// base64
 String get hash;
/// Create a copy of PinRecord
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$PinRecordCopyWith<PinRecord> get copyWith => _$PinRecordCopyWithImpl<PinRecord>(this as PinRecord, _$identity);

  /// Serializes this PinRecord to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is PinRecord&&(identical(other.version, version) || other.version == version)&&(identical(other.algorithm, algorithm) || other.algorithm == algorithm)&&(identical(other.iterations, iterations) || other.iterations == iterations)&&(identical(other.salt, salt) || other.salt == salt)&&(identical(other.hash, hash) || other.hash == hash));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,version,algorithm,iterations,salt,hash);

@override
String toString() {
  return 'PinRecord(version: $version, algorithm: $algorithm, iterations: $iterations, salt: $salt, hash: $hash)';
}


}

/// @nodoc
abstract mixin class $PinRecordCopyWith<$Res>  {
  factory $PinRecordCopyWith(PinRecord value, $Res Function(PinRecord) _then) = _$PinRecordCopyWithImpl;
@useResult
$Res call({
 int version, String algorithm, int iterations, String salt, String hash
});




}
/// @nodoc
class _$PinRecordCopyWithImpl<$Res>
    implements $PinRecordCopyWith<$Res> {
  _$PinRecordCopyWithImpl(this._self, this._then);

  final PinRecord _self;
  final $Res Function(PinRecord) _then;

/// Create a copy of PinRecord
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? version = null,Object? algorithm = null,Object? iterations = null,Object? salt = null,Object? hash = null,}) {
  return _then(_self.copyWith(
version: null == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as int,algorithm: null == algorithm ? _self.algorithm : algorithm // ignore: cast_nullable_to_non_nullable
as String,iterations: null == iterations ? _self.iterations : iterations // ignore: cast_nullable_to_non_nullable
as int,salt: null == salt ? _self.salt : salt // ignore: cast_nullable_to_non_nullable
as String,hash: null == hash ? _self.hash : hash // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

}


/// Adds pattern-matching-related methods to [PinRecord].
extension PinRecordPatterns on PinRecord {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _PinRecord value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _PinRecord() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _PinRecord value)  $default,){
final _that = this;
switch (_that) {
case _PinRecord():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _PinRecord value)?  $default,){
final _that = this;
switch (_that) {
case _PinRecord() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( int version,  String algorithm,  int iterations,  String salt,  String hash)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _PinRecord() when $default != null:
return $default(_that.version,_that.algorithm,_that.iterations,_that.salt,_that.hash);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( int version,  String algorithm,  int iterations,  String salt,  String hash)  $default,) {final _that = this;
switch (_that) {
case _PinRecord():
return $default(_that.version,_that.algorithm,_that.iterations,_that.salt,_that.hash);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( int version,  String algorithm,  int iterations,  String salt,  String hash)?  $default,) {final _that = this;
switch (_that) {
case _PinRecord() when $default != null:
return $default(_that.version,_that.algorithm,_that.iterations,_that.salt,_that.hash);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _PinRecord implements PinRecord {
  const _PinRecord({required this.version, required this.algorithm, required this.iterations, required this.salt, required this.hash});
  factory _PinRecord.fromJson(Map<String, dynamic> json) => _$PinRecordFromJson(json);

@override final  int version;
@override final  String algorithm;
@override final  int iterations;
/// base64
@override final  String salt;
/// base64
@override final  String hash;

/// Create a copy of PinRecord
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$PinRecordCopyWith<_PinRecord> get copyWith => __$PinRecordCopyWithImpl<_PinRecord>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$PinRecordToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _PinRecord&&(identical(other.version, version) || other.version == version)&&(identical(other.algorithm, algorithm) || other.algorithm == algorithm)&&(identical(other.iterations, iterations) || other.iterations == iterations)&&(identical(other.salt, salt) || other.salt == salt)&&(identical(other.hash, hash) || other.hash == hash));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,version,algorithm,iterations,salt,hash);

@override
String toString() {
  return 'PinRecord(version: $version, algorithm: $algorithm, iterations: $iterations, salt: $salt, hash: $hash)';
}


}

/// @nodoc
abstract mixin class _$PinRecordCopyWith<$Res> implements $PinRecordCopyWith<$Res> {
  factory _$PinRecordCopyWith(_PinRecord value, $Res Function(_PinRecord) _then) = __$PinRecordCopyWithImpl;
@override @useResult
$Res call({
 int version, String algorithm, int iterations, String salt, String hash
});




}
/// @nodoc
class __$PinRecordCopyWithImpl<$Res>
    implements _$PinRecordCopyWith<$Res> {
  __$PinRecordCopyWithImpl(this._self, this._then);

  final _PinRecord _self;
  final $Res Function(_PinRecord) _then;

/// Create a copy of PinRecord
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? version = null,Object? algorithm = null,Object? iterations = null,Object? salt = null,Object? hash = null,}) {
  return _then(_PinRecord(
version: null == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as int,algorithm: null == algorithm ? _self.algorithm : algorithm // ignore: cast_nullable_to_non_nullable
as String,iterations: null == iterations ? _self.iterations : iterations // ignore: cast_nullable_to_non_nullable
as int,salt: null == salt ? _self.salt : salt // ignore: cast_nullable_to_non_nullable
as String,hash: null == hash ? _self.hash : hash // ignore: cast_nullable_to_non_nullable
as String,
  ));
}


}


/// @nodoc
mixin _$LockoutState {

 int get failedAttempts;/// Kutish boshlangan payt (UTC). Soat orqaga surilganini aniqlash uchun.
 DateTime? get lockStartedAt;/// Kutish tugaydigan payt (UTC).
 DateTime? get lockedUntil;
/// Create a copy of LockoutState
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$LockoutStateCopyWith<LockoutState> get copyWith => _$LockoutStateCopyWithImpl<LockoutState>(this as LockoutState, _$identity);

  /// Serializes this LockoutState to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is LockoutState&&(identical(other.failedAttempts, failedAttempts) || other.failedAttempts == failedAttempts)&&(identical(other.lockStartedAt, lockStartedAt) || other.lockStartedAt == lockStartedAt)&&(identical(other.lockedUntil, lockedUntil) || other.lockedUntil == lockedUntil));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,failedAttempts,lockStartedAt,lockedUntil);

@override
String toString() {
  return 'LockoutState(failedAttempts: $failedAttempts, lockStartedAt: $lockStartedAt, lockedUntil: $lockedUntil)';
}


}

/// @nodoc
abstract mixin class $LockoutStateCopyWith<$Res>  {
  factory $LockoutStateCopyWith(LockoutState value, $Res Function(LockoutState) _then) = _$LockoutStateCopyWithImpl;
@useResult
$Res call({
 int failedAttempts, DateTime? lockStartedAt, DateTime? lockedUntil
});




}
/// @nodoc
class _$LockoutStateCopyWithImpl<$Res>
    implements $LockoutStateCopyWith<$Res> {
  _$LockoutStateCopyWithImpl(this._self, this._then);

  final LockoutState _self;
  final $Res Function(LockoutState) _then;

/// Create a copy of LockoutState
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? failedAttempts = null,Object? lockStartedAt = freezed,Object? lockedUntil = freezed,}) {
  return _then(_self.copyWith(
failedAttempts: null == failedAttempts ? _self.failedAttempts : failedAttempts // ignore: cast_nullable_to_non_nullable
as int,lockStartedAt: freezed == lockStartedAt ? _self.lockStartedAt : lockStartedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,lockedUntil: freezed == lockedUntil ? _self.lockedUntil : lockedUntil // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}

}


/// Adds pattern-matching-related methods to [LockoutState].
extension LockoutStatePatterns on LockoutState {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _LockoutState value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _LockoutState() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _LockoutState value)  $default,){
final _that = this;
switch (_that) {
case _LockoutState():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _LockoutState value)?  $default,){
final _that = this;
switch (_that) {
case _LockoutState() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( int failedAttempts,  DateTime? lockStartedAt,  DateTime? lockedUntil)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _LockoutState() when $default != null:
return $default(_that.failedAttempts,_that.lockStartedAt,_that.lockedUntil);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( int failedAttempts,  DateTime? lockStartedAt,  DateTime? lockedUntil)  $default,) {final _that = this;
switch (_that) {
case _LockoutState():
return $default(_that.failedAttempts,_that.lockStartedAt,_that.lockedUntil);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( int failedAttempts,  DateTime? lockStartedAt,  DateTime? lockedUntil)?  $default,) {final _that = this;
switch (_that) {
case _LockoutState() when $default != null:
return $default(_that.failedAttempts,_that.lockStartedAt,_that.lockedUntil);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _LockoutState implements LockoutState {
  const _LockoutState({this.failedAttempts = 0, this.lockStartedAt, this.lockedUntil});
  factory _LockoutState.fromJson(Map<String, dynamic> json) => _$LockoutStateFromJson(json);

@override@JsonKey() final  int failedAttempts;
/// Kutish boshlangan payt (UTC). Soat orqaga surilganini aniqlash uchun.
@override final  DateTime? lockStartedAt;
/// Kutish tugaydigan payt (UTC).
@override final  DateTime? lockedUntil;

/// Create a copy of LockoutState
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$LockoutStateCopyWith<_LockoutState> get copyWith => __$LockoutStateCopyWithImpl<_LockoutState>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$LockoutStateToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _LockoutState&&(identical(other.failedAttempts, failedAttempts) || other.failedAttempts == failedAttempts)&&(identical(other.lockStartedAt, lockStartedAt) || other.lockStartedAt == lockStartedAt)&&(identical(other.lockedUntil, lockedUntil) || other.lockedUntil == lockedUntil));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,failedAttempts,lockStartedAt,lockedUntil);

@override
String toString() {
  return 'LockoutState(failedAttempts: $failedAttempts, lockStartedAt: $lockStartedAt, lockedUntil: $lockedUntil)';
}


}

/// @nodoc
abstract mixin class _$LockoutStateCopyWith<$Res> implements $LockoutStateCopyWith<$Res> {
  factory _$LockoutStateCopyWith(_LockoutState value, $Res Function(_LockoutState) _then) = __$LockoutStateCopyWithImpl;
@override @useResult
$Res call({
 int failedAttempts, DateTime? lockStartedAt, DateTime? lockedUntil
});




}
/// @nodoc
class __$LockoutStateCopyWithImpl<$Res>
    implements _$LockoutStateCopyWith<$Res> {
  __$LockoutStateCopyWithImpl(this._self, this._then);

  final _LockoutState _self;
  final $Res Function(_LockoutState) _then;

/// Create a copy of LockoutState
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? failedAttempts = null,Object? lockStartedAt = freezed,Object? lockedUntil = freezed,}) {
  return _then(_LockoutState(
failedAttempts: null == failedAttempts ? _self.failedAttempts : failedAttempts // ignore: cast_nullable_to_non_nullable
as int,lockStartedAt: freezed == lockStartedAt ? _self.lockStartedAt : lockStartedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,lockedUntil: freezed == lockedUntil ? _self.lockedUntil : lockedUntil // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}


}

// dart format on
