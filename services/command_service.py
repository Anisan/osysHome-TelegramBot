"""Telegram command persistence."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db, row2dict
from plugins.TelegramBot.models.TelegramCommand import TelegramCommand


def command_to_dict(command: TelegramCommand) -> Dict[str, Any]:
    data = row2dict(command)
    users = (command.users or "").split(",") if command.users else []
    data["users"] = [item for item in users if item]
    return data


def save_command(payload: Dict[str, Any], entity_id: Optional[int] = None) -> TelegramCommand:
    users = payload.get("users")
    users_value = None
    if users is not None:
        if isinstance(users, list):
            users_value = ",".join(str(item) for item in users if str(item).strip())
        else:
            users_value = str(users)

    if entity_id is not None:
        command = TelegramCommand.query.get(entity_id)
        if command is None:
            raise ValueError(f"Command not found: {entity_id}")
        if "title" in payload and not payload.get("title"):
            raise ValueError("title is required")
    else:
        if not payload.get("title"):
            raise ValueError("title is required")
        command = TelegramCommand()
        db.session.add(command)

    command.title = payload.get("title", command.title)
    if "description" in payload:
        command.description = payload.get("description")
    if "active" in payload:
        command.active = bool(payload.get("active"))
    if "code" in payload:
        command.code = payload.get("code")
    if "priority" in payload:
        command.priority = int(payload.get("priority") or 0)
    if "show" in payload:
        command.show = bool(payload.get("show"))
    if users is not None:
        command.users = users_value

    db.session.commit()
    db.session.refresh(command)
    return command


def delete_command(entity_id: int) -> bool:
    command = TelegramCommand.query.get(entity_id)
    if command is None:
        return False
    db.session.delete(command)
    db.session.commit()
    return True
