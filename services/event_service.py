"""Telegram event persistence."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db, row2dict
from plugins.TelegramBot.models.TelegramEvent import TelegramEvent


def event_to_dict(event: TelegramEvent) -> Dict[str, Any]:
    data = row2dict(event)
    users = (event.users or "").split(",") if event.users else []
    data["users"] = [item for item in users if item]
    return data


def save_event(payload: Dict[str, Any], entity_id: Optional[int] = None) -> TelegramEvent:
    users = payload.get("users")
    users_value = None
    if users is not None:
        if isinstance(users, list):
            users_value = ",".join(str(item) for item in users if str(item).strip())
        else:
            users_value = str(users)

    if entity_id is not None:
        event = TelegramEvent.query.get(entity_id)
        if event is None:
            raise ValueError(f"Event not found: {entity_id}")
        if "title" in payload and not payload.get("title"):
            raise ValueError("title is required")
    else:
        if not payload.get("title"):
            raise ValueError("title is required")
        event = TelegramEvent()
        db.session.add(event)

    event.title = payload.get("title", event.title)
    if "description" in payload:
        event.description = payload.get("description")
    if "active" in payload:
        event.active = bool(payload.get("active"))
    if "code" in payload:
        event.code = payload.get("code")
    if "type" in payload:
        event.type = int(payload.get("type") or 0)
    if users is not None:
        event.users = users_value

    db.session.commit()
    db.session.refresh(event)
    return event


def delete_event(entity_id: int) -> bool:
    event = TelegramEvent.query.get(entity_id)
    if event is None:
        return False
    db.session.delete(event)
    db.session.commit()
    return True
