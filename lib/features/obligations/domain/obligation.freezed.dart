// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'obligation.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$Obligation {

 SyncMeta get meta; String get title; ObligationKind get kind; Money get amount;/// 1–31; qisqa oyda oyning oxirgi kuni.
 int get dayOfMonth; String? get categoryId; String? get debtId; bool get isActive;
/// Create a copy of Obligation
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ObligationCopyWith<Obligation> get copyWith => _$ObligationCopyWithImpl<Obligation>(this as Obligation, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Obligation&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.dayOfMonth, dayOfMonth) || other.dayOfMonth == dayOfMonth)&&(identical(other.categoryId, categoryId) || other.categoryId == categoryId)&&(identical(other.debtId, debtId) || other.debtId == debtId)&&(identical(other.isActive, isActive) || other.isActive == isActive));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,kind,amount,dayOfMonth,categoryId,debtId,isActive);

@override
String toString() {
  return 'Obligation(meta: $meta, title: $title, kind: $kind, amount: $amount, dayOfMonth: $dayOfMonth, categoryId: $categoryId, debtId: $debtId, isActive: $isActive)';
}


}

/// @nodoc
abstract mixin class $ObligationCopyWith<$Res>  {
  factory $ObligationCopyWith(Obligation value, $Res Function(Obligation) _then) = _$ObligationCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, ObligationKind kind, Money amount, int dayOfMonth, String? categoryId, String? debtId, bool isActive
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$ObligationCopyWithImpl<$Res>
    implements $ObligationCopyWith<$Res> {
  _$ObligationCopyWithImpl(this._self, this._then);

  final Obligation _self;
  final $Res Function(Obligation) _then;

/// Create a copy of Obligation
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? kind = null,Object? amount = null,Object? dayOfMonth = null,Object? categoryId = freezed,Object? debtId = freezed,Object? isActive = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as ObligationKind,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,dayOfMonth: null == dayOfMonth ? _self.dayOfMonth : dayOfMonth // ignore: cast_nullable_to_non_nullable
as int,categoryId: freezed == categoryId ? _self.categoryId : categoryId // ignore: cast_nullable_to_non_nullable
as String?,debtId: freezed == debtId ? _self.debtId : debtId // ignore: cast_nullable_to_non_nullable
as String?,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}
/// Create a copy of Obligation
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Obligation].
extension ObligationPatterns on Obligation {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Obligation value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Obligation() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Obligation value)  $default,){
final _that = this;
switch (_that) {
case _Obligation():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Obligation value)?  $default,){
final _that = this;
switch (_that) {
case _Obligation() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  ObligationKind kind,  Money amount,  int dayOfMonth,  String? categoryId,  String? debtId,  bool isActive)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Obligation() when $default != null:
return $default(_that.meta,_that.title,_that.kind,_that.amount,_that.dayOfMonth,_that.categoryId,_that.debtId,_that.isActive);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  ObligationKind kind,  Money amount,  int dayOfMonth,  String? categoryId,  String? debtId,  bool isActive)  $default,) {final _that = this;
switch (_that) {
case _Obligation():
return $default(_that.meta,_that.title,_that.kind,_that.amount,_that.dayOfMonth,_that.categoryId,_that.debtId,_that.isActive);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  ObligationKind kind,  Money amount,  int dayOfMonth,  String? categoryId,  String? debtId,  bool isActive)?  $default,) {final _that = this;
switch (_that) {
case _Obligation() when $default != null:
return $default(_that.meta,_that.title,_that.kind,_that.amount,_that.dayOfMonth,_that.categoryId,_that.debtId,_that.isActive);case _:
  return null;

}
}

}

/// @nodoc


class _Obligation implements Obligation {
  const _Obligation({required this.meta, required this.title, required this.kind, required this.amount, required this.dayOfMonth, this.categoryId, this.debtId, this.isActive = true});
  

@override final  SyncMeta meta;
@override final  String title;
@override final  ObligationKind kind;
@override final  Money amount;
/// 1–31; qisqa oyda oyning oxirgi kuni.
@override final  int dayOfMonth;
@override final  String? categoryId;
@override final  String? debtId;
@override@JsonKey() final  bool isActive;

/// Create a copy of Obligation
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ObligationCopyWith<_Obligation> get copyWith => __$ObligationCopyWithImpl<_Obligation>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Obligation&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.dayOfMonth, dayOfMonth) || other.dayOfMonth == dayOfMonth)&&(identical(other.categoryId, categoryId) || other.categoryId == categoryId)&&(identical(other.debtId, debtId) || other.debtId == debtId)&&(identical(other.isActive, isActive) || other.isActive == isActive));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,kind,amount,dayOfMonth,categoryId,debtId,isActive);

@override
String toString() {
  return 'Obligation(meta: $meta, title: $title, kind: $kind, amount: $amount, dayOfMonth: $dayOfMonth, categoryId: $categoryId, debtId: $debtId, isActive: $isActive)';
}


}

/// @nodoc
abstract mixin class _$ObligationCopyWith<$Res> implements $ObligationCopyWith<$Res> {
  factory _$ObligationCopyWith(_Obligation value, $Res Function(_Obligation) _then) = __$ObligationCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, ObligationKind kind, Money amount, int dayOfMonth, String? categoryId, String? debtId, bool isActive
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$ObligationCopyWithImpl<$Res>
    implements _$ObligationCopyWith<$Res> {
  __$ObligationCopyWithImpl(this._self, this._then);

  final _Obligation _self;
  final $Res Function(_Obligation) _then;

/// Create a copy of Obligation
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? kind = null,Object? amount = null,Object? dayOfMonth = null,Object? categoryId = freezed,Object? debtId = freezed,Object? isActive = null,}) {
  return _then(_Obligation(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as ObligationKind,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,dayOfMonth: null == dayOfMonth ? _self.dayOfMonth : dayOfMonth // ignore: cast_nullable_to_non_nullable
as int,categoryId: freezed == categoryId ? _self.categoryId : categoryId // ignore: cast_nullable_to_non_nullable
as String?,debtId: freezed == debtId ? _self.debtId : debtId // ignore: cast_nullable_to_non_nullable
as String?,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

/// Create a copy of Obligation
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
mixin _$Debt {

 SyncMeta get meta; CreditorType get creditorType; String get creditorName; Money get principal; Money get remaining; Money? get monthlyPayment; LocalDate? get dueDate; String? get reason; bool get hasMarkup;// MVP-4 maydonlari.
 Money? get totalPaid; Money? get markupAmount; String? get earlyRepaymentTerms; int? get priority; String? get note;// v9 (MVP_PLAN Vazifa 10).
 DebtScheduleType? get scheduleType; int? get termMonths;/// Yillik stavka (bp) — faqat bank krediti hisob-kitobi uchun.
 int? get annualRateBp; LocalDate? get startDate;/// Qarz oldidan friction javoblari (JSON, SPEC 2D.6).
 String? get borrowCheckJson;// v10 (MVP_PLAN Vazifa 11).
/// Yopish tartibi; `null` — standart (avval foizlilar).
 int? get payoffOrder;/// Muddatidan oldin to'lash jarimasi (qo'shimcha to'lovdan, bp).
 int? get prepayFeeBp;
/// Create a copy of Debt
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DebtCopyWith<Debt> get copyWith => _$DebtCopyWithImpl<Debt>(this as Debt, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Debt&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.creditorType, creditorType) || other.creditorType == creditorType)&&(identical(other.creditorName, creditorName) || other.creditorName == creditorName)&&(identical(other.principal, principal) || other.principal == principal)&&(identical(other.remaining, remaining) || other.remaining == remaining)&&(identical(other.monthlyPayment, monthlyPayment) || other.monthlyPayment == monthlyPayment)&&(identical(other.dueDate, dueDate) || other.dueDate == dueDate)&&(identical(other.reason, reason) || other.reason == reason)&&(identical(other.hasMarkup, hasMarkup) || other.hasMarkup == hasMarkup)&&(identical(other.totalPaid, totalPaid) || other.totalPaid == totalPaid)&&(identical(other.markupAmount, markupAmount) || other.markupAmount == markupAmount)&&(identical(other.earlyRepaymentTerms, earlyRepaymentTerms) || other.earlyRepaymentTerms == earlyRepaymentTerms)&&(identical(other.priority, priority) || other.priority == priority)&&(identical(other.note, note) || other.note == note)&&(identical(other.scheduleType, scheduleType) || other.scheduleType == scheduleType)&&(identical(other.termMonths, termMonths) || other.termMonths == termMonths)&&(identical(other.annualRateBp, annualRateBp) || other.annualRateBp == annualRateBp)&&(identical(other.startDate, startDate) || other.startDate == startDate)&&(identical(other.borrowCheckJson, borrowCheckJson) || other.borrowCheckJson == borrowCheckJson)&&(identical(other.payoffOrder, payoffOrder) || other.payoffOrder == payoffOrder)&&(identical(other.prepayFeeBp, prepayFeeBp) || other.prepayFeeBp == prepayFeeBp));
}


@override
int get hashCode => Object.hashAll([runtimeType,meta,creditorType,creditorName,principal,remaining,monthlyPayment,dueDate,reason,hasMarkup,totalPaid,markupAmount,earlyRepaymentTerms,priority,note,scheduleType,termMonths,annualRateBp,startDate,borrowCheckJson,payoffOrder,prepayFeeBp]);

@override
String toString() {
  return 'Debt(meta: $meta, creditorType: $creditorType, creditorName: $creditorName, principal: $principal, remaining: $remaining, monthlyPayment: $monthlyPayment, dueDate: $dueDate, reason: $reason, hasMarkup: $hasMarkup, totalPaid: $totalPaid, markupAmount: $markupAmount, earlyRepaymentTerms: $earlyRepaymentTerms, priority: $priority, note: $note, scheduleType: $scheduleType, termMonths: $termMonths, annualRateBp: $annualRateBp, startDate: $startDate, borrowCheckJson: $borrowCheckJson, payoffOrder: $payoffOrder, prepayFeeBp: $prepayFeeBp)';
}


}

/// @nodoc
abstract mixin class $DebtCopyWith<$Res>  {
  factory $DebtCopyWith(Debt value, $Res Function(Debt) _then) = _$DebtCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, CreditorType creditorType, String creditorName, Money principal, Money remaining, Money? monthlyPayment, LocalDate? dueDate, String? reason, bool hasMarkup, Money? totalPaid, Money? markupAmount, String? earlyRepaymentTerms, int? priority, String? note, DebtScheduleType? scheduleType, int? termMonths, int? annualRateBp, LocalDate? startDate, String? borrowCheckJson, int? payoffOrder, int? prepayFeeBp
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$DebtCopyWithImpl<$Res>
    implements $DebtCopyWith<$Res> {
  _$DebtCopyWithImpl(this._self, this._then);

  final Debt _self;
  final $Res Function(Debt) _then;

/// Create a copy of Debt
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? creditorType = null,Object? creditorName = null,Object? principal = null,Object? remaining = null,Object? monthlyPayment = freezed,Object? dueDate = freezed,Object? reason = freezed,Object? hasMarkup = null,Object? totalPaid = freezed,Object? markupAmount = freezed,Object? earlyRepaymentTerms = freezed,Object? priority = freezed,Object? note = freezed,Object? scheduleType = freezed,Object? termMonths = freezed,Object? annualRateBp = freezed,Object? startDate = freezed,Object? borrowCheckJson = freezed,Object? payoffOrder = freezed,Object? prepayFeeBp = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,creditorType: null == creditorType ? _self.creditorType : creditorType // ignore: cast_nullable_to_non_nullable
as CreditorType,creditorName: null == creditorName ? _self.creditorName : creditorName // ignore: cast_nullable_to_non_nullable
as String,principal: null == principal ? _self.principal : principal // ignore: cast_nullable_to_non_nullable
as Money,remaining: null == remaining ? _self.remaining : remaining // ignore: cast_nullable_to_non_nullable
as Money,monthlyPayment: freezed == monthlyPayment ? _self.monthlyPayment : monthlyPayment // ignore: cast_nullable_to_non_nullable
as Money?,dueDate: freezed == dueDate ? _self.dueDate : dueDate // ignore: cast_nullable_to_non_nullable
as LocalDate?,reason: freezed == reason ? _self.reason : reason // ignore: cast_nullable_to_non_nullable
as String?,hasMarkup: null == hasMarkup ? _self.hasMarkup : hasMarkup // ignore: cast_nullable_to_non_nullable
as bool,totalPaid: freezed == totalPaid ? _self.totalPaid : totalPaid // ignore: cast_nullable_to_non_nullable
as Money?,markupAmount: freezed == markupAmount ? _self.markupAmount : markupAmount // ignore: cast_nullable_to_non_nullable
as Money?,earlyRepaymentTerms: freezed == earlyRepaymentTerms ? _self.earlyRepaymentTerms : earlyRepaymentTerms // ignore: cast_nullable_to_non_nullable
as String?,priority: freezed == priority ? _self.priority : priority // ignore: cast_nullable_to_non_nullable
as int?,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,scheduleType: freezed == scheduleType ? _self.scheduleType : scheduleType // ignore: cast_nullable_to_non_nullable
as DebtScheduleType?,termMonths: freezed == termMonths ? _self.termMonths : termMonths // ignore: cast_nullable_to_non_nullable
as int?,annualRateBp: freezed == annualRateBp ? _self.annualRateBp : annualRateBp // ignore: cast_nullable_to_non_nullable
as int?,startDate: freezed == startDate ? _self.startDate : startDate // ignore: cast_nullable_to_non_nullable
as LocalDate?,borrowCheckJson: freezed == borrowCheckJson ? _self.borrowCheckJson : borrowCheckJson // ignore: cast_nullable_to_non_nullable
as String?,payoffOrder: freezed == payoffOrder ? _self.payoffOrder : payoffOrder // ignore: cast_nullable_to_non_nullable
as int?,prepayFeeBp: freezed == prepayFeeBp ? _self.prepayFeeBp : prepayFeeBp // ignore: cast_nullable_to_non_nullable
as int?,
  ));
}
/// Create a copy of Debt
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Debt].
extension DebtPatterns on Debt {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Debt value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Debt() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Debt value)  $default,){
final _that = this;
switch (_that) {
case _Debt():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Debt value)?  $default,){
final _that = this;
switch (_that) {
case _Debt() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  CreditorType creditorType,  String creditorName,  Money principal,  Money remaining,  Money? monthlyPayment,  LocalDate? dueDate,  String? reason,  bool hasMarkup,  Money? totalPaid,  Money? markupAmount,  String? earlyRepaymentTerms,  int? priority,  String? note,  DebtScheduleType? scheduleType,  int? termMonths,  int? annualRateBp,  LocalDate? startDate,  String? borrowCheckJson,  int? payoffOrder,  int? prepayFeeBp)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Debt() when $default != null:
return $default(_that.meta,_that.creditorType,_that.creditorName,_that.principal,_that.remaining,_that.monthlyPayment,_that.dueDate,_that.reason,_that.hasMarkup,_that.totalPaid,_that.markupAmount,_that.earlyRepaymentTerms,_that.priority,_that.note,_that.scheduleType,_that.termMonths,_that.annualRateBp,_that.startDate,_that.borrowCheckJson,_that.payoffOrder,_that.prepayFeeBp);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  CreditorType creditorType,  String creditorName,  Money principal,  Money remaining,  Money? monthlyPayment,  LocalDate? dueDate,  String? reason,  bool hasMarkup,  Money? totalPaid,  Money? markupAmount,  String? earlyRepaymentTerms,  int? priority,  String? note,  DebtScheduleType? scheduleType,  int? termMonths,  int? annualRateBp,  LocalDate? startDate,  String? borrowCheckJson,  int? payoffOrder,  int? prepayFeeBp)  $default,) {final _that = this;
switch (_that) {
case _Debt():
return $default(_that.meta,_that.creditorType,_that.creditorName,_that.principal,_that.remaining,_that.monthlyPayment,_that.dueDate,_that.reason,_that.hasMarkup,_that.totalPaid,_that.markupAmount,_that.earlyRepaymentTerms,_that.priority,_that.note,_that.scheduleType,_that.termMonths,_that.annualRateBp,_that.startDate,_that.borrowCheckJson,_that.payoffOrder,_that.prepayFeeBp);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  CreditorType creditorType,  String creditorName,  Money principal,  Money remaining,  Money? monthlyPayment,  LocalDate? dueDate,  String? reason,  bool hasMarkup,  Money? totalPaid,  Money? markupAmount,  String? earlyRepaymentTerms,  int? priority,  String? note,  DebtScheduleType? scheduleType,  int? termMonths,  int? annualRateBp,  LocalDate? startDate,  String? borrowCheckJson,  int? payoffOrder,  int? prepayFeeBp)?  $default,) {final _that = this;
switch (_that) {
case _Debt() when $default != null:
return $default(_that.meta,_that.creditorType,_that.creditorName,_that.principal,_that.remaining,_that.monthlyPayment,_that.dueDate,_that.reason,_that.hasMarkup,_that.totalPaid,_that.markupAmount,_that.earlyRepaymentTerms,_that.priority,_that.note,_that.scheduleType,_that.termMonths,_that.annualRateBp,_that.startDate,_that.borrowCheckJson,_that.payoffOrder,_that.prepayFeeBp);case _:
  return null;

}
}

}

/// @nodoc


class _Debt implements Debt {
  const _Debt({required this.meta, required this.creditorType, required this.creditorName, required this.principal, required this.remaining, this.monthlyPayment, this.dueDate, this.reason, this.hasMarkup = false, this.totalPaid, this.markupAmount, this.earlyRepaymentTerms, this.priority, this.note, this.scheduleType, this.termMonths, this.annualRateBp, this.startDate, this.borrowCheckJson, this.payoffOrder, this.prepayFeeBp});
  

@override final  SyncMeta meta;
@override final  CreditorType creditorType;
@override final  String creditorName;
@override final  Money principal;
@override final  Money remaining;
@override final  Money? monthlyPayment;
@override final  LocalDate? dueDate;
@override final  String? reason;
@override@JsonKey() final  bool hasMarkup;
// MVP-4 maydonlari.
@override final  Money? totalPaid;
@override final  Money? markupAmount;
@override final  String? earlyRepaymentTerms;
@override final  int? priority;
@override final  String? note;
// v9 (MVP_PLAN Vazifa 10).
@override final  DebtScheduleType? scheduleType;
@override final  int? termMonths;
/// Yillik stavka (bp) — faqat bank krediti hisob-kitobi uchun.
@override final  int? annualRateBp;
@override final  LocalDate? startDate;
/// Qarz oldidan friction javoblari (JSON, SPEC 2D.6).
@override final  String? borrowCheckJson;
// v10 (MVP_PLAN Vazifa 11).
/// Yopish tartibi; `null` — standart (avval foizlilar).
@override final  int? payoffOrder;
/// Muddatidan oldin to'lash jarimasi (qo'shimcha to'lovdan, bp).
@override final  int? prepayFeeBp;

/// Create a copy of Debt
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DebtCopyWith<_Debt> get copyWith => __$DebtCopyWithImpl<_Debt>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Debt&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.creditorType, creditorType) || other.creditorType == creditorType)&&(identical(other.creditorName, creditorName) || other.creditorName == creditorName)&&(identical(other.principal, principal) || other.principal == principal)&&(identical(other.remaining, remaining) || other.remaining == remaining)&&(identical(other.monthlyPayment, monthlyPayment) || other.monthlyPayment == monthlyPayment)&&(identical(other.dueDate, dueDate) || other.dueDate == dueDate)&&(identical(other.reason, reason) || other.reason == reason)&&(identical(other.hasMarkup, hasMarkup) || other.hasMarkup == hasMarkup)&&(identical(other.totalPaid, totalPaid) || other.totalPaid == totalPaid)&&(identical(other.markupAmount, markupAmount) || other.markupAmount == markupAmount)&&(identical(other.earlyRepaymentTerms, earlyRepaymentTerms) || other.earlyRepaymentTerms == earlyRepaymentTerms)&&(identical(other.priority, priority) || other.priority == priority)&&(identical(other.note, note) || other.note == note)&&(identical(other.scheduleType, scheduleType) || other.scheduleType == scheduleType)&&(identical(other.termMonths, termMonths) || other.termMonths == termMonths)&&(identical(other.annualRateBp, annualRateBp) || other.annualRateBp == annualRateBp)&&(identical(other.startDate, startDate) || other.startDate == startDate)&&(identical(other.borrowCheckJson, borrowCheckJson) || other.borrowCheckJson == borrowCheckJson)&&(identical(other.payoffOrder, payoffOrder) || other.payoffOrder == payoffOrder)&&(identical(other.prepayFeeBp, prepayFeeBp) || other.prepayFeeBp == prepayFeeBp));
}


@override
int get hashCode => Object.hashAll([runtimeType,meta,creditorType,creditorName,principal,remaining,monthlyPayment,dueDate,reason,hasMarkup,totalPaid,markupAmount,earlyRepaymentTerms,priority,note,scheduleType,termMonths,annualRateBp,startDate,borrowCheckJson,payoffOrder,prepayFeeBp]);

@override
String toString() {
  return 'Debt(meta: $meta, creditorType: $creditorType, creditorName: $creditorName, principal: $principal, remaining: $remaining, monthlyPayment: $monthlyPayment, dueDate: $dueDate, reason: $reason, hasMarkup: $hasMarkup, totalPaid: $totalPaid, markupAmount: $markupAmount, earlyRepaymentTerms: $earlyRepaymentTerms, priority: $priority, note: $note, scheduleType: $scheduleType, termMonths: $termMonths, annualRateBp: $annualRateBp, startDate: $startDate, borrowCheckJson: $borrowCheckJson, payoffOrder: $payoffOrder, prepayFeeBp: $prepayFeeBp)';
}


}

/// @nodoc
abstract mixin class _$DebtCopyWith<$Res> implements $DebtCopyWith<$Res> {
  factory _$DebtCopyWith(_Debt value, $Res Function(_Debt) _then) = __$DebtCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, CreditorType creditorType, String creditorName, Money principal, Money remaining, Money? monthlyPayment, LocalDate? dueDate, String? reason, bool hasMarkup, Money? totalPaid, Money? markupAmount, String? earlyRepaymentTerms, int? priority, String? note, DebtScheduleType? scheduleType, int? termMonths, int? annualRateBp, LocalDate? startDate, String? borrowCheckJson, int? payoffOrder, int? prepayFeeBp
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$DebtCopyWithImpl<$Res>
    implements _$DebtCopyWith<$Res> {
  __$DebtCopyWithImpl(this._self, this._then);

  final _Debt _self;
  final $Res Function(_Debt) _then;

/// Create a copy of Debt
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? creditorType = null,Object? creditorName = null,Object? principal = null,Object? remaining = null,Object? monthlyPayment = freezed,Object? dueDate = freezed,Object? reason = freezed,Object? hasMarkup = null,Object? totalPaid = freezed,Object? markupAmount = freezed,Object? earlyRepaymentTerms = freezed,Object? priority = freezed,Object? note = freezed,Object? scheduleType = freezed,Object? termMonths = freezed,Object? annualRateBp = freezed,Object? startDate = freezed,Object? borrowCheckJson = freezed,Object? payoffOrder = freezed,Object? prepayFeeBp = freezed,}) {
  return _then(_Debt(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,creditorType: null == creditorType ? _self.creditorType : creditorType // ignore: cast_nullable_to_non_nullable
as CreditorType,creditorName: null == creditorName ? _self.creditorName : creditorName // ignore: cast_nullable_to_non_nullable
as String,principal: null == principal ? _self.principal : principal // ignore: cast_nullable_to_non_nullable
as Money,remaining: null == remaining ? _self.remaining : remaining // ignore: cast_nullable_to_non_nullable
as Money,monthlyPayment: freezed == monthlyPayment ? _self.monthlyPayment : monthlyPayment // ignore: cast_nullable_to_non_nullable
as Money?,dueDate: freezed == dueDate ? _self.dueDate : dueDate // ignore: cast_nullable_to_non_nullable
as LocalDate?,reason: freezed == reason ? _self.reason : reason // ignore: cast_nullable_to_non_nullable
as String?,hasMarkup: null == hasMarkup ? _self.hasMarkup : hasMarkup // ignore: cast_nullable_to_non_nullable
as bool,totalPaid: freezed == totalPaid ? _self.totalPaid : totalPaid // ignore: cast_nullable_to_non_nullable
as Money?,markupAmount: freezed == markupAmount ? _self.markupAmount : markupAmount // ignore: cast_nullable_to_non_nullable
as Money?,earlyRepaymentTerms: freezed == earlyRepaymentTerms ? _self.earlyRepaymentTerms : earlyRepaymentTerms // ignore: cast_nullable_to_non_nullable
as String?,priority: freezed == priority ? _self.priority : priority // ignore: cast_nullable_to_non_nullable
as int?,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,scheduleType: freezed == scheduleType ? _self.scheduleType : scheduleType // ignore: cast_nullable_to_non_nullable
as DebtScheduleType?,termMonths: freezed == termMonths ? _self.termMonths : termMonths // ignore: cast_nullable_to_non_nullable
as int?,annualRateBp: freezed == annualRateBp ? _self.annualRateBp : annualRateBp // ignore: cast_nullable_to_non_nullable
as int?,startDate: freezed == startDate ? _self.startDate : startDate // ignore: cast_nullable_to_non_nullable
as LocalDate?,borrowCheckJson: freezed == borrowCheckJson ? _self.borrowCheckJson : borrowCheckJson // ignore: cast_nullable_to_non_nullable
as String?,payoffOrder: freezed == payoffOrder ? _self.payoffOrder : payoffOrder // ignore: cast_nullable_to_non_nullable
as int?,prepayFeeBp: freezed == prepayFeeBp ? _self.prepayFeeBp : prepayFeeBp // ignore: cast_nullable_to_non_nullable
as int?,
  ));
}

/// Create a copy of Debt
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
