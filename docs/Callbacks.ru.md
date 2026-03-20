# TelegramBot — Inline-клавиатуры и обработка `callback_query`

Inline-кнопки Telegram отправляют `callback_query`, где данные находятся в `callback.data`.

Плагин обрабатывает callback-нажатия через записи `TelegramEvent` типа `Callback`.

Код события выполняется так же, как код команды — через `exec()` на верхнем уровне, поэтому **`return` в коде нельзя** (см. раздел в [`Commands.ru.md`](Commands.ru.md)).

## 1. Создание inline-клавиатуры

Для построения inline-клавиатуры используется метод:

- `self.buildInlineKeyBoard(buttons)`

`buttons` — список “строк”, где каждая строка — словарь вида `{ "Текст": "callback_data" }`.

Пример отправки меню:

```python
buttons = [
    {"Статус": "menu:status"},
    {"Вкл": "menu:on", "Выкл": "menu:off"},
]

keyboard = self.buildInlineKeyBoard(buttons)
self.send_message(message.chat.id, "Выберите действие:", markup=keyboard)
```

## 2. Создание обработчика callback-нажатия

1. В админке откройте `TelegramBot` -> вкладка `Events`.
2. Нажмите `Add event`.
3. Заполните поля:
   - `Type`: `Callback`
   - `Name (title)`: регулярное выражение для `re.match` по `callback.data`
   - `Code`: Python-код обработчика

Матчинг происходит так:

- перебираются активные `TelegramEvent` где `type == Callback`
- для каждого выполняется `re.match(clb.title, callback.data)`
- при совпадении выполняется `TelegramEvent.code`

## 3. Пример: одна кнопка

Если ваша inline-кнопка отправляет `callback_data = "menu:status"`, то в `TelegramEvent.title` задайте:

- `^menu:status$`

Код обработчика:

```python
self.bot.answer_callback_query(callback.id)
self.send_message(callback.message.chat.id, "<b>Статус</b>: OK")
```

## 4. Пример: несколько кнопок одной обработкой

Если callback_data имеет формат `menu:<action>`, например `menu:on`, `menu:off`, `menu:status`, то:

- `TelegramEvent.title`: `^menu:(.+)$`

Код:

```python
import re

self.bot.answer_callback_query(callback.id)

m = re.match(r"^menu:(.+)$", callback.data or "")
if m:
    action = m.group(1)
    if action == "on":
        self.send_message(callback.message.chat.id, "Включено")
    elif action == "off":
        self.send_message(callback.message.chat.id, "Выключено")
    else:
        self.send_message(callback.message.chat.id, f"Получено действие: {action}")
```

## 5. Обновление текста без нового сообщения

Можно не отправлять новое сообщение, а изменить уже отправленное:

```python
self.bot.answer_callback_query(callback.id)

self.bot.edit_message_text(
    text="Статус обновлён",
    chat_id=callback.message.chat.id,
    message_id=callback.message.message_id,
)
```

## 6. Переменные в коде обработчика `Callback`

Внутри `TelegramEvent.code` для `Callback` доступны:

- `self` — объект модуля `TelegramBot` (например, `send_message`, `buildInlineKeyBoard`)
- `callback` — объект callback запроса (telebot `CallbackQuery`)
- `logger` — логгер

Полезные поля `callback`:
- `callback.message.chat.id`
- `callback.id`
- `callback.data`

