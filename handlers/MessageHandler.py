import re
from . import Handler
from app.database import session_scope, get_now_to_utc
from app.core.lib.execute import execute_and_capture_output
from ..models.TelegramUser import TelegramUser
from ..models.TelegramHistory import TelegramHistory
from ..models.TelegramCommand import TelegramCommand
from ..models.TelegramEvent import TelegramEvent
from ..constants import TypeEvent, TypeDirection

class MessageHandler(Handler):
    def __init__(self, module):
        super().__init__(module)
        self.config = module.config
        self._app = module._app
        self.module = module
        self._bot_id = None
        self._bot_username = None

    def events_work(self, message, typeEvent: TypeEvent):
        try:
            with session_scope() as session:
                self.logger.debug(message.json)
                events_all = session.query(TelegramEvent).where(
                    TelegramEvent.active,
                    TelegramEvent.type == typeEvent.value
                ).all()
                member_list = [None]
                if typeEvent == TypeEvent.Join:
                    member_list = list(getattr(message, "new_chat_members", None) or [])
                elif typeEvent == TypeEvent.Leave:
                    left_member = getattr(message, "left_chat_member", None)
                    member_list = [left_member] if left_member is not None else []

                # If we didn't get members for join/leave, still execute once for visibility.
                if not member_list:
                    member_list = [None]

                for member in member_list:
                    member_id = getattr(member, "id", None) if member else None
                    actor_user_id = self._resolve_actor_user_id(message, member)
                    chat_id = self._resolve_chat_id(message)
                    events = [
                        event for event in events_all
                        if self._entity_allows_user(event.users, actor_user_id, chat_id)
                    ]
                    member_name = None
                    if member:
                        member_name = (
                            getattr(member, "full_name", None)
                            or getattr(member, "first_name", None)
                            or getattr(member, "username", None)
                            or None
                        )

                    history = TelegramHistory()
                    history.created = get_now_to_utc()
                    history.user_id = str(member_id) if member_id is not None else str(message.chat.id)
                    history.type = typeEvent
                    history.direction = TypeDirection.Out if typeEvent == TypeEvent.Leave else TypeDirection.In
                    history.raw = str(message.json)

                    if typeEvent == TypeEvent.Join:
                        history.message = f"member_join: {member_name} ({member_id})"
                    elif typeEvent == TypeEvent.Leave:
                        history.message = f"member_leave: {member_name} ({member_id})"
                    elif typeEvent == TypeEvent.NewChatTitle:
                        history.message = f"chat_title: {getattr(message, 'new_chat_title', None)}"
                    elif typeEvent == TypeEvent.NewChatPhoto:
                        photos = getattr(message, "new_chat_photo", None)
                        count = len(photos) if isinstance(photos, list) else (1 if photos else 0)
                        history.message = f"chat_photo_updated: {count}"
                    elif typeEvent == TypeEvent.PinnedMessage:
                        pinned = getattr(message, "pinned_message", None)
                        if pinned:
                            text = getattr(pinned, "text", None) or getattr(pinned, "caption", None)
                            history.message = text or f"pinned_message_id: {getattr(pinned, 'message_id', None)}"
                        else:
                            history.message = "pinned_message"
                    elif typeEvent == TypeEvent.DeletedMessage:
                        deleted = getattr(message, "deleted_message", None)
                        if deleted:
                            text = getattr(deleted, "text", None) or getattr(deleted, "caption", None)
                            history.message = text or f"deleted_message_id: {getattr(deleted, 'message_id', None)}"
                        else:
                            history.message = "deleted_message"
                    else:
                        history.message = getattr(message, "text", None) or getattr(message, "caption", None) or str(message.json)

                    session.add(history)
                    session.commit()

                    for event in events:
                        self.logger.info("Execute event %s(%s)", event.title, event.description)
                        try:
                            code = event.code
                            variables = {
                                'self': self.module,
                                'message': message,
                                'logger': self.logger,
                                **vars(self),
                                'typeEvent': typeEvent,
                                'member': member,
                                'member_id': member_id,
                                'member_name': member_name,
                                'chat': getattr(message, "chat", None),
                                'from_user': getattr(message, "from_user", None),
                                'pinned_message': getattr(message, "pinned_message", None),
                                'deleted_message': getattr(message, "deleted_message", None),
                            }
                            # Выполняем код модуля в контексте с logger
                            output, error = execute_and_capture_output(code, variables)
                            if error:
                                self.logger.error(output)
                        except Exception as ex:
                            self.logger.exception(ex, exc_info=True) # TODO write adv info

                return True
        except Exception as ex:
            self.logger.exception(ex, exc_info=True) 
            return False

    def _entity_allows_user(self, users_raw, user_id: str, chat_id: str = "") -> bool:
        if not users_raw:
            return True
        allowed_ids = {value for value in (user_id, chat_id) if value}
        if not allowed_ids:
            return False
        users = [item.strip() for item in str(users_raw).split(",") if item and item.strip()]
        return any(candidate in users for candidate in allowed_ids)

    def _resolve_chat_id(self, message) -> str:
        chat = getattr(message, "chat", None)
        if chat is not None and getattr(chat, "id", None) is not None:
            return str(chat.id)
        return ""

    def _resolve_actor_user_id(self, message, member=None) -> str:
        if member is not None and getattr(member, "id", None) is not None:
            return str(member.id)

        from_user = getattr(message, "from_user", None)
        if from_user is not None and getattr(from_user, "id", None) is not None:
            return str(from_user.id)

        chat = getattr(message, "chat", None)
        if chat is not None and getattr(chat, "id", None) is not None:
            return str(chat.id)

        return ""

    def _load_bot_identity(self):
        if self._bot_id is not None or self._bot_username is not None:
            return
        try:
            me = self.bot.get_me()
            self._bot_id = getattr(me, "id", None)
            username = getattr(me, "username", None)
            self._bot_username = username.lower() if isinstance(username, str) else None
        except Exception:
            self._bot_id = None
            self._bot_username = None

    def _is_message_addressed_to_bot(self, message) -> bool:
        chat = getattr(message, "chat", None)
        chat_type = getattr(chat, "type", None)
        if chat_type == "private":
            return True

        self._load_bot_identity()

        text = (getattr(message, "text", None) or getattr(message, "caption", None) or "").lower()
        if self._bot_username and f"@{self._bot_username}" in text:
            return True

        if text.startswith("/") and self._bot_username and f"@{self._bot_username}" in text.split()[0]:
            return True

        reply_to = getattr(message, "reply_to_message", None)
        if reply_to:
            reply_user = getattr(reply_to, "from_user", None)
            reply_user_id = getattr(reply_user, "id", None) if reply_user else None
            reply_username = getattr(reply_user, "username", None) if reply_user else None
            if self._bot_id is not None and reply_user_id == self._bot_id:
                return True
            if self._bot_username and isinstance(reply_username, str) and reply_username.lower() == self._bot_username:
                return True

        return False

    def _log_unregistered_message(self, message):
        if not self._is_message_addressed_to_bot(message):
            return

        chat = getattr(message, "chat", None)
        from_user = getattr(message, "from_user", None)
        chat_id = getattr(chat, "id", None)
        username = getattr(from_user, "username", None) if from_user else None
        full_name = getattr(from_user, "full_name", None) if from_user else None
        content_type = getattr(message, "content_type", "unknown")
        text = getattr(message, "text", None) or getattr(message, "caption", None) or "<empty>"
        self.logger.warning(
            "Message from unregistered user ignored: chat_id=%s username=%s full_name=%s type=%s text=%s",
            chat_id,
            username,
            full_name,
            content_type,
            text[:300],
        )

    def handle(self):
        @self.bot.message_handler(func=lambda message: True)
        def handle(message) -> None:
            try:
                # Command dispatcher depends on text. System updates (join/leave) may not have message.text.
                if not getattr(message, "text", None):
                    return
                with session_scope() as session:
                    user = session.query(TelegramUser).where(TelegramUser.user_id == str(message.chat.id)).one_or_none()
                    if not user:
                        self._log_unregistered_message(message)
                        return 

                    if not self.events_work(message, TypeEvent.Text):
                        return
                    
                    if not user.command:
                        return

                    chat_id = str(message.chat.id)
                    commands_all = session.query(TelegramCommand).where(TelegramCommand.active).all()
                    commands = [command for command in commands_all if self._entity_allows_user(command.users, chat_id)]
                    for cmnd in commands:
                        result = re.match(cmnd.title, message.text)
                        if result:
                            self.logger.info("Execute command %s(%s)",cmnd.title,cmnd.description)
                            try:
                                code = cmnd.code
                                variables = {
                                    'self': self.module,
                                    'message': message,
                                    'logger': self.logger,
                                    **vars(self)
                                }
                                output, error = execute_and_capture_output(code, variables)
                                if error:
                                    self.logger.error(output)
                            except Exception as ex:
                                self.logger.exception(ex, exc_info=True) # TODO write adv info
            except Exception as ex:
                self.logger.exception(ex, exc_info=True) 
                

        @self.bot.message_handler(content_types=['photo'])
        def handle_photo(message) -> None:
            self.events_work(message,TypeEvent.Image)

        @self.bot.message_handler(content_types=['audio'])
        def handle_audio(message) -> None:
            self.events_work(message,TypeEvent.Audio)

        @self.bot.message_handler(content_types=['voice'])
        def handle_voice(message) -> None:
            self.events_work(message,TypeEvent.Voice)

        @self.bot.message_handler(content_types=['document'])
        def handle_doc(message) -> None:
            self.events_work(message,TypeEvent.Document)

        @self.bot.message_handler(content_types=['sticker'])
        def handle_sticker(message) -> None:
            self.events_work(message,TypeEvent.Sticker)

        @self.bot.message_handler(content_types=['video'])
        def handle_video(message) -> None:
            self.events_work(message,TypeEvent.Video)

        @self.bot.message_handler(content_types=['venue'])
        def handle_venue(message) -> None:
            self.events_work(message,TypeEvent.Venue)

        @self.bot.message_handler(content_types=['contact'])
        def handle_contact(message) -> None:
            self.events_work(message,TypeEvent.Contact)

        @self.bot.message_handler(content_types=['dice'])
        def handle_dice(message) -> None:
            self.events_work(message,TypeEvent.Dice)

        @self.bot.message_handler(content_types=['location'])
        @self.bot.edited_message_handler(content_types=['location'])
        def handle_location(message) -> None:
            self.events_work(message,TypeEvent.Location)

        # --- Telegram system-like member updates (groups/supergroups) ---
        @self.bot.message_handler(func=lambda message: bool(getattr(message, "new_chat_members", None)))
        def handle_new_chat_members(message) -> None:
            self.events_work(message, TypeEvent.Join)

        @self.bot.message_handler(func=lambda message: getattr(message, "left_chat_member", None) is not None)
        def handle_left_chat_member(message) -> None:
            self.events_work(message, TypeEvent.Leave)

        @self.bot.message_handler(func=lambda message: bool(getattr(message, "new_chat_title", None)))
        def handle_new_chat_title(message) -> None:
            self.events_work(message, TypeEvent.NewChatTitle)

        @self.bot.message_handler(func=lambda message: bool(getattr(message, "new_chat_photo", None)))
        def handle_new_chat_photo(message) -> None:
            self.events_work(message, TypeEvent.NewChatPhoto)

        @self.bot.message_handler(func=lambda message: getattr(message, "pinned_message", None) is not None)
        def handle_pinned_message(message) -> None:
            self.events_work(message, TypeEvent.PinnedMessage)

        @self.bot.message_handler(func=lambda message: getattr(message, "deleted_message", None) is not None)
        def handle_deleted_message(message) -> None:
            self.events_work(message, TypeEvent.DeletedMessage)
