// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'debts.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$DebtInstallment {

 SyncMeta get meta; String get debtId; LocalDate get dueOn; Money get amount; Money get interest;
/// Create a copy of DebtInstallment
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DebtInstallmentCopyWith<DebtInstallment> get copyWith => _$DebtInstallmentCopyWithImpl<DebtInstallment>(this as DebtInstallment, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DebtInstallment&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.debtId, debtId) || other.debtId == debtId)&&(identical(other.dueOn, dueOn) || other.dueOn == dueOn)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.interest, interest) || other.interest == interest));
}


@override
int get hashCode => Object.hash(runtimeType,meta,debtId,dueOn,amount,interest);

@override
String toString() {
  return 'DebtInstallment(meta: $meta, debtId: $debtId, dueOn: $dueOn, amount: $amount, interest: $interest)';
}


}

/// @nodoc
abstract mixin class $DebtInstallmentCopyWith<$Res>  {
  factory $DebtInstallmentCopyWith(DebtInstallment value, $Res Function(DebtInstallment) _then) = _$DebtInstallmentCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String debtId, LocalDate dueOn, Money amount, Money interest
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$DebtInstallmentCopyWithImpl<$Res>
    implements $DebtInstallmentCopyWith<$Res> {
  _$DebtInstallmentCopyWithImpl(this._self, this._then);

  final DebtInstallment _self;
  final $Res Function(DebtInstallment) _then;

/// Create a copy of DebtInstallment
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? debtId = null,Object? dueOn = null,Object? amount = null,Object? interest = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,debtId: null == debtId ? _self.debtId : debtId // ignore: cast_nullable_to_non_nullable
as String,dueOn: null == dueOn ? _self.dueOn : dueOn // ignore: cast_nullable_to_non_nullable
as LocalDate,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,interest: null == interest ? _self.interest : interest // ignore: cast_nullable_to_non_nullable
as Money,
  ));
}
/// Create a copy of DebtInstallment
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [DebtInstallment].
extension DebtInstallmentPatterns on DebtInstallment {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DebtInstallment value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DebtInstallment() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DebtInstallment value)  $default,){
final _that = this;
switch (_that) {
case _DebtInstallment():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DebtInstallment value)?  $default,){
final _that = this;
switch (_that) {
case _DebtInstallment() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String debtId,  LocalDate dueOn,  Money amount,  Money interest)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DebtInstallment() when $default != null:
return $default(_that.meta,_that.debtId,_that.dueOn,_that.amount,_that.interest);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String debtId,  LocalDate dueOn,  Money amount,  Money interest)  $default,) {final _that = this;
switch (_that) {
case _DebtInstallment():
return $default(_that.meta,_that.debtId,_that.dueOn,_that.amount,_that.interest);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String debtId,  LocalDate dueOn,  Money amount,  Money interest)?  $default,) {final _that = this;
switch (_that) {
case _DebtInstallment() when $default != null:
return $default(_that.meta,_that.debtId,_that.dueOn,_that.amount,_that.interest);case _:
  return null;

}
}

}

/// @nodoc


class _DebtInstallment extends DebtInstallment {
  const _DebtInstallment({required this.meta, required this.debtId, required this.dueOn, required this.amount, required this.interest}): super._();
  

@override final  SyncMeta meta;
@override final  String debtId;
@override final  LocalDate dueOn;
@override final  Money amount;
@override final  Money interest;

/// Create a copy of DebtInstallment
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DebtInstallmentCopyWith<_DebtInstallment> get copyWith => __$DebtInstallmentCopyWithImpl<_DebtInstallment>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DebtInstallment&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.debtId, debtId) || other.debtId == debtId)&&(identical(other.dueOn, dueOn) || other.dueOn == dueOn)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.interest, interest) || other.interest == interest));
}


@override
int get hashCode => Object.hash(runtimeType,meta,debtId,dueOn,amount,interest);

@override
String toString() {
  return 'DebtInstallment(meta: $meta, debtId: $debtId, dueOn: $dueOn, amount: $amount, interest: $interest)';
}


}

/// @nodoc
abstract mixin class _$DebtInstallmentCopyWith<$Res> implements $DebtInstallmentCopyWith<$Res> {
  factory _$DebtInstallmentCopyWith(_DebtInstallment value, $Res Function(_DebtInstallment) _then) = __$DebtInstallmentCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String debtId, LocalDate dueOn, Money amount, Money interest
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$DebtInstallmentCopyWithImpl<$Res>
    implements _$DebtInstallmentCopyWith<$Res> {
  __$DebtInstallmentCopyWithImpl(this._self, this._then);

  final _DebtInstallment _self;
  final $Res Function(_DebtInstallment) _then;

/// Create a copy of DebtInstallment
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? debtId = null,Object? dueOn = null,Object? amount = null,Object? interest = null,}) {
  return _then(_DebtInstallment(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,debtId: null == debtId ? _self.debtId : debtId // ignore: cast_nullable_to_non_nullable
as String,dueOn: null == dueOn ? _self.dueOn : dueOn // ignore: cast_nullable_to_non_nullable
as LocalDate,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,interest: null == interest ? _self.interest : interest // ignore: cast_nullable_to_non_nullable
as Money,
  ));
}

/// Create a copy of DebtInstallment
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
mixin _$DebtPayment {

 SyncMeta get meta; String get debtId; Money get amount; LocalDate get paidOn; bool get isPrepayment; String? get note;/// Qo'shimcha to'lovdan ushlangan jarima (v10, `amount` ichida).
 Money? get fee;/// Kim to'ladi (`DebtContributor`); `null` — oilaning o'zi.
 String? get contributorId;
/// Create a copy of DebtPayment
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DebtPaymentCopyWith<DebtPayment> get copyWith => _$DebtPaymentCopyWithImpl<DebtPayment>(this as DebtPayment, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DebtPayment&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.debtId, debtId) || other.debtId == debtId)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.paidOn, paidOn) || other.paidOn == paidOn)&&(identical(other.isPrepayment, isPrepayment) || other.isPrepayment == isPrepayment)&&(identical(other.note, note) || other.note == note)&&(identical(other.fee, fee) || other.fee == fee)&&(identical(other.contributorId, contributorId) || other.contributorId == contributorId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,debtId,amount,paidOn,isPrepayment,note,fee,contributorId);

@override
String toString() {
  return 'DebtPayment(meta: $meta, debtId: $debtId, amount: $amount, paidOn: $paidOn, isPrepayment: $isPrepayment, note: $note, fee: $fee, contributorId: $contributorId)';
}


}

/// @nodoc
abstract mixin class $DebtPaymentCopyWith<$Res>  {
  factory $DebtPaymentCopyWith(DebtPayment value, $Res Function(DebtPayment) _then) = _$DebtPaymentCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String debtId, Money amount, LocalDate paidOn, bool isPrepayment, String? note, Money? fee, String? contributorId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$DebtPaymentCopyWithImpl<$Res>
    implements $DebtPaymentCopyWith<$Res> {
  _$DebtPaymentCopyWithImpl(this._self, this._then);

  final DebtPayment _self;
  final $Res Function(DebtPayment) _then;

/// Create a copy of DebtPayment
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? debtId = null,Object? amount = null,Object? paidOn = null,Object? isPrepayment = null,Object? note = freezed,Object? fee = freezed,Object? contributorId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,debtId: null == debtId ? _self.debtId : debtId // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,paidOn: null == paidOn ? _self.paidOn : paidOn // ignore: cast_nullable_to_non_nullable
as LocalDate,isPrepayment: null == isPrepayment ? _self.isPrepayment : isPrepayment // ignore: cast_nullable_to_non_nullable
as bool,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,fee: freezed == fee ? _self.fee : fee // ignore: cast_nullable_to_non_nullable
as Money?,contributorId: freezed == contributorId ? _self.contributorId : contributorId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of DebtPayment
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [DebtPayment].
extension DebtPaymentPatterns on DebtPayment {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DebtPayment value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DebtPayment() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DebtPayment value)  $default,){
final _that = this;
switch (_that) {
case _DebtPayment():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DebtPayment value)?  $default,){
final _that = this;
switch (_that) {
case _DebtPayment() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String debtId,  Money amount,  LocalDate paidOn,  bool isPrepayment,  String? note,  Money? fee,  String? contributorId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DebtPayment() when $default != null:
return $default(_that.meta,_that.debtId,_that.amount,_that.paidOn,_that.isPrepayment,_that.note,_that.fee,_that.contributorId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String debtId,  Money amount,  LocalDate paidOn,  bool isPrepayment,  String? note,  Money? fee,  String? contributorId)  $default,) {final _that = this;
switch (_that) {
case _DebtPayment():
return $default(_that.meta,_that.debtId,_that.amount,_that.paidOn,_that.isPrepayment,_that.note,_that.fee,_that.contributorId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String debtId,  Money amount,  LocalDate paidOn,  bool isPrepayment,  String? note,  Money? fee,  String? contributorId)?  $default,) {final _that = this;
switch (_that) {
case _DebtPayment() when $default != null:
return $default(_that.meta,_that.debtId,_that.amount,_that.paidOn,_that.isPrepayment,_that.note,_that.fee,_that.contributorId);case _:
  return null;

}
}

}

/// @nodoc


class _DebtPayment extends DebtPayment {
  const _DebtPayment({required this.meta, required this.debtId, required this.amount, required this.paidOn, this.isPrepayment = false, this.note, this.fee, this.contributorId}): super._();
  

@override final  SyncMeta meta;
@override final  String debtId;
@override final  Money amount;
@override final  LocalDate paidOn;
@override@JsonKey() final  bool isPrepayment;
@override final  String? note;
/// Qo'shimcha to'lovdan ushlangan jarima (v10, `amount` ichida).
@override final  Money? fee;
/// Kim to'ladi (`DebtContributor`); `null` — oilaning o'zi.
@override final  String? contributorId;

/// Create a copy of DebtPayment
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DebtPaymentCopyWith<_DebtPayment> get copyWith => __$DebtPaymentCopyWithImpl<_DebtPayment>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DebtPayment&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.debtId, debtId) || other.debtId == debtId)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.paidOn, paidOn) || other.paidOn == paidOn)&&(identical(other.isPrepayment, isPrepayment) || other.isPrepayment == isPrepayment)&&(identical(other.note, note) || other.note == note)&&(identical(other.fee, fee) || other.fee == fee)&&(identical(other.contributorId, contributorId) || other.contributorId == contributorId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,debtId,amount,paidOn,isPrepayment,note,fee,contributorId);

@override
String toString() {
  return 'DebtPayment(meta: $meta, debtId: $debtId, amount: $amount, paidOn: $paidOn, isPrepayment: $isPrepayment, note: $note, fee: $fee, contributorId: $contributorId)';
}


}

/// @nodoc
abstract mixin class _$DebtPaymentCopyWith<$Res> implements $DebtPaymentCopyWith<$Res> {
  factory _$DebtPaymentCopyWith(_DebtPayment value, $Res Function(_DebtPayment) _then) = __$DebtPaymentCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String debtId, Money amount, LocalDate paidOn, bool isPrepayment, String? note, Money? fee, String? contributorId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$DebtPaymentCopyWithImpl<$Res>
    implements _$DebtPaymentCopyWith<$Res> {
  __$DebtPaymentCopyWithImpl(this._self, this._then);

  final _DebtPayment _self;
  final $Res Function(_DebtPayment) _then;

/// Create a copy of DebtPayment
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? debtId = null,Object? amount = null,Object? paidOn = null,Object? isPrepayment = null,Object? note = freezed,Object? fee = freezed,Object? contributorId = freezed,}) {
  return _then(_DebtPayment(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,debtId: null == debtId ? _self.debtId : debtId // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,paidOn: null == paidOn ? _self.paidOn : paidOn // ignore: cast_nullable_to_non_nullable
as LocalDate,isPrepayment: null == isPrepayment ? _self.isPrepayment : isPrepayment // ignore: cast_nullable_to_non_nullable
as bool,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,fee: freezed == fee ? _self.fee : fee // ignore: cast_nullable_to_non_nullable
as Money?,contributorId: freezed == contributorId ? _self.contributorId : contributorId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of DebtPayment
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
mixin _$Receivable {

 SyncMeta get meta; String get debtorName; Money get principal; Money get remaining; LocalDate get dueDate; String? get reason; String? get note;
/// Create a copy of Receivable
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ReceivableCopyWith<Receivable> get copyWith => _$ReceivableCopyWithImpl<Receivable>(this as Receivable, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Receivable&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.debtorName, debtorName) || other.debtorName == debtorName)&&(identical(other.principal, principal) || other.principal == principal)&&(identical(other.remaining, remaining) || other.remaining == remaining)&&(identical(other.dueDate, dueDate) || other.dueDate == dueDate)&&(identical(other.reason, reason) || other.reason == reason)&&(identical(other.note, note) || other.note == note));
}


@override
int get hashCode => Object.hash(runtimeType,meta,debtorName,principal,remaining,dueDate,reason,note);

@override
String toString() {
  return 'Receivable(meta: $meta, debtorName: $debtorName, principal: $principal, remaining: $remaining, dueDate: $dueDate, reason: $reason, note: $note)';
}


}

/// @nodoc
abstract mixin class $ReceivableCopyWith<$Res>  {
  factory $ReceivableCopyWith(Receivable value, $Res Function(Receivable) _then) = _$ReceivableCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String debtorName, Money principal, Money remaining, LocalDate dueDate, String? reason, String? note
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$ReceivableCopyWithImpl<$Res>
    implements $ReceivableCopyWith<$Res> {
  _$ReceivableCopyWithImpl(this._self, this._then);

  final Receivable _self;
  final $Res Function(Receivable) _then;

/// Create a copy of Receivable
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? debtorName = null,Object? principal = null,Object? remaining = null,Object? dueDate = null,Object? reason = freezed,Object? note = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,debtorName: null == debtorName ? _self.debtorName : debtorName // ignore: cast_nullable_to_non_nullable
as String,principal: null == principal ? _self.principal : principal // ignore: cast_nullable_to_non_nullable
as Money,remaining: null == remaining ? _self.remaining : remaining // ignore: cast_nullable_to_non_nullable
as Money,dueDate: null == dueDate ? _self.dueDate : dueDate // ignore: cast_nullable_to_non_nullable
as LocalDate,reason: freezed == reason ? _self.reason : reason // ignore: cast_nullable_to_non_nullable
as String?,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of Receivable
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Receivable].
extension ReceivablePatterns on Receivable {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Receivable value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Receivable() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Receivable value)  $default,){
final _that = this;
switch (_that) {
case _Receivable():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Receivable value)?  $default,){
final _that = this;
switch (_that) {
case _Receivable() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String debtorName,  Money principal,  Money remaining,  LocalDate dueDate,  String? reason,  String? note)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Receivable() when $default != null:
return $default(_that.meta,_that.debtorName,_that.principal,_that.remaining,_that.dueDate,_that.reason,_that.note);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String debtorName,  Money principal,  Money remaining,  LocalDate dueDate,  String? reason,  String? note)  $default,) {final _that = this;
switch (_that) {
case _Receivable():
return $default(_that.meta,_that.debtorName,_that.principal,_that.remaining,_that.dueDate,_that.reason,_that.note);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String debtorName,  Money principal,  Money remaining,  LocalDate dueDate,  String? reason,  String? note)?  $default,) {final _that = this;
switch (_that) {
case _Receivable() when $default != null:
return $default(_that.meta,_that.debtorName,_that.principal,_that.remaining,_that.dueDate,_that.reason,_that.note);case _:
  return null;

}
}

}

/// @nodoc


class _Receivable extends Receivable {
  const _Receivable({required this.meta, required this.debtorName, required this.principal, required this.remaining, required this.dueDate, this.reason, this.note}): super._();
  

@override final  SyncMeta meta;
@override final  String debtorName;
@override final  Money principal;
@override final  Money remaining;
@override final  LocalDate dueDate;
@override final  String? reason;
@override final  String? note;

/// Create a copy of Receivable
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ReceivableCopyWith<_Receivable> get copyWith => __$ReceivableCopyWithImpl<_Receivable>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Receivable&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.debtorName, debtorName) || other.debtorName == debtorName)&&(identical(other.principal, principal) || other.principal == principal)&&(identical(other.remaining, remaining) || other.remaining == remaining)&&(identical(other.dueDate, dueDate) || other.dueDate == dueDate)&&(identical(other.reason, reason) || other.reason == reason)&&(identical(other.note, note) || other.note == note));
}


@override
int get hashCode => Object.hash(runtimeType,meta,debtorName,principal,remaining,dueDate,reason,note);

@override
String toString() {
  return 'Receivable(meta: $meta, debtorName: $debtorName, principal: $principal, remaining: $remaining, dueDate: $dueDate, reason: $reason, note: $note)';
}


}

/// @nodoc
abstract mixin class _$ReceivableCopyWith<$Res> implements $ReceivableCopyWith<$Res> {
  factory _$ReceivableCopyWith(_Receivable value, $Res Function(_Receivable) _then) = __$ReceivableCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String debtorName, Money principal, Money remaining, LocalDate dueDate, String? reason, String? note
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$ReceivableCopyWithImpl<$Res>
    implements _$ReceivableCopyWith<$Res> {
  __$ReceivableCopyWithImpl(this._self, this._then);

  final _Receivable _self;
  final $Res Function(_Receivable) _then;

/// Create a copy of Receivable
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? debtorName = null,Object? principal = null,Object? remaining = null,Object? dueDate = null,Object? reason = freezed,Object? note = freezed,}) {
  return _then(_Receivable(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,debtorName: null == debtorName ? _self.debtorName : debtorName // ignore: cast_nullable_to_non_nullable
as String,principal: null == principal ? _self.principal : principal // ignore: cast_nullable_to_non_nullable
as Money,remaining: null == remaining ? _self.remaining : remaining // ignore: cast_nullable_to_non_nullable
as Money,dueDate: null == dueDate ? _self.dueDate : dueDate // ignore: cast_nullable_to_non_nullable
as LocalDate,reason: freezed == reason ? _self.reason : reason // ignore: cast_nullable_to_non_nullable
as String?,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of Receivable
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
mixin _$Goal {

 SyncMeta get meta; String get title; Money get target; LocalDate? get targetDate;
/// Create a copy of Goal
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$GoalCopyWith<Goal> get copyWith => _$GoalCopyWithImpl<Goal>(this as Goal, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Goal&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.target, target) || other.target == target)&&(identical(other.targetDate, targetDate) || other.targetDate == targetDate));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,target,targetDate);

@override
String toString() {
  return 'Goal(meta: $meta, title: $title, target: $target, targetDate: $targetDate)';
}


}

/// @nodoc
abstract mixin class $GoalCopyWith<$Res>  {
  factory $GoalCopyWith(Goal value, $Res Function(Goal) _then) = _$GoalCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, Money target, LocalDate? targetDate
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$GoalCopyWithImpl<$Res>
    implements $GoalCopyWith<$Res> {
  _$GoalCopyWithImpl(this._self, this._then);

  final Goal _self;
  final $Res Function(Goal) _then;

/// Create a copy of Goal
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? target = null,Object? targetDate = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,target: null == target ? _self.target : target // ignore: cast_nullable_to_non_nullable
as Money,targetDate: freezed == targetDate ? _self.targetDate : targetDate // ignore: cast_nullable_to_non_nullable
as LocalDate?,
  ));
}
/// Create a copy of Goal
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Goal].
extension GoalPatterns on Goal {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Goal value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Goal() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Goal value)  $default,){
final _that = this;
switch (_that) {
case _Goal():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Goal value)?  $default,){
final _that = this;
switch (_that) {
case _Goal() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money target,  LocalDate? targetDate)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Goal() when $default != null:
return $default(_that.meta,_that.title,_that.target,_that.targetDate);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money target,  LocalDate? targetDate)  $default,) {final _that = this;
switch (_that) {
case _Goal():
return $default(_that.meta,_that.title,_that.target,_that.targetDate);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  Money target,  LocalDate? targetDate)?  $default,) {final _that = this;
switch (_that) {
case _Goal() when $default != null:
return $default(_that.meta,_that.title,_that.target,_that.targetDate);case _:
  return null;

}
}

}

/// @nodoc


class _Goal implements Goal {
  const _Goal({required this.meta, required this.title, required this.target, this.targetDate});
  

@override final  SyncMeta meta;
@override final  String title;
@override final  Money target;
@override final  LocalDate? targetDate;

/// Create a copy of Goal
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$GoalCopyWith<_Goal> get copyWith => __$GoalCopyWithImpl<_Goal>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Goal&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.target, target) || other.target == target)&&(identical(other.targetDate, targetDate) || other.targetDate == targetDate));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,target,targetDate);

@override
String toString() {
  return 'Goal(meta: $meta, title: $title, target: $target, targetDate: $targetDate)';
}


}

/// @nodoc
abstract mixin class _$GoalCopyWith<$Res> implements $GoalCopyWith<$Res> {
  factory _$GoalCopyWith(_Goal value, $Res Function(_Goal) _then) = __$GoalCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, Money target, LocalDate? targetDate
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$GoalCopyWithImpl<$Res>
    implements _$GoalCopyWith<$Res> {
  __$GoalCopyWithImpl(this._self, this._then);

  final _Goal _self;
  final $Res Function(_Goal) _then;

/// Create a copy of Goal
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? target = null,Object? targetDate = freezed,}) {
  return _then(_Goal(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,target: null == target ? _self.target : target // ignore: cast_nullable_to_non_nullable
as Money,targetDate: freezed == targetDate ? _self.targetDate : targetDate // ignore: cast_nullable_to_non_nullable
as LocalDate?,
  ));
}

/// Create a copy of Goal
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
mixin _$LoanSigner {

 SyncMeta get meta; String get documentId; SignerRole get role; String get name; List<int>? get signaturePng; DateTime? get signedAt;
/// Create a copy of LoanSigner
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$LoanSignerCopyWith<LoanSigner> get copyWith => _$LoanSignerCopyWithImpl<LoanSigner>(this as LoanSigner, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is LoanSigner&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.documentId, documentId) || other.documentId == documentId)&&(identical(other.role, role) || other.role == role)&&(identical(other.name, name) || other.name == name)&&const DeepCollectionEquality().equals(other.signaturePng, signaturePng)&&(identical(other.signedAt, signedAt) || other.signedAt == signedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,documentId,role,name,const DeepCollectionEquality().hash(signaturePng),signedAt);

@override
String toString() {
  return 'LoanSigner(meta: $meta, documentId: $documentId, role: $role, name: $name, signaturePng: $signaturePng, signedAt: $signedAt)';
}


}

/// @nodoc
abstract mixin class $LoanSignerCopyWith<$Res>  {
  factory $LoanSignerCopyWith(LoanSigner value, $Res Function(LoanSigner) _then) = _$LoanSignerCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String documentId, SignerRole role, String name, List<int>? signaturePng, DateTime? signedAt
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$LoanSignerCopyWithImpl<$Res>
    implements $LoanSignerCopyWith<$Res> {
  _$LoanSignerCopyWithImpl(this._self, this._then);

  final LoanSigner _self;
  final $Res Function(LoanSigner) _then;

/// Create a copy of LoanSigner
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? documentId = null,Object? role = null,Object? name = null,Object? signaturePng = freezed,Object? signedAt = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,documentId: null == documentId ? _self.documentId : documentId // ignore: cast_nullable_to_non_nullable
as String,role: null == role ? _self.role : role // ignore: cast_nullable_to_non_nullable
as SignerRole,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,signaturePng: freezed == signaturePng ? _self.signaturePng : signaturePng // ignore: cast_nullable_to_non_nullable
as List<int>?,signedAt: freezed == signedAt ? _self.signedAt : signedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}
/// Create a copy of LoanSigner
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [LoanSigner].
extension LoanSignerPatterns on LoanSigner {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _LoanSigner value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _LoanSigner() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _LoanSigner value)  $default,){
final _that = this;
switch (_that) {
case _LoanSigner():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _LoanSigner value)?  $default,){
final _that = this;
switch (_that) {
case _LoanSigner() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String documentId,  SignerRole role,  String name,  List<int>? signaturePng,  DateTime? signedAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _LoanSigner() when $default != null:
return $default(_that.meta,_that.documentId,_that.role,_that.name,_that.signaturePng,_that.signedAt);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String documentId,  SignerRole role,  String name,  List<int>? signaturePng,  DateTime? signedAt)  $default,) {final _that = this;
switch (_that) {
case _LoanSigner():
return $default(_that.meta,_that.documentId,_that.role,_that.name,_that.signaturePng,_that.signedAt);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String documentId,  SignerRole role,  String name,  List<int>? signaturePng,  DateTime? signedAt)?  $default,) {final _that = this;
switch (_that) {
case _LoanSigner() when $default != null:
return $default(_that.meta,_that.documentId,_that.role,_that.name,_that.signaturePng,_that.signedAt);case _:
  return null;

}
}

}

/// @nodoc


class _LoanSigner extends LoanSigner {
  const _LoanSigner({required this.meta, required this.documentId, required this.role, required this.name, final  List<int>? signaturePng, this.signedAt}): _signaturePng = signaturePng,super._();
  

@override final  SyncMeta meta;
@override final  String documentId;
@override final  SignerRole role;
@override final  String name;
 final  List<int>? _signaturePng;
@override List<int>? get signaturePng {
  final value = _signaturePng;
  if (value == null) return null;
  if (_signaturePng is EqualUnmodifiableListView) return _signaturePng;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(value);
}

@override final  DateTime? signedAt;

/// Create a copy of LoanSigner
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$LoanSignerCopyWith<_LoanSigner> get copyWith => __$LoanSignerCopyWithImpl<_LoanSigner>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _LoanSigner&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.documentId, documentId) || other.documentId == documentId)&&(identical(other.role, role) || other.role == role)&&(identical(other.name, name) || other.name == name)&&const DeepCollectionEquality().equals(other._signaturePng, _signaturePng)&&(identical(other.signedAt, signedAt) || other.signedAt == signedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,documentId,role,name,const DeepCollectionEquality().hash(_signaturePng),signedAt);

@override
String toString() {
  return 'LoanSigner(meta: $meta, documentId: $documentId, role: $role, name: $name, signaturePng: $signaturePng, signedAt: $signedAt)';
}


}

/// @nodoc
abstract mixin class _$LoanSignerCopyWith<$Res> implements $LoanSignerCopyWith<$Res> {
  factory _$LoanSignerCopyWith(_LoanSigner value, $Res Function(_LoanSigner) _then) = __$LoanSignerCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String documentId, SignerRole role, String name, List<int>? signaturePng, DateTime? signedAt
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$LoanSignerCopyWithImpl<$Res>
    implements _$LoanSignerCopyWith<$Res> {
  __$LoanSignerCopyWithImpl(this._self, this._then);

  final _LoanSigner _self;
  final $Res Function(_LoanSigner) _then;

/// Create a copy of LoanSigner
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? documentId = null,Object? role = null,Object? name = null,Object? signaturePng = freezed,Object? signedAt = freezed,}) {
  return _then(_LoanSigner(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,documentId: null == documentId ? _self.documentId : documentId // ignore: cast_nullable_to_non_nullable
as String,role: null == role ? _self.role : role // ignore: cast_nullable_to_non_nullable
as SignerRole,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,signaturePng: freezed == signaturePng ? _self._signaturePng : signaturePng // ignore: cast_nullable_to_non_nullable
as List<int>?,signedAt: freezed == signedAt ? _self.signedAt : signedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}

/// Create a copy of LoanSigner
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
mixin _$DebtContributor {

 SyncMeta get meta; String get debtId; String get name; String? get memberId; Money? get monthlyShare;
/// Create a copy of DebtContributor
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DebtContributorCopyWith<DebtContributor> get copyWith => _$DebtContributorCopyWithImpl<DebtContributor>(this as DebtContributor, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DebtContributor&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.debtId, debtId) || other.debtId == debtId)&&(identical(other.name, name) || other.name == name)&&(identical(other.memberId, memberId) || other.memberId == memberId)&&(identical(other.monthlyShare, monthlyShare) || other.monthlyShare == monthlyShare));
}


@override
int get hashCode => Object.hash(runtimeType,meta,debtId,name,memberId,monthlyShare);

@override
String toString() {
  return 'DebtContributor(meta: $meta, debtId: $debtId, name: $name, memberId: $memberId, monthlyShare: $monthlyShare)';
}


}

/// @nodoc
abstract mixin class $DebtContributorCopyWith<$Res>  {
  factory $DebtContributorCopyWith(DebtContributor value, $Res Function(DebtContributor) _then) = _$DebtContributorCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String debtId, String name, String? memberId, Money? monthlyShare
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$DebtContributorCopyWithImpl<$Res>
    implements $DebtContributorCopyWith<$Res> {
  _$DebtContributorCopyWithImpl(this._self, this._then);

  final DebtContributor _self;
  final $Res Function(DebtContributor) _then;

/// Create a copy of DebtContributor
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? debtId = null,Object? name = null,Object? memberId = freezed,Object? monthlyShare = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,debtId: null == debtId ? _self.debtId : debtId // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,monthlyShare: freezed == monthlyShare ? _self.monthlyShare : monthlyShare // ignore: cast_nullable_to_non_nullable
as Money?,
  ));
}
/// Create a copy of DebtContributor
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [DebtContributor].
extension DebtContributorPatterns on DebtContributor {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DebtContributor value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DebtContributor() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DebtContributor value)  $default,){
final _that = this;
switch (_that) {
case _DebtContributor():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DebtContributor value)?  $default,){
final _that = this;
switch (_that) {
case _DebtContributor() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String debtId,  String name,  String? memberId,  Money? monthlyShare)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DebtContributor() when $default != null:
return $default(_that.meta,_that.debtId,_that.name,_that.memberId,_that.monthlyShare);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String debtId,  String name,  String? memberId,  Money? monthlyShare)  $default,) {final _that = this;
switch (_that) {
case _DebtContributor():
return $default(_that.meta,_that.debtId,_that.name,_that.memberId,_that.monthlyShare);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String debtId,  String name,  String? memberId,  Money? monthlyShare)?  $default,) {final _that = this;
switch (_that) {
case _DebtContributor() when $default != null:
return $default(_that.meta,_that.debtId,_that.name,_that.memberId,_that.monthlyShare);case _:
  return null;

}
}

}

/// @nodoc


class _DebtContributor implements DebtContributor {
  const _DebtContributor({required this.meta, required this.debtId, required this.name, this.memberId, this.monthlyShare});
  

@override final  SyncMeta meta;
@override final  String debtId;
@override final  String name;
@override final  String? memberId;
@override final  Money? monthlyShare;

/// Create a copy of DebtContributor
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DebtContributorCopyWith<_DebtContributor> get copyWith => __$DebtContributorCopyWithImpl<_DebtContributor>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DebtContributor&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.debtId, debtId) || other.debtId == debtId)&&(identical(other.name, name) || other.name == name)&&(identical(other.memberId, memberId) || other.memberId == memberId)&&(identical(other.monthlyShare, monthlyShare) || other.monthlyShare == monthlyShare));
}


@override
int get hashCode => Object.hash(runtimeType,meta,debtId,name,memberId,monthlyShare);

@override
String toString() {
  return 'DebtContributor(meta: $meta, debtId: $debtId, name: $name, memberId: $memberId, monthlyShare: $monthlyShare)';
}


}

/// @nodoc
abstract mixin class _$DebtContributorCopyWith<$Res> implements $DebtContributorCopyWith<$Res> {
  factory _$DebtContributorCopyWith(_DebtContributor value, $Res Function(_DebtContributor) _then) = __$DebtContributorCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String debtId, String name, String? memberId, Money? monthlyShare
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$DebtContributorCopyWithImpl<$Res>
    implements _$DebtContributorCopyWith<$Res> {
  __$DebtContributorCopyWithImpl(this._self, this._then);

  final _DebtContributor _self;
  final $Res Function(_DebtContributor) _then;

/// Create a copy of DebtContributor
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? debtId = null,Object? name = null,Object? memberId = freezed,Object? monthlyShare = freezed,}) {
  return _then(_DebtContributor(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,debtId: null == debtId ? _self.debtId : debtId // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,monthlyShare: freezed == monthlyShare ? _self.monthlyShare : monthlyShare // ignore: cast_nullable_to_non_nullable
as Money?,
  ));
}

/// Create a copy of DebtContributor
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
mixin _$SellableItem {

 SyncMeta get meta; String get name; Money get estimated; SellableStatus get status; Money? get soldFor; LocalDate? get soldOn;/// Puli yo'naltirilgan qarz; `null` — hali yo'naltirilmagan.
 String? get debtId; String? get paymentId;
/// Create a copy of SellableItem
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$SellableItemCopyWith<SellableItem> get copyWith => _$SellableItemCopyWithImpl<SellableItem>(this as SellableItem, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is SellableItem&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.name, name) || other.name == name)&&(identical(other.estimated, estimated) || other.estimated == estimated)&&(identical(other.status, status) || other.status == status)&&(identical(other.soldFor, soldFor) || other.soldFor == soldFor)&&(identical(other.soldOn, soldOn) || other.soldOn == soldOn)&&(identical(other.debtId, debtId) || other.debtId == debtId)&&(identical(other.paymentId, paymentId) || other.paymentId == paymentId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,name,estimated,status,soldFor,soldOn,debtId,paymentId);

@override
String toString() {
  return 'SellableItem(meta: $meta, name: $name, estimated: $estimated, status: $status, soldFor: $soldFor, soldOn: $soldOn, debtId: $debtId, paymentId: $paymentId)';
}


}

/// @nodoc
abstract mixin class $SellableItemCopyWith<$Res>  {
  factory $SellableItemCopyWith(SellableItem value, $Res Function(SellableItem) _then) = _$SellableItemCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String name, Money estimated, SellableStatus status, Money? soldFor, LocalDate? soldOn, String? debtId, String? paymentId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$SellableItemCopyWithImpl<$Res>
    implements $SellableItemCopyWith<$Res> {
  _$SellableItemCopyWithImpl(this._self, this._then);

  final SellableItem _self;
  final $Res Function(SellableItem) _then;

/// Create a copy of SellableItem
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? name = null,Object? estimated = null,Object? status = null,Object? soldFor = freezed,Object? soldOn = freezed,Object? debtId = freezed,Object? paymentId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,estimated: null == estimated ? _self.estimated : estimated // ignore: cast_nullable_to_non_nullable
as Money,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as SellableStatus,soldFor: freezed == soldFor ? _self.soldFor : soldFor // ignore: cast_nullable_to_non_nullable
as Money?,soldOn: freezed == soldOn ? _self.soldOn : soldOn // ignore: cast_nullable_to_non_nullable
as LocalDate?,debtId: freezed == debtId ? _self.debtId : debtId // ignore: cast_nullable_to_non_nullable
as String?,paymentId: freezed == paymentId ? _self.paymentId : paymentId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of SellableItem
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [SellableItem].
extension SellableItemPatterns on SellableItem {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _SellableItem value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _SellableItem() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _SellableItem value)  $default,){
final _that = this;
switch (_that) {
case _SellableItem():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _SellableItem value)?  $default,){
final _that = this;
switch (_that) {
case _SellableItem() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String name,  Money estimated,  SellableStatus status,  Money? soldFor,  LocalDate? soldOn,  String? debtId,  String? paymentId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _SellableItem() when $default != null:
return $default(_that.meta,_that.name,_that.estimated,_that.status,_that.soldFor,_that.soldOn,_that.debtId,_that.paymentId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String name,  Money estimated,  SellableStatus status,  Money? soldFor,  LocalDate? soldOn,  String? debtId,  String? paymentId)  $default,) {final _that = this;
switch (_that) {
case _SellableItem():
return $default(_that.meta,_that.name,_that.estimated,_that.status,_that.soldFor,_that.soldOn,_that.debtId,_that.paymentId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String name,  Money estimated,  SellableStatus status,  Money? soldFor,  LocalDate? soldOn,  String? debtId,  String? paymentId)?  $default,) {final _that = this;
switch (_that) {
case _SellableItem() when $default != null:
return $default(_that.meta,_that.name,_that.estimated,_that.status,_that.soldFor,_that.soldOn,_that.debtId,_that.paymentId);case _:
  return null;

}
}

}

/// @nodoc


class _SellableItem extends SellableItem {
  const _SellableItem({required this.meta, required this.name, required this.estimated, this.status = SellableStatus.listed, this.soldFor, this.soldOn, this.debtId, this.paymentId}): super._();
  

@override final  SyncMeta meta;
@override final  String name;
@override final  Money estimated;
@override@JsonKey() final  SellableStatus status;
@override final  Money? soldFor;
@override final  LocalDate? soldOn;
/// Puli yo'naltirilgan qarz; `null` — hali yo'naltirilmagan.
@override final  String? debtId;
@override final  String? paymentId;

/// Create a copy of SellableItem
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$SellableItemCopyWith<_SellableItem> get copyWith => __$SellableItemCopyWithImpl<_SellableItem>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _SellableItem&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.name, name) || other.name == name)&&(identical(other.estimated, estimated) || other.estimated == estimated)&&(identical(other.status, status) || other.status == status)&&(identical(other.soldFor, soldFor) || other.soldFor == soldFor)&&(identical(other.soldOn, soldOn) || other.soldOn == soldOn)&&(identical(other.debtId, debtId) || other.debtId == debtId)&&(identical(other.paymentId, paymentId) || other.paymentId == paymentId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,name,estimated,status,soldFor,soldOn,debtId,paymentId);

@override
String toString() {
  return 'SellableItem(meta: $meta, name: $name, estimated: $estimated, status: $status, soldFor: $soldFor, soldOn: $soldOn, debtId: $debtId, paymentId: $paymentId)';
}


}

/// @nodoc
abstract mixin class _$SellableItemCopyWith<$Res> implements $SellableItemCopyWith<$Res> {
  factory _$SellableItemCopyWith(_SellableItem value, $Res Function(_SellableItem) _then) = __$SellableItemCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String name, Money estimated, SellableStatus status, Money? soldFor, LocalDate? soldOn, String? debtId, String? paymentId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$SellableItemCopyWithImpl<$Res>
    implements _$SellableItemCopyWith<$Res> {
  __$SellableItemCopyWithImpl(this._self, this._then);

  final _SellableItem _self;
  final $Res Function(_SellableItem) _then;

/// Create a copy of SellableItem
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? name = null,Object? estimated = null,Object? status = null,Object? soldFor = freezed,Object? soldOn = freezed,Object? debtId = freezed,Object? paymentId = freezed,}) {
  return _then(_SellableItem(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,estimated: null == estimated ? _self.estimated : estimated // ignore: cast_nullable_to_non_nullable
as Money,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as SellableStatus,soldFor: freezed == soldFor ? _self.soldFor : soldFor // ignore: cast_nullable_to_non_nullable
as Money?,soldOn: freezed == soldOn ? _self.soldOn : soldOn // ignore: cast_nullable_to_non_nullable
as LocalDate?,debtId: freezed == debtId ? _self.debtId : debtId // ignore: cast_nullable_to_non_nullable
as String?,paymentId: freezed == paymentId ? _self.paymentId : paymentId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of SellableItem
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
