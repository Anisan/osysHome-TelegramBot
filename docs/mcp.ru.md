# MCP — TelegramBot

## Collections

| ID | binding_mode | has_code | Описание |
|----|--------------|----------|----------|
| `commands` | `none` | yes | Команды бота |
| `events` | `none` | yes | Обработчики событий |
| `users` | `none` | no | Пользователи Telegram |
| `history` | `none` | no | История (только чтение) |

## Примеры

### Создать команду

```json
{
  "plugin": "TelegramBot",
  "action": "upsert_entity",
  "args": {
    "collection": "commands",
    "payload": {
      "title": "/status",
      "active": true,
      "show": true,
      "priority": 0,
      "code": "say('System OK')",
      "users": []
    }
  }
}
```

### Валидация кода

```json
{
  "plugin": "TelegramBot",
  "action": "validate_entity_code",
  "args": {
    "collection": "commands",
    "code": "say('hello')"
  }
}
```

### Операции

```json
{
  "plugin": "TelegramBot",
  "action": "invoke",
  "args": {
    "operation": "send_test_message",
    "params": {"chat_id": "123456", "text": "test"}
  }
}
```

```json
{
  "plugin": "TelegramBot",
  "action": "invoke",
  "args": {"operation": "reload_bot", "params": {}}
}
```

```json
{
  "plugin": "TelegramBot",
  "action": "invoke",
  "args": {
    "operation": "clean_history",
    "params": {"days": 14}
  }
}
```

```json
{
  "plugin": "TelegramBot",
  "action": "invoke",
  "args": {"operation": "resend_failed_messages", "params": {}}
}
```

```json
{
  "plugin": "TelegramBot",
  "action": "invoke",
  "args": {"operation": "refresh_user_profiles", "params": {}}
}
```
