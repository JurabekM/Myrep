// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'prices.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$PriceItem {

 SyncMeta get meta; String get name;/// kg, dona, litr … (foydalanuvchi matni).
 String get unit;/// Oylik iste'mol, mingdan birlarda — indeksdagi og'irlik.
 int get monthlyQuantityMilli; int get sortOrder; bool get isArchived;
/// Create a copy of PriceItem
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$PriceItemCopyWith<PriceItem> get copyWith => _$PriceItemCopyWithImpl<PriceItem>(this as PriceItem, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is PriceItem&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.name, name) || other.name == name)&&(identical(other.unit, unit) || other.unit == unit)&&(identical(other.monthlyQuantityMilli, monthlyQuantityMilli) || other.monthlyQuantityMilli == monthlyQuantityMilli)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder)&&(identical(other.isArchived, isArchived) || other.isArchived == isArchived));
}


@override
int get hashCode => Object.hash(runtimeType,meta,name,unit,monthlyQuantityMilli,sortOrder,isArchived);

@override
String toString() {
  return 'PriceItem(meta: $meta, name: $name, unit: $unit, monthlyQuantityMilli: $monthlyQuantityMilli, sortOrder: $sortOrder, isArchived: $isArchived)';
}


}

/// @nodoc
abstract mixin class $PriceItemCopyWith<$Res>  {
  factory $PriceItemCopyWith(PriceItem value, $Res Function(PriceItem) _then) = _$PriceItemCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String name, String unit, int monthlyQuantityMilli, int sortOrder, bool isArchived
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$PriceItemCopyWithImpl<$Res>
    implements $PriceItemCopyWith<$Res> {
  _$PriceItemCopyWithImpl(this._self, this._then);

  final PriceItem _self;
  final $Res Function(PriceItem) _then;

/// Create a copy of PriceItem
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? name = null,Object? unit = null,Object? monthlyQuantityMilli = null,Object? sortOrder = null,Object? isArchived = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,unit: null == unit ? _self.unit : unit // ignore: cast_nullable_to_non_nullable
as String,monthlyQuantityMilli: null == monthlyQuantityMilli ? _self.monthlyQuantityMilli : monthlyQuantityMilli // ignore: cast_nullable_to_non_nullable
as int,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,isArchived: null == isArchived ? _self.isArchived : isArchived // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}
/// Create a copy of PriceItem
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [PriceItem].
extension PriceItemPatterns on PriceItem {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _PriceItem value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _PriceItem() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _PriceItem value)  $default,){
final _that = this;
switch (_that) {
case _PriceItem():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _PriceItem value)?  $default,){
final _that = this;
switch (_that) {
case _PriceItem() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String name,  String unit,  int monthlyQuantityMilli,  int sortOrder,  bool isArchived)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _PriceItem() when $default != null:
return $default(_that.meta,_that.name,_that.unit,_that.monthlyQuantityMilli,_that.sortOrder,_that.isArchived);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String name,  String unit,  int monthlyQuantityMilli,  int sortOrder,  bool isArchived)  $default,) {final _that = this;
switch (_that) {
case _PriceItem():
return $default(_that.meta,_that.name,_that.unit,_that.monthlyQuantityMilli,_that.sortOrder,_that.isArchived);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String name,  String unit,  int monthlyQuantityMilli,  int sortOrder,  bool isArchived)?  $default,) {final _that = this;
switch (_that) {
case _PriceItem() when $default != null:
return $default(_that.meta,_that.name,_that.unit,_that.monthlyQuantityMilli,_that.sortOrder,_that.isArchived);case _:
  return null;

}
}

}

/// @nodoc


class _PriceItem implements PriceItem {
  const _PriceItem({required this.meta, required this.name, required this.unit, this.monthlyQuantityMilli = 1000, this.sortOrder = 0, this.isArchived = false});
  

@override final  SyncMeta meta;
@override final  String name;
/// kg, dona, litr … (foydalanuvchi matni).
@override final  String unit;
/// Oylik iste'mol, mingdan birlarda — indeksdagi og'irlik.
@override@JsonKey() final  int monthlyQuantityMilli;
@override@JsonKey() final  int sortOrder;
@override@JsonKey() final  bool isArchived;

/// Create a copy of PriceItem
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$PriceItemCopyWith<_PriceItem> get copyWith => __$PriceItemCopyWithImpl<_PriceItem>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _PriceItem&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.name, name) || other.name == name)&&(identical(other.unit, unit) || other.unit == unit)&&(identical(other.monthlyQuantityMilli, monthlyQuantityMilli) || other.monthlyQuantityMilli == monthlyQuantityMilli)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder)&&(identical(other.isArchived, isArchived) || other.isArchived == isArchived));
}


@override
int get hashCode => Object.hash(runtimeType,meta,name,unit,monthlyQuantityMilli,sortOrder,isArchived);

@override
String toString() {
  return 'PriceItem(meta: $meta, name: $name, unit: $unit, monthlyQuantityMilli: $monthlyQuantityMilli, sortOrder: $sortOrder, isArchived: $isArchived)';
}


}

/// @nodoc
abstract mixin class _$PriceItemCopyWith<$Res> implements $PriceItemCopyWith<$Res> {
  factory _$PriceItemCopyWith(_PriceItem value, $Res Function(_PriceItem) _then) = __$PriceItemCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String name, String unit, int monthlyQuantityMilli, int sortOrder, bool isArchived
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$PriceItemCopyWithImpl<$Res>
    implements _$PriceItemCopyWith<$Res> {
  __$PriceItemCopyWithImpl(this._self, this._then);

  final _PriceItem _self;
  final $Res Function(_PriceItem) _then;

/// Create a copy of PriceItem
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? name = null,Object? unit = null,Object? monthlyQuantityMilli = null,Object? sortOrder = null,Object? isArchived = null,}) {
  return _then(_PriceItem(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,unit: null == unit ? _self.unit : unit // ignore: cast_nullable_to_non_nullable
as String,monthlyQuantityMilli: null == monthlyQuantityMilli ? _self.monthlyQuantityMilli : monthlyQuantityMilli // ignore: cast_nullable_to_non_nullable
as int,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,isArchived: null == isArchived ? _self.isArchived : isArchived // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

/// Create a copy of PriceItem
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
mixin _$PricePoint {

 SyncMeta get meta; String get itemId; Money get price; LocalDate get observedOn; String? get place;
/// Create a copy of PricePoint
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$PricePointCopyWith<PricePoint> get copyWith => _$PricePointCopyWithImpl<PricePoint>(this as PricePoint, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is PricePoint&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.itemId, itemId) || other.itemId == itemId)&&(identical(other.price, price) || other.price == price)&&(identical(other.observedOn, observedOn) || other.observedOn == observedOn)&&(identical(other.place, place) || other.place == place));
}


@override
int get hashCode => Object.hash(runtimeType,meta,itemId,price,observedOn,place);

@override
String toString() {
  return 'PricePoint(meta: $meta, itemId: $itemId, price: $price, observedOn: $observedOn, place: $place)';
}


}

/// @nodoc
abstract mixin class $PricePointCopyWith<$Res>  {
  factory $PricePointCopyWith(PricePoint value, $Res Function(PricePoint) _then) = _$PricePointCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String itemId, Money price, LocalDate observedOn, String? place
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$PricePointCopyWithImpl<$Res>
    implements $PricePointCopyWith<$Res> {
  _$PricePointCopyWithImpl(this._self, this._then);

  final PricePoint _self;
  final $Res Function(PricePoint) _then;

/// Create a copy of PricePoint
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? itemId = null,Object? price = null,Object? observedOn = null,Object? place = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,itemId: null == itemId ? _self.itemId : itemId // ignore: cast_nullable_to_non_nullable
as String,price: null == price ? _self.price : price // ignore: cast_nullable_to_non_nullable
as Money,observedOn: null == observedOn ? _self.observedOn : observedOn // ignore: cast_nullable_to_non_nullable
as LocalDate,place: freezed == place ? _self.place : place // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of PricePoint
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [PricePoint].
extension PricePointPatterns on PricePoint {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _PricePoint value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _PricePoint() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _PricePoint value)  $default,){
final _that = this;
switch (_that) {
case _PricePoint():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _PricePoint value)?  $default,){
final _that = this;
switch (_that) {
case _PricePoint() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String itemId,  Money price,  LocalDate observedOn,  String? place)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _PricePoint() when $default != null:
return $default(_that.meta,_that.itemId,_that.price,_that.observedOn,_that.place);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String itemId,  Money price,  LocalDate observedOn,  String? place)  $default,) {final _that = this;
switch (_that) {
case _PricePoint():
return $default(_that.meta,_that.itemId,_that.price,_that.observedOn,_that.place);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String itemId,  Money price,  LocalDate observedOn,  String? place)?  $default,) {final _that = this;
switch (_that) {
case _PricePoint() when $default != null:
return $default(_that.meta,_that.itemId,_that.price,_that.observedOn,_that.place);case _:
  return null;

}
}

}

/// @nodoc


class _PricePoint implements PricePoint {
  const _PricePoint({required this.meta, required this.itemId, required this.price, required this.observedOn, this.place});
  

@override final  SyncMeta meta;
@override final  String itemId;
@override final  Money price;
@override final  LocalDate observedOn;
@override final  String? place;

/// Create a copy of PricePoint
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$PricePointCopyWith<_PricePoint> get copyWith => __$PricePointCopyWithImpl<_PricePoint>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _PricePoint&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.itemId, itemId) || other.itemId == itemId)&&(identical(other.price, price) || other.price == price)&&(identical(other.observedOn, observedOn) || other.observedOn == observedOn)&&(identical(other.place, place) || other.place == place));
}


@override
int get hashCode => Object.hash(runtimeType,meta,itemId,price,observedOn,place);

@override
String toString() {
  return 'PricePoint(meta: $meta, itemId: $itemId, price: $price, observedOn: $observedOn, place: $place)';
}


}

/// @nodoc
abstract mixin class _$PricePointCopyWith<$Res> implements $PricePointCopyWith<$Res> {
  factory _$PricePointCopyWith(_PricePoint value, $Res Function(_PricePoint) _then) = __$PricePointCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String itemId, Money price, LocalDate observedOn, String? place
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$PricePointCopyWithImpl<$Res>
    implements _$PricePointCopyWith<$Res> {
  __$PricePointCopyWithImpl(this._self, this._then);

  final _PricePoint _self;
  final $Res Function(_PricePoint) _then;

/// Create a copy of PricePoint
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? itemId = null,Object? price = null,Object? observedOn = null,Object? place = freezed,}) {
  return _then(_PricePoint(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,itemId: null == itemId ? _self.itemId : itemId // ignore: cast_nullable_to_non_nullable
as String,price: null == price ? _self.price : price // ignore: cast_nullable_to_non_nullable
as Money,observedOn: null == observedOn ? _self.observedOn : observedOn // ignore: cast_nullable_to_non_nullable
as LocalDate,place: freezed == place ? _self.place : place // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of PricePoint
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
