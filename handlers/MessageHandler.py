import re
from sqlalchemy import or_
from . import Handler
from app.database import session_scope
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

    def events_work(self, message, typeEvent: TypeEvent):
        try:
            with session_scope() as session:
                self.logger.debug(message.json)
                history = TelegramHistory()
                history.user_id = message.chat.id
                history.message = message.text
                history.type = TypeEvent.Text
                history.direction = TypeDirection.In
                history.raw = str(message.json)
                session.add(history)
                session.commit()   

                events = session.query(TelegramEvent).where(TelegramEvent.active, TelegramEvent.type == typeEvent.value).all()
                for event in events:
                    self.logger.info("Execute event %s(%s)",event.title,event.description)
                    try:
                        code = event.code
                        variables = {
                            'self': self.module,
                            'message': message,
                            'logger': self.logger,
                            **vars(self)
                        }
                        # Выполняем код модуля в контексте с logger
                        output, error = execute_and_capture_output(code, variables)
                        if error:
                            self.logger.error(output)
                    except Exception as ex:
                        self.logger.critical(ex, exc_info=True) # TODO write adv info

                return True
        except Exception as ex:
            self.logger.critical(ex, exc_info=True) 
            return False


    def handle(self):
        @self.bot.message_handler(func=lambda message: True)
        def handle(message) -> None:
            try:
                with session_scope() as session:
                    user = session.query(TelegramUser).where(TelegramUser.user_id == str(message.chat.id)).one_or_none()
                    if not user:
                        return 

                    if not self.events_work(message, TypeEvent.Text):
                        return
                    
                    if not user.command:
                        return

                    commands = session.query(TelegramCommand).where(TelegramCommand.active, or_(not TelegramCommand.users, TelegramCommand.users == "", TelegramCommand.users.contains(message.chat.id))).all()
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
                                self.logger.critical(ex, exc_info=True) # TODO write adv info
            except Exception as ex:
                self.logger.critical(ex, exc_info=True) 
                

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
