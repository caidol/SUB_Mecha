import threading
from sqlalchemy import Boolean, Column, Integer, String, UnicodeText, distinct, func 
from sqlalchemy.dialects import postgresql

from src.core.sql import SESSION, BASE, engine as ENGINE 

# this is a bad practice however is my only viable option at the moment for 
# sake of simplicity.
WARN_REASONS = {}
WARN_FILTER_TRIGGERS = {}

class Warns(BASE):
    __tablename__ = "warns"

    user_id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)
    num_warns = Column(Integer, default=0)

    def __init__(self, user_id, chat_id):
        self.user_id = user_id
        self.chat_id = chat_id
        self.num_warns = 0

    def __repr__(self):
        return "<{} warns for {} in {}>".format(
            self.num_warns, self.user_id, self.chat_id
        )


class WarnFilters(BASE):
    __tablename__ = "warn_filters"

    chat_id = Column(String(14), primary_key=True)
    keyword = Column(UnicodeText, primary_key=True)
    reply = Column(UnicodeText)

    def __init__(self, chat_id, keyword):
        self.chat_id = str(chat_id) # ensure it is a string
        self.keyword = keyword 
    
    def __repr__(self):
        return "<Permissions for {}>".format(self.chat_id)
    
    def __eq__(self, other):
        return bool(
            isinstance(other, WarnFilters)
            and self.chat_id == other.chat_id 
            and self.keyword == other.keyword
        )
    
class WarnSettings(BASE):
    __tablename__ = "warn_settings"
    chat_id = Column(String(14), primary_key=True)
    warn_limit = Column(Integer, default=3)
    soft_warn = Column(Boolean, default=False)

    def __init__(self, chat_id, warn_limit=3, soft_warn=False):
        self.chat_id = str(chat_id)
        self.warn_limit = warn_limit
        self.soft_warn = soft_warn

    def __repr__(self):
        return "<{} has {} possible warns.>".format(self.chat_id, self.warn_limit)

def create_tables():
    Warns.__table__.create(bind=ENGINE, checkfirst=True)
    WarnFilters.__table__.create(bind=ENGINE, checkfirst=True)
    WarnSettings.__table__.create(bind=ENGINE, checkfirst=True)

WARN_INSERTION_LOCK = threading.RLock()
WARN_FILTER_INSERTION_LOCK = threading.RLock()
WARN_SETTINGS_INSERTION_LOCK = threading.RLock()

def warn_user(user_id, chat_id, reason=None):
    with WARN_INSERTION_LOCK:
        warned_user = SESSION.query(Warns).get((user_id, str(chat_id)))
        if not warned_user:
            warned_user = Warns(user_id, str(chat_id))
        
        warned_user.num_warns += 1
        
        warn_reasons = WARN_REASONS.get(str(chat_id))
        if warn_reasons:
            if str(user_id) in warn_reasons.keys():
                warn_reasons[str(user_id)].append(reason)
            else:
                warn_reasons[str(user_id)] = [reason]
        else:
            WARN_REASONS[str(chat_id)] = {str(user_id): [reason]}

        
        reasons = WARN_REASONS.get(str(chat_id))[str(user_id)]
        num_warns = warned_user.num_warns

        SESSION.merge(warned_user)
        SESSION.commit()

        return num_warns, reasons
 
def remove_warn(user_id, chat_id):
    with WARN_INSERTION_LOCK:
        removed = False
        warned_user = SESSION.query(Warns).get((user_id, str(chat_id)))

        if warned_user and warned_user.num_warns > 0:
            warned_user.num_warns -= 1

            SESSION.add(warned_user)
            SESSION.commit()

        warn_reasons = WARN_REASONS.get(str(chat_id))
        if warn_reasons:
            warn_reasons[str(user_id)] = (warn_reasons[str(user_id)])[:-1]

        removed = True
        
        SESSION.close()
        return removed

def reset_warns(user_id, chat_id):
    with WARN_INSERTION_LOCK:
        warned_user = SESSION.query(Warns).get((user_id, str(chat_id)))

        if warned_user:
            warned_user.num_warns = 0

            SESSION.add(warned_user)
            SESSION.commit()
        
        warn_reasons = WARN_REASONS.get(str(chat_id))
        if warn_reasons:
            warn_reasons[str(user_id)] = []
        
        SESSION.close()
       
def get_warns(user_id, chat_id):
    try:
        user = SESSION.query(Warns).get((user_id, str(chat_id)))
        if not user:
            return None
        
        warn_reasons = WARN_REASONS.get(str(chat_id))
        if warn_reasons:
            reasons = WARN_REASONS.get(str(chat_id))[str(user_id)]
        else:
            reasons = None

        num_warns = user.num_warns

        return num_warns, reasons
    finally:
        SESSION.close()

        
def add_warn_filter(chat_id, keyword, reply=None):
    with WARN_FILTER_INSERTION_LOCK:
        warn_filter = WarnFilters(str(chat_id), keyword)
        warn_filter.reply = reply

        SESSION.merge(warn_filter)
        SESSION.commit()

        warn_filter_triggers = WARN_FILTER_TRIGGERS.get(str(chat_id))

        if warn_filter_triggers:
            warn_filter_triggers.append(keyword)
        else:
            WARN_FILTER_TRIGGERS[str(chat_id)] = [keyword]


def remove_warn_filter(chat_id, keyword):
    with WARN_FILTER_INSERTION_LOCK:
        warn_filter = SESSION.query(WarnFilters).get((str(chat_id), keyword))
        if warn_filter:
            SESSION.delete(warn_filter)
            SESSION.commit()

            warn_filter_triggers = WARN_FILTER_TRIGGERS.get(str(chat_id))
            if warn_filter_triggers:
                warn_filter_triggers[str(chat_id)] = (
                    trigger.delete() for trigger 
                    in warn_filter_triggers[str(chat_id)] 
                    if trigger == keyword
                )

            return True 
        SESSION.close()
        return False 
    
def get_chat_warn_triggers(chat_id):
    try:
        if WARN_FILTER_TRIGGERS.get(str(chat_id)):
            return WARN_FILTER_TRIGGERS[str(chat_id)]
        else:
            return None
    finally:
        SESSION.close()

def get_chat_warn_filters(chat_id):
    try:
        return (
            SESSION.query(WarnFilters).filter(WarnFilters.chat_id == str(chat_id)).all()
        )
    finally:
        SESSION.close()

def get_warn_filter(chat_id, keyword):
    try:
        return SESSION.query(WarnFilters).get((str(chat_id), keyword))
    finally:
        SESSION.close()

def set_warn_limit(chat_id, warn_limit):
    with WARN_SETTINGS_INSERTION_LOCK:
        current_setting = SESSION.query(WarnSettings).get(str(chat_id))
        if not current_setting:
            current_setting = WarnSettings(str(chat_id), warn_limit=warn_limit)

        current_setting.warn_limit = warn_limit
        SESSION.merge(current_setting)
        SESSION.commit()

def set_warn_severity(chat_id, soft_warn):
    with WARN_SETTINGS_INSERTION_LOCK:
        current_setting = SESSION.query(WarnSettings).get(str(chat_id))
        if not current_setting:
            current_setting = WarnSettings(str(chat_id), soft_warn=soft_warn)

        current_setting.soft_warn = soft_warn
        SESSION.add(current_setting) # work on updating instead
        SESSION.commit()

def get_warn_setting(chat_id):
    try:
        setting = SESSION.query(WarnSettings).get(str(chat_id))
        if setting:
            return setting.warn_limit, setting.soft_warn
        else:
            return 3, False
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

def num_warn_filters():
    try:
        return SESSION.query(WarnFilters).count()
    finally:
        SESSION.close()

def num_warn_chat_filters(chat_id):
    try:
        return (
            SESSION.query(WarnFilters.chat_id)
            .filter(WarnFilters.chat_id == str(chat_id))
            .count()
        )
    finally:
        SESSION.close()

def num_warn_filter_chats():
    try:
        return SESSION.query(func.count(distinct(WarnFilters.chat_id))).scalar()
    finally:
        SESSION.close()

def migrate_chat(old_chat_id, new_chat_id):
    with WARN_INSERTION_LOCK:
        chat_notes = (
            SESSION.query(Warns).filter(Warns.chat_id == str(old_chat_id)) 
        )
        for note in chat_notes:
            note.chat_id == str(new_chat_id)
        SESSION.commit()
    
    with WARN_FILTER_INSERTION_LOCK:
        chat_filters = (
            SESSION.query(WarnFilters)
            .filter(WarnFilters.chat_id == str(old_chat_id))
            .all()
        )
        for filter in chat_filters:
            filter.chat_id = str(new_chat_id)
        SESSION.commit()
    
    with WARN_SETTINGS_INSERTION_LOCK:
        chat_settings = (
            SESSION.query(WarnSettings)
            .filter(WarnSettings.chat_id == str(old_chat_id))
            .all()
        )
        for setting in chat_settings:
            setting.chat_id = str(new_chat_id)
        SESSION.commit()

create_tables()