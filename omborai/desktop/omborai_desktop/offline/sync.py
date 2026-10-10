"""Sinxronizatsiya: avval navbatdagi operatsiyalar yuboriladi (push), keyin o'zgarishlar olinadi (pull)."""

from dataclasses import dataclass

from ..api import ApiClient
from .store import LocalStore


@dataclass(frozen=True)
class SyncReport:
    pushed: int
    applied: int
    rejected: int
    pulled_products: int
    pulled_movements: int


class SyncService:
    def __init__(self, api: ApiClient, local: LocalStore, batch_size: int = 100) -> None:
        self._api = api
        self._local = local
        self._batch = batch_size

    def run_once(self, store_id: str) -> SyncReport:
        pushed, applied, rejected = self._push()
        products, movements = self._pull(store_id)
        return SyncReport(pushed, applied, rejected, products, movements)

    def _push(self) -> tuple[int, int, int]:
        total = applied = rejected = 0
        while True:
            ops = self._local.pending_ops(limit=self._batch)
            if not ops:
                break
            body = {"ops": [{"type": op.op_type, "op_id": op.op_id, "payload": op.payload} for op in ops]}
            results = self._api.sync_push(body)["results"]
            self._local.apply_push_results(results)
            total += len(ops)
            applied += sum(1 for r in results if r["status"] == "applied")
            rejected += sum(1 for r in results if r["status"] == "rejected")
            if len(ops) < self._batch:
                break
        return total, applied, rejected

    def _pull(self, store_id: str) -> tuple[int, int]:
        products = movements = 0
        while True:
            page = self._api.sync_pull(store_id, self._local.cursors())
            self._local.apply_pull(page)
            products += len(page["products"])
            movements += len(page["movements"])
            if not page["has_more"]:
                break
        return products, movements
