from flask import redirect,send_from_directory
import requests
import os
import telebot
from sqlalchemy import or_, delete, desc
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import InputMediaPhoto, InputMediaVideo
from app.database import session_scope, get_now_to_utc, row2dict, convert_utc_to_local
                    
from app.authentication.handlers import handle_user_required
from app.core.lib.cache import saveToCache, getCacheDir
from app.core.main.BasePlugin import BasePlugin
from app.core.lib.constants import CategoryNotify
from app.core.lib.common import addNotify
from app.core.lib.object import getProperty
from plugins.TelegramBot.forms.SettingsForm import SettingsForm
from plugins.TelegramBot.forms.TelegramUserForm import editUser
from plugins.TelegramBot.models.TelegramUser import TelegramUser
from plugins.TelegramBot.models.TelegramHistory import TelegramHistory
from plugins.TelegramBot.models.TelegramCommand import TelegramCommand
from plugins.TelegramBot.models.TelegramEvent import TelegramEvent
from plugins.TelegramBot.handlers.CommandHandler import CommandHandler
from plugins.TelegramBot.handlers.MessageHandler import MessageHandler
from plugins.TelegramBot.handlers.CallbackHandler import CallbackHandler
from plugins.TelegramBot.constants import TypeEvent, TypeDirection, MAX_SEND_ATTEMPTS


class TelegramBot(BasePlugin):

    def __init__(self,app):
        super().__init__(app,__name__)
        self.title = "TelegramBot"
        self.description = """This is a plugin for Telegram"""
        self.version = "0.2"
        self.category = "App"
        self.actions = ["cycle", "say", "search"]
        self.bot = None
        self.isStarted = False

    def _get_proxies(self):
        """Return proxies dict for requests/telebot from config proxy_url."""
        url = (self.config.get('proxy_url') or '').strip()
        if not url:
            return None
        return {'http': url, 'https': url}

    def _get_timeout(self):
        """Return timeout in seconds for API requests (default 30)."""
        val = self.config.get('timeout')
        if val is None:
            return 30
        try:
            return max(5, min(300, int(val)))
        except (TypeError, ValueError):
            return 30

    def initialization(self):
        TOKEN = self.config.get('token','')
        if not TOKEN:
            self.logger.warning("Please set token in config")
            addNotify("Empty TOKEN", "Please set token in config", CategoryNotify.Error, self.name)
            return False
        proxies = self._get_proxies()
        if proxies:
            telebot.apihelper.proxy = proxies
            self.logger.info("Using proxy for Telegram API")
        else:
            telebot.apihelper.proxy = None
        timeout_sec = self._get_timeout()
        telebot.apihelper.CONNECT_TIMEOUT = timeout_sec
        telebot.apihelper.READ_TIMEOUT = timeout_sec
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

        with session_scope() as session:
            users = session.query(TelegramUser).all()
            for user in users:
                self.save_user_avatar(user.user_id)

    def cyclic_task(self):
        if not self.isStarted:
            if self.bot:
                import threading

                def wrapper():
                    try:
                        self.bot.polling(non_stop=True, long_polling_timeout=5)
                    except Exception as ex:
                        self.logger.exception(ex)
                        self.isStarted = False

                self.isStarted = True
                thread = threading.Thread(name="Thread_pooling_telegram",target=wrapper)
                thread.start()
        else:
            if self.event.is_set():
                # Останавливаем цикл обработки сообщений
                if self.bot:
                    self.bot.stop_polling()
                self.isStarted = False
                return

            # resend error mesages
            self.resend_error_message()

            # clean history
            history_day = self.config.get('history_day',7)
            TelegramHistory.clean_history_day(history_day)

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
                with session_scope() as session:
                    session.query(TelegramUser).filter(TelegramUser.id == int(user)).delete()
                    session.commit()
                return redirect(self.name)
        if op == "add_user":
            result = editUser(request)
            return result

        if op == "update_users":
            with session_scope() as session:
                users = session.query(TelegramUser).all()
                for user in users:
                    info = self.save_user_avatar(user.user_id)
                    if info:
                        user.name = info.title if info.title else info.username
                session.commit()
            return redirect("TelegramBot")

        if op == "add_command":
            from plugins.TelegramBot.forms.TelegramCommandForm import addCommand
            return addCommand(request)
        if command:
            if op == "edit":
                from plugins.TelegramBot.forms.TelegramCommandForm import editCommand
                return editCommand(request)
            elif op == "delete":
                with session_scope() as session:
                    session.query(TelegramCommand).filter(TelegramCommand.id == int(command)).delete()
                    session.commit()
                return redirect(self.name + "?tab=commands")

        if op == "add_event":
            from plugins.TelegramBot.forms.TelegramEventForm import addEvent
            return addEvent(request)
        if event:
            if op == "edit":
                from plugins.TelegramBot.forms.TelegramEventForm import editEvent
                return editEvent(request)
            elif op == "delete":
                with session_scope() as session:
                    session.query(TelegramEvent).filter(TelegramEvent.id == int(event)).delete()
                    session.commit()
                return redirect(self.name + "?tab=events")

        if op == "clean_history":
            TelegramHistory.delete()
            return redirect(self.name + "?tab=history")

        if history:
            if op == "delete":
                with session_scope() as session:
                    sql = delete(TelegramHistory).where(TelegramHistory.id == history)
                    session.execute(sql)
                    session.commit()
                return redirect(self.name + "?tab=history")

        if tab == 'commands':
            commands = TelegramCommand.query.all()
            commands = [row2dict(command) for command in commands]
            content = {
                "commands": commands,
                "tab": tab,
            }
            return self.render('commands_bot.html', content)

        if tab == 'events':
            events = TelegramEvent.query.all()
            events = [row2dict(event) for event in events]
            content = {
                "events": events,
                "tab": tab,
            }
            return self.render('events_bot.html', content)

        if tab == 'history':
            history = TelegramHistory.query.order_by(desc(TelegramHistory.created)).limit(200).all()
            history = [row2dict(item) for item in history]
            for item in history:
                d = item.get('direction') or item.get('_direction')
                if hasattr(d, 'value'):
                    item['direction'] = d.value
                elif isinstance(d, int):
                    item['direction'] = d
                else:
                    item['direction'] = 0
            content = {
                "history": history,
                "tab": tab,
            }
            return self.render('history_bot.html', content)

        if tab == "settings":
            settings = SettingsForm()
            if request.method == 'GET':
                settings.token.data = self.config.get('token','')
                settings.history_day.data = self.config.get('history_day',7)
                settings.register.data = self.config.get('register', False)
                settings.proxy_url.data = self.config.get('proxy_url', '')
                settings.timeout.data = self.config.get('timeout', 30)
                settings.commands_in_row.data = self.config.get('commands_in_row', 2)
            else:
                if settings.validate_on_submit():
                    old_token = self.config.get("token",'')
                    old_proxy = self.config.get('proxy_url', '')
                    old_timeout = self.config.get('timeout', 30)
                    self.config["token"] = settings.token.data
                    self.config["history_day"] = settings.history_day.data
                    self.config['register'] = settings.register.data
                    self.config['proxy_url'] = (settings.proxy_url.data or '').strip()
                    self.config['timeout'] = settings.timeout.data if settings.timeout.data is not None else 30
                    self.config['commands_in_row'] = settings.commands_in_row.data if settings.commands_in_row.data is not None else 2
                    self.saveConfig()
                    if (old_token != self.config["token"] or old_proxy != self.config.get('proxy_url', '')
                            or old_timeout != self.config.get('timeout', 30)):
                        self.stop_cycle()
                        self.initialization()
                        self.start_cycle()
                    return redirect(self.name)
            content = {
                "form": settings,
                "tab": tab,
            }
            return self.render('settings_bot.html', content)

        users = TelegramUser.query.all()
        users = [row2dict(user) for user in users]
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
        with session_scope() as session:
            users = session.query(TelegramUser).filter(TelegramUser.say > -1).all()
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
                proxies = self._get_proxies()
                response = requests.get(file_url, proxies=proxies, timeout=self._get_timeout())

                file_path = saveToCache(str(user_id) + ".jpg",response.content,os.path.join(self.name,"avatars"))

                self.logger.debug(f"Avatar saved to {file_path}")
            else:
                self.logger.debug("User has no profile photos.")
            return chat
        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")
            return None

    def route_index(self):
        @self.blueprint.route('/TelegramBot/avatars/<path:filename>', methods=["GET"])
        @handle_user_required
        def avatars(filename):
            path = getCacheDir()
            from app.configuration import Config
            full_path = os.path.join(Config.APP_DIR,path,self.name,"avatars")
            return send_from_directory(full_path, filename)

    def resend_error_message(self):
        fatalDescription = [
            'Bad Request: chat not found',
            'Forbidden: bot was blocked by the user'
        ]
        with session_scope() as session:
            messages = session.query(TelegramHistory).filter(
                TelegramHistory._direction >= int(TypeDirection.ErrorOut.value),
                TelegramHistory._direction < int(TypeDirection.ErrorOutFatal.value),
                TelegramHistory.send_attempts < MAX_SEND_ATTEMPTS
            ).order_by(TelegramHistory.created).limit(10).all()
            for message in messages:
                if message.type != TypeEvent.Text:
                    continue
                message.send_attempts += 1
                dt = convert_utc_to_local(message.created)
                text = f'{message.message}\n(resent at {str(dt)}) [{message.send_attempts}/{MAX_SEND_ATTEMPTS}]'
                direction, result = self._send_message(message.user_id, text)
                if direction == TypeDirection.Out:
                    message.direction = TypeDirection.Resend
                    session.commit()
                else:
                    if message.send_attempts >= MAX_SEND_ATTEMPTS:
                        message.direction = TypeDirection.ErrorOutFatal
                    elif isinstance(result, dict) and result.get("description") in fatalDescription:
                        message.direction = TypeDirection.ErrorOutFatal
                    session.commit()

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

    def _send_message(self, chat_id, message, markup=None, parse_mode='HTML'):
        with session_scope() as session:
            if not markup:
                user = session.query(TelegramUser).where(TelegramUser.user_id == str(chat_id)).one_or_none()
                if user and user.command:
                    commands_in_row = self.config.get('commands_in_row', 2)
                    try:
                        commands_in_row = int(commands_in_row)
                    except (TypeError, ValueError):
                        commands_in_row = 2
                    commands_in_row = max(1, min(10, commands_in_row))
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=commands_in_row)
                    cmnds = session.query(TelegramCommand).where(TelegramCommand.active, TelegramCommand.show,
                                                                 or_(not TelegramCommand.users, TelegramCommand.users == "", TelegramCommand.users.contains(chat_id))).order_by(TelegramCommand.priority).all()   # todo users validate
                    buttons = []
                    for cmnd in cmnds:
                        item = types.KeyboardButton(cmnd.title)
                        buttons.append(item)
                    if buttons:
                        markup.add(*buttons)
            try:
                res = self.bot.send_message(chat_id, message, reply_markup=markup, parse_mode=parse_mode)
                return TypeDirection.Out, res
            except telebot.apihelper.ApiTelegramException as ex:
                return TypeDirection.ErrorOut, ex.result_json
            except Exception as ex:
                self.logger.exception(ex)
                return TypeDirection.ErrorOut, ex

    def send_message(self, chat_id, message, markup=None, parse_mode='HTML'):
        with session_scope() as session:
            history = TelegramHistory()
            history.created = get_now_to_utc()
            history.user_id = chat_id
            history.message = message
            history.type = TypeEvent.Text
            history.direction = TypeDirection.Out
            session.add(history)
            session.commit()
            direction, result = self._send_message(chat_id, message, markup, parse_mode)
            if direction != TypeDirection.Out:
                history.direction = direction
                history.raw = str(result)
                history.send_attempts = 1
                session.commit()
                return None
            else:
                history.raw = str(result.json)
                session.commit()
                return result

    def send_video(self, chat_id, message, path_file):
        self.bot.send_video(chat_id=chat_id, caption=message, video=open(path_file, 'rb'), supports_streaming=True)

    def send_image(self, chat_id, message, path_image):
        self.bot.send_photo(chat_id, path_image, message)

    def send_album(self, chat_id:str, photos:list):
        """ Send album photos to chat

        Args:
            chat_id (str): Chat
            photos (photos): List photos {'path': filepath, 'caption': text}
        """

        media = []
        for photo in photos:
            with open(photo['path'], 'rb') as fh:
                data = fh.read()
                media_photo = InputMediaPhoto(data)
                if 'caption' in photo:
                    media_photo.caption = photo['caption']
                media_photo.parse_mode = 'HTML'
                media.append(media_photo)

        self.bot.send_media_group(chat_id=chat_id, media=media)

    def sendMessageByName(self, name, message):
        """ Send message to user by name

        Args:
            name (str): Name
            message (str): Message
        """
        with session_scope() as session:
            user = session.query(TelegramUser).filter(TelegramUser.name == name).one_or_none()
            if user:
                self.send_message(user.user_id, message)

    def sendMessageToAdmin(self, message):
        """Send message to admins

        Args:
            message (str): Message
        """
        with session_scope() as session:
            users = session.query(TelegramUser).filter(TelegramUser.user is not None).all()
            for user in users:
                role = getProperty(user.user + ".role")
                if role == 'admin':
                    self.send_message(user.user_id, message)
