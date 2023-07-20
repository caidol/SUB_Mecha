import threading
from src.core.sql import BASE, SESSION, engine as ENGINE
from sqlalchemy import Boolean, Column, Integer, String, UnicodeText, distinct, func 
from sqlalchemy.dialects import postgresql

class Warns(BASE):
    __tablename__ = "warns"

    user_id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)
    num_warns = Column(Integer, default=0)
    reasons = Column(postgresql.ARRAY(UnicodeText))

    def __init__(self, user_id, chat_id):
        self.user_id = user_id
        self.chat_id = chat_id
        self.num_warns = 0
        self.reasons = []

    def __repr__(self):
        return "<{} warns for {} in {} for reasons {}>".format(
            self.num_warns, self.user_id, self.chat_id, self.reasons,
        )

'''
class WarnFilters(BASE):
    __tablename__ = "warn_filters"

    chat_id = Column(String(14), primary_key=True)
    keyword = 
'''

Warns.__tablename__.create(bind=ENGINE, checkfirst=True)

WARN_INSERTION_LOCK = threading.RLock()

def warn_user(user_id, chat_id, reason=None):
    with WARN_INSERTION_LOCK:
        warned_user = SESSION.query(Warns).get((user_id, str(chat_id)))
        if not warned_user:
            warned_user = Warns(user_id, str(chat_id))
        
        warned_user.num_warns += 1
        if reason:
            warned_user.reasons.append([reason])
        
        reasons = warned_user.reasons
        num_warns = warned_user.num_warns

        SESSION.add(warned_user)
        SESSION.commit()

        return num_warns, reasons
    
def remove_warn(user_id, chat_id):
    with WARN_INSERTION_LOCK:
        removed = False
        warned_user = SESSION.query(Warns).get((user_id, str(chat_id)))

        if warned_user and warned_user.num_warns > 0:
            warned_user.num_warns -= 1
            warned_user.reasons = warned_user.reasons[:-1]

            SESSION.add(warned_user)
            SESSION.commit()

            removed = True
        
        SESSION.close()
        return removed
    
def reset_warns(user_id, chat_id):
    with WARN_INSERTION_LOCK:
        warned_user = SESSION.query(Warns).get((user_id, str(chat_id)))

        if warned_user:
            warned_user.num_warns = 0
            warned_user.reasons = []

            SESSION.add(warned_user)
            SESSION.commit()
        
        SESSION.close()

def get_warns(user_id, chat_id):
    try:
        user = SESSION.query(Warns).get((user_id, str(chat_id)))
        if not user:
            return None
        reasons = user.reasons
        num_warns = user.num_warns

        return num_warns, reasons
    finally:
        SESSION.close()

def num_warns():
    try:
        return SESSION.query(func.sum(Warns.num_warns)).scalar() or 0
    finally:
        SESSION.close()

def num_warn_chats():
    try:
        return SESSION.query(func.count(distinct(Warns.chat_id))).scalar()
    finally:
        SESSION.close()