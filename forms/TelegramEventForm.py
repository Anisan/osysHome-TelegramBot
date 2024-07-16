from flask import render_template, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectMultipleField, widgets , SelectField, TextAreaField
from wtforms.validators import DataRequired
from app.database import db
from plugins.TelegramBot.models.TelegramUser import TelegramUser
from plugins.TelegramBot.models.TelegramEvent import TelegramEvent
from ..constants import TypeEvent

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.TableWidget(with_table_tag=False)
    option_widget = widgets.CheckboxInput()

# Определение класса формы
class TelegramEventForm(FlaskForm):
    title = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    active = BooleanField('Active')
    type = SelectField('Type')
    code = TextAreaField("Code", render_kw={"rows": 15})
    submit = SubmitField('Submit')

_typesEvent = [(t.value, t.name) for t in TypeEvent]

def addEvent(request):
    form = TelegramEventForm()
    form.type.choices = _typesEvent

    if form.validate_on_submit():
        # Создаем экземпляр модели данных
        telegram_event = TelegramEvent(
            title=form.title.data,
            description=form.description.data,
            active=form.active.data,
            code=form.code.data,
            type=form.type.data
        )
        db.session.add(telegram_event)
        db.session.commit()  # Сохраняем изменения в базе данных
        return redirect("TelegramBot?tab=events")
    
    form.title.data = ""
    form.description.data = ""
    form.active.data = True
    return render_template('telegram_event.html', form=form)

def editEvent(request):
    id = request.args.get("event",None)
    command = TelegramEvent.get_by_id(id)
    form = TelegramEventForm(obj=command)
    form.type.choices = _typesEvent
    
    if form.validate_on_submit():
        form.populate_obj(command)
        db.session.commit()
        return redirect("TelegramBot?tab=events")
    
    return render_template('telegram_event.html', form=form)