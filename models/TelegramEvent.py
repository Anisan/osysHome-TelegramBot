from app.database import Column, SurrogatePK, db

class TelegramEvent(SurrogatePK, db.Model):
    __tablename__ = 'tlg_event'
    title = Column(db.String(100))
    description = Column(db.String(255))
    active = Column(db.Boolean, default=True)
    type = Column(db.Integer, default=0)
    code = Column(db.Text)
