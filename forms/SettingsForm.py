from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired

# Определение класса формы
class SettingsForm(FlaskForm):
    token = StringField('Token', validators=[DataRequired()])
    register = BooleanField("Register new user")
    submit = SubmitField('Submit')