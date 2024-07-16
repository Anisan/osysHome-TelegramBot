import json, re
from app.database import session_scope
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
                                self.logger.critical(ex, exc_info=True)
            except Exception as ex:
                self.logger.critical(ex, exc_info=True) 
             
            