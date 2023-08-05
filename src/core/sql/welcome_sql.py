import threading 
import random
from typing import Union

from sqlalchemy import BigInteger, Boolean, Column, Integer, String, UnicodeText

from src.core.sql import BASE, SESSION, engine as ENGINE
from src.utils.msg_types import SendTypes


DEFAULT_WELCOME = "Hello {first}. How are you?"
DEFAULT_GOODBYE = "Goodbye {first}, thanks for stopping by!"

DEFAULT_WELCOME_MESSAGES = [
    "{first} is here!",  # Discord welcome messages copied
    "Ready player {first}",
    "Genos, {first} is here.",
    "A wild {first} appeared.",
    "{first} came in like a Lion!",
    "{first} has joined your party.",
    "{first} just joined. Can I get a heal?",
    "{first} just joined the chat - asdgfhak!",
    "{first} just joined. Everyone, look busy!",
    "Welcome, {first}. Stay awhile and listen.",
    "Welcome, {first}. We were expecting you ( ͡° ͜ʖ ͡°)",
    "Welcome, {first}. We hope you brought pizza.",
    "Welcome, {first}. Leave your weapons by the door.",
    "Swoooosh. {first} just landed.",
    "Brace yourselves. {first} just joined the chat.",
    "{first} just joined. Hide your bananas.",
    "{first} just arrived. Seems OP - please nerf.",
    "{first} just slid into the chat.",
    "A {first} has spawned in the chat.",
    "Big {first} showed up!",
    "Where’s {first}? In the chat!",
    "{first} hopped into the chat. Kangaroo!!",
    "{first} just showed up. Hold my beer.",
    "Challenger approaching! {first} has appeared!",
    "It's a bird! It's a plane! Nevermind, it's just {first}.",
    "It's {first}! Praise the sun! \o/",
    "Never gonna give {first} up. Never gonna let {first} down.",
    "Ha! {first} has joined! You activated my trap card!",
    "Hey! Listen! {first} has joined!",
    "We've been expecting you {first}",
    "It's dangerous to go alone, take {first}!",
    "{first} has joined the chat! It's super effective!",
    "Cheers, love! {first} is here!",
    "{first} is here, as the prophecy foretold.",
    "{first} has arrived. Party's over.",
    "{first} is here to kick butt and chew bubblegum. And {first} is all out of gum.",
    "Hello. Is it {first} you're looking for?",
    "{first} has joined. Stay awhile and listen!",
    "Roses are red, violets are blue, {first} joined this chat with you",
    "Welcome {first}, Avoid Punches if you can!",
    "It's a bird! It's a plane! - Nope, its {first}!",
    "{first} Joined! - Ok.",
    "{first} just fell into the chat!",
    "Something just fell from the sky! - oh, its {first}.",
    "{first} Just teleported into the chat!",
    "Who needs Google? You're everything we were searching for.",
    "This place must have free WiFi, cause I'm feeling a connection.",
    "Speak friend and enter.",
    "Welcome you are",
    "Welcome {first}, your princess is in another castle.",
    "Hi {first}, welcome to the dark side.",
    "Hola {first}, beware of people with disaster levels",
    "Hey {first}, we have the droids you are looking for.",
    "Hi {first}\nThis isn't a strange place, this is my home, it's the people who are strange.",
    "Oh, hey {first} what's the password?",
    "Hey {first}, I know what we're gonna do today",
    "{first} just joined, be at alert they could be a spy.",
    "{first} joined the group, read by Mark Zuckerberg, CIA and 35 others.",
    "Everyone stop what you’re doing, We are now in the presence of {first}.",
    "Hey {first}, do you wanna know how I got these scars?",
    "Welcome {first}, drop your weapons and proceed to the spy scanner.",
    "You’re here now {first}, Resistance is futile",
    "{first} just arrived, the force is strong with this one.",
    "{first} just joined on president’s orders.",
    "Hi {first}, is the glass half full or half empty?",
    "Yipee Kayaye {first} arrived.",
    "Welcome {first}, if you’re a secret agent press 1, otherwise start a conversation",
    "They may take our lives, but they’ll never take our {first}.",
    "Coast is clear! You can come out guys, it’s just {first}.",
    "Welcome {first}, pay no attention to that guy lurking.",
    "Welcome {first}, may the force be with you.",
    "May the {first} be with you.",
    "Ladies and gentlemen, I give you ...  {first}.",
    "Behold my new evil scheme, the {first}-Inator.",
    "Ah, {first} the Platypus, you're just in time... to be trapped.",
    "In the jungle, you must wait...until the dice read five or eight.",  # Jumanji stuff
    "Dr.{first} Famed archeologist and international explorer,\nWelcome to Jumanji!\nJumanji's Fate is up to you now.",
    "{first}, this will not be an easy mission - monkeys slow the expedition.",  # End of Jumanji stuff
    "Elementary, my dear {first}.",
    "I'm back - {first}.",
    "Bond. {first} Bond.",
]

DEFAULT_GOODBYE_MESSAGES = [
    "{first} will be missed.",
    "{first} just went offline.",
    "{first} has left the lobby.",
    "{first} has left the clan.",
    "{first} has left the game.",
    "{first} has fled the area.",
    "{first} is out of the running.",
    "Nice knowing ya, {first}!",
    "It was a fun time {first}.",
    "We hope to see you again soon, {first}.",
    "I donut want to say goodbye, {first}.",
    "Goodbye {first}! Guess who's gonna miss you :')",
    "Goodbye {first}! It's gonna be lonely without ya.",
    "Please don't leave me alone in this place, {first}!",
    "Good luck finding better shit-posters than us, {first}!",
    "You know we're gonna miss you {first}. Right? Right? Right?",
    "Congratulations, {first}! You're officially free of this mess.",
    "{first}. You were an opponent worth fighting.",
    "Bring him the photo",
    "Go outside!",
    "Ask again later",
    "Think for yourself",
    "Question authority",
    "You are worshiping a sun god",
    "Don't leave the house today",
    "Give up!",
    "Wake up",
    "Look to la luna",
    "Meet strangers without prejudice",
    "A hanged man will bring you no luck today",
    "You are dark inside",
    "Have you seen the exit?",
    "Get a baby pet it will cheer you up.",
    "Your princess is in another castle.",
    "You are playing it wrong give me the controller",
    "Trust good people",
    "Live to die.",
    "When life gives you lemons reroll!",
    "Well, that was worthless",
    "I fell asleep!",
    "May your troubles be many",
    "Your old life lies in ruin",
    "Always look on the bright side",
    "It is dangerous to go alone",
    "You will never be forgiven",
    "You have nobody to blame but yourself",
    "Only a sinner",
    "Use bombs wisely",
    "Nobody knows the troubles you have seen",
    "You look fat you should exercise more",
    "Follow the zebra",
    "Why so blue?",
    "The devil in disguise",
    "Go outside",
    "Always your head in the clouds",
]

class Welcome(BASE):
    __tablename__ = "welcome_pref"
    chat_id = Column(String(14), primary_key=True)
    should_welcome = Column(Boolean, default=True)
    should_goodbye = Column(Boolean, default=True)
    custom_content = Column(UnicodeText, default=None)

    custom_welcome = Column(
        UnicodeText, default=random.choice(DEFAULT_WELCOME_MESSAGES),
    )
    welcome_type = Column(Integer, default=SendTypes.TEXT.value) # will need to look at this

    custom_leave = Column(UnicodeText, default=random.choice(DEFAULT_GOODBYE_MESSAGES))
    leave_type = Column(Integer, default=SendTypes.TEXT.value) # will need to look at this 

    clean_welcome = Column(BigInteger)
    clean_goodbye = Column(BigInteger)

    def __init__(self, chat_id, should_welcome=True, should_goodbye=True):
        self.chat_id = str(chat_id)
        self.should_welcome = should_welcome
        self.should_goodbye = should_goodbye

    def __repr__(self):
        return "<Chat {} should welcome new users: {}\nand should say goodbye: {}>".format(
            self.chat_id, self.should_welcome, self.should_goodbye,
        )

class WelcomeButtons(BASE):
    __tablename__ = "welcome_urls"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)
    name = Column(UnicodeText, nullable=False)
    url = Column(UnicodeText, nullable=False)
    same_line = Column(Boolean, default=False)

class GoodbyeButtons(BASE):
    __tablename__ = "leave_urls"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)
    name = Column(UnicodeText, nullable=False)
    same_line = Column(Boolean, default=False)

    def __init__(self, chat_id, name, url, same_line=False):
        self.chat_id = str(chat_id)
        self.name = name
        self.url = url 
        self.same_line = same_line

class WelcomeMute(BASE):
    __tablename__ = "welcome_mutes"
    chat_id = Column(String(14), primary_key=True)
    welcomemutes = Column(UnicodeText, default=False)

    def __init__(self, chat_id, welcomemutes):
        self.chat_id = str(chat_id)
        self.welcomemutes = welcomemutes

class WelcomeMuteUsers(BASE):
    __tablename__ = "human_checks"
    user_id = Column(Integer, primary_key=True)
    chat_id = Column(String(14), primary_key=True)
    human_check = Column(Boolean)

    def __init__(self, user_id, chat_id, human_check):
        self.user_id = user_id
        self.chat_id = str(chat_id) # ensure a string 
        self.human_check = human_check

class CleanServiceSetting(BASE):
    __tablename__ = "clean_service"
    chat_id = Column(String(14), primary_key=True)
    clean_service = Column(Boolean, default=True)

    def __init__(self, chat_id, clean_service):
        self.chat_id = str(chat_id) # ensure a string 
        self.clean_service = clean_service
    
    def __repr__(self):
        return "<Chat used clean service ({})>".format(self.chat_id)

def create_tables():
    Welcome.__table__.create(bind=ENGINE, checkfirst=True)
    WelcomeButtons.__table__.create(bind=ENGINE, checkfirst=True)
    GoodbyeButtons.__table__.create(bind=ENGINE, checkfirst=True)
    WelcomeMute.__table__.create(bind=ENGINE, checkfirst=True)
    WelcomeMuteUsers.__table__.create(bind=ENGINE, checkfirst=True)
    CleanServiceSetting.__table__.create(bind=ENGINE, checkfirst=True)

INSERTION_LOCK = threading.RLock()
WELC_BTN_LOCK = threading.RLock()
LEAVE_BTN_LOCK = threading.RLock()
WM_LOCK = threading.RLock()
CS_LOCK = threading.RLock()

def welcome_mutes(chat_id):
    try:
        welcome_mutes = SESSION.query(WelcomeMute).get(str(chat_id))
        if welcome_mutes:
            return welcome_mutes.welcomemutes
        return False
    finally:
        SESSION.close()

def set_clean_welcome(chat_id, clean_welcome):
    with INSERTION_LOCK:
        curr = SESSION.query(Welcome).get(str(chat_id))
        if not curr:
            curr = Welcome(str(chat_id))
        
        curr.clean_welcome = int(clean_welcome)
        
        SESSION.merge(curr)
        SESSION.commit()

def set_clean_goodbye(chat_id, clean_goodbye):
    with INSERTION_LOCK:
        curr = SESSION.query(Welcome).get(str(chat_id))
        if not curr:
            curr = Welcome(str(chat_id))
        
        curr.clean_goodbye = clean_goodbye

        SESSION.merge(curr)
        SESSION.commit()

def set_welcome_mutes(chat_id, welcomemutes):
    with WM_LOCK:
        welcome_mute = SESSION.query(WelcomeMute).get((str(chat_id)))
        if not welcome_mute:
            welcome_mute = WelcomeMute(str(chat_id), welcomemutes)
        else:
            welcome_mute.welcomemutes = welcomemutes
                
        SESSION.merge(welcome_mute)
        SESSION.commit()

def set_human_checks(user_id, chat_id):
    with INSERTION_LOCK:
        human_check = SESSION.query(WelcomeMuteUsers).get((user_id, str(chat_id)))
        if not human_check:
            human_check = WelcomeMuteUsers(user_id, str(chat_id), True)
        else:
            human_check.human_check = True
        
        SESSION.merge(human_check)
        SESSION.commit()

        return human_check
    
def get_human_checks(user_id, chat_id):
    try:
        human_check = SESSION.query(WelcomeMuteUsers).get((user_id, str(chat_id)))
        if not human_check:
            return None 
        human_check = human_check.human_check
        return human_check
    finally:
        SESSION.close()

def set_welc_pref(chat_id, should_welcome):
    with INSERTION_LOCK:
        welcome_pref = SESSION.query(Welcome).get(str(chat_id))
        if not welcome_pref:
            welcome_pref = Welcome(str(chat_id), should_welcome=should_welcome)
        else:
            welcome_pref.should_welcome = should_welcome
        
        SESSION.merge(welcome_pref)
        SESSION.commit()

def get_welc_pref(chat_id):
    welcome_pref = SESSION.query(Welcome).get(str(chat_id))
    SESSION.close()

    if welcome_pref:
        return (
            welcome_pref.should_welcome,
            welcome_pref.custom_welcome,
            welcome_pref.custom_content,
            welcome_pref.welcome_type,
        )
    else:
        # return the default characters 
        return True, DEFAULT_WELCOME, None, SendTypes.TEXT
    
def get_welc_buttons(chat_id):
    try:
        return (
            SESSION.query(WelcomeButtons)
            .filter(WelcomeButtons.chat_id == str(chat_id))
            .order_by(WelcomeButtons.id)
            .all()
        )
    finally:
        SESSION.close()

def set_gdbye_pref(chat_id, should_goodbye):
    with INSERTION_LOCK:
        gdbye_pref = SESSION.query(Welcome).get(str(chat_id))
        if not gdbye_pref:
            gdbye_pref = Welcome(str(chat_id), should_goodbye=should_goodbye)
        else:
            gdbye_pref.should_goodbye = should_goodbye
        
        SESSION.merge(gdbye_pref)
        SESSION.commit()

def get_gdbye_pref(chat_id):
    goodbye_pref = SESSION.query(Welcome).get(str(chat_id))
    SESSION.close()
    if goodbye_pref:
        return (
            goodbye_pref.should_goodbye, 
            goodbye_pref.custom_leave,
            goodbye_pref.leave_type,
        )
    else:
        return True, DEFAULT_GOODBYE, SendTypes.TEXT

def get_gdbye_buttons(chat_id):
    try:
        return (
            SESSION.query(GoodbyeButtons)
            .filter(GoodbyeButtons.chat_id == str(chat_id))
            .order_by(GoodbyeButtons.id)
            .all()
        )
    finally:
        SESSION.close()

def set_custom_welcome(chat_id, custom_content, custom_welcome, welcome_type, buttons=None):
    if buttons is None:
        buttons = []
    
    with INSERTION_LOCK:
        welcome_settings = SESSION.query(Welcome).get(str(chat_id))
        if not welcome_settings:
            welcome_settings = Welcome(str(chat_id), True)
        
        if custom_welcome or custom_content:
            welcome_settings.custom_content = custom_content
            welcome_settings.custom_welcome = custom_welcome
            welcome_settings.welcome_type = welcome_type.value
        else:
            welcome_settings.custom_welcome = DEFAULT_WELCOME
            welcome_settings.welcome_type = SendTypes.TEXT.value
        
        SESSION.merge(welcome_settings)

        with WELC_BTN_LOCK:
            welcome_mutes_buttons = (
                SESSION.query(WelcomeButtons)
                .filter(WelcomeButtons.chat_id == str(chat_id))
                .all()
            )
            for btn in welcome_mutes_buttons:
                SESSION.delete(btn)
            
            id_number = 0
            for btn_name, url, same_line in buttons:
                id_number += 1
                button = WelcomeButtons(
                    id_number,
                    chat_id, btn_name, url, same_line
                )
                SESSION.merge(button)
        
        SESSION.commit()

def set_custom_goodbye(chat_id, custom_goodbye, goodbye_type, buttons=None):
    if buttons is None:
        buttons = []
    
    with INSERTION_LOCK:
        welcome_settings = SESSION.query(Welcome).get(str(chat_id))
        if not welcome_settings:
            welcome_settings = Welcome(str(chat_id), True)
        
        if custom_goodbye:
            welcome_settings.custom_leave = custom_goodbye
            welcome_settings.leave_type = goodbye_type
        
        else:
            welcome_settings.custom_leave = DEFAULT_GOODBYE
            welcome_settings.leave_type = SendTypes.TEXT.value
        
        SESSION.merge(welcome_settings)
        
        with LEAVE_BTN_LOCK:
            welcome_mutes_buttons = (
                SESSION.query(GoodbyeButtons)
                .filter(GoodbyeButtons.chat_id == str(chat_id))
                .all()
            )
            for btn in welcome_mutes_buttons:
                SESSION.delete(btn)

            id_number = 0
            for btn_name, url, same_line in buttons:
                id_number += 1
                button = GoodbyeButtons(id_number, chat_id, name=btn_name, url=url, same_line=same_line)
                SESSION.merge(button)
        
        SESSION.commit()

def get_clean_welcome_preference(chat_id):
    welc = SESSION.query(Welcome).get(str(chat_id))
    SESSION.close()

    if welc:
        return welc.clean_welcome
    
    return False

def get_clean_goodbye_preference(chat_id):
    goodbye = SESSION.query(Welcome).get(str(chat_id))
    SESSION.close()

    if goodbye:
        return goodbye.clean_goodbye
    
    return False

def clean_service(chat_id: Union[int, str]):
    try:
        chat_setting = SESSION.query(CleanServiceSetting).get(str(chat_id))
        if chat_setting:
            return chat_setting.clean_service 
        return False
    finally:
        SESSION.close()

def set_clean_service(chat_id: Union[int, str], setting: bool):
    with CS_LOCK:
        chat_setting = SESSION.query(CleanServiceSetting).get((str(chat_id)))
        if not chat_setting:
            chat_setting = CleanServiceSetting(str(chat_id), setting)
        
        chat_setting.clean_service = setting
        SESSION.merge(chat_setting)
        SESSION.commit()

def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        chat = SESSION.query(Welcome).get(str(old_chat_id))
        if chat:
            chat.chat_id = str(new_chat_id)

        with WELC_BTN_LOCK:
            chat_buttons = (
                SESSION.query(WelcomeButtons)
                .filter(WelcomeButtons.chat_id == str(old_chat_id))
                .all()
            )
            for btn in chat_buttons:
                btn.chat_id = str(new_chat_id)

        with LEAVE_BTN_LOCK:
            chat_buttons = (
                SESSION.query(GoodbyeButtons)
                .filter(GoodbyeButtons.chat_id == str(old_chat_id))
                .all()
            )
            for btn in chat_buttons:
                btn.chat_id = str(new_chat_id)

        SESSION.commit()
        
create_tables()