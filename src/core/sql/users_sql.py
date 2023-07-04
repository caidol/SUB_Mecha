import threading

from __init__ import BASE, SESSION, engine as ENGINE
from sqlalchemy import (
    Column, 
    ForeignKey,
    Integer,
    String, 
    UnicodeText,
    UniqueConstraint,
    func,
)

INSERTION_LOCK = threading.RLock()

class Users(BASE):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    username = Column(UnicodeText)

    def __init__(self, user_id, username=None):
        self.user_id = user_id
        self.username = username 

    def __repr__(self):
        return "<User {} ({})>".format(self.username, self.user_id)

class Chats(BASE):
    __tablename__ = "chats"

    chat_id = Column(String(14), primary_key=True)
    chat_name = Column(UnicodeText, nullable=False)

    def __init__(self, chat_id, chat_name):
        self.chat_id = str(chat_id)
        self.chat_name = chat_name

    def __repr__(self):
        return "<Chat {} ({})>".format(self.chat_name, self.chat_id)

class ChatMembers(BASE):
    __tablename__ = "chat_members"
    private_chat_id = Column(Integer, primary_key=True)

    chat = Column(
        String(14),
        ForeignKey("chats.chat_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )

    user = Column(
        Integer,
        ForeignKey("users.user_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    
    __table_args__ = (UniqueConstraint("chat", "user", name="chat_member_uc"),)

    def __init__(self, chat, user):
        self.chat = chat
        self.user = user

    def __repr__(self):
        return "<Chat user {} ({}) in chat {} ({})>".format(
            self.user.username,
            self.user.user_id,
            self.chat.chat_name, 
            self.chat.chat_id,
        )

Users.__table__.create(bind=ENGINE)
Chats.__table__.create(bind=ENGINE)
ChatMembers.__table__.create(bind=ENGINE)

# These functions below require a re-entry lock (RLock) because they are directly editing
# information in the database tables

#TODO add these functions later

# These functions below do not require a re-entry insertion lock because they are only querying
# specific tables for information

def get_name_by_userid(user_id):
    try:
        return SESSION.query(Users).get(Users.user_id == int(user_id)).first()
    finally:
        SESSION.close()

def get_userid_by_name(username):
    try:
        return (
            SESSION.query(Users)
            .filter(func.lower(Users.username) == username.lower())
        )
    finally:
        SESSION.close()

def get_num_chats():
    try:
        return SESSION.query(Chats).count()
    finally:
        SESSION.close()

def get_num_users():
    try:
        return SESSION.query(Users).count()
    finally:
        SESSION.close()