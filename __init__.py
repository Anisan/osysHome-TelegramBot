from flask import redirect,send_from_directory
import requests
import os
import telebot
from sqlalchemy import or_, delete
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database import session_scope, getSession, db
from app.authentication.handlers import handle_user_required
from app.core.lib.cache import saveToCache, getCacheDir
from app.core.main.BasePlugin import BasePlugin
from app.core.lib.constants import CategoryNotify
from app.core.lib.common import addNotify
from plugins.TelegramBot.forms.SettingsForm import SettingsForm
from plugins.TelegramBot.forms.TelegramUserForm import editUser
from plugins.TelegramBot.models.TelegramUser import TelegramUser
from plugins.TelegramBot.models.TelegramHistory import TelegramHistory
from plugins.TelegramBot.models.TelegramCommand import TelegramCommand
from plugins.TelegramBot.models.TelegramEvent import TelegramEvent
from plugins.TelegramBot.handlers.CommandHandler import CommandHandler
from plugins.TelegramBot.handlers.MessageHandler import MessageHandler
from plugins.TelegramBot.handlers.CallbackHandler import CallbackHandler
from plugins.TelegramBot.constants import TypeEvent, TypeDirection


class TelegramBot(BasePlugin):

    def __init__(self,app):
        super().__init__(app,__name__)
        self.title = "TelegramBot"
        self.description = """This is a plugin for Telegram"""
        self.version = "0.2"
        self.category = "App"
        self.actions = ["cycle", "say", "search"]
        self.bot = None
        self.session = getSession()
        self.isStarted = False

    def initialization(self):
        TOKEN = self.config.get('token','')
        if not TOKEN:
            self.logger.warning("Please set token in config")
            addNotify("Empty TOKEN", "Please set token in config", CategoryNotify.Error, self.name)
            return False
        self.bot = telebot.TeleBot(TOKEN, threaded=False)
        # import logging
        # logger = telebot.logger
        # telebot.logger.setLevel(logging.DEBUG)
        self.handlerCommand = CommandHandler(self)
        self.handlerCommand.handle()
        self.handlerMessage = MessageHandler(self)
        self.handlerMessage.handle()
        self.callbackHandler = CallbackHandler(self)
        self.callbackHandler.handle()

        users = self.session.query(TelegramUser).all()
        for user in users:
            self.save_user_avatar(user.user_id)

    def cyclic_task(self):
        if self.bot:
            if not self.isStarted:
                import threading

                def wrapper():
                    try:
                        self.bot.polling(non_stop=True, long_polling_timeout=5)
                    except Exception as ex:
                        self.logger.exception(ex)

                thread = threading.Thread(name="Thread_pooling_telegram",target=wrapper)
                thread.start()
                self.isStarted = True
            if self.event.is_set():
                # Останавливаем цикл обработки сообщений
                self.bot.stop_polling()
                self.isStarted = False
        else:
            self.event.wait(60.0)

    def admin(self, request):
        args = request.args
        user = args.get('user',None)
        command = args.get('command',None)
        event = args.get('event',None)
        history = args.get('history',None)
        op = args.get('op','')
        tab = args.get('tab','')
        if user:
            if op == "edit":
                result = editUser(request)
                return result
            elif op == "delete":
                self.session.query(TelegramUser).filter(TelegramUser.id == int(user)).delete()
                self.session.commit()
                return redirect(self.name)

        if op == "add_command":
            from plugins.TelegramBot.forms.TelegramCommandForm import addCommand
            return addCommand(request)
        if command:
            if op == "edit":
                from plugins.TelegramBot.forms.TelegramCommandForm import editCommand
                return editCommand(request)
            elif op == "delete":
                self.session.query(TelegramCommand).filter(TelegramCommand.id == int(command)).delete()
                self.session.commit()
                return redirect(self.name + "?tab=commands")

        if op == "add_event":
            from plugins.TelegramBot.forms.TelegramEventForm import addEvent
            return addEvent(request)
        if event:
            if op == "edit":
                from plugins.TelegramBot.forms.TelegramEventForm import editEvent
                return editEvent(request)
            elif op == "delete":
                self.session.query(TelegramEvent).filter(TelegramEvent.id == int(event)).delete()
                self.session.commit()
                return redirect(self.name + "?tab=events")

        if op == "clean_history":
            sql = delete(TelegramHistory)
            db.session.execute(sql)
            db.session.commit()
            return redirect(self.name + "?tab=history")

        if history:
            if op == "delete":
                sql = delete(TelegramHistory).where(TelegramHistory.id == history)
                db.session.execute(sql)
                db.session.commit()
                return redirect(self.name + "?tab=history")

        if tab == 'commands':
            commands = TelegramCommand.query.all()
            content = {
                "commands": commands,
                "tab": tab,
            }
            return self.render('commands_bot.html', content)

        if tab == 'events':
            events = TelegramEvent.query.all()
            content = {
                "events": events,
                "tab": tab,
            }
            return self.render('events_bot.html', content)

        if tab == 'history':
            history = TelegramHistory.query.all()
            content = {
                "history": history,
                "tab": tab,
            }
            return self.render('history_bot.html', content)

        if tab == "settings":
            settings = SettingsForm()
            if request.method == 'GET':
                settings.token.data = self.config.get('token','')
                settings.register.data = self.config.get('register', False)
            else:
                if settings.validate_on_submit():
                    self.config["token"] = settings.token.data
                    self.config['register'] = settings.register.data
                    self.saveConfig()
                    return redirect(self.name)
            content = {
                "form": settings,
                "tab": tab,
            }
            return self.render('settings_bot.html', content)

        users = TelegramUser.query.all()
        content = {
            "users": users,
            "tab":tab,
        }
        return self.render('users_bot.html', content)

    def search(self, query: str) -> str:
        res = []
        commands = TelegramCommand.query.filter(or_(TelegramCommand.code.contains(query),TelegramCommand.title.contains(query),TelegramCommand.description.contains(query))).all()
        for cmnd in commands:
            res.append({"url":f'TelegramBot?command={cmnd.id}&op=edit', "title":f'{cmnd.title} - {cmnd.description}',
                        "tags":[{"name":"TelegramBot","color":"success"},{"name":"Command","color":"primary"}]})
        events = TelegramEvent.query.filter(or_(TelegramEvent.code.contains(query),TelegramEvent.title.contains(query),TelegramEvent.description.contains(query))).all()
        for event in events:
            res.append(
                {"url":f'TelegramBot?event={event.id}&op=edit',
                 "title":f'{event.title} - {event.description}',
                 "tags":[{"name":"TelegramBot","color":"success"},
                         {"name":"Event","color":"warning"}]}
            )
        return res

    def say(self, message, level=0, args=None):
        users = self.session.query(TelegramUser).filter(TelegramUser.say > -1).all()
        for user in users:
            if level >= user.say:
                if args and 'image' in args:
                    self.bot.send_photo(user.user_id, args['image'], message)
                else:
                    self.send_message(user.user_id, message)

    def save_user_avatar(self, user_id):
        try:
            token = self.config.get('token','')
            chat = self.bot.get_chat(user_id)
            if chat.photo:
                file_id = chat.photo.big_file_id
                file_info = self.bot.get_file(file_id)
                file_url = f"https://api.telegram.org/file/bot{token}/{file_info.file_path}"
                response = requests.get(file_url)

                file_path = saveToCache(str(user_id) + ".jpg",response.content,os.path.join(self.name,"avatars"))

                self.logger.debug(f"Avatar saved to {file_path}")
            else:
                self.logger.debug("User has no profile photos.")
        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")

    def route_index(self):
        @self.blueprint.route('/TelegramBot/avatars/<path:filename>', methods=["GET"])
        @handle_user_required
        def avatars(filename):
            path = getCacheDir()
            from settings import Config
            full_path = os.path.join(Config.APP_DIR,path,self.name,"avatars")
            return send_from_directory(full_path, filename)

    def buildInlineKeyBoard(self, buttons: list[dict]) -> InlineKeyboardMarkup:
        """ Build inline keyboard

        Args:
            buttons (list[dict]): List rows dict buttons. Key -> text, Value -> callback_data

        Returns:
            InlineKeyboardMarkup: Keyboard
        """
        markup = InlineKeyboardMarkup()
        for btn in buttons:
            row = []
            for key, value in btn.items():
                keyb = InlineKeyboardButton(key, callback_data=value)
                row.append(keyb)
            markup.add(*row)
        return markup

    def send_message(self, chat_id, message, markup=None, parse_mode='HTML'):
        with session_scope() as session:
            if not markup:
                user = session.query(TelegramUser).where(TelegramUser.user_id == str(chat_id)).one_or_none()
                if user and user.command:
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    cmnds = session.query(TelegramCommand).where(TelegramCommand.active, TelegramCommand.show,
                                                                 or_(not TelegramCommand.users, TelegramCommand.users == "", TelegramCommand.users.contains(chat_id))).order_by(TelegramCommand.priority).all()   # todo users validate
                    for cmnd in cmnds:
                        item = types.KeyboardButton(cmnd.title)
                        markup.add(item)

            history = TelegramHistory()
            history.user_id = chat_id
            history.message = message
            history.type = TypeEvent.Text
            history.direction = TypeDirection.Out
            session.add(history)
            try:
                res = self.bot.send_message(chat_id, message, reply_markup=markup, parse_mode=parse_mode)
            except Exception as ex:
                self.logger.exception(ex)
                history.direction = TypeDirection.ErrorOut

            history.raw = str(res.json)
            session.commit()

    def send_video(self, chat_id, message, path_file):
        self.bot.send_video(chat_id=chat_id, caption=message, video=open(path_file, 'rb'), supports_streaming=True)

    def sendMessageByName(self, name, message):
        user = self.session.query(TelegramUser).filter(TelegramUser.name == name).one_or_none()
        if user:
            self.send_message(user.user_id, message)

    # Функция для обработки текстовых сообщений
    async def echo(self,update):
        await update.message.reply_text(update.message.text)
