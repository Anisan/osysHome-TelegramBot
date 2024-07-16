from flask import render_template, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectMultipleField, widgets , IntegerField, TextAreaField
from wtforms.validators import DataRequired
from plugins.TelegramBot.models.TelegramUser import TelegramUser
from plugins.TelegramBot.models.TelegramCommand import TelegramCommand
from app.database import db

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.TableWidget(with_table_tag=False)
    #widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

# Определение класса формы
class TelegramCommandForm(FlaskForm):
    title = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    active = BooleanField('Active')
    code = TextAreaField("Code", render_kw={"rows": 15})
    priority = IntegerField('Proirity')
    show = BooleanField('Show')
    users = MultiCheckboxField('Users')
    submit = SubmitField('Submit')

def addCommand(request):
    form = TelegramCommandForm()
    
    form.users.data = []
    users = TelegramUser.query.all()
    form.users.choices = [(user.user_id, user.name) for user in users]

    if form.validate_on_submit():
                # Создаем экземпляр модели данных
        telegram_command = TelegramCommand(
            title=form.title.data,
            description=form.description.data,
            active=form.active.data,
            code=form.code.data,
            priority=form.priority.data,
            show=form.show.data
        )
        # Заполняем поле users данными из формы
        telegram_command.users = ",".join(form.users.data)

        # Сохраняем экземпляр в базе данных
        db.session.add(telegram_command)
        db.session.commit()  # Сохраняем изменения в базе данных
        return redirect("TelegramBot?tab=commands")
    
    form.title.data = ""
    form.description.data = ""
    form.active.data = True
    form.priority.data = 0
    form.show.data = True
    return render_template('telegram_command.html', form=form)

def editCommand(request):
    id = request.args.get("command",None)
    command = TelegramCommand.get_by_id(id)
    form = TelegramCommandForm(obj=command)
    users = TelegramUser.query.all()
    form.users.choices = [(user.user_id, user.name) for user in users]

    
    if form.validate_on_submit():
        # Создаем экземпляр модели данных
        form.populate_obj(command)
        # Заполняем поле users данными из формы
        command.users = ",".join(form.users.data)

        db.session.commit()  # Сохраняем изменения в базе данных
        return redirect("TelegramBot?tab=commands")
    
    form.users.data = command.users.split(',') if command.users else []
    return render_template('telegram_command.html', form=form)