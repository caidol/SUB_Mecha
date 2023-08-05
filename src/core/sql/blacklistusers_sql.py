import threading 

from src.core.sql import BASE, SESSION, engine as ENGINE
from sqlalchemy import Column, String, UnicodeText

class BlacklistUsers(BASE):
    __tablename__ = "blacklistusers"
    chat_id = Column(String(14), primary_key=True)
    user_id = Column(String(14), primary_key=True)
    reason = Column(UnicodeText)

    def __init__(self, chat_id, user_id, reason=None):
        self.chat_id = str(chat_id)
        self.user_id = str(user_id)
        self.reason = reason 

    def __repr__(self):
        return "<User {} has been blacklisted for {}".format(
            self.user_id, self.reason, 
        )

def create_tables(): 
    BlacklistUsers.__table__.create(bind=ENGINE, checkfirst=True)

BLACKLIST_USERS_LOCK = threading.RLock()

def blacklist_user(chat_id, user_id, reason=None):
    with BLACKLIST_USERS_LOCK:
        user = SESSION.query(BlacklistUsers).get((str(chat_id), str(user_id)))

        if not user:
            user = BlacklistUsers(str(chat_id), str(user_id), reason)
        else:
            user.reason = reason 

        SESSION.merge(user)
        SESSION.commit()

def unblacklist_user(chat_id, user_id):
    with BLACKLIST_USERS_LOCK:
        user = SESSION.query(BlacklistUsers).get((str(chat_id), str(user_id)))
        if user:
            SESSION.delete(user)
        
        SESSION.commit()

def get_reason(chat_id, user_id):
    user = SESSION.query(BlacklistUsers).get((str(chat_id), str(user_id)))
    reason = ""
    if user:
        reason = user.reason

    SESSION.close()
    return reason 

def is_user_blacklisted(chat_id, user_id):
    blacklisted_user = SESSION.query(BlacklistUsers).get((str(chat_id), str(user_id)))
    if blacklisted_user:
        return True 
    
    return False 

def list_blacklisted_users(chat_id):
    try:
        return SESSION.query(BlacklistUsers).filter(BlacklistUsers.chat_id == str(chat_id)).all()
    finally:
        SESSION.close()

def migrate_chat(old_chat_id, new_chat_id):
    with BLACKLIST_USERS_LOCK:
        blacklist_users = (
            SESSION.query(BlacklistUsers)
            .filter(BlacklistUsers.chat_id == str(old_chat_id))
            .all()
        )
        for user in blacklist_users:
            user.chat_id = str(new_chat_id)
        SESSION.commit()

create_tables()