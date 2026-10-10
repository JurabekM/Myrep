import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import Principal, get_principal, require_roles
from ..errors import ProblemError
from ..models import Category, Product, ProductBarcode, StockMovement, Supplier
from ..schemas import (
    CategoryIn,
    CategoryOut,
    ProductIn,
    ProductOut,
    ProductPage,
    ProductPatch,
    SupplierIn,
    SupplierOut,
)

router = APIRouter(tags=["catalog"])

WRITE_ROLES = ("owner", "manager", "warehouse")
ADMIN_ROLES = ("owner", "manager")


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _to_out(
    session: AsyncSession,
    products: list[Product],
    store_id: uuid.UUID | None,
) -> list[ProductOut]:
    """Tovarlarni barcode va (ixtiyoriy) filial qoldig'i bilan birga qaytaradi: 2 ta so'rov, N+1 yo'q."""
    if not products:
        return []
    ids = [p.id for p in products]

    codes: dict[uuid.UUID, list[str]] = {pid: [] for pid in ids}
    rows = await session.execute(
        select(ProductBarcode.product_id, ProductBarcode.barcode).where(
            ProductBarcode.product_id.in_(ids), ProductBarcode.deleted_at.is_(None)
        )
    )
    for pid, code in rows.all():
        codes[pid].append(code)

    stock: dict[uuid.UUID, Decimal] = {}
    if store_id is not None:
        rows = await session.execute(
            select(StockMovement.product_id, func.sum(StockMovement.qty))
            .where(StockMovement.store_id == store_id, StockMovement.product_id.in_(ids))
            .group_by(StockMovement.product_id)
        )
        stock = {pid: Decimal(qty) for pid, qty in rows.all()}

    return [
        ProductOut(
            id=p.id,
            name=p.name,
            unit=p.unit,
            category_id=p.category_id,
            sale_price=p.sale_price,
            cost_price=p.cost_price,
            min_stock=p.min_stock,
            is_active=p.is_active,
            barcodes=sorted(codes[p.id]),
            stock_qty=stock.get(p.id, Decimal("0.000")) if store_id is not None else None,
            version=p.version,
        )
        for p in products
    ]


async def _replace_barcodes(
    session: AsyncSession, tenant_id: uuid.UUID, product_id: uuid.UUID, codes: list[str]
) -> None:
    await session.execute(delete(ProductBarcode).where(ProductBarcode.product_id == product_id))
    for code in codes:
        session.add(ProductBarcode(tenant_id=tenant_id, product_id=product_id, barcode=code))
    await session.flush()


async def _load_product(session: AsyncSession, product_id: uuid.UUID) -> Product:
    product = await session.scalar(
        select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
    )
    if product is None:
        raise ProblemError(404, "Tovar topilmadi")
    return product


async def _ensure_category(session: AsyncSession, category_id: uuid.UUID | None) -> None:
    if category_id is None:
        return
    found = await session.scalar(
        select(Category.id).where(Category.id == category_id, Category.deleted_at.is_(None))
    )
    if found is None:
        raise ProblemError(422, "Kategoriya topilmadi")


def _barcode_conflict(exc: IntegrityError) -> ProblemError:
    return ProblemError(409, "Shtrix-kod band", "Bu shtrix-kod boshqa tovarga biriktirilgan")


# ---------------------------------------------------------------------------
# Kategoriyalar
# ---------------------------------------------------------------------------

categories = APIRouter(prefix="/categories", tags=["catalog"])


@categories.get("", response_model=list[CategoryOut])
async def list_categories(
    _: Principal = Depends(get_principal), session: AsyncSession = Depends(get_db)
) -> list[Category]:
    rows = await session.execute(
        select(Category).where(Category.deleted_at.is_(None)).order_by(Category.name)
    )
    return list(rows.scalars().all())


@categories.post("", status_code=201, response_model=CategoryOut)
async def create_category(
    body: CategoryIn,
    principal: Principal = Depends(require_roles(*ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> Category:
    category = Category(tenant_id=principal.tenant_id, name=body.name)
    session.add(category)
    try:
        await session.commit()
    except IntegrityError as exc:
        raise ProblemError(409, "Kategoriya mavjud") from exc
    return category


# ---------------------------------------------------------------------------
# Yetkazuvchilar
# ---------------------------------------------------------------------------

suppliers_router = APIRouter(prefix="/suppliers", tags=["catalog"])


@suppliers_router.get("", response_model=list[SupplierOut])
async def list_suppliers(
    _: Principal = Depends(get_principal), session: AsyncSession = Depends(get_db)
) -> list[Supplier]:
    rows = await session.execute(
        select(Supplier).where(Supplier.deleted_at.is_(None)).order_by(Supplier.name)
    )
    return list(rows.scalars().all())


@suppliers_router.post("", status_code=201, response_model=SupplierOut)
async def create_supplier(
    body: SupplierIn,
    principal: Principal = Depends(require_roles(*WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> Supplier:
    supplier = Supplier(tenant_id=principal.tenant_id, name=body.name, phone=body.phone)
    session.add(supplier)
    await session.commit()
    return supplier


# ---------------------------------------------------------------------------
# Tovarlar
# ---------------------------------------------------------------------------

products = APIRouter(prefix="/products", tags=["catalog"])


@products.get("", response_model=ProductPage)
async def list_products(
    q: str | None = Query(default=None, max_length=100, description="Nom yoki shtrix-kod bo'yicha"),
    store_id: uuid.UUID | None = None,
    low_stock: bool = False,
    cursor: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> ProductPage:
    """Keyset pagination: cursor — oxirgi ko'rilgan tovar id'si."""
    stmt = select(Product).where(Product.deleted_at.is_(None))

    if q:
        pattern = f"%{_escape_like(q.strip())}%"
        by_code = select(ProductBarcode.product_id).where(ProductBarcode.barcode == q.strip())
        stmt = stmt.where(Product.name.ilike(pattern, escape="\\") | Product.id.in_(by_code))

    if low_stock:
        if store_id is None:
            raise ProblemError(422, "low_stock uchun store_id kerak")
        bal = (
            select(StockMovement.product_id, func.sum(StockMovement.qty).label("qty"))
            .where(StockMovement.store_id == store_id)
            .group_by(StockMovement.product_id)
            .subquery()
        )
        stmt = stmt.join(bal, bal.c.product_id == Product.id).where(bal.c.qty < Product.min_stock)

    if cursor is not None:
        stmt = stmt.where(Product.id > cursor)

    rows = await session.execute(stmt.order_by(Product.id).limit(limit + 1))
    found = list(rows.scalars().all())
    has_more = len(found) > limit
    page = found[:limit]
    return ProductPage(
        items=await _to_out(session, page, store_id),
        next_cursor=page[-1].id if has_more and page else None,
    )


@products.get("/by-barcode/{code}", response_model=ProductOut)
async def get_by_barcode(
    code: str,
    store_id: uuid.UUID | None = None,
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> ProductOut:
    """Kassa skaneri uchun: shtrix-kod bo'yicha tezkor qidiruv."""
    product = await session.scalar(
        select(Product)
        .join(ProductBarcode, ProductBarcode.product_id == Product.id)
        .where(ProductBarcode.barcode == code, Product.deleted_at.is_(None))
    )
    if product is None:
        raise ProblemError(404, "Tovar topilmadi", "Bu shtrix-kod bo'yicha tovar yo'q")
    return (await _to_out(session, [product], store_id))[0]


@products.post("", status_code=201, response_model=ProductOut)
async def create_product(
    body: ProductIn,
    store_id: uuid.UUID | None = None,
    principal: Principal = Depends(require_roles(*WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> ProductOut:
    await _ensure_category(session, body.category_id)
    product = Product(
        tenant_id=principal.tenant_id,
        category_id=body.category_id,
        name=body.name,
        unit=body.unit,
        sale_price=body.sale_price,
        cost_price=body.cost_price,
        min_stock=body.min_stock,
    )
    session.add(product)
    try:
        await session.flush()
        await _replace_barcodes(session, principal.tenant_id, product.id, body.barcodes)
        await session.commit()
    except IntegrityError as exc:
        raise _barcode_conflict(exc) from exc
    return (await _to_out(session, [product], store_id))[0]


@products.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = None,
    _: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_db),
) -> ProductOut:
    product = await _load_product(session, product_id)
    return (await _to_out(session, [product], store_id))[0]


@products.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: uuid.UUID,
    body: ProductPatch,
    store_id: uuid.UUID | None = None,
    principal: Principal = Depends(require_roles(*WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> ProductOut:
    product = await _load_product(session, product_id)
    data = body.model_dump(exclude_unset=True)
    codes = data.pop("barcodes", None)

    if "category_id" in data:
        await _ensure_category(session, data["category_id"])
    for field, value in data.items():
        setattr(product, field, value)
    product.version += 1

    try:
        if codes is not None:
            await _replace_barcodes(session, principal.tenant_id, product.id, codes)
        await session.commit()
    except IntegrityError as exc:
        raise _barcode_conflict(exc) from exc
    return (await _to_out(session, [product], store_id))[0]


@products.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    principal: Principal = Depends(require_roles(*ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Yumshoq o'chirish: tarix (ledger, cheklar) saqlanadi."""
    product = await _load_product(session, product_id)
    product.deleted_at = func.now()
    product.version += 1
    await session.commit()
    return Response(status_code=204)
