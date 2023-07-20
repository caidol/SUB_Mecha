import threading 
from sqlalchemy import func, distinct, Column, String, UnicodeText, Integer 
from src.core.sql import SESSION, BASE, engine as ENGINE

# Below are the ranked blacklist responses depending on severity
# 0 -> nothing
# 1 -> delete
# 2 -> warn
# 3 -> mute
# 4 -> kick
# 5 -> ban
# 6 -> tban
# 7 -> tmute

class BlacklistFilters(BASE):
    __tablename__ = "blacklist_filters"
    chat_id = Column(String(14), primary_key=True)
    trigger = Column(UnicodeText, primary_key=True, nullable=False)

    def __init__(self, chat_id, trigger):
        self.chat_id = str(chat_id) # Ensure that it's represented as a string
        self.trigger = trigger 
    
    def __repr__(self):
        return "<Blacklist filter containing trigger '{}' for {}".format(self.trigger, self.chat_id)
    
    def __eq__(self, other):
        return bool(
            isinstance(other, BlacklistFilters)
            and self.chat_id == other.chat_id
            and self.trigger == other.trigger,
        )
    
class BlacklistSettings(BASE):
    __tablename__ = "blacklist_settings"
    chat_id = Column(String(14), primary_key=True)
    blacklist_type = Column(Integer, default=1) # Default to deleting the message
    value = Column(UnicodeText, default="0") # Default to "0" to indicate that no time is used

    def __init__(self, chat_id, blacklist_type = 1, value = "0"):
        self.chat_id = str(chat_id) # Ensure that it's represented as a string
        self.blacklist_type = blacklist_type
        self.value = value 

    def __repr__(self):
        return "<{} will execute the {} action upon detection of the blacklist trigger>".format(
            self.chat_id,
            self.blacklist_type
        )

BlacklistFilters.__tablename__.create(bind=ENGINE)
BlacklistSettings.__tablename__.create(bind=ENGINE)

BLACKLIST_FILTER_INSERTION_LOCK = threading.RLock()
BLACKLIST_FILTER_SETTINGS_INSERTION_LOCK = threading.RLock()

def add_to_blacklist(chat_id, trigger):
    with BLACKLIST_FILTER_INSERTION_LOCK:
        blacklist_filter = BlacklistFilters(str(chat_id), trigger)
        SESSION.add(blacklist_filter)
        SESSION.flush()

def remove_from_blacklist(chat_id, trigger):
    with BLACKLIST_FILTER_INSERTION_LOCK:
        blacklist_filter = SESSION.query(BlacklistFilters).get(str(chat_id), trigger)
        if blacklist_filter:
            SESSION.delete(blacklist_filter)
            SESSION.commit()
            
            return True 
        
        SESSION.close()
        return False
    
def get_chat_blacklist(chat_id):
    try:
        return (
            SESSION.query(BlacklistFilters)
            .filter(BlacklistFilters.chat_id == str(chat_id))
            .all()
        )
    finally:
        SESSION.close()

def num_blacklist_filters():
    try:
        return SESSION.query(BlacklistFilters).count()
    finally:
        SESSION.close()
        
def get_num_blacklist_chat_filters(chat_id):
    try:
        return (
            SESSION.query(BlacklistFilters.chat_id)
            .filter(BlacklistFilters.chat_id == str(chat_id))
            .count()
        )
    finally:
        SESSION.close()

def get_num_blacklist_filter_chats():
    try:
        return SESSION.query(func.count(distinct(BlacklistFilters.chat_id))).scalar()
    finally:
        SESSION.close()

def set_blacklist_severity(chat_id, blacklist_type, value):
    with BLACKLIST_FILTER_SETTINGS_INSERTION_LOCK:
        current_setting = SESSION.query(BlacklistSettings).get(str(chat_id))
        if not current_setting:
            current_setting = BlacklistSettings(
                chat_id, blacklist_type=int(blacklist_type), value=str(value),
            )
        current_setting.blacklist_type = int(blacklist_type)
        current_setting.value = str(value)

        SESSION.add(current_setting)
        SESSION.commit()

def get_blacklist_setting(chat_id):
    try:
        current_setting = SESSION.query(BlacklistSettings).get(str(chat_id))
        if current_setting:
            return current_setting.blacklist_type, current_setting.value
        else:
            return 1, "0"
    finally:
        SESSION.close()

def migrate_chat(old_chat_id, new_chat_id):
    with BLACKLIST_FILTER_INSERTION_LOCK:
        chat_filters = (
            SESSION.query(BlacklistFilters)
            .filter(BlacklistFilters.chat_id == str(old_chat_id))
            .all()
        )
        for filter in chat_filters:
            filter.chat_id == str(new_chat_id)
        SESSION.commit()