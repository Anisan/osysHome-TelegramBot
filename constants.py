""" Constants TelegramBot"""
from enum import Enum

class TypeEvent(Enum):
    """ Type event """
    Callback = 0
    Text = 1
    Image = 2
    Voice = 3
    Audio = 4
    Video = 5
    Document = 6
    Sticker = 7
    Location = 8

class TypeDirection(Enum):
    """ Type direction """
    Unknown = 0
    Out = 1
    In = 2
    Resend = 3
    ErrorOut = -1