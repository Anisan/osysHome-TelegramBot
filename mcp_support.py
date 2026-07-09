"""MCP integration helpers for TelegramBot plugin."""

from __future__ import annotations

import ast
from typing import List, Tuple

from app.core.lib.mcp_contract import (
    build_plugin_mcp_descriptors,
    revision_from_datetime,
    revision_from_dict,
    validate_entity_payload,
)
from app.database import session_scope

from sqlalchemy import desc, or_

from plugins.TelegramBot.constants import TypeDirection, TypeEvent
from plugins.TelegramBot.models.TelegramCommand import TelegramCommand
from plugins.TelegramBot.models.TelegramEvent import TelegramEvent
from plugins.TelegramBot.models.TelegramHistory import TelegramHistory
from plugins.TelegramBot.models.TelegramUser import TelegramUser
from plugins.TelegramBot.services import command_service, event_service, user_service

COMMANDS = "commands"
EVENTS = "events"
USERS = "users"
HISTORY = "history"

_CODE_COLLECTIONS = {COMMANDS, EVENTS}


def mcp_capabilities() -> dict:
    event_enum = {item.value: item.name for item in TypeEvent}
    return {
        "mcp_version": 1,
        "entities": True,
        "config_schema": True,
        "collections": [
            {
                "id": COMMANDS,
                "title": "Commands",
                "binding_mode": "none",
                "writable": True,
                "has_code": True,
                "list_filters": ["query"],
                "default_sort": "title asc",
            },
            {
                "id": EVENTS,
                "title": "Events",
                "binding_mode": "none",
                "writable": True,
                "has_code": True,
                "list_filters": ["query"],
                "default_sort": "title asc",
            },
            {
                "id": USERS,
                "title": "Users",
                "binding_mode": "none",
                "writable": True,
                "has_code": False,
                "list_filters": ["query"],
                "default_sort": "name asc",
            },
            {
                "id": HISTORY,
                "title": "History",
                "binding_mode": "none",
                "writable": False,
                "has_code": False,
                "list_filters": ["query"],
                "default_sort": "created desc",
            },
        ],
        "operations": [
            "reload_bot",
            "send_test_message",
            "send_message",
            "resend_failed_messages",
            "clean_history",
            "refresh_user_profiles",
        ],
        "operation_schemas": {
            "reload_bot": {
                "description": "Reinitialize Telegram bot and restart polling lifecycle",
                "params": {"type": "object", "properties": {}},
            },
            "send_test_message": {
                "description": "Send a test text message to one chat id",
                "params": {
                    "type": "object",
                    "properties": {
                        "chat_id": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["chat_id", "text"],
                },
            },
            "send_message": {
                "description": "Send a text message to one chat id and save it in history",
                "params": {
                    "type": "object",
                    "properties": {
                        "chat_id": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["chat_id", "text"],
                },
            },
            "resend_failed_messages": {
                "description": "Retry queued failed outgoing text messages",
                "params": {"type": "object", "properties": {}},
            },
            "clean_history": {
                "description": "Clean history by retention days or remove all records",
                "params": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Retention in days. Omit and set all=true for full cleanup.",
                        },
                        "all": {
                            "type": "boolean",
                            "default": False,
                            "description": "Delete all history records, including failed ones.",
                        },
                    },
                },
            },
            "refresh_user_profiles": {
                "description": "Update Telegram user names and avatars from Telegram API",
                "params": {"type": "object", "properties": {}},
            },
        },
        "notes": [
            "commands.title and events.title are regular expressions matched by re.match().",
            "commands.code and events.code run via exec() with runtime variables from handlers.",
            "commands and events support users list (chat ids) to limit execution scope.",
            "history collection is read-only and used for audits, troubleshooting, and resend queue visibility.",
            f"events.type enum: {event_enum}",
            f"history.direction enum: {{value:name}} = { {item.value: item.name for item in TypeDirection} }",
        ],
    }


def mcp_config_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "token": {"type": "string", "writeOnly": True},
            "register": {"type": "boolean"},
            "history_day": {"type": "integer", "minimum": 1},
            "proxy_url": {"type": "string"},
            "timeout": {"type": "integer", "minimum": 5, "maximum": 300},
            "commands_in_row": {"type": "integer", "minimum": 1, "maximum": 10},
            "level_logging": {"type": "string"},
        },
        "required": ["token"],
    }


def _collection_meta(collection: str) -> dict:
    for item in mcp_capabilities()["collections"]:
        if item["id"] == collection:
            return item
    raise ValueError(f"Unsupported collection: {collection}")


def mcp_entity_schema(collection: str) -> dict:
    _collection_meta(collection)
    if collection == COMMANDS:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "readOnly": True},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "active": {"type": "boolean"},
                "code": {
                    "type": "string",
                    "description": (
                        "Python code executed via exec with `self`, `message`, `logger`. "
                        "Do not use 'return' statements."
                    ),
                },
                "priority": {"type": "integer"},
                "show": {"type": "boolean"},
                "users": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed Telegram chat ids. Empty list means no restriction.",
                },
            },
            "required": ["title"],
        }
    if collection == EVENTS:
        event_types = ", ".join(f"{item.name}({item.value})" for item in TypeEvent)
        return {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "readOnly": True},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "active": {"type": "boolean"},
                "type": {
                    "type": "integer",
                    "enum": [item.value for item in TypeEvent],
                    "description": f"Telegram event type. Allowed: {event_types}",
                },
                "code": {
                    "type": "string",
                    "description": (
                        "Python code executed via exec. Callback type has `callback`; "
                        "other types have `message`. `self` and `logger` are always available."
                    ),
                },
                "users": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed Telegram chat ids. Empty list means no restriction.",
                },
            },
            "required": ["title"],
        }
    if collection == USERS:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "readOnly": True},
                "user_id": {"type": "string"},
                "name": {"type": "string"},
                "user": {"type": "string"},
                "say": {"type": "integer"},
                "command": {"type": "boolean"},
                "created": {"type": "string", "readOnly": True},
            },
            "required": ["user_id", "name"],
        }
    if collection == HISTORY:
        return {
            "type": "object",
            "readOnly": True,
            "properties": {
                "id": {"type": "integer", "readOnly": True},
                "user_id": {"type": "string", "readOnly": True},
                "created": {"type": "string", "readOnly": True},
                "direction": {
                    "type": "integer",
                    "enum": [item.value for item in TypeDirection],
                    "readOnly": True,
                },
                "type": {
                    "type": "integer",
                    "enum": [item.value for item in TypeEvent],
                    "readOnly": True,
                },
                "message": {"type": "string", "readOnly": True},
                "raw": {"type": ["string", "null"], "readOnly": True},
                "send_attempts": {"type": "integer", "readOnly": True},
            },
        }
    raise ValueError(f"Unsupported collection: {collection}")


def _query_filter(model, query: str):
    like = f"%{query}%"
    if model is TelegramCommand:
        return or_(model.title.ilike(like), model.description.ilike(like))
    if model is TelegramEvent:
        return or_(model.title.ilike(like), model.description.ilike(like))
    if model is TelegramUser:
        return or_(model.name.ilike(like), model.user_id.ilike(like), model.user.ilike(like))
    if model is TelegramHistory:
        return or_(model.user_id.ilike(like), model.message.ilike(like))
    return None


def mcp_list_entities(collection: str, query: str = None, limit: int = 100) -> List[dict]:
    limit = max(1, min(int(limit or 100), 5000))
    if collection == COMMANDS:
        q = TelegramCommand.query
        if query:
            q = q.filter(_query_filter(TelegramCommand, query))
        return [command_service.command_to_dict(row) for row in q.order_by(TelegramCommand.title).limit(limit).all()]
    if collection == EVENTS:
        q = TelegramEvent.query
        if query:
            q = q.filter(_query_filter(TelegramEvent, query))
        return [event_service.event_to_dict(row) for row in q.order_by(TelegramEvent.title).limit(limit).all()]
    if collection == USERS:
        q = TelegramUser.query
        if query:
            q = q.filter(_query_filter(TelegramUser, query))
        return [user_service.user_to_dict(row) for row in q.order_by(TelegramUser.name).limit(limit).all()]
    if collection == HISTORY:
        q = TelegramHistory.query
        if query:
            q = q.filter(_query_filter(TelegramHistory, query))
        rows = q.order_by(desc(TelegramHistory.created)).limit(limit).all()
        result = []
        for row in rows:
            item = {
                "id": row.id,
                "user_id": row.user_id,
                "created": row.created.isoformat(sep=" ", timespec="seconds") if row.created else None,
                "direction": row._direction,
                "type": row._type,
                "message": row.message,
                "send_attempts": row.send_attempts,
            }
            result.append(item)
        return result
    raise ValueError(f"Unsupported collection: {collection}")


def mcp_get_entity(collection: str, entity_id) -> dict:
    if collection == COMMANDS:
        row = TelegramCommand.query.get(entity_id)
        if row is None:
            raise ValueError(f"Command not found: {entity_id}")
        return command_service.command_to_dict(row)
    if collection == EVENTS:
        row = TelegramEvent.query.get(entity_id)
        if row is None:
            raise ValueError(f"Event not found: {entity_id}")
        return event_service.event_to_dict(row)
    if collection == USERS:
        row = TelegramUser.query.get(entity_id)
        if row is None:
            raise ValueError(f"User not found: {entity_id}")
        return user_service.user_to_dict(row)
    if collection == HISTORY:
        row = TelegramHistory.query.get(entity_id)
        if row is None:
            raise ValueError(f"History record not found: {entity_id}")
        return {
            "id": row.id,
            "user_id": row.user_id,
            "created": row.created.isoformat(sep=" ", timespec="seconds") if row.created else None,
            "direction": row._direction,
            "type": row._type,
            "message": row.message,
            "raw": row.raw,
            "send_attempts": row.send_attempts,
        }
    raise ValueError(f"Unsupported collection: {collection}")


def mcp_upsert_entity(collection: str, payload: dict, entity_id=None) -> dict:
    meta = _collection_meta(collection)
    if not meta.get("writable"):
        raise ValueError(f"Collection '{collection}' is read-only")
    if collection == COMMANDS:
        row = command_service.save_command(payload, entity_id=entity_id)
        return command_service.command_to_dict(row)
    if collection == EVENTS:
        row = event_service.save_event(payload, entity_id=entity_id)
        return event_service.event_to_dict(row)
    if collection == USERS:
        row = user_service.save_user(payload, entity_id=entity_id)
        return user_service.user_to_dict(row)
    raise ValueError(f"Unsupported collection: {collection}")


def mcp_delete_entity(collection: str, entity_id) -> bool:
    meta = _collection_meta(collection)
    if not meta.get("writable"):
        raise ValueError(f"Collection '{collection}' is read-only")
    if collection == COMMANDS:
        return command_service.delete_command(int(entity_id))
    if collection == EVENTS:
        return event_service.delete_event(int(entity_id))
    if collection == USERS:
        return user_service.delete_user(int(entity_id))
    raise ValueError(f"Unsupported collection: {collection}")


def _validate_code(code: str, forbid_return: bool = False) -> dict:
    errors = []
    tree = None
    try:
        tree = ast.parse(code or "")
    except SyntaxError as ex:
        errors.append({"message": str(ex), "line": ex.lineno, "column": ex.offset})
    if tree is not None and forbid_return:
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                errors.append(
                    {
                        "message": "Do not use 'return' in command code (it is executed via exec)",
                        "line": getattr(node, "lineno", None),
                        "column": getattr(node, "col_offset", None),
                    }
                )
    return {"ok": len(errors) == 0, "errors": errors}


def mcp_validate_entity_code(collection: str, code: str) -> dict:
    if collection not in _CODE_COLLECTIONS:
        raise ValueError(f"Collection '{collection}' does not support code validation")
    return _validate_code(code, forbid_return=(collection == COMMANDS))


def mcp_run_entity_dry(collection: str, code: str, context: dict = None) -> dict:  # pylint: disable=unused-argument
    if collection not in _CODE_COLLECTIONS:
        raise ValueError(f"Collection '{collection}' does not support dry-run code")
    validation = _validate_code(code, forbid_return=(collection == COMMANDS))
    if not validation["ok"]:
        return {"ok": False, "validation": validation, "events": []}
    return {"ok": True, "validation": validation, "events": [], "note": "Syntax OK; runtime execution is not simulated"}


def mcp_invoke(plugin_instance, operation: str, params: dict = None) -> dict:
    params = params or {}
    if operation == "reload_bot":
        if plugin_instance.bot:
            try:
                plugin_instance.bot.stop_polling()
            except Exception:
                pass
        plugin_instance.isStarted = False
        plugin_instance.initialization()
        return {"ok": True, "operation": operation}
    if operation == "send_test_message":
        chat_id = str(params.get("chat_id") or "").strip()
        text = str(params.get("text") or "").strip()
        if not chat_id or not text:
            raise ValueError("chat_id and text are required")
        plugin_instance.send_message(chat_id, text)
        return {"ok": True, "operation": operation, "chat_id": chat_id}
    if operation == "send_message":
        chat_id = str(params.get("chat_id") or "").strip()
        text = str(params.get("text") or "").strip()
        if not chat_id or not text:
            raise ValueError("chat_id and text are required")
        plugin_instance.send_message(chat_id, text)
        return {"ok": True, "operation": operation, "chat_id": chat_id}
    if operation == "resend_failed_messages":
        plugin_instance.resend_error_message()
        return {"ok": True, "operation": operation}
    if operation == "clean_history":
        if bool(params.get("all")):
            TelegramHistory.delete()
            return {"ok": True, "operation": operation, "mode": "all"}
        days = params.get("days")
        if days in (None, ""):
            days = plugin_instance.config.get("history_day", 7)
        days = int(days)
        if days < 1:
            raise ValueError("days must be >= 1")
        TelegramHistory.clean_history_day(days)
        return {"ok": True, "operation": operation, "mode": "retention", "days": days}
    if operation == "refresh_user_profiles":
        updated = 0
        with session_scope() as session:
            users = session.query(TelegramUser).all()
            for user in users:
                info = plugin_instance.save_user_avatar(user.user_id)
                if info:
                    user.name = info.title if info.title else info.username
                    updated += 1
            session.commit()
        return {"ok": True, "operation": operation, "updated": updated}
    raise ValueError(f"Unsupported operation: {operation}")


_REVISION_KEYS = {
    COMMANDS: ["id", "title", "description", "active", "code", "priority", "show", "users"],
    EVENTS: ["id", "title", "description", "active", "type", "code"],
    USERS: ["id", "user_id", "name", "user", "say", "command"],
    HISTORY: ["id", "user_id", "created", "direction", "type", "message"],
}


def mcp_descriptors() -> Tuple[list, list, list]:
    return build_plugin_mcp_descriptors("TelegramBot", mcp_capabilities())


def mcp_entity_revision(collection: str, entity_id) -> str:
    if collection == HISTORY:
        entity = mcp_get_entity(collection, entity_id)
        created = revision_from_datetime(entity.get("created"))
        if created:
            return created
    if collection not in _REVISION_KEYS:
        raise ValueError(f"Unsupported collection: {collection}")
    entity = mcp_get_entity(collection, entity_id)
    return revision_from_dict(entity, keys=_REVISION_KEYS[collection])


def mcp_validate_entity(collection: str, payload: dict, entity_id=None) -> dict:
    if collection == HISTORY:
        return {"ok": False, "errors": [{"field": "collection", "message": "history is read-only"}]}
    schema = mcp_entity_schema(collection)
    payload_to_validate = payload
    if entity_id not in (None, ""):
        try:
            current = mcp_get_entity(collection, entity_id)
        except ValueError as ex:
            return {"ok": False, "errors": [{"field": "id", "message": str(ex)}]}
        payload_to_validate = {**current, **payload}
    result = validate_entity_payload(payload_to_validate, schema)
    if not result.get("ok"):
        return result

    if collection in _CODE_COLLECTIONS and "code" in payload_to_validate:
        code_validation = mcp_validate_entity_code(collection, str(payload_to_validate.get("code") or ""))
        if not code_validation.get("ok"):
            return {
                "ok": False,
                "errors": code_validation.get("errors") or [{"field": "code", "message": "invalid code"}],
            }

    return {"ok": True, "errors": []}
