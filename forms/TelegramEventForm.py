from flask import render_template, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectMultipleField, SelectField, TextAreaField
from wtforms.validators import DataRequired
from plugins.TelegramBot.models.TelegramEvent import TelegramEvent
from plugins.TelegramBot.models.TelegramUser import TelegramUser
from plugins.TelegramBot.services.event_service import save_event
from ..constants import TypeEvent

# Определение класса формы
class TelegramEventForm(FlaskForm):
    title = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    active = BooleanField('Active')
    type = SelectField('Type')
    code = TextAreaField("Code", render_kw={"rows": 15})
    users = SelectMultipleField('Users', coerce=str)
    submit = SubmitField('Submit')


_typesEvent = [(t.value, t.name) for t in TypeEvent]


def addEvent(request):
    form = TelegramEventForm()
    form.type.choices = _typesEvent
    users = TelegramUser.query.all()
    form.users.choices = [(user.user_id, user.name) for user in users]
    form.users.data = []

    if form.validate_on_submit():
        save_event({
            "title": form.title.data,
            "description": form.description.data,
            "active": form.active.data,
            "code": form.code.data,
            "type": form.type.data,
            "users": form.users.data,
        })
        return redirect("TelegramBot?tab=events")
    
    form.title.data = ""
    form.description.data = ""
    form.active.data = True
    return render_template('telegram_event.html', form=form)

def editEvent(request):
    event_id = request.args.get("event",None)
    event = TelegramEvent.get_by_id(event_id)
    form = TelegramEventForm(obj=event)
    form.type.choices = _typesEvent
    users = TelegramUser.query.all()
    form.users.choices = [(user.user_id, user.name) for user in users]
    
    if form.validate_on_submit():
        save_event({
            "title": form.title.data,
            "description": form.description.data,
            "active": form.active.data,
            "code": form.code.data,
            "type": form.type.data,
            "users": form.users.data,
        }, entity_id=event.id)
        return redirect("TelegramBot?tab=events")

    form.users.data = event.users.split(',') if event.users else []
    return render_template('telegram_event.html', form=form)