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
    # Telegram system-like chat updates (groups/supergroups).
    Join = 12          # new_chat_members
    Leave = 13         # left_chat_member
    NewChatTitle = 14  # new_chat_title
    NewChatPhoto = 15  # new_chat_photo
    PinnedMessage = 16 # pinned_message
    DeletedMessage = 17 # deleted_message

class TypeDirection(Enum):
    """ Type direction (0–5, no gaps). All values are used. """
    Unknown = 0
    In = 1
    Out = 2
    Resend = 3
    ErrorOut = 4
    ErrorOutFatal = 5

MAX_SEND_ATTEMPTS = 5
