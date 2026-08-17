from fastapi import APIRouter

from app.api.v1 import (
    auth,
    banks,
    budgets,
    categories,
    challenges,
    debts,
    family,
    gamification,
    goals,
    loans,
    payments,
    reports,
    sync,
    transactions,
    wallets,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(wallets.router)
api_router.include_router(transactions.router)
api_router.include_router(budgets.router)
api_router.include_router(goals.router)
api_router.include_router(loans.router)
api_router.include_router(debts.router)
api_router.include_router(sync.router)
api_router.include_router(payments.router)
api_router.include_router(banks.router)
api_router.include_router(reports.router)
api_router.include_router(gamification.router)
api_router.include_router(challenges.router)
api_router.include_router(family.router)
