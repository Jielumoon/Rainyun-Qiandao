"""账户管理路由。"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Body, Depends

from rainyun.data.models import Account
from rainyun.data.store import DataStore
from rainyun.web.deps import get_store, require_auth
from rainyun.web.errors import ApiError
from rainyun.web.responses import success_response

router = APIRouter(prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(require_auth)])


@router.get("")
def list_accounts(store: DataStore = Depends(get_store)) -> dict:
    data = store.load()
    accounts = [account.to_dict() for account in data.accounts]
    return success_response(accounts)


@router.post("")
def create_account(
    payload: dict = Body(default_factory=dict), store: DataStore = Depends(get_store)
) -> dict:
    data = store.load()
    account = Account.from_dict(payload)
    if not account.id:
        account.id = f"acc_{uuid4().hex[:8]}"
    try:
        store.add_account(account)
    except ValueError as exc:
        raise ApiError(str(exc)) from exc
    return success_response(account.to_dict())


@router.get("/{account_id}")
def get_account(account_id: str, store: DataStore = Depends(get_store)) -> dict:
    data = store.load()
    account = next((item for item in data.accounts if item.id == account_id), None)
    if not account:
        raise ApiError("账户不存在", status_code=404)
    return success_response(account.to_dict())


@router.put("/{account_id}")
def update_account(
    account_id: str,
    payload: dict = Body(default_factory=dict),
    store: DataStore = Depends(get_store),
) -> dict:
    data = store.load()
    existing = next((item for item in data.accounts if item.id == account_id), None)
    if not existing:
        raise ApiError("账户不存在", status_code=404)
    account = Account.from_dict(existing.to_dict())
    patch = Account.from_dict(payload)
    account.name = patch.name or account.name
    account.username = patch.username or account.username
    if patch.password:
        account.password = patch.password
    account.api_key = patch.api_key or account.api_key
    account.enabled = patch.enabled
    account.auto_renew = patch.auto_renew
    account.renew_products = patch.renew_products
    account.id = account_id
    try:
        store.update_account(account)
    except KeyError as exc:
        raise ApiError("账户不存在", status_code=404) from exc
    return success_response(account.to_dict())


@router.delete("/{account_id}")
def delete_account(account_id: str, store: DataStore = Depends(get_store)) -> dict:
    store.load()
    deleted = store.delete_account(account_id)
    if not deleted:
        raise ApiError("账户不存在", status_code=404)
    return success_response({"deleted": True})
