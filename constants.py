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
    Venue = 9
    Contact = 10
    Dice = 11

class TypeDirection(Enum):
    """ Type direction (0–5, no gaps). All values are used. """
    Unknown = 0
    In = 1
    Out = 2
    Resend = 3
    ErrorOut = 4
    ErrorOutFatal = 5

MAX_SEND_ATTEMPTS = 5
