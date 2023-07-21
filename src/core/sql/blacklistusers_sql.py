import threading 

from src.core.sql import BASE, SESSION, engine as ENGINE
from sqlalchemy import Column, String, UnicodeText

class BlacklistUsers(BASE):
    __tablename__ = "blacklistusers"
    user_id = Column(String(14), primary_key=True)
    reason = Column(UnicodeText)

    def __init__(self, user_id, reason=None):
        self.user_id = user_id
        self.reason = reason 

    def __repr__(self):
        return "<User {} has been blacklisted for {}".format(
            self.user_id, self.reason, 
        )
    
BlacklistUsers.__table__.create(bind=ENGINE)

BLACKLIST_USERS_LOCK = threading.RLock()
#BLACKLIST_USERS = set()

def blacklist_user(user_id, reason=None):
    with BLACKLIST_USERS_LOCK:
        user = SESSION.query(BlacklistUsers).get(str(user_id))
        if not user:
            user = BlacklistUsers(str(user_id), reason)
        else:
            user.reason = reason 

        SESSION.add(user)
        SESSION.commit()

def unblacklist_user(user_id):
    with BLACKLIST_USERS_LOCK:
        user = SESSION.query(BlacklistUsers).get(str(user_id))
        if user:
            SESSION.delete(user)
        
        SESSION.commit()

def get_reason(user_id):
    user = SESSION.query(BlacklistUsers).get(str(user_id))
    reason = ""
    if user:
        reason = user.reason

    SESSION.close()
    return reason 

def is_user_blacklisted(user_id):
    blacklisted_user = SESSION.query(BlacklistUsers).get(str(user_id))
    if blacklisted_user:
        return True 
    
    return False 

def list_blacklisted_users():
    try:
        return SESSION.query(BlacklistUsers).all()
    finally:
        SESSION.close()