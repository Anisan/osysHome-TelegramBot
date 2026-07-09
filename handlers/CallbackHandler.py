import re
from app.database import session_scope, get_now_to_utc
from app.core.lib.execute import execute_and_capture_output
from . import Handler
from ..models.TelegramUser import TelegramUser
from ..models.TelegramHistory import TelegramHistory
from ..models.TelegramEvent import TelegramEvent
from ..constants import TypeEvent, TypeDirection

class CallbackHandler(Handler):
    def __init__(self, module):
        super().__init__(module)
        self.config = module.config
        self._app = module._app
        self.module = module

    def handle(self):
        @self.bot.callback_query_handler(func=lambda callback: True)
        def handle_inline(callback):
            try:
                with session_scope() as session:
                    self.logger.debug(callback.json)
                    history = TelegramHistory()
                    history.created = get_now_to_utc()
                    history.user_id = callback.from_user.id
                    history.message = callback.data
                    history.type = TypeEvent.Callback
                    history.direction = TypeDirection.In
                    history.raw = str(callback.json)

                    session.add(history)
                    session.commit()

                    user = session.query(TelegramUser).where(TelegramUser.user_id == str(callback.from_user.id)).one_or_none()
                    if not user:
                        return False

                    callbacks = session.query(TelegramEvent).where(TelegramEvent.active, TelegramEvent.type == 0).all()
                    for clb in callbacks:
                        actor_user_id = self._resolve_callback_actor_user_id(callback)
                        chat_id = self._resolve_callback_chat_id(callback)
                        if not self._entity_allows_user(clb.users, actor_user_id, chat_id):
                            continue
                        result = re.match(clb.title, callback.data)
                        if result:
                            self.logger.info("Execute event %s(%s)",clb.title,clb.description)
                            try:
                                variables = {
                                    'self': self.module,
                                    'callback': callback,
                                    'logger': self.logger,
                                    **vars(self)
                                }
                                output, error = execute_and_capture_output(clb.code, variables)
                                if error:
                                    self.logger.error(output)
                            except Exception as ex:
                                self.logger.exception(ex, exc_info=True)
            except Exception as ex:
                self.logger.exception(ex, exc_info=True) 

    def _entity_allows_user(self, users_raw, user_id: str, chat_id: str = "") -> bool:
        if not users_raw:
            return True
        allowed_ids = {value for value in (user_id, chat_id) if value}
        if not allowed_ids:
            return False
        users = [item.strip() for item in str(users_raw).split(",") if item and item.strip()]
        return any(candidate in users for candidate in allowed_ids)

    def _resolve_callback_actor_user_id(self, callback) -> str:
        from_user = getattr(callback, "from_user", None)
        if from_user is not None and getattr(from_user, "id", None) is not None:
            return str(from_user.id)

        return self._resolve_callback_chat_id(callback)

    def _resolve_callback_chat_id(self, callback) -> str:
        message = getattr(callback, "message", None)
        if message is not None:
            chat = getattr(message, "chat", None)
            if chat is not None and getattr(chat, "id", None) is not None:
                return str(chat.id)

        return ""
             
            