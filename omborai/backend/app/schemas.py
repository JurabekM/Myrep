import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ---------------------------------------------------------------------------
# Auth va tenant
# ---------------------------------------------------------------------------


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    tenant_name: str = Field(min_length=2, max_length=200, description="Do'kon egasi hisobi nomi")
    store_name: str = Field(min_length=2, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=256)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token turi, parol emas
    expires_in: int


class StoreIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


class MembershipOut(BaseModel):
    store_id: uuid.UUID | None
    role: str


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    tenant_id: uuid.UUID
    memberships: list[MembershipOut]


# ---------------------------------------------------------------------------
# Katalog (tovar, kategoriya, yetkazuvchi)
# ---------------------------------------------------------------------------

Unit = Literal["dona", "kg", "litr", "metr", "quti", "paket"]
BARCODE_RE = re.compile(r"^[A-Za-z0-9-]{4,64}$")
MAX_MONEY = 10**12


def _clean_barcodes(value: list[str]) -> list[str]:
    cleaned = [code.strip() for code in value]
    for code in cleaned:
        if not BARCODE_RE.match(code):
            raise ValueError(f"Noto'g'ri shtrix-kod: {code!r}")
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("Shtrix-kodlar takrorlangan")
    return cleaned


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    unit: Unit = "dona"
    category_id: uuid.UUID | None = None
    sale_price: int = Field(ge=0, le=MAX_MONEY, description="So'mda, butun son")
    cost_price: int = Field(default=0, ge=0, le=MAX_MONEY)
    min_stock: Decimal = Field(default=Decimal(0), ge=0)
    barcodes: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("barcodes")
    @classmethod
    def _check_barcodes(cls, value: list[str]) -> list[str]:
        return _clean_barcodes(value)


class ProductPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    unit: Unit | None = None
    category_id: uuid.UUID | None = None
    sale_price: int | None = Field(default=None, ge=0, le=MAX_MONEY)
    cost_price: int | None = Field(default=None, ge=0, le=MAX_MONEY)
    min_stock: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None
    barcodes: list[str] | None = Field(default=None, max_length=10)

    @field_validator("barcodes")
    @classmethod
    def _check_barcodes(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _clean_barcodes(value)


class ProductOut(BaseModel):
    id: uuid.UUID
    name: str
    unit: str
    category_id: uuid.UUID | None
    sale_price: int
    cost_price: int
    min_stock: Decimal
    is_active: bool
    barcodes: list[str]
    stock_qty: Decimal | None = None
    version: int


class ProductPage(BaseModel):
    items: list[ProductOut]
    next_cursor: uuid.UUID | None


class SupplierIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=32)


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    phone: str | None


# ---------------------------------------------------------------------------
# Kirim, ombor harakatlari, qoldiq
# ---------------------------------------------------------------------------


class PurchaseItemIn(BaseModel):
    product_id: uuid.UUID
    qty: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit_cost: int = Field(ge=0, le=MAX_MONEY)


class PurchaseIn(BaseModel):
    store_id: uuid.UUID
    supplier_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=300)
    items: list[PurchaseItemIn] = Field(min_length=1, max_length=200)


class PurchaseItemOut(BaseModel):
    product_id: uuid.UUID
    qty: Decimal
    unit_cost: int


class PurchaseOut(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    supplier_id: uuid.UUID | None
    note: str | None
    total_cost: int
    created_at: datetime
    items: list[PurchaseItemOut]


class MovementIn(BaseModel):
    store_id: uuid.UUID
    product_id: uuid.UUID
    kind: Literal["adjustment", "writeoff"]
    qty: Decimal = Field(
        max_digits=14,
        decimal_places=3,
        description="adjustment: ishorali (+ qo'shish, - kamaytirish); writeoff: musbat miqdor",
    )
    note: str | None = Field(default=None, max_length=300)


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    product_id: uuid.UUID
    qty: Decimal
    kind: str
    reference_type: str | None
    reference_id: uuid.UUID | None
    note: str | None
    created_by: uuid.UUID
    created_at: datetime


class BalanceOut(BaseModel):
    product_id: uuid.UUID
    name: str
    unit: str
    qty: Decimal
    min_stock: Decimal
    low: bool


# ---------------------------------------------------------------------------
# Faza 3: kassa smenasi va savdo
# ---------------------------------------------------------------------------

PaymentMethod = Literal["cash", "card", "click", "payme"]


class SaleItemIn(BaseModel):
    product_id: uuid.UUID
    qty: Decimal = Field(gt=0, max_digits=14, decimal_places=3)


class PaymentIn(BaseModel):
    method: PaymentMethod
    amount: int = Field(gt=0, le=MAX_MONEY)


class SaleIn(BaseModel):
    id: uuid.UUID = Field(description="Klient tomonidan yaratilgan UUID (idempotentlik kaliti)")
    store_id: uuid.UUID
    items: list[SaleItemIn] = Field(min_length=1, max_length=200)
    discount: int = Field(default=0, ge=0, le=MAX_MONEY)
    payments: list[PaymentIn] = Field(min_length=1, max_length=5)
    client_created_at: datetime | None = None


class SaleItemOut(BaseModel):
    product_id: uuid.UUID
    product_name: str
    unit: str
    qty: Decimal
    unit_price: int
    line_total: int


class PaymentOut(BaseModel):
    method: str
    amount: int


class SaleOut(BaseModel):
    id: uuid.UUID
    number: int
    store_id: uuid.UUID
    shift_id: uuid.UUID
    status: str
    subtotal: int
    discount: int
    total: int
    created_by: uuid.UUID
    created_at: datetime
    client_created_at: datetime | None
    items: list[SaleItemOut]
    payments: list[PaymentOut]


class ShiftOpenIn(BaseModel):
    store_id: uuid.UUID
    opening_cash: int = Field(default=0, ge=0, le=MAX_MONEY)


class ShiftCloseIn(BaseModel):
    closing_cash: int = Field(ge=0, le=MAX_MONEY)


class ShiftOut(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    opened_by: uuid.UUID
    opened_at: datetime
    closed_at: datetime | None
    opening_cash: int
    closing_cash: int | None


class ShiftSummaryOut(BaseModel):
    shift: ShiftOut
    sales_count: int
    total_sales: int
    refunds_count: int
    total_refunds: int
    by_method: dict[str, int]
    expected_cash: int
    closing_cash: int | None
    difference: int | None


# ---------------------------------------------------------------------------
# Faza 4: offline sinxronizatsiya (push / pull)
# ---------------------------------------------------------------------------
from typing import Annotated  # noqa: E402

from pydantic import model_validator  # noqa: E402


class SyncSaleOp(BaseModel):
    type: Literal["sale"]
    op_id: uuid.UUID
    payload: SaleIn

    @model_validator(mode="after")
    def _same_id(self) -> "SyncSaleOp":
        if self.payload.id != self.op_id:
            raise ValueError("Savdo uchun op_id va payload.id bir xil bo'lishi kerak")
        return self


class SyncMovementOp(BaseModel):
    type: Literal["movement"]
    op_id: uuid.UUID
    payload: MovementIn


SyncOpIn = Annotated[SyncSaleOp | SyncMovementOp, Field(discriminator="type")]


class SyncPushIn(BaseModel):
    ops: list[SyncOpIn] = Field(min_length=1, max_length=100)


class SyncResultOut(BaseModel):
    op_id: uuid.UUID
    status: Literal["applied", "rejected"]
    duplicate: bool = False
    error_title: str | None = None
    error_detail: str | None = None


class SyncPushOut(BaseModel):
    results: list[SyncResultOut]


class SyncProductOut(BaseModel):
    id: uuid.UUID
    name: str
    unit: str
    category_id: uuid.UUID | None
    sale_price: int
    cost_price: int
    min_stock: Decimal
    is_active: bool
    barcodes: list[str]
    version: int
    deleted: bool


class SyncPullOut(BaseModel):
    products: list[SyncProductOut]
    movements: list[MovementOut]
    sales: list["SaleOut"]
    cursors: dict[str, str]
    has_more: bool
