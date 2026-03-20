# TelegramBot — какие типы сообщений можно перехватывать

Плагин оперирует двумя сущностями:

- `TelegramCommand` — срабатывает по входящему тексту (`message.text`) для “команд”
- `TelegramEvent` — срабатывает по типу входящего события (`TypeEvent`)

В обеих схемах используется регулярное выражение `title` и/или совпадение типа, но механика разная.

## 1. TelegramCommand

`TelegramCommand` выполняется при поступлении текстового сообщения.

Что проверяется:

1. Пользователь должен существовать в БД (`TelegramUser`)
2. У пользователя должен быть включен флаг `TelegramUser.command`
3. Для каждой активной команды выполняется:
   - `re.match(TelegramCommand.title, message.text)`
4. При совпадении выполняется `TelegramCommand.code`

## 2. TelegramEvent

`TelegramEvent` создаётся с полем `Type` (из `TypeEvent`) и `Code`.

Что происходит:

1. Бот находит активные `TelegramEvent` с нужным `type`
2. Для каждого события выполняет `TelegramEvent.code`

Особенность `Callback`:

- для `TelegramEvent.type == Callback` дополнительно делается фильтрация регуляркой:
  - `re.match(TelegramEvent.title, callback.data)`

Для остальных типов (`Text/Image/Voice/...`) регулярка `title` как фильтр не применяется — фильтр делается только по `type`.

## 3. Список `TypeEvent` и content type

| `TypeEvent` | content type Telegram |
|---|---|
| `Callback` | callback_query |
| `Text` | текст (`message.text`) |
| `Image` | `photo` |
| `Voice` | `voice` |
| `Audio` | `audio` |
| `Video` | `video` |
| `Document` | `document` |
| `Sticker` | `sticker` |
| `Location` | `location` |
| `Venue` | `venue` |
| `Contact` | `contact` |
| `Dice` | `dice` |

## 4. Переменные в `TelegramEvent.code`

- Для `Callback` доступны: `self`, `callback`, `logger`
  - полезное: `callback.data`, `callback.id`, `callback.message.chat.id`
- Для остальных типов доступны: `self`, `message`, `logger`
  - полезное: `message.chat.id`, и поля конкретного типа (например, `message.voice.file_id`)
