from app.database import Column, Model, SurrogatePK, db
import datetime

class TelegramCommand(SurrogatePK, db.Model):
    __tablename__ = 'tlg_command'
    title = Column(db.String(100))
    description = Column(db.String(255))
    active = Column(db.Boolean, default=True)
    code = Column(db.Text)
    priority = Column(db.Integer, default=0)
    show = Column(db.Boolean, default=True)
    users = Column(db.String(512))
