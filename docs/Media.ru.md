# TelegramBot — Работа с медиа и сохранение в кэш

Для входящих медиа (`photo`, `voice`, `audio`, `video`, `document`, `sticker`) можно:

- скачать файл через Telegram API
- сохранить в кэш (фактически файловое хранилище osysHome) через `saveToCache(...)`
- затем делать полезные действия: проигрывать `voice`/`audio`, отправлять назад, сохранять метаданные и т.д.

В примерах ниже предполагается, что код выполняется в `TelegramEvent.code` (для нужного `TypeEvent`).

## 1. Общая схема скачивания и сохранения

1. Берём `file_id` из входящего `message`:
   - `photo`: `message.photo[-1].file_id` (обычно последний — максимальное качество)
   - `voice`: `message.voice.file_id`
   - `audio`: `message.audio.file_id`
   - `video`: `message.video.file_id`
   - `document`: `message.document.file_id`
   - `sticker`: `message.sticker.file_id`
2. Скачиваем файл:

```python
file_info = self.bot.get_file(file_id)
data = self.bot.download_file(file_info.file_path)  # bytes
```

3. Сохраняем:

```python
import os

path = saveToCache(
    f"voice_{message.chat.id}_{file_id}.ogg",
    data,
    directory=os.path.join(self.name, "media", "voice"),
)
```

`saveToCache` использует `directory` относительно кэша `Config.CACHE_FILE_PATH`.

## 2. Что можно сделать после сохранения

- вернуть медиа пользователю (`send_voice`, `send_image`, `send_video`)
- проиграть звук через систему osysHome: `playSound(path, level=0)`
- использовать путь `path` в дальнейшей логике (например, отправить в другой плагин)

## 3. Примеры

### 3.1 `voice`: сохранить и проиграть через `playSound`

Событие типа `Voice`:

```python
import os

file_id = message.voice.file_id
file_info = self.bot.get_file(file_id)
voice_bytes = self.bot.download_file(file_info.file_path)

voice_path = saveToCache(
    f"voice_{message.chat.id}_{file_id}.ogg",
    voice_bytes,
    directory=os.path.join(self.name, "media", "voice"),
)

playSound(voice_path, level=0)
self.send_message(message.chat.id, "Голос принят, проигрываю...")
```

### 3.2 `audio`: сохранить и проиграть через `playSound`

Событие типа `Audio`:

```python
import os

file_id = message.audio.file_id
file_info = self.bot.get_file(file_id)
audio_bytes = self.bot.download_file(file_info.file_path)

audio_path = saveToCache(
    f"audio_{message.chat.id}_{file_id}.mp3",
    audio_bytes,
    directory=os.path.join(self.name, "media", "audio"),
)

playSound(audio_path, level=0)
self.send_message(message.chat.id, "Аудио принято, проигрываю...")
```

### 3.3 `photo`: сохранить и отправить назад

Событие типа `Image`:

```python
import os

file_id = message.photo[-1].file_id
file_info = self.bot.get_file(file_id)
photo_bytes = self.bot.download_file(file_info.file_path)

photo_path = saveToCache(
    f"photo_{message.chat.id}_{file_id}.jpg",
    photo_bytes,
    directory=os.path.join(self.name, "media", "images"),
)

self.send_image(message.chat.id, "Фото сохранено. Спасибо!", photo_path)
```

### 3.4 `video`: сохранить и отправить назад

Событие типа `Video`:

```python
import os

file_id = message.video.file_id
file_info = self.bot.get_file(file_id)
video_bytes = self.bot.download_file(file_info.file_path)

video_path = saveToCache(
    f"video_{message.chat.id}_{file_id}.mp4",
    video_bytes,
    directory=os.path.join(self.name, "media", "video"),
)

self.send_video(message.chat.id, "Видео сохранено.", video_path)
```

### 3.5 `document`: сохранить файл (и показать имя)

Событие типа `Document`:

```python
import os

file_id = message.document.file_id
file_info = self.bot.get_file(file_id)
doc_bytes = self.bot.download_file(file_info.file_path)

file_name = getattr(message.document, "file_name", "") or f"doc_{file_id}.bin"
ext = os.path.splitext(file_name)[1] or ".bin"

doc_path = saveToCache(
    f"document_{message.chat.id}_{file_id}{ext}",
    doc_bytes,
    directory=os.path.join(self.name, "media", "documents"),
)

self.send_message(
    message.chat.id,
    f"Документ сохранён: {file_name} (bytes={len(doc_bytes)})"
)
```

### 3.6 “не файл”: `location`, `dice`, `sticker`

- `Location`:

```python
lat = getattr(message.location, "latitude", None)
lon = getattr(message.location, "longitude", None)
self.send_message(message.chat.id, f"GPS: {lat}, {lon}")
```

- `Dice`:

```python
import random

value = int(getattr(message.dice, "value", 0) or 0)
pick = random.choice(["ok", "done", "try_again"])
self.send_message(message.chat.id, f"Кость: {value}. Реакция: {pick}")
```

- `Sticker`:

```python
emoji = getattr(getattr(message, "sticker", None), "emoji", "") or ":)"
self.send_message(message.chat.id, f"Принял стикер: {emoji}")
```

