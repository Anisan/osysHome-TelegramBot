# TelegramBot - Работа с медиа

Руководство по обработке входящих медиа-сообщений и сохранению файлов через `saveToCache`.

## Общая схема

1. Получить `file_id` из `message`.
2. Скачать файл через Telegram API.
3. Сохранить байты в кэш.
4. Выполнить действие: ответить, воспроизвести, передать дальше.

```mermaid
flowchart LR
    A["message.*.file_id"] --> B["get_file()"]
    B --> C["download_file()"]
    C --> D["saveToCache()"]
    D --> E["send/play/process"]
```

Базовый шаблон:

```python
import os

file_info = self.bot.get_file(file_id)
data = self.bot.download_file(file_info.file_path)
path = saveToCache(
    f"file_{message.chat.id}_{file_id}.bin",
    data,
    directory=os.path.join(self.name, "media", "misc"),
)
```

> [!NOTE]
> `saveToCache` сохраняет файл в `Config.CACHE_FILE_PATH` + указанный `directory`.

---

## Что можно делать после сохранения

| Действие | Метод |
| --- | --- |
| Отправить текст | `self.send_message(...)` |
| Отправить изображение | `self.send_image(...)` |
| Отправить видео | `self.send_video(...)` |
| Отправить voice | `self.bot.send_voice(...)` |
| Проиграть звук в системе | `playSound(path, level=0)` |

---

## Рабочие примеры

### `Voice`: сохранить и воспроизвести

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

### `Audio`: сохранить и воспроизвести

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

### `Image`: сохранить и отправить обратно

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

### `Video`: сохранить и отправить обратно

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

### `Document`: сохранить и показать информацию

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
self.send_message(message.chat.id, f"Документ сохранён: {file_name} ({len(doc_bytes)} bytes)")
```

### События без файлов: `Location`, `Dice`, `Sticker`

```python
# Location
lat = getattr(message.location, "latitude", None)
lon = getattr(message.location, "longitude", None)
self.send_message(message.chat.id, f"GPS: {lat}, {lon}")
```

```python
# Dice
import random
value = int(getattr(message.dice, "value", 0) or 0)
pick = random.choice(["ok", "done", "try_again"])
self.send_message(message.chat.id, f"Кость: {value}. Реакция: {pick}")
```

```python
# Sticker
emoji = getattr(getattr(message, "sticker", None), "emoji", "") or ":)"
self.send_message(message.chat.id, f"Принял стикер: {emoji}")
```

> [!CAUTION]
> Для больших файлов учитывайте время скачивания и блокировки сети; при необходимости ограничивайте размеры и типы документов.

