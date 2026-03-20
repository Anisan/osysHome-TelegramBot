# TelegramBot — История сообщений и повторные отправки

Плагин `TelegramBot` хранит историю событий в таблице `TelegramHistory`.

## 1. История (`TelegramHistory`): что хранится

В истории доступны поля:

- `user_id` — chat id пользователя (для callback используется `callback.from_user.id`)
- `created` — время события (UTC)
- `direction` — направление/статус (см. `TypeDirection`)
- `type` — тип события (см. `TypeEvent`)
- `message` — “текст события”:
  - для `Text` обычно `message.text`
  - для `Callback` — `callback.data`
- `raw` — исходный JSON события (строкой)
- `send_attempts` — счетчик повторов отправки (используется для outbound-ошибок текста)

В админке `TelegramBot` история показывается во вкладке `History` (последние записи).

## 2. Повторные отправки (`resend_error_message`)

Повторная отправка запускается из `TelegramBot.cyclic_task()` примерно раз в 60 секунд.

Сейчас повторяются только сообщения типа `TypeEvent.Text` (т.е. текстовые исходящие сообщения, которые не ушли с первого раза).

Логика:

1. Отбираются записи `TelegramHistory`, где:
   - `direction` находится в ошибочном диапазоне (`ErrorOut`, но не `ErrorOutFatal`)
   - `send_attempts < MAX_SEND_ATTEMPTS`
   - `type == TypeEvent.Text`
2. Для каждой записи:
   - увеличивается `send_attempts`
   - выполняется отправка текста заново (через внутренний `_send_message(message.user_id, text)`)
3. После отправки:
   - успех переводит `direction` в `Resend`
   - ошибка может переводить `direction` в `ErrorOutFatal` если:
     - попыток стало `>= MAX_SEND_ATTEMPTS`, или
     - ошибка выглядит “фатальной” (по тексту результата)

`MAX_SEND_ATTEMPTS` задан в `plugins/TelegramBot/constants.py` (текущее значение: `5`).

## 3. Очистка истории

В `TelegramBot.cyclic_task()` также вызывается:

- `TelegramHistory.clean_history_day(history_day)`

где `history_day` берется из настроек `TelegramBot` (Settings -> `History days`).

