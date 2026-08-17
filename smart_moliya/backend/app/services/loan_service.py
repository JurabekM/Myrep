import uuid
from datetime import date
from decimal import Decimal

from app.models.loan import Loan
from app.repositories.loan_repository import LoanRepository
from app.schemas.loan import LoanCreate, LoanStatus


class LoanService:
    def __init__(self, loan_repository: LoanRepository):
        self.loan_repository = loan_repository

    async def create_loan(self, user_id: uuid.UUID, data: LoanCreate) -> Loan:
        loan = Loan(
            user_id=user_id,
            principal=data.principal,
            interest_rate=data.interest_rate,
            due_date=data.due_date,
            penalty_rate_per_day=data.penalty_rate_per_day,
        )
        loan = await self.loan_repository.add(loan)
        await self.loan_repository.commit()
        return loan

    async def list_with_status(self, user_id: uuid.UUID) -> list[LoanStatus]:
        loans = await self.loan_repository.list_by_user(user_id)
        today = date.today()
        return [
            LoanStatus(
                id=loan.id,
                principal=loan.principal,
                interest_rate=loan.interest_rate,
                due_date=loan.due_date,
                penalty_rate_per_day=loan.penalty_rate_per_day,
                current_penalty=Decimal(str(loan.calculate_penalty(today))),
                is_overdue=today > loan.due_date,
            )
            for loan in loans
        ]
