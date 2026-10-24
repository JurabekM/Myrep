// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'venture.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$VentureEntry {

 SyncMeta get meta; String get partnershipId; VentureEntryKind get kind; String get title;/// Musbat; tuzatish — ishorali (manfiy — kamaytiradi).
 Money get amount; LocalDate get occurredOn; String? get note;/// Chek yoki dalil rasmi (shifrlangan bazada).
 List<int>? get receiptImage;
/// Create a copy of VentureEntry
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$VentureEntryCopyWith<VentureEntry> get copyWith => _$VentureEntryCopyWithImpl<VentureEntry>(this as VentureEntry, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is VentureEntry&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.title, title) || other.title == title)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.occurredOn, occurredOn) || other.occurredOn == occurredOn)&&(identical(other.note, note) || other.note == note)&&const DeepCollectionEquality().equals(other.receiptImage, receiptImage));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,kind,title,amount,occurredOn,note,const DeepCollectionEquality().hash(receiptImage));

@override
String toString() {
  return 'VentureEntry(meta: $meta, partnershipId: $partnershipId, kind: $kind, title: $title, amount: $amount, occurredOn: $occurredOn, note: $note, receiptImage: $receiptImage)';
}


}

/// @nodoc
abstract mixin class $VentureEntryCopyWith<$Res>  {
  factory $VentureEntryCopyWith(VentureEntry value, $Res Function(VentureEntry) _then) = _$VentureEntryCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String partnershipId, VentureEntryKind kind, String title, Money amount, LocalDate occurredOn, String? note, List<int>? receiptImage
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$VentureEntryCopyWithImpl<$Res>
    implements $VentureEntryCopyWith<$Res> {
  _$VentureEntryCopyWithImpl(this._self, this._then);

  final VentureEntry _self;
  final $Res Function(VentureEntry) _then;

/// Create a copy of VentureEntry
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? partnershipId = null,Object? kind = null,Object? title = null,Object? amount = null,Object? occurredOn = null,Object? note = freezed,Object? receiptImage = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as VentureEntryKind,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,occurredOn: null == occurredOn ? _self.occurredOn : occurredOn // ignore: cast_nullable_to_non_nullable
as LocalDate,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,receiptImage: freezed == receiptImage ? _self.receiptImage : receiptImage // ignore: cast_nullable_to_non_nullable
as List<int>?,
  ));
}
/// Create a copy of VentureEntry
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [VentureEntry].
extension VentureEntryPatterns on VentureEntry {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _VentureEntry value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _VentureEntry() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _VentureEntry value)  $default,){
final _that = this;
switch (_that) {
case _VentureEntry():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _VentureEntry value)?  $default,){
final _that = this;
switch (_that) {
case _VentureEntry() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  VentureEntryKind kind,  String title,  Money amount,  LocalDate occurredOn,  String? note,  List<int>? receiptImage)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _VentureEntry() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.kind,_that.title,_that.amount,_that.occurredOn,_that.note,_that.receiptImage);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  VentureEntryKind kind,  String title,  Money amount,  LocalDate occurredOn,  String? note,  List<int>? receiptImage)  $default,) {final _that = this;
switch (_that) {
case _VentureEntry():
return $default(_that.meta,_that.partnershipId,_that.kind,_that.title,_that.amount,_that.occurredOn,_that.note,_that.receiptImage);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String partnershipId,  VentureEntryKind kind,  String title,  Money amount,  LocalDate occurredOn,  String? note,  List<int>? receiptImage)?  $default,) {final _that = this;
switch (_that) {
case _VentureEntry() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.kind,_that.title,_that.amount,_that.occurredOn,_that.note,_that.receiptImage);case _:
  return null;

}
}

}

/// @nodoc


class _VentureEntry extends VentureEntry {
  const _VentureEntry({required this.meta, required this.partnershipId, required this.kind, required this.title, required this.amount, required this.occurredOn, this.note, final  List<int>? receiptImage}): _receiptImage = receiptImage,super._();
  

@override final  SyncMeta meta;
@override final  String partnershipId;
@override final  VentureEntryKind kind;
@override final  String title;
/// Musbat; tuzatish — ishorali (manfiy — kamaytiradi).
@override final  Money amount;
@override final  LocalDate occurredOn;
@override final  String? note;
/// Chek yoki dalil rasmi (shifrlangan bazada).
 final  List<int>? _receiptImage;
/// Chek yoki dalil rasmi (shifrlangan bazada).
@override List<int>? get receiptImage {
  final value = _receiptImage;
  if (value == null) return null;
  if (_receiptImage is EqualUnmodifiableListView) return _receiptImage;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(value);
}


/// Create a copy of VentureEntry
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$VentureEntryCopyWith<_VentureEntry> get copyWith => __$VentureEntryCopyWithImpl<_VentureEntry>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _VentureEntry&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.title, title) || other.title == title)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.occurredOn, occurredOn) || other.occurredOn == occurredOn)&&(identical(other.note, note) || other.note == note)&&const DeepCollectionEquality().equals(other._receiptImage, _receiptImage));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,kind,title,amount,occurredOn,note,const DeepCollectionEquality().hash(_receiptImage));

@override
String toString() {
  return 'VentureEntry(meta: $meta, partnershipId: $partnershipId, kind: $kind, title: $title, amount: $amount, occurredOn: $occurredOn, note: $note, receiptImage: $receiptImage)';
}


}

/// @nodoc
abstract mixin class _$VentureEntryCopyWith<$Res> implements $VentureEntryCopyWith<$Res> {
  factory _$VentureEntryCopyWith(_VentureEntry value, $Res Function(_VentureEntry) _then) = __$VentureEntryCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String partnershipId, VentureEntryKind kind, String title, Money amount, LocalDate occurredOn, String? note, List<int>? receiptImage
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$VentureEntryCopyWithImpl<$Res>
    implements _$VentureEntryCopyWith<$Res> {
  __$VentureEntryCopyWithImpl(this._self, this._then);

  final _VentureEntry _self;
  final $Res Function(_VentureEntry) _then;

/// Create a copy of VentureEntry
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? partnershipId = null,Object? kind = null,Object? title = null,Object? amount = null,Object? occurredOn = null,Object? note = freezed,Object? receiptImage = freezed,}) {
  return _then(_VentureEntry(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as VentureEntryKind,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,occurredOn: null == occurredOn ? _self.occurredOn : occurredOn // ignore: cast_nullable_to_non_nullable
as LocalDate,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,receiptImage: freezed == receiptImage ? _self._receiptImage : receiptImage // ignore: cast_nullable_to_non_nullable
as List<int>?,
  ));
}

/// Create a copy of VentureEntry
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
mixin _$VenturePeriod {

 SyncMeta get meta; String get partnershipId; LocalDate get startDate; LocalDate get endDate; Money get income; Money get expense; Money get net; Money get buyout; bool get negligence; String? get negligenceNote; String? get incomeId;
/// Create a copy of VenturePeriod
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$VenturePeriodCopyWith<VenturePeriod> get copyWith => _$VenturePeriodCopyWithImpl<VenturePeriod>(this as VenturePeriod, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is VenturePeriod&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.startDate, startDate) || other.startDate == startDate)&&(identical(other.endDate, endDate) || other.endDate == endDate)&&(identical(other.income, income) || other.income == income)&&(identical(other.expense, expense) || other.expense == expense)&&(identical(other.net, net) || other.net == net)&&(identical(other.buyout, buyout) || other.buyout == buyout)&&(identical(other.negligence, negligence) || other.negligence == negligence)&&(identical(other.negligenceNote, negligenceNote) || other.negligenceNote == negligenceNote)&&(identical(other.incomeId, incomeId) || other.incomeId == incomeId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,startDate,endDate,income,expense,net,buyout,negligence,negligenceNote,incomeId);

@override
String toString() {
  return 'VenturePeriod(meta: $meta, partnershipId: $partnershipId, startDate: $startDate, endDate: $endDate, income: $income, expense: $expense, net: $net, buyout: $buyout, negligence: $negligence, negligenceNote: $negligenceNote, incomeId: $incomeId)';
}


}

/// @nodoc
abstract mixin class $VenturePeriodCopyWith<$Res>  {
  factory $VenturePeriodCopyWith(VenturePeriod value, $Res Function(VenturePeriod) _then) = _$VenturePeriodCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String partnershipId, LocalDate startDate, LocalDate endDate, Money income, Money expense, Money net, Money buyout, bool negligence, String? negligenceNote, String? incomeId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$VenturePeriodCopyWithImpl<$Res>
    implements $VenturePeriodCopyWith<$Res> {
  _$VenturePeriodCopyWithImpl(this._self, this._then);

  final VenturePeriod _self;
  final $Res Function(VenturePeriod) _then;

/// Create a copy of VenturePeriod
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? partnershipId = null,Object? startDate = null,Object? endDate = null,Object? income = null,Object? expense = null,Object? net = null,Object? buyout = null,Object? negligence = null,Object? negligenceNote = freezed,Object? incomeId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,startDate: null == startDate ? _self.startDate : startDate // ignore: cast_nullable_to_non_nullable
as LocalDate,endDate: null == endDate ? _self.endDate : endDate // ignore: cast_nullable_to_non_nullable
as LocalDate,income: null == income ? _self.income : income // ignore: cast_nullable_to_non_nullable
as Money,expense: null == expense ? _self.expense : expense // ignore: cast_nullable_to_non_nullable
as Money,net: null == net ? _self.net : net // ignore: cast_nullable_to_non_nullable
as Money,buyout: null == buyout ? _self.buyout : buyout // ignore: cast_nullable_to_non_nullable
as Money,negligence: null == negligence ? _self.negligence : negligence // ignore: cast_nullable_to_non_nullable
as bool,negligenceNote: freezed == negligenceNote ? _self.negligenceNote : negligenceNote // ignore: cast_nullable_to_non_nullable
as String?,incomeId: freezed == incomeId ? _self.incomeId : incomeId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of VenturePeriod
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [VenturePeriod].
extension VenturePeriodPatterns on VenturePeriod {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _VenturePeriod value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _VenturePeriod() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _VenturePeriod value)  $default,){
final _that = this;
switch (_that) {
case _VenturePeriod():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _VenturePeriod value)?  $default,){
final _that = this;
switch (_that) {
case _VenturePeriod() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  LocalDate startDate,  LocalDate endDate,  Money income,  Money expense,  Money net,  Money buyout,  bool negligence,  String? negligenceNote,  String? incomeId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _VenturePeriod() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.startDate,_that.endDate,_that.income,_that.expense,_that.net,_that.buyout,_that.negligence,_that.negligenceNote,_that.incomeId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  LocalDate startDate,  LocalDate endDate,  Money income,  Money expense,  Money net,  Money buyout,  bool negligence,  String? negligenceNote,  String? incomeId)  $default,) {final _that = this;
switch (_that) {
case _VenturePeriod():
return $default(_that.meta,_that.partnershipId,_that.startDate,_that.endDate,_that.income,_that.expense,_that.net,_that.buyout,_that.negligence,_that.negligenceNote,_that.incomeId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String partnershipId,  LocalDate startDate,  LocalDate endDate,  Money income,  Money expense,  Money net,  Money buyout,  bool negligence,  String? negligenceNote,  String? incomeId)?  $default,) {final _that = this;
switch (_that) {
case _VenturePeriod() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.startDate,_that.endDate,_that.income,_that.expense,_that.net,_that.buyout,_that.negligence,_that.negligenceNote,_that.incomeId);case _:
  return null;

}
}

}

/// @nodoc


class _VenturePeriod implements VenturePeriod {
  const _VenturePeriod({required this.meta, required this.partnershipId, required this.startDate, required this.endDate, required this.income, required this.expense, required this.net, required this.buyout, this.negligence = false, this.negligenceNote, this.incomeId});
  

@override final  SyncMeta meta;
@override final  String partnershipId;
@override final  LocalDate startDate;
@override final  LocalDate endDate;
@override final  Money income;
@override final  Money expense;
@override final  Money net;
@override final  Money buyout;
@override@JsonKey() final  bool negligence;
@override final  String? negligenceNote;
@override final  String? incomeId;

/// Create a copy of VenturePeriod
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$VenturePeriodCopyWith<_VenturePeriod> get copyWith => __$VenturePeriodCopyWithImpl<_VenturePeriod>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _VenturePeriod&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.startDate, startDate) || other.startDate == startDate)&&(identical(other.endDate, endDate) || other.endDate == endDate)&&(identical(other.income, income) || other.income == income)&&(identical(other.expense, expense) || other.expense == expense)&&(identical(other.net, net) || other.net == net)&&(identical(other.buyout, buyout) || other.buyout == buyout)&&(identical(other.negligence, negligence) || other.negligence == negligence)&&(identical(other.negligenceNote, negligenceNote) || other.negligenceNote == negligenceNote)&&(identical(other.incomeId, incomeId) || other.incomeId == incomeId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,startDate,endDate,income,expense,net,buyout,negligence,negligenceNote,incomeId);

@override
String toString() {
  return 'VenturePeriod(meta: $meta, partnershipId: $partnershipId, startDate: $startDate, endDate: $endDate, income: $income, expense: $expense, net: $net, buyout: $buyout, negligence: $negligence, negligenceNote: $negligenceNote, incomeId: $incomeId)';
}


}

/// @nodoc
abstract mixin class _$VenturePeriodCopyWith<$Res> implements $VenturePeriodCopyWith<$Res> {
  factory _$VenturePeriodCopyWith(_VenturePeriod value, $Res Function(_VenturePeriod) _then) = __$VenturePeriodCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String partnershipId, LocalDate startDate, LocalDate endDate, Money income, Money expense, Money net, Money buyout, bool negligence, String? negligenceNote, String? incomeId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$VenturePeriodCopyWithImpl<$Res>
    implements _$VenturePeriodCopyWith<$Res> {
  __$VenturePeriodCopyWithImpl(this._self, this._then);

  final _VenturePeriod _self;
  final $Res Function(_VenturePeriod) _then;

/// Create a copy of VenturePeriod
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? partnershipId = null,Object? startDate = null,Object? endDate = null,Object? income = null,Object? expense = null,Object? net = null,Object? buyout = null,Object? negligence = null,Object? negligenceNote = freezed,Object? incomeId = freezed,}) {
  return _then(_VenturePeriod(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,startDate: null == startDate ? _self.startDate : startDate // ignore: cast_nullable_to_non_nullable
as LocalDate,endDate: null == endDate ? _self.endDate : endDate // ignore: cast_nullable_to_non_nullable
as LocalDate,income: null == income ? _self.income : income // ignore: cast_nullable_to_non_nullable
as Money,expense: null == expense ? _self.expense : expense // ignore: cast_nullable_to_non_nullable
as Money,net: null == net ? _self.net : net // ignore: cast_nullable_to_non_nullable
as Money,buyout: null == buyout ? _self.buyout : buyout // ignore: cast_nullable_to_non_nullable
as Money,negligence: null == negligence ? _self.negligence : negligence // ignore: cast_nullable_to_non_nullable
as bool,negligenceNote: freezed == negligenceNote ? _self.negligenceNote : negligenceNote // ignore: cast_nullable_to_non_nullable
as String?,incomeId: freezed == incomeId ? _self.incomeId : incomeId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of VenturePeriod
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
mixin _$DistributionShare {

 SyncMeta get meta; String get periodId; String get partnerId; Money get amount; Money get buyout;
/// Create a copy of DistributionShare
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DistributionShareCopyWith<DistributionShare> get copyWith => _$DistributionShareCopyWithImpl<DistributionShare>(this as DistributionShare, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DistributionShare&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.periodId, periodId) || other.periodId == periodId)&&(identical(other.partnerId, partnerId) || other.partnerId == partnerId)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.buyout, buyout) || other.buyout == buyout));
}


@override
int get hashCode => Object.hash(runtimeType,meta,periodId,partnerId,amount,buyout);

@override
String toString() {
  return 'DistributionShare(meta: $meta, periodId: $periodId, partnerId: $partnerId, amount: $amount, buyout: $buyout)';
}


}

/// @nodoc
abstract mixin class $DistributionShareCopyWith<$Res>  {
  factory $DistributionShareCopyWith(DistributionShare value, $Res Function(DistributionShare) _then) = _$DistributionShareCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String periodId, String partnerId, Money amount, Money buyout
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$DistributionShareCopyWithImpl<$Res>
    implements $DistributionShareCopyWith<$Res> {
  _$DistributionShareCopyWithImpl(this._self, this._then);

  final DistributionShare _self;
  final $Res Function(DistributionShare) _then;

/// Create a copy of DistributionShare
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? periodId = null,Object? partnerId = null,Object? amount = null,Object? buyout = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,periodId: null == periodId ? _self.periodId : periodId // ignore: cast_nullable_to_non_nullable
as String,partnerId: null == partnerId ? _self.partnerId : partnerId // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,buyout: null == buyout ? _self.buyout : buyout // ignore: cast_nullable_to_non_nullable
as Money,
  ));
}
/// Create a copy of DistributionShare
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [DistributionShare].
extension DistributionSharePatterns on DistributionShare {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DistributionShare value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DistributionShare() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DistributionShare value)  $default,){
final _that = this;
switch (_that) {
case _DistributionShare():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DistributionShare value)?  $default,){
final _that = this;
switch (_that) {
case _DistributionShare() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String periodId,  String partnerId,  Money amount,  Money buyout)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DistributionShare() when $default != null:
return $default(_that.meta,_that.periodId,_that.partnerId,_that.amount,_that.buyout);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String periodId,  String partnerId,  Money amount,  Money buyout)  $default,) {final _that = this;
switch (_that) {
case _DistributionShare():
return $default(_that.meta,_that.periodId,_that.partnerId,_that.amount,_that.buyout);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String periodId,  String partnerId,  Money amount,  Money buyout)?  $default,) {final _that = this;
switch (_that) {
case _DistributionShare() when $default != null:
return $default(_that.meta,_that.periodId,_that.partnerId,_that.amount,_that.buyout);case _:
  return null;

}
}

}

/// @nodoc


class _DistributionShare implements DistributionShare {
  const _DistributionShare({required this.meta, required this.periodId, required this.partnerId, required this.amount, required this.buyout});
  

@override final  SyncMeta meta;
@override final  String periodId;
@override final  String partnerId;
@override final  Money amount;
@override final  Money buyout;

/// Create a copy of DistributionShare
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DistributionShareCopyWith<_DistributionShare> get copyWith => __$DistributionShareCopyWithImpl<_DistributionShare>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DistributionShare&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.periodId, periodId) || other.periodId == periodId)&&(identical(other.partnerId, partnerId) || other.partnerId == partnerId)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.buyout, buyout) || other.buyout == buyout));
}


@override
int get hashCode => Object.hash(runtimeType,meta,periodId,partnerId,amount,buyout);

@override
String toString() {
  return 'DistributionShare(meta: $meta, periodId: $periodId, partnerId: $partnerId, amount: $amount, buyout: $buyout)';
}


}

/// @nodoc
abstract mixin class _$DistributionShareCopyWith<$Res> implements $DistributionShareCopyWith<$Res> {
  factory _$DistributionShareCopyWith(_DistributionShare value, $Res Function(_DistributionShare) _then) = __$DistributionShareCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String periodId, String partnerId, Money amount, Money buyout
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$DistributionShareCopyWithImpl<$Res>
    implements _$DistributionShareCopyWith<$Res> {
  __$DistributionShareCopyWithImpl(this._self, this._then);

  final _DistributionShare _self;
  final $Res Function(_DistributionShare) _then;

/// Create a copy of DistributionShare
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? periodId = null,Object? partnerId = null,Object? amount = null,Object? buyout = null,}) {
  return _then(_DistributionShare(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,periodId: null == periodId ? _self.periodId : periodId // ignore: cast_nullable_to_non_nullable
as String,partnerId: null == partnerId ? _self.partnerId : partnerId // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,buyout: null == buyout ? _self.buyout : buyout // ignore: cast_nullable_to_non_nullable
as Money,
  ));
}

/// Create a copy of DistributionShare
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
mixin _$Skill {

 SyncMeta get meta; String get name; String? get memberId;
/// Create a copy of Skill
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$SkillCopyWith<Skill> get copyWith => _$SkillCopyWithImpl<Skill>(this as Skill, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Skill&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.name, name) || other.name == name)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,name,memberId);

@override
String toString() {
  return 'Skill(meta: $meta, name: $name, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class $SkillCopyWith<$Res>  {
  factory $SkillCopyWith(Skill value, $Res Function(Skill) _then) = _$SkillCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String name, String? memberId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$SkillCopyWithImpl<$Res>
    implements $SkillCopyWith<$Res> {
  _$SkillCopyWithImpl(this._self, this._then);

  final Skill _self;
  final $Res Function(Skill) _then;

/// Create a copy of Skill
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? name = null,Object? memberId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of Skill
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Skill].
extension SkillPatterns on Skill {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Skill value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Skill() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Skill value)  $default,){
final _that = this;
switch (_that) {
case _Skill():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Skill value)?  $default,){
final _that = this;
switch (_that) {
case _Skill() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String name,  String? memberId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Skill() when $default != null:
return $default(_that.meta,_that.name,_that.memberId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String name,  String? memberId)  $default,) {final _that = this;
switch (_that) {
case _Skill():
return $default(_that.meta,_that.name,_that.memberId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String name,  String? memberId)?  $default,) {final _that = this;
switch (_that) {
case _Skill() when $default != null:
return $default(_that.meta,_that.name,_that.memberId);case _:
  return null;

}
}

}

/// @nodoc


class _Skill implements Skill {
  const _Skill({required this.meta, required this.name, this.memberId});
  

@override final  SyncMeta meta;
@override final  String name;
@override final  String? memberId;

/// Create a copy of Skill
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$SkillCopyWith<_Skill> get copyWith => __$SkillCopyWithImpl<_Skill>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Skill&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.name, name) || other.name == name)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,name,memberId);

@override
String toString() {
  return 'Skill(meta: $meta, name: $name, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class _$SkillCopyWith<$Res> implements $SkillCopyWith<$Res> {
  factory _$SkillCopyWith(_Skill value, $Res Function(_Skill) _then) = __$SkillCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String name, String? memberId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$SkillCopyWithImpl<$Res>
    implements _$SkillCopyWith<$Res> {
  __$SkillCopyWithImpl(this._self, this._then);

  final _Skill _self;
  final $Res Function(_Skill) _then;

/// Create a copy of Skill
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? name = null,Object? memberId = freezed,}) {
  return _then(_Skill(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of Skill
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
mixin _$VentureIdea {

 SyncMeta get meta; String get title; Money get pessimisticIncome; Money get baseIncome; Money get optimisticIncome; Money get monthlyExpense; int get myShareBp; String? get skillId;
/// Create a copy of VentureIdea
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$VentureIdeaCopyWith<VentureIdea> get copyWith => _$VentureIdeaCopyWithImpl<VentureIdea>(this as VentureIdea, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is VentureIdea&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.pessimisticIncome, pessimisticIncome) || other.pessimisticIncome == pessimisticIncome)&&(identical(other.baseIncome, baseIncome) || other.baseIncome == baseIncome)&&(identical(other.optimisticIncome, optimisticIncome) || other.optimisticIncome == optimisticIncome)&&(identical(other.monthlyExpense, monthlyExpense) || other.monthlyExpense == monthlyExpense)&&(identical(other.myShareBp, myShareBp) || other.myShareBp == myShareBp)&&(identical(other.skillId, skillId) || other.skillId == skillId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,pessimisticIncome,baseIncome,optimisticIncome,monthlyExpense,myShareBp,skillId);

@override
String toString() {
  return 'VentureIdea(meta: $meta, title: $title, pessimisticIncome: $pessimisticIncome, baseIncome: $baseIncome, optimisticIncome: $optimisticIncome, monthlyExpense: $monthlyExpense, myShareBp: $myShareBp, skillId: $skillId)';
}


}

/// @nodoc
abstract mixin class $VentureIdeaCopyWith<$Res>  {
  factory $VentureIdeaCopyWith(VentureIdea value, $Res Function(VentureIdea) _then) = _$VentureIdeaCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, Money pessimisticIncome, Money baseIncome, Money optimisticIncome, Money monthlyExpense, int myShareBp, String? skillId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$VentureIdeaCopyWithImpl<$Res>
    implements $VentureIdeaCopyWith<$Res> {
  _$VentureIdeaCopyWithImpl(this._self, this._then);

  final VentureIdea _self;
  final $Res Function(VentureIdea) _then;

/// Create a copy of VentureIdea
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? pessimisticIncome = null,Object? baseIncome = null,Object? optimisticIncome = null,Object? monthlyExpense = null,Object? myShareBp = null,Object? skillId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,pessimisticIncome: null == pessimisticIncome ? _self.pessimisticIncome : pessimisticIncome // ignore: cast_nullable_to_non_nullable
as Money,baseIncome: null == baseIncome ? _self.baseIncome : baseIncome // ignore: cast_nullable_to_non_nullable
as Money,optimisticIncome: null == optimisticIncome ? _self.optimisticIncome : optimisticIncome // ignore: cast_nullable_to_non_nullable
as Money,monthlyExpense: null == monthlyExpense ? _self.monthlyExpense : monthlyExpense // ignore: cast_nullable_to_non_nullable
as Money,myShareBp: null == myShareBp ? _self.myShareBp : myShareBp // ignore: cast_nullable_to_non_nullable
as int,skillId: freezed == skillId ? _self.skillId : skillId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of VentureIdea
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [VentureIdea].
extension VentureIdeaPatterns on VentureIdea {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _VentureIdea value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _VentureIdea() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _VentureIdea value)  $default,){
final _that = this;
switch (_that) {
case _VentureIdea():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _VentureIdea value)?  $default,){
final _that = this;
switch (_that) {
case _VentureIdea() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money pessimisticIncome,  Money baseIncome,  Money optimisticIncome,  Money monthlyExpense,  int myShareBp,  String? skillId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _VentureIdea() when $default != null:
return $default(_that.meta,_that.title,_that.pessimisticIncome,_that.baseIncome,_that.optimisticIncome,_that.monthlyExpense,_that.myShareBp,_that.skillId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money pessimisticIncome,  Money baseIncome,  Money optimisticIncome,  Money monthlyExpense,  int myShareBp,  String? skillId)  $default,) {final _that = this;
switch (_that) {
case _VentureIdea():
return $default(_that.meta,_that.title,_that.pessimisticIncome,_that.baseIncome,_that.optimisticIncome,_that.monthlyExpense,_that.myShareBp,_that.skillId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  Money pessimisticIncome,  Money baseIncome,  Money optimisticIncome,  Money monthlyExpense,  int myShareBp,  String? skillId)?  $default,) {final _that = this;
switch (_that) {
case _VentureIdea() when $default != null:
return $default(_that.meta,_that.title,_that.pessimisticIncome,_that.baseIncome,_that.optimisticIncome,_that.monthlyExpense,_that.myShareBp,_that.skillId);case _:
  return null;

}
}

}

/// @nodoc


class _VentureIdea implements VentureIdea {
  const _VentureIdea({required this.meta, required this.title, required this.pessimisticIncome, required this.baseIncome, required this.optimisticIncome, required this.monthlyExpense, this.myShareBp = 10000, this.skillId});
  

@override final  SyncMeta meta;
@override final  String title;
@override final  Money pessimisticIncome;
@override final  Money baseIncome;
@override final  Money optimisticIncome;
@override final  Money monthlyExpense;
@override@JsonKey() final  int myShareBp;
@override final  String? skillId;

/// Create a copy of VentureIdea
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$VentureIdeaCopyWith<_VentureIdea> get copyWith => __$VentureIdeaCopyWithImpl<_VentureIdea>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _VentureIdea&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.pessimisticIncome, pessimisticIncome) || other.pessimisticIncome == pessimisticIncome)&&(identical(other.baseIncome, baseIncome) || other.baseIncome == baseIncome)&&(identical(other.optimisticIncome, optimisticIncome) || other.optimisticIncome == optimisticIncome)&&(identical(other.monthlyExpense, monthlyExpense) || other.monthlyExpense == monthlyExpense)&&(identical(other.myShareBp, myShareBp) || other.myShareBp == myShareBp)&&(identical(other.skillId, skillId) || other.skillId == skillId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,pessimisticIncome,baseIncome,optimisticIncome,monthlyExpense,myShareBp,skillId);

@override
String toString() {
  return 'VentureIdea(meta: $meta, title: $title, pessimisticIncome: $pessimisticIncome, baseIncome: $baseIncome, optimisticIncome: $optimisticIncome, monthlyExpense: $monthlyExpense, myShareBp: $myShareBp, skillId: $skillId)';
}


}

/// @nodoc
abstract mixin class _$VentureIdeaCopyWith<$Res> implements $VentureIdeaCopyWith<$Res> {
  factory _$VentureIdeaCopyWith(_VentureIdea value, $Res Function(_VentureIdea) _then) = __$VentureIdeaCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, Money pessimisticIncome, Money baseIncome, Money optimisticIncome, Money monthlyExpense, int myShareBp, String? skillId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$VentureIdeaCopyWithImpl<$Res>
    implements _$VentureIdeaCopyWith<$Res> {
  __$VentureIdeaCopyWithImpl(this._self, this._then);

  final _VentureIdea _self;
  final $Res Function(_VentureIdea) _then;

/// Create a copy of VentureIdea
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? pessimisticIncome = null,Object? baseIncome = null,Object? optimisticIncome = null,Object? monthlyExpense = null,Object? myShareBp = null,Object? skillId = freezed,}) {
  return _then(_VentureIdea(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,pessimisticIncome: null == pessimisticIncome ? _self.pessimisticIncome : pessimisticIncome // ignore: cast_nullable_to_non_nullable
as Money,baseIncome: null == baseIncome ? _self.baseIncome : baseIncome // ignore: cast_nullable_to_non_nullable
as Money,optimisticIncome: null == optimisticIncome ? _self.optimisticIncome : optimisticIncome // ignore: cast_nullable_to_non_nullable
as Money,monthlyExpense: null == monthlyExpense ? _self.monthlyExpense : monthlyExpense // ignore: cast_nullable_to_non_nullable
as Money,myShareBp: null == myShareBp ? _self.myShareBp : myShareBp // ignore: cast_nullable_to_non_nullable
as int,skillId: freezed == skillId ? _self.skillId : skillId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of VentureIdea
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
mixin _$IdeaCapexItem {

 SyncMeta get meta; String get ideaId; String get title; Money get amount;
/// Create a copy of IdeaCapexItem
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$IdeaCapexItemCopyWith<IdeaCapexItem> get copyWith => _$IdeaCapexItemCopyWithImpl<IdeaCapexItem>(this as IdeaCapexItem, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is IdeaCapexItem&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.ideaId, ideaId) || other.ideaId == ideaId)&&(identical(other.title, title) || other.title == title)&&(identical(other.amount, amount) || other.amount == amount));
}


@override
int get hashCode => Object.hash(runtimeType,meta,ideaId,title,amount);

@override
String toString() {
  return 'IdeaCapexItem(meta: $meta, ideaId: $ideaId, title: $title, amount: $amount)';
}


}

/// @nodoc
abstract mixin class $IdeaCapexItemCopyWith<$Res>  {
  factory $IdeaCapexItemCopyWith(IdeaCapexItem value, $Res Function(IdeaCapexItem) _then) = _$IdeaCapexItemCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String ideaId, String title, Money amount
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$IdeaCapexItemCopyWithImpl<$Res>
    implements $IdeaCapexItemCopyWith<$Res> {
  _$IdeaCapexItemCopyWithImpl(this._self, this._then);

  final IdeaCapexItem _self;
  final $Res Function(IdeaCapexItem) _then;

/// Create a copy of IdeaCapexItem
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? ideaId = null,Object? title = null,Object? amount = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,ideaId: null == ideaId ? _self.ideaId : ideaId // ignore: cast_nullable_to_non_nullable
as String,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,
  ));
}
/// Create a copy of IdeaCapexItem
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [IdeaCapexItem].
extension IdeaCapexItemPatterns on IdeaCapexItem {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _IdeaCapexItem value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _IdeaCapexItem() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _IdeaCapexItem value)  $default,){
final _that = this;
switch (_that) {
case _IdeaCapexItem():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _IdeaCapexItem value)?  $default,){
final _that = this;
switch (_that) {
case _IdeaCapexItem() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String ideaId,  String title,  Money amount)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _IdeaCapexItem() when $default != null:
return $default(_that.meta,_that.ideaId,_that.title,_that.amount);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String ideaId,  String title,  Money amount)  $default,) {final _that = this;
switch (_that) {
case _IdeaCapexItem():
return $default(_that.meta,_that.ideaId,_that.title,_that.amount);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String ideaId,  String title,  Money amount)?  $default,) {final _that = this;
switch (_that) {
case _IdeaCapexItem() when $default != null:
return $default(_that.meta,_that.ideaId,_that.title,_that.amount);case _:
  return null;

}
}

}

/// @nodoc


class _IdeaCapexItem implements IdeaCapexItem {
  const _IdeaCapexItem({required this.meta, required this.ideaId, required this.title, required this.amount});
  

@override final  SyncMeta meta;
@override final  String ideaId;
@override final  String title;
@override final  Money amount;

/// Create a copy of IdeaCapexItem
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$IdeaCapexItemCopyWith<_IdeaCapexItem> get copyWith => __$IdeaCapexItemCopyWithImpl<_IdeaCapexItem>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _IdeaCapexItem&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.ideaId, ideaId) || other.ideaId == ideaId)&&(identical(other.title, title) || other.title == title)&&(identical(other.amount, amount) || other.amount == amount));
}


@override
int get hashCode => Object.hash(runtimeType,meta,ideaId,title,amount);

@override
String toString() {
  return 'IdeaCapexItem(meta: $meta, ideaId: $ideaId, title: $title, amount: $amount)';
}


}

/// @nodoc
abstract mixin class _$IdeaCapexItemCopyWith<$Res> implements $IdeaCapexItemCopyWith<$Res> {
  factory _$IdeaCapexItemCopyWith(_IdeaCapexItem value, $Res Function(_IdeaCapexItem) _then) = __$IdeaCapexItemCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String ideaId, String title, Money amount
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$IdeaCapexItemCopyWithImpl<$Res>
    implements _$IdeaCapexItemCopyWith<$Res> {
  __$IdeaCapexItemCopyWithImpl(this._self, this._then);

  final _IdeaCapexItem _self;
  final $Res Function(_IdeaCapexItem) _then;

/// Create a copy of IdeaCapexItem
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? ideaId = null,Object? title = null,Object? amount = null,}) {
  return _then(_IdeaCapexItem(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,ideaId: null == ideaId ? _self.ideaId : ideaId // ignore: cast_nullable_to_non_nullable
as String,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,
  ));
}

/// Create a copy of IdeaCapexItem
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
mixin _$OfferCheckRecord {

 SyncMeta get meta; String get title; String get answersJson; OfferVerdict get verdict;/// v16 (SPEC 2G.6): summa, va'da qilingan oylik stavka, maslahatchi va
/// qaror.
 Money? get amount; int? get promisedMonthlyBp; String? get advisor; OfferDecision? get decision; DateTime? get decidedAt;
/// Create a copy of OfferCheckRecord
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$OfferCheckRecordCopyWith<OfferCheckRecord> get copyWith => _$OfferCheckRecordCopyWithImpl<OfferCheckRecord>(this as OfferCheckRecord, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is OfferCheckRecord&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.answersJson, answersJson) || other.answersJson == answersJson)&&(identical(other.verdict, verdict) || other.verdict == verdict)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.promisedMonthlyBp, promisedMonthlyBp) || other.promisedMonthlyBp == promisedMonthlyBp)&&(identical(other.advisor, advisor) || other.advisor == advisor)&&(identical(other.decision, decision) || other.decision == decision)&&(identical(other.decidedAt, decidedAt) || other.decidedAt == decidedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,answersJson,verdict,amount,promisedMonthlyBp,advisor,decision,decidedAt);

@override
String toString() {
  return 'OfferCheckRecord(meta: $meta, title: $title, answersJson: $answersJson, verdict: $verdict, amount: $amount, promisedMonthlyBp: $promisedMonthlyBp, advisor: $advisor, decision: $decision, decidedAt: $decidedAt)';
}


}

/// @nodoc
abstract mixin class $OfferCheckRecordCopyWith<$Res>  {
  factory $OfferCheckRecordCopyWith(OfferCheckRecord value, $Res Function(OfferCheckRecord) _then) = _$OfferCheckRecordCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, String answersJson, OfferVerdict verdict, Money? amount, int? promisedMonthlyBp, String? advisor, OfferDecision? decision, DateTime? decidedAt
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$OfferCheckRecordCopyWithImpl<$Res>
    implements $OfferCheckRecordCopyWith<$Res> {
  _$OfferCheckRecordCopyWithImpl(this._self, this._then);

  final OfferCheckRecord _self;
  final $Res Function(OfferCheckRecord) _then;

/// Create a copy of OfferCheckRecord
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? answersJson = null,Object? verdict = null,Object? amount = freezed,Object? promisedMonthlyBp = freezed,Object? advisor = freezed,Object? decision = freezed,Object? decidedAt = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,answersJson: null == answersJson ? _self.answersJson : answersJson // ignore: cast_nullable_to_non_nullable
as String,verdict: null == verdict ? _self.verdict : verdict // ignore: cast_nullable_to_non_nullable
as OfferVerdict,amount: freezed == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money?,promisedMonthlyBp: freezed == promisedMonthlyBp ? _self.promisedMonthlyBp : promisedMonthlyBp // ignore: cast_nullable_to_non_nullable
as int?,advisor: freezed == advisor ? _self.advisor : advisor // ignore: cast_nullable_to_non_nullable
as String?,decision: freezed == decision ? _self.decision : decision // ignore: cast_nullable_to_non_nullable
as OfferDecision?,decidedAt: freezed == decidedAt ? _self.decidedAt : decidedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}
/// Create a copy of OfferCheckRecord
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [OfferCheckRecord].
extension OfferCheckRecordPatterns on OfferCheckRecord {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _OfferCheckRecord value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _OfferCheckRecord() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _OfferCheckRecord value)  $default,){
final _that = this;
switch (_that) {
case _OfferCheckRecord():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _OfferCheckRecord value)?  $default,){
final _that = this;
switch (_that) {
case _OfferCheckRecord() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  String answersJson,  OfferVerdict verdict,  Money? amount,  int? promisedMonthlyBp,  String? advisor,  OfferDecision? decision,  DateTime? decidedAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _OfferCheckRecord() when $default != null:
return $default(_that.meta,_that.title,_that.answersJson,_that.verdict,_that.amount,_that.promisedMonthlyBp,_that.advisor,_that.decision,_that.decidedAt);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  String answersJson,  OfferVerdict verdict,  Money? amount,  int? promisedMonthlyBp,  String? advisor,  OfferDecision? decision,  DateTime? decidedAt)  $default,) {final _that = this;
switch (_that) {
case _OfferCheckRecord():
return $default(_that.meta,_that.title,_that.answersJson,_that.verdict,_that.amount,_that.promisedMonthlyBp,_that.advisor,_that.decision,_that.decidedAt);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  String answersJson,  OfferVerdict verdict,  Money? amount,  int? promisedMonthlyBp,  String? advisor,  OfferDecision? decision,  DateTime? decidedAt)?  $default,) {final _that = this;
switch (_that) {
case _OfferCheckRecord() when $default != null:
return $default(_that.meta,_that.title,_that.answersJson,_that.verdict,_that.amount,_that.promisedMonthlyBp,_that.advisor,_that.decision,_that.decidedAt);case _:
  return null;

}
}

}

/// @nodoc


class _OfferCheckRecord implements OfferCheckRecord {
  const _OfferCheckRecord({required this.meta, required this.title, required this.answersJson, required this.verdict, this.amount, this.promisedMonthlyBp, this.advisor, this.decision, this.decidedAt});
  

@override final  SyncMeta meta;
@override final  String title;
@override final  String answersJson;
@override final  OfferVerdict verdict;
/// v16 (SPEC 2G.6): summa, va'da qilingan oylik stavka, maslahatchi va
/// qaror.
@override final  Money? amount;
@override final  int? promisedMonthlyBp;
@override final  String? advisor;
@override final  OfferDecision? decision;
@override final  DateTime? decidedAt;

/// Create a copy of OfferCheckRecord
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$OfferCheckRecordCopyWith<_OfferCheckRecord> get copyWith => __$OfferCheckRecordCopyWithImpl<_OfferCheckRecord>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _OfferCheckRecord&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.answersJson, answersJson) || other.answersJson == answersJson)&&(identical(other.verdict, verdict) || other.verdict == verdict)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.promisedMonthlyBp, promisedMonthlyBp) || other.promisedMonthlyBp == promisedMonthlyBp)&&(identical(other.advisor, advisor) || other.advisor == advisor)&&(identical(other.decision, decision) || other.decision == decision)&&(identical(other.decidedAt, decidedAt) || other.decidedAt == decidedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,answersJson,verdict,amount,promisedMonthlyBp,advisor,decision,decidedAt);

@override
String toString() {
  return 'OfferCheckRecord(meta: $meta, title: $title, answersJson: $answersJson, verdict: $verdict, amount: $amount, promisedMonthlyBp: $promisedMonthlyBp, advisor: $advisor, decision: $decision, decidedAt: $decidedAt)';
}


}

/// @nodoc
abstract mixin class _$OfferCheckRecordCopyWith<$Res> implements $OfferCheckRecordCopyWith<$Res> {
  factory _$OfferCheckRecordCopyWith(_OfferCheckRecord value, $Res Function(_OfferCheckRecord) _then) = __$OfferCheckRecordCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, String answersJson, OfferVerdict verdict, Money? amount, int? promisedMonthlyBp, String? advisor, OfferDecision? decision, DateTime? decidedAt
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$OfferCheckRecordCopyWithImpl<$Res>
    implements _$OfferCheckRecordCopyWith<$Res> {
  __$OfferCheckRecordCopyWithImpl(this._self, this._then);

  final _OfferCheckRecord _self;
  final $Res Function(_OfferCheckRecord) _then;

/// Create a copy of OfferCheckRecord
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? answersJson = null,Object? verdict = null,Object? amount = freezed,Object? promisedMonthlyBp = freezed,Object? advisor = freezed,Object? decision = freezed,Object? decidedAt = freezed,}) {
  return _then(_OfferCheckRecord(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,answersJson: null == answersJson ? _self.answersJson : answersJson // ignore: cast_nullable_to_non_nullable
as String,verdict: null == verdict ? _self.verdict : verdict // ignore: cast_nullable_to_non_nullable
as OfferVerdict,amount: freezed == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money?,promisedMonthlyBp: freezed == promisedMonthlyBp ? _self.promisedMonthlyBp : promisedMonthlyBp // ignore: cast_nullable_to_non_nullable
as int?,advisor: freezed == advisor ? _self.advisor : advisor // ignore: cast_nullable_to_non_nullable
as String?,decision: freezed == decision ? _self.decision : decision // ignore: cast_nullable_to_non_nullable
as OfferDecision?,decidedAt: freezed == decidedAt ? _self.decidedAt : decidedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}

/// Create a copy of OfferCheckRecord
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
