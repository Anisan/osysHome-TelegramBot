from flask import redirect, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField, IntegerField
from wtforms.validators import DataRequired, Optional
from ..models.TelegramUser import TelegramUser
from ..services.user_service import save_user
from app.core.lib.object import getObjectsByClass

# Определение класса формы
class TelegramUserForm(FlaskForm):
    user_id = StringField('Telegram Chat ID', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    user = SelectField('User', validators=[Optional()], coerce=str, validate_choice=False)
    say = IntegerField("Say level")
    command = BooleanField("Commands")
    submit = SubmitField('Submit')

def editUser(request):
    user_id = request.args.get("user", None)
    user = TelegramUser.get_by_id(user_id)
    form = TelegramUserForm(obj=user)  # Передаем объект в форму для редактирования
    form.user.choices = [("","")]
    
    if form.validate_on_submit():
        payload = {
            "user_id": form.user_id.data,
            "name": form.name.data,
            "user": form.user.data,
            "say": form.say.data,
            "command": form.command.data,
        }
        if user_id:
            save_user(payload, entity_id=int(user_id))
        else:
            save_user(payload)
        return redirect("TelegramBot")

    users = getObjectsByClass("Users")
    form.user.choices = [("","")] + [(user.name, user.description if user.description else user.name) for user in users]
    return render_template('telegram_user.html', user=user_id, form=form)