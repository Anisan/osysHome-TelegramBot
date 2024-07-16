import datetime
from app.database import Column, Model, SurrogatePK, db

class TelegramUser(SurrogatePK, db.Model):
    __tablename__ = 'tlg_user'
    user_id = Column(db.String(100))
    name = Column(db.String(255))
    created = Column(db.DateTime(), default = datetime.datetime.now())
    user = Column(db.String(100))
    say = Column(db.Integer)
    command = Column(db.Boolean)
