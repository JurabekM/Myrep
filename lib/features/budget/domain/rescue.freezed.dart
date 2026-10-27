// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'rescue.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$SavingsRescue {

 SyncMeta get meta; RescueKind get kind;/// Obuna uchun — oylik ekvivalent; konvert uchun — qoldiq;
/// o'tkazish uchun — o'tkazilgan summa.
 Money get amount; LocalDate get occurredOn; String? get sourceId;
/// Create a copy of SavingsRescue
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$SavingsRescueCopyWith<SavingsRescue> get copyWith => _$SavingsRescueCopyWithImpl<SavingsRescue>(this as SavingsRescue, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is SavingsRescue&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.occurredOn, occurredOn) || other.occurredOn == occurredOn)&&(identical(other.sourceId, sourceId) || other.sourceId == sourceId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,kind,amount,occurredOn,sourceId);

@override
String toString() {
  return 'SavingsRescue(meta: $meta, kind: $kind, amount: $amount, occurredOn: $occurredOn, sourceId: $sourceId)';
}


}

/// @nodoc
abstract mixin class $SavingsRescueCopyWith<$Res>  {
  factory $SavingsRescueCopyWith(SavingsRescue value, $Res Function(SavingsRescue) _then) = _$SavingsRescueCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, RescueKind kind, Money amount, LocalDate occurredOn, String? sourceId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$SavingsRescueCopyWithImpl<$Res>
    implements $SavingsRescueCopyWith<$Res> {
  _$SavingsRescueCopyWithImpl(this._self, this._then);

  final SavingsRescue _self;
  final $Res Function(SavingsRescue) _then;

/// Create a copy of SavingsRescue
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? kind = null,Object? amount = null,Object? occurredOn = null,Object? sourceId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as RescueKind,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,occurredOn: null == occurredOn ? _self.occurredOn : occurredOn // ignore: cast_nullable_to_non_nullable
as LocalDate,sourceId: freezed == sourceId ? _self.sourceId : sourceId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of SavingsRescue
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [SavingsRescue].
extension SavingsRescuePatterns on SavingsRescue {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _SavingsRescue value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _SavingsRescue() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _SavingsRescue value)  $default,){
final _that = this;
switch (_that) {
case _SavingsRescue():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _SavingsRescue value)?  $default,){
final _that = this;
switch (_that) {
case _SavingsRescue() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  RescueKind kind,  Money amount,  LocalDate occurredOn,  String? sourceId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _SavingsRescue() when $default != null:
return $default(_that.meta,_that.kind,_that.amount,_that.occurredOn,_that.sourceId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  RescueKind kind,  Money amount,  LocalDate occurredOn,  String? sourceId)  $default,) {final _that = this;
switch (_that) {
case _SavingsRescue():
return $default(_that.meta,_that.kind,_that.amount,_that.occurredOn,_that.sourceId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  RescueKind kind,  Money amount,  LocalDate occurredOn,  String? sourceId)?  $default,) {final _that = this;
switch (_that) {
case _SavingsRescue() when $default != null:
return $default(_that.meta,_that.kind,_that.amount,_that.occurredOn,_that.sourceId);case _:
  return null;

}
}

}

/// @nodoc


class _SavingsRescue implements SavingsRescue {
  const _SavingsRescue({required this.meta, required this.kind, required this.amount, required this.occurredOn, this.sourceId});
  

@override final  SyncMeta meta;
@override final  RescueKind kind;
/// Obuna uchun — oylik ekvivalent; konvert uchun — qoldiq;
/// o'tkazish uchun — o'tkazilgan summa.
@override final  Money amount;
@override final  LocalDate occurredOn;
@override final  String? sourceId;

/// Create a copy of SavingsRescue
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$SavingsRescueCopyWith<_SavingsRescue> get copyWith => __$SavingsRescueCopyWithImpl<_SavingsRescue>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _SavingsRescue&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.occurredOn, occurredOn) || other.occurredOn == occurredOn)&&(identical(other.sourceId, sourceId) || other.sourceId == sourceId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,kind,amount,occurredOn,sourceId);

@override
String toString() {
  return 'SavingsRescue(meta: $meta, kind: $kind, amount: $amount, occurredOn: $occurredOn, sourceId: $sourceId)';
}


}

/// @nodoc
abstract mixin class _$SavingsRescueCopyWith<$Res> implements $SavingsRescueCopyWith<$Res> {
  factory _$SavingsRescueCopyWith(_SavingsRescue value, $Res Function(_SavingsRescue) _then) = __$SavingsRescueCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, RescueKind kind, Money amount, LocalDate occurredOn, String? sourceId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$SavingsRescueCopyWithImpl<$Res>
    implements _$SavingsRescueCopyWith<$Res> {
  __$SavingsRescueCopyWithImpl(this._self, this._then);

  final _SavingsRescue _self;
  final $Res Function(_SavingsRescue) _then;

/// Create a copy of SavingsRescue
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? kind = null,Object? amount = null,Object? occurredOn = null,Object? sourceId = freezed,}) {
  return _then(_SavingsRescue(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as RescueKind,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,occurredOn: null == occurredOn ? _self.occurredOn : occurredOn // ignore: cast_nullable_to_non_nullable
as LocalDate,sourceId: freezed == sourceId ? _self.sourceId : sourceId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of SavingsRescue
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
