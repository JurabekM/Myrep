// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'subscription.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$Subscription {

 SyncMeta get meta; String get title;/// Bir davr narxi ([cycle] bo'yicha).
 Money get price; SubscriptionCycle get cycle; LocalDate get startedOn; LocalDate? get lastUsedOn; LocalDate? get cancelledOn;
/// Create a copy of Subscription
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$SubscriptionCopyWith<Subscription> get copyWith => _$SubscriptionCopyWithImpl<Subscription>(this as Subscription, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Subscription&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.price, price) || other.price == price)&&(identical(other.cycle, cycle) || other.cycle == cycle)&&(identical(other.startedOn, startedOn) || other.startedOn == startedOn)&&(identical(other.lastUsedOn, lastUsedOn) || other.lastUsedOn == lastUsedOn)&&(identical(other.cancelledOn, cancelledOn) || other.cancelledOn == cancelledOn));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,price,cycle,startedOn,lastUsedOn,cancelledOn);

@override
String toString() {
  return 'Subscription(meta: $meta, title: $title, price: $price, cycle: $cycle, startedOn: $startedOn, lastUsedOn: $lastUsedOn, cancelledOn: $cancelledOn)';
}


}

/// @nodoc
abstract mixin class $SubscriptionCopyWith<$Res>  {
  factory $SubscriptionCopyWith(Subscription value, $Res Function(Subscription) _then) = _$SubscriptionCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, Money price, SubscriptionCycle cycle, LocalDate startedOn, LocalDate? lastUsedOn, LocalDate? cancelledOn
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$SubscriptionCopyWithImpl<$Res>
    implements $SubscriptionCopyWith<$Res> {
  _$SubscriptionCopyWithImpl(this._self, this._then);

  final Subscription _self;
  final $Res Function(Subscription) _then;

/// Create a copy of Subscription
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? price = null,Object? cycle = null,Object? startedOn = null,Object? lastUsedOn = freezed,Object? cancelledOn = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,price: null == price ? _self.price : price // ignore: cast_nullable_to_non_nullable
as Money,cycle: null == cycle ? _self.cycle : cycle // ignore: cast_nullable_to_non_nullable
as SubscriptionCycle,startedOn: null == startedOn ? _self.startedOn : startedOn // ignore: cast_nullable_to_non_nullable
as LocalDate,lastUsedOn: freezed == lastUsedOn ? _self.lastUsedOn : lastUsedOn // ignore: cast_nullable_to_non_nullable
as LocalDate?,cancelledOn: freezed == cancelledOn ? _self.cancelledOn : cancelledOn // ignore: cast_nullable_to_non_nullable
as LocalDate?,
  ));
}
/// Create a copy of Subscription
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Subscription].
extension SubscriptionPatterns on Subscription {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Subscription value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Subscription() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Subscription value)  $default,){
final _that = this;
switch (_that) {
case _Subscription():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Subscription value)?  $default,){
final _that = this;
switch (_that) {
case _Subscription() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money price,  SubscriptionCycle cycle,  LocalDate startedOn,  LocalDate? lastUsedOn,  LocalDate? cancelledOn)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Subscription() when $default != null:
return $default(_that.meta,_that.title,_that.price,_that.cycle,_that.startedOn,_that.lastUsedOn,_that.cancelledOn);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money price,  SubscriptionCycle cycle,  LocalDate startedOn,  LocalDate? lastUsedOn,  LocalDate? cancelledOn)  $default,) {final _that = this;
switch (_that) {
case _Subscription():
return $default(_that.meta,_that.title,_that.price,_that.cycle,_that.startedOn,_that.lastUsedOn,_that.cancelledOn);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  Money price,  SubscriptionCycle cycle,  LocalDate startedOn,  LocalDate? lastUsedOn,  LocalDate? cancelledOn)?  $default,) {final _that = this;
switch (_that) {
case _Subscription() when $default != null:
return $default(_that.meta,_that.title,_that.price,_that.cycle,_that.startedOn,_that.lastUsedOn,_that.cancelledOn);case _:
  return null;

}
}

}

/// @nodoc


class _Subscription extends Subscription {
  const _Subscription({required this.meta, required this.title, required this.price, required this.cycle, required this.startedOn, this.lastUsedOn, this.cancelledOn}): super._();
  

@override final  SyncMeta meta;
@override final  String title;
/// Bir davr narxi ([cycle] bo'yicha).
@override final  Money price;
@override final  SubscriptionCycle cycle;
@override final  LocalDate startedOn;
@override final  LocalDate? lastUsedOn;
@override final  LocalDate? cancelledOn;

/// Create a copy of Subscription
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$SubscriptionCopyWith<_Subscription> get copyWith => __$SubscriptionCopyWithImpl<_Subscription>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Subscription&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.price, price) || other.price == price)&&(identical(other.cycle, cycle) || other.cycle == cycle)&&(identical(other.startedOn, startedOn) || other.startedOn == startedOn)&&(identical(other.lastUsedOn, lastUsedOn) || other.lastUsedOn == lastUsedOn)&&(identical(other.cancelledOn, cancelledOn) || other.cancelledOn == cancelledOn));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,price,cycle,startedOn,lastUsedOn,cancelledOn);

@override
String toString() {
  return 'Subscription(meta: $meta, title: $title, price: $price, cycle: $cycle, startedOn: $startedOn, lastUsedOn: $lastUsedOn, cancelledOn: $cancelledOn)';
}


}

/// @nodoc
abstract mixin class _$SubscriptionCopyWith<$Res> implements $SubscriptionCopyWith<$Res> {
  factory _$SubscriptionCopyWith(_Subscription value, $Res Function(_Subscription) _then) = __$SubscriptionCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, Money price, SubscriptionCycle cycle, LocalDate startedOn, LocalDate? lastUsedOn, LocalDate? cancelledOn
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$SubscriptionCopyWithImpl<$Res>
    implements _$SubscriptionCopyWith<$Res> {
  __$SubscriptionCopyWithImpl(this._self, this._then);

  final _Subscription _self;
  final $Res Function(_Subscription) _then;

/// Create a copy of Subscription
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? price = null,Object? cycle = null,Object? startedOn = null,Object? lastUsedOn = freezed,Object? cancelledOn = freezed,}) {
  return _then(_Subscription(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,price: null == price ? _self.price : price // ignore: cast_nullable_to_non_nullable
as Money,cycle: null == cycle ? _self.cycle : cycle // ignore: cast_nullable_to_non_nullable
as SubscriptionCycle,startedOn: null == startedOn ? _self.startedOn : startedOn // ignore: cast_nullable_to_non_nullable
as LocalDate,lastUsedOn: freezed == lastUsedOn ? _self.lastUsedOn : lastUsedOn // ignore: cast_nullable_to_non_nullable
as LocalDate?,cancelledOn: freezed == cancelledOn ? _self.cancelledOn : cancelledOn // ignore: cast_nullable_to_non_nullable
as LocalDate?,
  ));
}

/// Create a copy of Subscription
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
