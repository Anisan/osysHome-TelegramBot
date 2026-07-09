"""Telegram user persistence."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db, get_now_to_utc, row2dict
from plugins.TelegramBot.models.TelegramUser import TelegramUser


def user_to_dict(user: TelegramUser) -> Dict[str, Any]:
    return row2dict(user)


def save_user(payload: Dict[str, Any], entity_id: Optional[int] = None) -> TelegramUser:
    if entity_id is not None:
        user = TelegramUser.query.get(entity_id)
        if user is None:
            raise ValueError(f"User not found: {entity_id}")
        if "user_id" in payload and not payload.get("user_id"):
            raise ValueError("user_id is required")
        if "name" in payload and not payload.get("name"):
            raise ValueError("name is required")
    else:
        if not payload.get("user_id"):
            raise ValueError("user_id is required")
        if not payload.get("name"):
            raise ValueError("name is required")
        user = TelegramUser()
        user.created = get_now_to_utc()
        db.session.add(user)
    if "user_id" in payload:
        user.user_id = str(payload.get("user_id"))
    if "name" in payload:
        user.name = payload.get("name")
    if "user" in payload:
        user.user = payload.get("user") or None
    if "say" in payload:
        user.say = payload.get("say")
    if "command" in payload:
        user.command = bool(payload.get("command"))

    db.session.commit()
    db.session.refresh(user)
    return user


def delete_user(entity_id: int) -> bool:
    user = TelegramUser.query.get(entity_id)
    if user is None:
        return False
    db.session.delete(user)
    db.session.commit()
    return True
