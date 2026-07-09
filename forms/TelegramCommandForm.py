from flask import render_template, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectMultipleField, IntegerField, TextAreaField
from wtforms.validators import DataRequired
from plugins.TelegramBot.models.TelegramUser import TelegramUser
from plugins.TelegramBot.models.TelegramCommand import TelegramCommand
from plugins.TelegramBot.services.command_service import save_command

# Определение класса формы
class TelegramCommandForm(FlaskForm):
    title = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    active = BooleanField('Active')
    code = TextAreaField("Code", render_kw={"rows": 15})
    priority = IntegerField('Proirity')
    show = BooleanField('Show')
    users = SelectMultipleField('Users', coerce=str)
    submit = SubmitField('Submit')

def addCommand(request):
    form = TelegramCommandForm()
    
    form.users.data = []
    users = TelegramUser.query.all()
    form.users.choices = [(user.user_id, user.name) for user in users]

    if form.validate_on_submit():
        save_command({
            "title": form.title.data,
            "description": form.description.data,
            "active": form.active.data,
            "code": form.code.data,
            "priority": form.priority.data,
            "show": form.show.data,
            "users": form.users.data,
        })
        return redirect("TelegramBot?tab=commands")
    
    form.title.data = ""
    form.description.data = ""
    form.active.data = True
    form.priority.data = 0
    form.show.data = True
    return render_template('telegram_command.html', form=form)

def editCommand(request):
    command_id = request.args.get("command",None)
    command = TelegramCommand.get_by_id(command_id)
    form = TelegramCommandForm(obj=command)
    users = TelegramUser.query.all()
    form.users.choices = [(user.user_id, user.name) for user in users]

    
    if form.validate_on_submit():
        save_command({
            "title": form.title.data,
            "description": form.description.data,
            "active": form.active.data,
            "code": form.code.data,
            "priority": form.priority.data,
            "show": form.show.data,
            "users": form.users.data,
        }, entity_id=command.id)
        return redirect("TelegramBot?tab=commands")
    
    form.users.data = command.users.split(',') if command.users else []
    return render_template('telegram_command.html', form=form)