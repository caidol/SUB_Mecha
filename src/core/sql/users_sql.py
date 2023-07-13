import threading

from src import dispatcher, BOT_USERNAME
from src.core.sql import BASE, SESSION, engine as ENGINE
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

def create_tables():
    Users.__table__.create(bind=ENGINE)
    Chats.__table__.create(bind=ENGINE)
    ChatMembers.__table__.create(bind=ENGINE)

# These functions below require a re-entry lock (RLock) because they are directly editing
# information in the database tables

def check_bot_in_db():
    with INSERTION_LOCK:
        bot = Users(dispatcher.bot.id, BOT_USERNAME)
        SESSION.merge(bot)
        SESSION.commit()

def update_user(user_id, username, chat_id=None, chat_name=None):
    with INSERTION_LOCK:
        user = SESSION.query(Users).get(user_id)

        if not user:
            user = Users(user_id, username)
            SESSION.add(user)
            SESSION.flush()
        else:
            user.username = username
        
        if not chat_id or not chat_name:
            SESSION.commit()
            return
        
        chat = SESSION.query(Chats).get(str(chat_id))
        if not chat:
            chat = Chats(str(chat_id), chat_name)
            SESSION.add(chat)
            SESSION.flush()
        else:
            chat.chat_name = chat_name

        member = (
            SESSION.query(ChatMembers)
            .filter(ChatMembers.chat == chat.chat_id, ChatMembers.user == user.user_id)
            .first()
        )
        if not member:
            chat_member = ChatMembers(chat.chat_id, user.user_id)
            SESSION.add(chat_member)
            SESSION.flush()
        
        SESSION.commit()

# These functions below do not require a re-entry insertion lock because they are only querying
# specific tables for information

def get_name_by_userid(user_id):
    try:
        return (
            SESSION.query(Users)
            .filter(Users.user_id == int(user_id))
            .all()
        )
    finally:
        SESSION.close()

def get_userid_by_name(username):
    try:
        return (
            SESSION.query(Users)
            .filter(func.lower(Users.username) == username.lower())
            .all()
        )
    finally:
        SESSION.close()

def get_chat_members(chat_id):
    try:
        return SESSION.query(ChatMembers).filter(ChatMembers.chat == str(chat_id)).all()
    finally:
        SESSION.close()

def get_all_chats():
    try:
        return SESSION.query(Chats).all()
    finally:
        SESSION.close()

def get_all_users():
    try:
        return SESSION.query(Users).all()
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