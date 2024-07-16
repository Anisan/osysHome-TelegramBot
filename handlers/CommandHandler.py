from . import Handler
from ..models.TelegramUser import TelegramUser
from app.database import session_scope
from app.core.lib.constants import CategoryNotify
from app.core.lib.common import addNotify

class CommandHandler(Handler):
    def __init__(self, module):
        super().__init__(module)
        self.config = module.config
        self._app = module._app

    def handle(self):
        @self.bot.message_handler(commands=['start'])
        def handle(message) -> None:
            try:
                self.logger.debug(message.json)
                register = self.config.get('register',False)
                if  not register: 
                    addNotify('Незарегистрированный пользователь','@'+message.from_user.username+' ('+str(message.from_user.id)+')', CategoryNotify.Warning, "TelegramBot")
                    return
                with session_scope() as session:

                    user = session.query(TelegramUser).filter(TelegramUser.user_id == str(message.from_user.id)).one_or_none()
                    if  user is None:
                        # save user
                        user = TelegramUser()
                        user.user_id = message.from_user.id
                        user.name = message.from_user.username
                        user.say = 0
                        session.add(user)
                        session.commit()
                        self.bot.reply_to(message,'Привет! Я телеграм-бот.')
                        addNotify('Зарегистрирован пользователь','@'+message.from_user.username+' ('+str(message.from_user.id)+')', CategoryNotify.Info, "TelegramBot")
                    else:
                        self.bot.reply_to(message,'Вы уже зарегистрированы!')
            except Exception as ex:
                self.logger.critical(ex, exc_info=True) 
