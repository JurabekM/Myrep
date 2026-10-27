// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'expense.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$Category {

 SyncMeta get meta;/// Standart kategoriya kaliti (nomi ARB'dan); foydalanuvchinikida `null`.
 CategoryKey? get systemKey;/// Foydalanuvchi bergan nom.
 String? get name; Necessity? get defaultNecessity; int get sortOrder; bool get isArchived;
/// Create a copy of Category
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CategoryCopyWith<Category> get copyWith => _$CategoryCopyWithImpl<Category>(this as Category, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Category&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.systemKey, systemKey) || other.systemKey == systemKey)&&(identical(other.name, name) || other.name == name)&&(identical(other.defaultNecessity, defaultNecessity) || other.defaultNecessity == defaultNecessity)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder)&&(identical(other.isArchived, isArchived) || other.isArchived == isArchived));
}


@override
int get hashCode => Object.hash(runtimeType,meta,systemKey,name,defaultNecessity,sortOrder,isArchived);

@override
String toString() {
  return 'Category(meta: $meta, systemKey: $systemKey, name: $name, defaultNecessity: $defaultNecessity, sortOrder: $sortOrder, isArchived: $isArchived)';
}


}

/// @nodoc
abstract mixin class $CategoryCopyWith<$Res>  {
  factory $CategoryCopyWith(Category value, $Res Function(Category) _then) = _$CategoryCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, CategoryKey? systemKey, String? name, Necessity? defaultNecessity, int sortOrder, bool isArchived
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$CategoryCopyWithImpl<$Res>
    implements $CategoryCopyWith<$Res> {
  _$CategoryCopyWithImpl(this._self, this._then);

  final Category _self;
  final $Res Function(Category) _then;

/// Create a copy of Category
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? systemKey = freezed,Object? name = freezed,Object? defaultNecessity = freezed,Object? sortOrder = null,Object? isArchived = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,systemKey: freezed == systemKey ? _self.systemKey : systemKey // ignore: cast_nullable_to_non_nullable
as CategoryKey?,name: freezed == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String?,defaultNecessity: freezed == defaultNecessity ? _self.defaultNecessity : defaultNecessity // ignore: cast_nullable_to_non_nullable
as Necessity?,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,isArchived: null == isArchived ? _self.isArchived : isArchived // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}
/// Create a copy of Category
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Category].
extension CategoryPatterns on Category {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Category value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Category() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Category value)  $default,){
final _that = this;
switch (_that) {
case _Category():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Category value)?  $default,){
final _that = this;
switch (_that) {
case _Category() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  CategoryKey? systemKey,  String? name,  Necessity? defaultNecessity,  int sortOrder,  bool isArchived)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Category() when $default != null:
return $default(_that.meta,_that.systemKey,_that.name,_that.defaultNecessity,_that.sortOrder,_that.isArchived);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  CategoryKey? systemKey,  String? name,  Necessity? defaultNecessity,  int sortOrder,  bool isArchived)  $default,) {final _that = this;
switch (_that) {
case _Category():
return $default(_that.meta,_that.systemKey,_that.name,_that.defaultNecessity,_that.sortOrder,_that.isArchived);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  CategoryKey? systemKey,  String? name,  Necessity? defaultNecessity,  int sortOrder,  bool isArchived)?  $default,) {final _that = this;
switch (_that) {
case _Category() when $default != null:
return $default(_that.meta,_that.systemKey,_that.name,_that.defaultNecessity,_that.sortOrder,_that.isArchived);case _:
  return null;

}
}

}

/// @nodoc


class _Category implements Category {
  const _Category({required this.meta, this.systemKey, this.name, this.defaultNecessity, this.sortOrder = 0, this.isArchived = false});
  

@override final  SyncMeta meta;
/// Standart kategoriya kaliti (nomi ARB'dan); foydalanuvchinikida `null`.
@override final  CategoryKey? systemKey;
/// Foydalanuvchi bergan nom.
@override final  String? name;
@override final  Necessity? defaultNecessity;
@override@JsonKey() final  int sortOrder;
@override@JsonKey() final  bool isArchived;

/// Create a copy of Category
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CategoryCopyWith<_Category> get copyWith => __$CategoryCopyWithImpl<_Category>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Category&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.systemKey, systemKey) || other.systemKey == systemKey)&&(identical(other.name, name) || other.name == name)&&(identical(other.defaultNecessity, defaultNecessity) || other.defaultNecessity == defaultNecessity)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder)&&(identical(other.isArchived, isArchived) || other.isArchived == isArchived));
}


@override
int get hashCode => Object.hash(runtimeType,meta,systemKey,name,defaultNecessity,sortOrder,isArchived);

@override
String toString() {
  return 'Category(meta: $meta, systemKey: $systemKey, name: $name, defaultNecessity: $defaultNecessity, sortOrder: $sortOrder, isArchived: $isArchived)';
}


}

/// @nodoc
abstract mixin class _$CategoryCopyWith<$Res> implements $CategoryCopyWith<$Res> {
  factory _$CategoryCopyWith(_Category value, $Res Function(_Category) _then) = __$CategoryCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, CategoryKey? systemKey, String? name, Necessity? defaultNecessity, int sortOrder, bool isArchived
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$CategoryCopyWithImpl<$Res>
    implements _$CategoryCopyWith<$Res> {
  __$CategoryCopyWithImpl(this._self, this._then);

  final _Category _self;
  final $Res Function(_Category) _then;

/// Create a copy of Category
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? systemKey = freezed,Object? name = freezed,Object? defaultNecessity = freezed,Object? sortOrder = null,Object? isArchived = null,}) {
  return _then(_Category(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,systemKey: freezed == systemKey ? _self.systemKey : systemKey // ignore: cast_nullable_to_non_nullable
as CategoryKey?,name: freezed == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String?,defaultNecessity: freezed == defaultNecessity ? _self.defaultNecessity : defaultNecessity // ignore: cast_nullable_to_non_nullable
as Necessity?,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,isArchived: null == isArchived ? _self.isArchived : isArchived // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

/// Create a copy of Category
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
mixin _$Expense {

 SyncMeta get meta; Money get amount; String get categoryId; PaymentChannel get channel;/// UTC.
 DateTime get spentAt; String? get memberId;/// MVP-2; MVP-1 da so'ralmaydi.
 Necessity? get necessity; String? get envelopeId; bool get isGift; bool get isOstentation; bool get fundedByDebt; String? get note;/// Kuzatiladigan odat (SPEC 2B.9).
 String? get habitId;
/// Create a copy of Expense
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ExpenseCopyWith<Expense> get copyWith => _$ExpenseCopyWithImpl<Expense>(this as Expense, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Expense&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.categoryId, categoryId) || other.categoryId == categoryId)&&(identical(other.channel, channel) || other.channel == channel)&&(identical(other.spentAt, spentAt) || other.spentAt == spentAt)&&(identical(other.memberId, memberId) || other.memberId == memberId)&&(identical(other.necessity, necessity) || other.necessity == necessity)&&(identical(other.envelopeId, envelopeId) || other.envelopeId == envelopeId)&&(identical(other.isGift, isGift) || other.isGift == isGift)&&(identical(other.isOstentation, isOstentation) || other.isOstentation == isOstentation)&&(identical(other.fundedByDebt, fundedByDebt) || other.fundedByDebt == fundedByDebt)&&(identical(other.note, note) || other.note == note)&&(identical(other.habitId, habitId) || other.habitId == habitId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,amount,categoryId,channel,spentAt,memberId,necessity,envelopeId,isGift,isOstentation,fundedByDebt,note,habitId);

@override
String toString() {
  return 'Expense(meta: $meta, amount: $amount, categoryId: $categoryId, channel: $channel, spentAt: $spentAt, memberId: $memberId, necessity: $necessity, envelopeId: $envelopeId, isGift: $isGift, isOstentation: $isOstentation, fundedByDebt: $fundedByDebt, note: $note, habitId: $habitId)';
}


}

/// @nodoc
abstract mixin class $ExpenseCopyWith<$Res>  {
  factory $ExpenseCopyWith(Expense value, $Res Function(Expense) _then) = _$ExpenseCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, Money amount, String categoryId, PaymentChannel channel, DateTime spentAt, String? memberId, Necessity? necessity, String? envelopeId, bool isGift, bool isOstentation, bool fundedByDebt, String? note, String? habitId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$ExpenseCopyWithImpl<$Res>
    implements $ExpenseCopyWith<$Res> {
  _$ExpenseCopyWithImpl(this._self, this._then);

  final Expense _self;
  final $Res Function(Expense) _then;

/// Create a copy of Expense
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? amount = null,Object? categoryId = null,Object? channel = null,Object? spentAt = null,Object? memberId = freezed,Object? necessity = freezed,Object? envelopeId = freezed,Object? isGift = null,Object? isOstentation = null,Object? fundedByDebt = null,Object? note = freezed,Object? habitId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,categoryId: null == categoryId ? _self.categoryId : categoryId // ignore: cast_nullable_to_non_nullable
as String,channel: null == channel ? _self.channel : channel // ignore: cast_nullable_to_non_nullable
as PaymentChannel,spentAt: null == spentAt ? _self.spentAt : spentAt // ignore: cast_nullable_to_non_nullable
as DateTime,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,necessity: freezed == necessity ? _self.necessity : necessity // ignore: cast_nullable_to_non_nullable
as Necessity?,envelopeId: freezed == envelopeId ? _self.envelopeId : envelopeId // ignore: cast_nullable_to_non_nullable
as String?,isGift: null == isGift ? _self.isGift : isGift // ignore: cast_nullable_to_non_nullable
as bool,isOstentation: null == isOstentation ? _self.isOstentation : isOstentation // ignore: cast_nullable_to_non_nullable
as bool,fundedByDebt: null == fundedByDebt ? _self.fundedByDebt : fundedByDebt // ignore: cast_nullable_to_non_nullable
as bool,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,habitId: freezed == habitId ? _self.habitId : habitId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of Expense
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Expense].
extension ExpensePatterns on Expense {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Expense value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Expense() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Expense value)  $default,){
final _that = this;
switch (_that) {
case _Expense():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Expense value)?  $default,){
final _that = this;
switch (_that) {
case _Expense() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  Money amount,  String categoryId,  PaymentChannel channel,  DateTime spentAt,  String? memberId,  Necessity? necessity,  String? envelopeId,  bool isGift,  bool isOstentation,  bool fundedByDebt,  String? note,  String? habitId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Expense() when $default != null:
return $default(_that.meta,_that.amount,_that.categoryId,_that.channel,_that.spentAt,_that.memberId,_that.necessity,_that.envelopeId,_that.isGift,_that.isOstentation,_that.fundedByDebt,_that.note,_that.habitId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  Money amount,  String categoryId,  PaymentChannel channel,  DateTime spentAt,  String? memberId,  Necessity? necessity,  String? envelopeId,  bool isGift,  bool isOstentation,  bool fundedByDebt,  String? note,  String? habitId)  $default,) {final _that = this;
switch (_that) {
case _Expense():
return $default(_that.meta,_that.amount,_that.categoryId,_that.channel,_that.spentAt,_that.memberId,_that.necessity,_that.envelopeId,_that.isGift,_that.isOstentation,_that.fundedByDebt,_that.note,_that.habitId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  Money amount,  String categoryId,  PaymentChannel channel,  DateTime spentAt,  String? memberId,  Necessity? necessity,  String? envelopeId,  bool isGift,  bool isOstentation,  bool fundedByDebt,  String? note,  String? habitId)?  $default,) {final _that = this;
switch (_that) {
case _Expense() when $default != null:
return $default(_that.meta,_that.amount,_that.categoryId,_that.channel,_that.spentAt,_that.memberId,_that.necessity,_that.envelopeId,_that.isGift,_that.isOstentation,_that.fundedByDebt,_that.note,_that.habitId);case _:
  return null;

}
}

}

/// @nodoc


class _Expense implements Expense {
  const _Expense({required this.meta, required this.amount, required this.categoryId, required this.channel, required this.spentAt, this.memberId, this.necessity, this.envelopeId, this.isGift = false, this.isOstentation = false, this.fundedByDebt = false, this.note, this.habitId});
  

@override final  SyncMeta meta;
@override final  Money amount;
@override final  String categoryId;
@override final  PaymentChannel channel;
/// UTC.
@override final  DateTime spentAt;
@override final  String? memberId;
/// MVP-2; MVP-1 da so'ralmaydi.
@override final  Necessity? necessity;
@override final  String? envelopeId;
@override@JsonKey() final  bool isGift;
@override@JsonKey() final  bool isOstentation;
@override@JsonKey() final  bool fundedByDebt;
@override final  String? note;
/// Kuzatiladigan odat (SPEC 2B.9).
@override final  String? habitId;

/// Create a copy of Expense
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ExpenseCopyWith<_Expense> get copyWith => __$ExpenseCopyWithImpl<_Expense>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Expense&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.categoryId, categoryId) || other.categoryId == categoryId)&&(identical(other.channel, channel) || other.channel == channel)&&(identical(other.spentAt, spentAt) || other.spentAt == spentAt)&&(identical(other.memberId, memberId) || other.memberId == memberId)&&(identical(other.necessity, necessity) || other.necessity == necessity)&&(identical(other.envelopeId, envelopeId) || other.envelopeId == envelopeId)&&(identical(other.isGift, isGift) || other.isGift == isGift)&&(identical(other.isOstentation, isOstentation) || other.isOstentation == isOstentation)&&(identical(other.fundedByDebt, fundedByDebt) || other.fundedByDebt == fundedByDebt)&&(identical(other.note, note) || other.note == note)&&(identical(other.habitId, habitId) || other.habitId == habitId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,amount,categoryId,channel,spentAt,memberId,necessity,envelopeId,isGift,isOstentation,fundedByDebt,note,habitId);

@override
String toString() {
  return 'Expense(meta: $meta, amount: $amount, categoryId: $categoryId, channel: $channel, spentAt: $spentAt, memberId: $memberId, necessity: $necessity, envelopeId: $envelopeId, isGift: $isGift, isOstentation: $isOstentation, fundedByDebt: $fundedByDebt, note: $note, habitId: $habitId)';
}


}

/// @nodoc
abstract mixin class _$ExpenseCopyWith<$Res> implements $ExpenseCopyWith<$Res> {
  factory _$ExpenseCopyWith(_Expense value, $Res Function(_Expense) _then) = __$ExpenseCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, Money amount, String categoryId, PaymentChannel channel, DateTime spentAt, String? memberId, Necessity? necessity, String? envelopeId, bool isGift, bool isOstentation, bool fundedByDebt, String? note, String? habitId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$ExpenseCopyWithImpl<$Res>
    implements _$ExpenseCopyWith<$Res> {
  __$ExpenseCopyWithImpl(this._self, this._then);

  final _Expense _self;
  final $Res Function(_Expense) _then;

/// Create a copy of Expense
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? amount = null,Object? categoryId = null,Object? channel = null,Object? spentAt = null,Object? memberId = freezed,Object? necessity = freezed,Object? envelopeId = freezed,Object? isGift = null,Object? isOstentation = null,Object? fundedByDebt = null,Object? note = freezed,Object? habitId = freezed,}) {
  return _then(_Expense(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,categoryId: null == categoryId ? _self.categoryId : categoryId // ignore: cast_nullable_to_non_nullable
as String,channel: null == channel ? _self.channel : channel // ignore: cast_nullable_to_non_nullable
as PaymentChannel,spentAt: null == spentAt ? _self.spentAt : spentAt // ignore: cast_nullable_to_non_nullable
as DateTime,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,necessity: freezed == necessity ? _self.necessity : necessity // ignore: cast_nullable_to_non_nullable
as Necessity?,envelopeId: freezed == envelopeId ? _self.envelopeId : envelopeId // ignore: cast_nullable_to_non_nullable
as String?,isGift: null == isGift ? _self.isGift : isGift // ignore: cast_nullable_to_non_nullable
as bool,isOstentation: null == isOstentation ? _self.isOstentation : isOstentation // ignore: cast_nullable_to_non_nullable
as bool,fundedByDebt: null == fundedByDebt ? _self.fundedByDebt : fundedByDebt // ignore: cast_nullable_to_non_nullable
as bool,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,habitId: freezed == habitId ? _self.habitId : habitId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of Expense
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
mixin _$ExpenseTemplate {

 SyncMeta get meta; String get title; Money get amount; String get categoryId; PaymentChannel get channel;/// `null` — kategoriya toifasi olinadi.
 Necessity? get necessity; String? get habitId; int get sortOrder;
/// Create a copy of ExpenseTemplate
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ExpenseTemplateCopyWith<ExpenseTemplate> get copyWith => _$ExpenseTemplateCopyWithImpl<ExpenseTemplate>(this as ExpenseTemplate, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ExpenseTemplate&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.categoryId, categoryId) || other.categoryId == categoryId)&&(identical(other.channel, channel) || other.channel == channel)&&(identical(other.necessity, necessity) || other.necessity == necessity)&&(identical(other.habitId, habitId) || other.habitId == habitId)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,amount,categoryId,channel,necessity,habitId,sortOrder);

@override
String toString() {
  return 'ExpenseTemplate(meta: $meta, title: $title, amount: $amount, categoryId: $categoryId, channel: $channel, necessity: $necessity, habitId: $habitId, sortOrder: $sortOrder)';
}


}

/// @nodoc
abstract mixin class $ExpenseTemplateCopyWith<$Res>  {
  factory $ExpenseTemplateCopyWith(ExpenseTemplate value, $Res Function(ExpenseTemplate) _then) = _$ExpenseTemplateCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, Money amount, String categoryId, PaymentChannel channel, Necessity? necessity, String? habitId, int sortOrder
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$ExpenseTemplateCopyWithImpl<$Res>
    implements $ExpenseTemplateCopyWith<$Res> {
  _$ExpenseTemplateCopyWithImpl(this._self, this._then);

  final ExpenseTemplate _self;
  final $Res Function(ExpenseTemplate) _then;

/// Create a copy of ExpenseTemplate
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? amount = null,Object? categoryId = null,Object? channel = null,Object? necessity = freezed,Object? habitId = freezed,Object? sortOrder = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,categoryId: null == categoryId ? _self.categoryId : categoryId // ignore: cast_nullable_to_non_nullable
as String,channel: null == channel ? _self.channel : channel // ignore: cast_nullable_to_non_nullable
as PaymentChannel,necessity: freezed == necessity ? _self.necessity : necessity // ignore: cast_nullable_to_non_nullable
as Necessity?,habitId: freezed == habitId ? _self.habitId : habitId // ignore: cast_nullable_to_non_nullable
as String?,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,
  ));
}
/// Create a copy of ExpenseTemplate
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [ExpenseTemplate].
extension ExpenseTemplatePatterns on ExpenseTemplate {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ExpenseTemplate value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ExpenseTemplate() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ExpenseTemplate value)  $default,){
final _that = this;
switch (_that) {
case _ExpenseTemplate():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ExpenseTemplate value)?  $default,){
final _that = this;
switch (_that) {
case _ExpenseTemplate() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money amount,  String categoryId,  PaymentChannel channel,  Necessity? necessity,  String? habitId,  int sortOrder)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ExpenseTemplate() when $default != null:
return $default(_that.meta,_that.title,_that.amount,_that.categoryId,_that.channel,_that.necessity,_that.habitId,_that.sortOrder);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money amount,  String categoryId,  PaymentChannel channel,  Necessity? necessity,  String? habitId,  int sortOrder)  $default,) {final _that = this;
switch (_that) {
case _ExpenseTemplate():
return $default(_that.meta,_that.title,_that.amount,_that.categoryId,_that.channel,_that.necessity,_that.habitId,_that.sortOrder);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  Money amount,  String categoryId,  PaymentChannel channel,  Necessity? necessity,  String? habitId,  int sortOrder)?  $default,) {final _that = this;
switch (_that) {
case _ExpenseTemplate() when $default != null:
return $default(_that.meta,_that.title,_that.amount,_that.categoryId,_that.channel,_that.necessity,_that.habitId,_that.sortOrder);case _:
  return null;

}
}

}

/// @nodoc


class _ExpenseTemplate implements ExpenseTemplate {
  const _ExpenseTemplate({required this.meta, required this.title, required this.amount, required this.categoryId, this.channel = PaymentChannel.cash, this.necessity, this.habitId, this.sortOrder = 0});
  

@override final  SyncMeta meta;
@override final  String title;
@override final  Money amount;
@override final  String categoryId;
@override@JsonKey() final  PaymentChannel channel;
/// `null` — kategoriya toifasi olinadi.
@override final  Necessity? necessity;
@override final  String? habitId;
@override@JsonKey() final  int sortOrder;

/// Create a copy of ExpenseTemplate
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ExpenseTemplateCopyWith<_ExpenseTemplate> get copyWith => __$ExpenseTemplateCopyWithImpl<_ExpenseTemplate>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _ExpenseTemplate&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.categoryId, categoryId) || other.categoryId == categoryId)&&(identical(other.channel, channel) || other.channel == channel)&&(identical(other.necessity, necessity) || other.necessity == necessity)&&(identical(other.habitId, habitId) || other.habitId == habitId)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,amount,categoryId,channel,necessity,habitId,sortOrder);

@override
String toString() {
  return 'ExpenseTemplate(meta: $meta, title: $title, amount: $amount, categoryId: $categoryId, channel: $channel, necessity: $necessity, habitId: $habitId, sortOrder: $sortOrder)';
}


}

/// @nodoc
abstract mixin class _$ExpenseTemplateCopyWith<$Res> implements $ExpenseTemplateCopyWith<$Res> {
  factory _$ExpenseTemplateCopyWith(_ExpenseTemplate value, $Res Function(_ExpenseTemplate) _then) = __$ExpenseTemplateCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, Money amount, String categoryId, PaymentChannel channel, Necessity? necessity, String? habitId, int sortOrder
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$ExpenseTemplateCopyWithImpl<$Res>
    implements _$ExpenseTemplateCopyWith<$Res> {
  __$ExpenseTemplateCopyWithImpl(this._self, this._then);

  final _ExpenseTemplate _self;
  final $Res Function(_ExpenseTemplate) _then;

/// Create a copy of ExpenseTemplate
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? amount = null,Object? categoryId = null,Object? channel = null,Object? necessity = freezed,Object? habitId = freezed,Object? sortOrder = null,}) {
  return _then(_ExpenseTemplate(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,categoryId: null == categoryId ? _self.categoryId : categoryId // ignore: cast_nullable_to_non_nullable
as String,channel: null == channel ? _self.channel : channel // ignore: cast_nullable_to_non_nullable
as PaymentChannel,necessity: freezed == necessity ? _self.necessity : necessity // ignore: cast_nullable_to_non_nullable
as Necessity?,habitId: freezed == habitId ? _self.habitId : habitId // ignore: cast_nullable_to_non_nullable
as String?,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

/// Create a copy of ExpenseTemplate
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
mixin _$NecessityChange {

 SyncMeta get meta; String get categoryId; Necessity? get from; Necessity? get to; String? get memberId;
/// Create a copy of NecessityChange
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$NecessityChangeCopyWith<NecessityChange> get copyWith => _$NecessityChangeCopyWithImpl<NecessityChange>(this as NecessityChange, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is NecessityChange&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.categoryId, categoryId) || other.categoryId == categoryId)&&(identical(other.from, from) || other.from == from)&&(identical(other.to, to) || other.to == to)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,categoryId,from,to,memberId);

@override
String toString() {
  return 'NecessityChange(meta: $meta, categoryId: $categoryId, from: $from, to: $to, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class $NecessityChangeCopyWith<$Res>  {
  factory $NecessityChangeCopyWith(NecessityChange value, $Res Function(NecessityChange) _then) = _$NecessityChangeCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String categoryId, Necessity? from, Necessity? to, String? memberId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$NecessityChangeCopyWithImpl<$Res>
    implements $NecessityChangeCopyWith<$Res> {
  _$NecessityChangeCopyWithImpl(this._self, this._then);

  final NecessityChange _self;
  final $Res Function(NecessityChange) _then;

/// Create a copy of NecessityChange
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? categoryId = null,Object? from = freezed,Object? to = freezed,Object? memberId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,categoryId: null == categoryId ? _self.categoryId : categoryId // ignore: cast_nullable_to_non_nullable
as String,from: freezed == from ? _self.from : from // ignore: cast_nullable_to_non_nullable
as Necessity?,to: freezed == to ? _self.to : to // ignore: cast_nullable_to_non_nullable
as Necessity?,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of NecessityChange
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [NecessityChange].
extension NecessityChangePatterns on NecessityChange {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _NecessityChange value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _NecessityChange() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _NecessityChange value)  $default,){
final _that = this;
switch (_that) {
case _NecessityChange():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _NecessityChange value)?  $default,){
final _that = this;
switch (_that) {
case _NecessityChange() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String categoryId,  Necessity? from,  Necessity? to,  String? memberId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _NecessityChange() when $default != null:
return $default(_that.meta,_that.categoryId,_that.from,_that.to,_that.memberId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String categoryId,  Necessity? from,  Necessity? to,  String? memberId)  $default,) {final _that = this;
switch (_that) {
case _NecessityChange():
return $default(_that.meta,_that.categoryId,_that.from,_that.to,_that.memberId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String categoryId,  Necessity? from,  Necessity? to,  String? memberId)?  $default,) {final _that = this;
switch (_that) {
case _NecessityChange() when $default != null:
return $default(_that.meta,_that.categoryId,_that.from,_that.to,_that.memberId);case _:
  return null;

}
}

}

/// @nodoc


class _NecessityChange implements NecessityChange {
  const _NecessityChange({required this.meta, required this.categoryId, this.from, this.to, this.memberId});
  

@override final  SyncMeta meta;
@override final  String categoryId;
@override final  Necessity? from;
@override final  Necessity? to;
@override final  String? memberId;

/// Create a copy of NecessityChange
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$NecessityChangeCopyWith<_NecessityChange> get copyWith => __$NecessityChangeCopyWithImpl<_NecessityChange>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _NecessityChange&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.categoryId, categoryId) || other.categoryId == categoryId)&&(identical(other.from, from) || other.from == from)&&(identical(other.to, to) || other.to == to)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,categoryId,from,to,memberId);

@override
String toString() {
  return 'NecessityChange(meta: $meta, categoryId: $categoryId, from: $from, to: $to, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class _$NecessityChangeCopyWith<$Res> implements $NecessityChangeCopyWith<$Res> {
  factory _$NecessityChangeCopyWith(_NecessityChange value, $Res Function(_NecessityChange) _then) = __$NecessityChangeCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String categoryId, Necessity? from, Necessity? to, String? memberId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$NecessityChangeCopyWithImpl<$Res>
    implements _$NecessityChangeCopyWith<$Res> {
  __$NecessityChangeCopyWithImpl(this._self, this._then);

  final _NecessityChange _self;
  final $Res Function(_NecessityChange) _then;

/// Create a copy of NecessityChange
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? categoryId = null,Object? from = freezed,Object? to = freezed,Object? memberId = freezed,}) {
  return _then(_NecessityChange(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,categoryId: null == categoryId ? _self.categoryId : categoryId // ignore: cast_nullable_to_non_nullable
as String,from: freezed == from ? _self.from : from // ignore: cast_nullable_to_non_nullable
as Necessity?,to: freezed == to ? _self.to : to // ignore: cast_nullable_to_non_nullable
as Necessity?,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of NecessityChange
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
