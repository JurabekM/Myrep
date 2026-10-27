// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'income.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$Income {

 SyncMeta get meta; Money get amount; IncomeSource get source; PaymentChannel get channel;/// UTC.
 DateTime get receivedAt; String? get memberId;/// «Ter / mol / tavakkal» (ixtiyoriy).
 IncomeSourceType? get sourceType; String? get note;
/// Create a copy of Income
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$IncomeCopyWith<Income> get copyWith => _$IncomeCopyWithImpl<Income>(this as Income, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Income&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.source, source) || other.source == source)&&(identical(other.channel, channel) || other.channel == channel)&&(identical(other.receivedAt, receivedAt) || other.receivedAt == receivedAt)&&(identical(other.memberId, memberId) || other.memberId == memberId)&&(identical(other.sourceType, sourceType) || other.sourceType == sourceType)&&(identical(other.note, note) || other.note == note));
}


@override
int get hashCode => Object.hash(runtimeType,meta,amount,source,channel,receivedAt,memberId,sourceType,note);

@override
String toString() {
  return 'Income(meta: $meta, amount: $amount, source: $source, channel: $channel, receivedAt: $receivedAt, memberId: $memberId, sourceType: $sourceType, note: $note)';
}


}

/// @nodoc
abstract mixin class $IncomeCopyWith<$Res>  {
  factory $IncomeCopyWith(Income value, $Res Function(Income) _then) = _$IncomeCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, Money amount, IncomeSource source, PaymentChannel channel, DateTime receivedAt, String? memberId, IncomeSourceType? sourceType, String? note
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$IncomeCopyWithImpl<$Res>
    implements $IncomeCopyWith<$Res> {
  _$IncomeCopyWithImpl(this._self, this._then);

  final Income _self;
  final $Res Function(Income) _then;

/// Create a copy of Income
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? amount = null,Object? source = null,Object? channel = null,Object? receivedAt = null,Object? memberId = freezed,Object? sourceType = freezed,Object? note = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,source: null == source ? _self.source : source // ignore: cast_nullable_to_non_nullable
as IncomeSource,channel: null == channel ? _self.channel : channel // ignore: cast_nullable_to_non_nullable
as PaymentChannel,receivedAt: null == receivedAt ? _self.receivedAt : receivedAt // ignore: cast_nullable_to_non_nullable
as DateTime,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,sourceType: freezed == sourceType ? _self.sourceType : sourceType // ignore: cast_nullable_to_non_nullable
as IncomeSourceType?,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of Income
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Income].
extension IncomePatterns on Income {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Income value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Income() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Income value)  $default,){
final _that = this;
switch (_that) {
case _Income():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Income value)?  $default,){
final _that = this;
switch (_that) {
case _Income() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  Money amount,  IncomeSource source,  PaymentChannel channel,  DateTime receivedAt,  String? memberId,  IncomeSourceType? sourceType,  String? note)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Income() when $default != null:
return $default(_that.meta,_that.amount,_that.source,_that.channel,_that.receivedAt,_that.memberId,_that.sourceType,_that.note);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  Money amount,  IncomeSource source,  PaymentChannel channel,  DateTime receivedAt,  String? memberId,  IncomeSourceType? sourceType,  String? note)  $default,) {final _that = this;
switch (_that) {
case _Income():
return $default(_that.meta,_that.amount,_that.source,_that.channel,_that.receivedAt,_that.memberId,_that.sourceType,_that.note);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  Money amount,  IncomeSource source,  PaymentChannel channel,  DateTime receivedAt,  String? memberId,  IncomeSourceType? sourceType,  String? note)?  $default,) {final _that = this;
switch (_that) {
case _Income() when $default != null:
return $default(_that.meta,_that.amount,_that.source,_that.channel,_that.receivedAt,_that.memberId,_that.sourceType,_that.note);case _:
  return null;

}
}

}

/// @nodoc


class _Income implements Income {
  const _Income({required this.meta, required this.amount, required this.source, required this.channel, required this.receivedAt, this.memberId, this.sourceType, this.note});
  

@override final  SyncMeta meta;
@override final  Money amount;
@override final  IncomeSource source;
@override final  PaymentChannel channel;
/// UTC.
@override final  DateTime receivedAt;
@override final  String? memberId;
/// «Ter / mol / tavakkal» (ixtiyoriy).
@override final  IncomeSourceType? sourceType;
@override final  String? note;

/// Create a copy of Income
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$IncomeCopyWith<_Income> get copyWith => __$IncomeCopyWithImpl<_Income>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Income&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.source, source) || other.source == source)&&(identical(other.channel, channel) || other.channel == channel)&&(identical(other.receivedAt, receivedAt) || other.receivedAt == receivedAt)&&(identical(other.memberId, memberId) || other.memberId == memberId)&&(identical(other.sourceType, sourceType) || other.sourceType == sourceType)&&(identical(other.note, note) || other.note == note));
}


@override
int get hashCode => Object.hash(runtimeType,meta,amount,source,channel,receivedAt,memberId,sourceType,note);

@override
String toString() {
  return 'Income(meta: $meta, amount: $amount, source: $source, channel: $channel, receivedAt: $receivedAt, memberId: $memberId, sourceType: $sourceType, note: $note)';
}


}

/// @nodoc
abstract mixin class _$IncomeCopyWith<$Res> implements $IncomeCopyWith<$Res> {
  factory _$IncomeCopyWith(_Income value, $Res Function(_Income) _then) = __$IncomeCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, Money amount, IncomeSource source, PaymentChannel channel, DateTime receivedAt, String? memberId, IncomeSourceType? sourceType, String? note
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$IncomeCopyWithImpl<$Res>
    implements _$IncomeCopyWith<$Res> {
  __$IncomeCopyWithImpl(this._self, this._then);

  final _Income _self;
  final $Res Function(_Income) _then;

/// Create a copy of Income
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? amount = null,Object? source = null,Object? channel = null,Object? receivedAt = null,Object? memberId = freezed,Object? sourceType = freezed,Object? note = freezed,}) {
  return _then(_Income(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,source: null == source ? _self.source : source // ignore: cast_nullable_to_non_nullable
as IncomeSource,channel: null == channel ? _self.channel : channel // ignore: cast_nullable_to_non_nullable
as PaymentChannel,receivedAt: null == receivedAt ? _self.receivedAt : receivedAt // ignore: cast_nullable_to_non_nullable
as DateTime,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,sourceType: freezed == sourceType ? _self.sourceType : sourceType // ignore: cast_nullable_to_non_nullable
as IncomeSourceType?,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of Income
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
