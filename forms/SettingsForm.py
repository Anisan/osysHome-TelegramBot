from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, IntegerField
from wtforms.validators import DataRequired

# Определение класса формы
class SettingsForm(FlaskForm):
    token = StringField('Token', validators=[DataRequired()])
    register = BooleanField("Register new user")
    history_day = IntegerField("History keep day")
    submit = SubmitField('Submit')
    