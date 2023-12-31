import threading

from sqlalchemy import String, Column, Integer, UnicodeText
from sqlalchemy import inspect
from src.core.sql import SESSION, BASE, engine as ENGINE

# Flood strength types (the higher the number the lower the severity)
# 1 = ban
# 2 = kick
# 3 = mute
# 4 = tban
# 5 = tmute

DEFAULT_COUNT = 1
DEFAULT_LIMIT = 0
DEFAULT_OBJECT = (None, DEFAULT_COUNT, DEFAULT_LIMIT)

class FloodControl(BASE):
    __tablename__ = "antiflood"
    chat_id = Column(String(14), primary_key=True)
    user_id = Column(Integer)
    count = Column(Integer, default=DEFAULT_COUNT)
    limit = Column(Integer, default=DEFAULT_LIMIT)

    def __init__(self, chat_id, user_id, count, limit):
        self.chat_id = str(chat_id) # ensure that its in a string format
        self.user_id = user_id
        self.count = count 
        self.limit = limit

    def __repr__(self):
        return f"<flood control for {self.chat_id}>"
    
class FloodSettings(BASE):
    __tablename__ = "antiflood_settings"
    chat_id = Column(String(14), primary_key=True)
    flood_type = Column(Integer, default=1)
    value = Column(UnicodeText, default="0")

    def __init__(self, chat_id, flood_type=1, value="0"):
        self.chat_id = str(chat_id)
        self.flood_type = flood_type
        self.value = value

    def __repr__(self):
        return f"<{self.chat_id} will be executing {self.flood_type}.>"

def create_tables():
    FloodControl.__table__.create(bind=ENGINE, checkfirst=True)
    FloodSettings.__table__.create(bind=ENGINE, checkfirst=True)

INSERTION_FLOOD_LOCK = threading.RLock()
INSERTION_FLOOD_SETTINGS_LOCK = threading.RLock()

CHAT_FLOOD = {}

def set_flood(chat_id, amount):
    with INSERTION_FLOOD_LOCK:
        flood = SESSION.query(FloodControl).get(str(chat_id))
        if not flood:
            flood = FloodControl(str(chat_id), None, DEFAULT_COUNT, amount)
        
        flood.user_id = None
        flood.limit = amount

        #CHAT_FLOOD[str(chat_id)] = (None, DEFAULT_COUNT, amount)

        SESSION.merge(flood)
        SESSION.commit()

def update_flood(chat_id: str, user_id) -> None:
    with INSERTION_FLOOD_LOCK:
        current_chat_flood = SESSION.query(FloodControl).get(str(chat_id)) #CHAT_FLOOD.get(str(chat_id))
        if not current_chat_flood:
            return False 
        
        curr_user_id = current_chat_flood.user_id
        count = current_chat_flood.count 
        limit = current_chat_flood.limit

        if limit == 0: # no antiflood found
            return False
        
        if user_id != curr_user_id or user_id is None: # other user
            current_chat_flood.user_id = user_id
        
        current_chat_flood.count += 1
        if current_chat_flood.count > limit: # too many messages, kick
            current_chat_flood.count = DEFAULT_COUNT
            SESSION.merge(current_chat_flood)
            SESSION.commit()
            return True

        # default -> update
        SESSION.merge(current_chat_flood)
        SESSION.commit()
        return False

def reset_flood(chat_id, user_id):
    with INSERTION_FLOOD_LOCK:
        current_chat_flood = SESSION.query(FloodControl).get(str(chat_id))
        if not current_chat_flood:
            return 
        
        curr_user_id = current_chat_flood.user_id
        if user_id != curr_user_id or user_id is None: # other user
            current_chat_flood.user_id = user_id

        current_chat_flood.count = DEFAULT_COUNT
        SESSION.merge(current_chat_flood)
        SESSION.commit()


def get_flood_limit(chat_id):
    try:
        return (
            SESSION.query(FloodControl.limit)
            .filter(FloodControl.chat_id == str(chat_id))
            .first()
        )[0]
    finally:
        SESSION.close()

def set_flood_severity(chat_id, flood_type, value):
    with INSERTION_FLOOD_SETTINGS_LOCK:
        current_setting = SESSION.query(FloodSettings).get(str(chat_id))
        if not current_setting:
            current_setting = FloodSettings(chat_id, flood_type=int(flood_type), value=value)
        
        current_setting.flood_type = int(flood_type)
        current_setting.value = str(value)

        SESSION.add(current_setting)
        SESSION.commit()

def get_flood_setting(chat_id):
    try:
        settings = SESSION.query(FloodSettings).get(str(chat_id))
        if settings:
            return settings.flood_type, settings.value
        else:
            return 1, "0" # return defaults otherwise
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_FLOOD_LOCK:
        try:
            flood = SESSION.query(FloodControl).get(str(old_chat_id))
            if flood:
                CHAT_FLOOD[str(new_chat_id)] = CHAT_FLOOD.get(str(old_chat_id), DEFAULT_OBJECT)
                flood.chat_id = str(new_chat_id)
                SESSION.commit()
        finally:
            SESSION.close()

def __load_flood_settings():
    global CHAT_FLOOD
    try:
        all_chats = SESSION.query(FloodControl).all()
        CHAT_FLOOD = {chat.chat_id: (None, DEFAULT_COUNT, chat.limit) for chat in all_chats}
    finally:
        SESSION.close()

#__load_flood_settings()
create_tables()