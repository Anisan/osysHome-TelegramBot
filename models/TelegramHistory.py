import datetime
from app.database import Column, Model, SurrogatePK, db
from plugins.TelegramBot.constants import TypeDirection, TypeEvent

class TelegramHistory(SurrogatePK, db.Model):
    __tablename__ = 'tlg_history'
    user_id = Column(db.String(100))
    created = Column(db.DateTime(), default = datetime.datetime.now())
    _direction = Column("direction", db.Integer)
    _type = Column("type", db.Integer)
    message = Column(db.Text)
    raw = Column(db.Text)

    @property
    def direction(self):
        return TypeDirection(self._direction)

    @direction.setter
    def direction(self, value):
        if isinstance(value, TypeDirection):
            self._direction = value.value
        elif isinstance(value, int):
            self._direction = value
        else:
            raise ValueError("Invalid value for direction")
        
    @property
    def type(self) -> TypeEvent:
        return TypeEvent(self._type)

    @type.setter
    def type(self, value):
        if isinstance(value, TypeEvent):
            self._type = value.value
        elif isinstance(value, int):
            self._type = value
        else:
            raise ValueError("Invalid value for event")