from flask import redirect, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField, IntegerField
from wtforms.validators import DataRequired, Optional
from ..models.TelegramUser import TelegramUser
from app.database import db
from app.core.lib.object import getObjectsByClass

# Определение класса формы
class TelegramUserForm(FlaskForm):
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
        if user_id:
            form.populate_obj(user)  # Обновляем значения объекта данными из формы
            user.user = form.user.data
            db.session.commit()  # Сохраняем изменения в базе данных
            return redirect("TelegramBot")
    
    users = getObjectsByClass("Users")
    form.user.choices = [("","")] + [(user.name, user.description if user.description else user.name) for user in users]
    return render_template('telegram_user.html', user=user_id, form=form)