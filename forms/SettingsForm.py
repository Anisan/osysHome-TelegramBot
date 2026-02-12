from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange

# Определение класса формы
class SettingsForm(FlaskForm):
    token = StringField('Token', validators=[DataRequired()])
    register = BooleanField("Register new user")
    history_day = IntegerField("History keep day")
    proxy_url = StringField('Proxy URL', validators=[Optional()])
    timeout = IntegerField('Timeout (seconds)', default=30, validators=[Optional(), NumberRange(min=5, max=300)])
    submit = SubmitField('Submit')
    