import threading 
import random

from sqlalchemy import BigInteger, Boolean, Column, Integer, String, UnicodeText 

# Everything below this comment is a temp solution

from src import LOGGER#, DATABASE_URL
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

DATABASE_URL = "sqlite:///warns.db"
LOGGER.info("Database URL: {}".format(DATABASE_URL))

def initialise_engine() -> scoped_session:
    global ENGINE
    ENGINE = create_engine(DATABASE_URL, echo=True)
    BASE.metadata.bind = ENGINE
    BASE.metadata.create_all(ENGINE)
    return scoped_session(sessionmaker(bind=ENGINE, autoflush=False))

BASE = declarative_base()
SESSION = initialise_engine()

# Everything above this comment is a temp solution


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
    "You're leaving, {first}? Yare Yare Daze.",
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
    welcome_type = Column(Integer, default=0) # will need to look at this

    custom_leave = Column(UnicodeText, default=random.choice(DEFAULT_GOODBYE_MESSAGES))
    leave_type = Column(Integer, default=0) # will need to look at this 

    clean_welcome = Column(BigInteger)

    def __init__(self, chat_id, should_welcome=True, should_goodbye=True):
        self.chat_id = str(chat_id)
        self.should_welcome = should_welcome
        self.should_goodbye = should_goodbye

    def __repr__(self):
        return "<Chat {} should welcome new users: {}\nand should say goodbye as {}>".format(
            self.chat_id, self.should_welcome, self.should_goodbye,
        )

class WelcomeMute(BASE):
    __tablename__ = "welcome_mutes"
    chat_id = Column(String(14), primary_key=True)
    welcomemutes = Column(UnicodeText, default=False)

    def __init__(self, chat_id, welcomemutes):
        self.chat_id = str(chat_id)
        self.welcomemutes = welcomemutes

class Captcha(BASE):
    __tablename__ = "captcha"
    chat_id = Column(String(14), primary_key=True)
    captcha_enabled = Column(Boolean, default=True)

    def __init__(self, chat_id, captcha_enabled):
        self.chat_id = str(chat_id)
        self.captcha_enabled = captcha_enabled

def create_tables():
    Welcome.__table__.create(bind=ENGINE)
    WelcomeMute.__table__.create(bind=ENGINE)
    Captcha.__table__.create(bind=ENGINE)

CAPTCHA_INSERTION_LOCK = threading.RLock()

def get_captcha_status(chat_id):
    try:
        return (
            SESSION.query(Captcha.captcha_enabled)
            .filter(Captcha.chat_id == str(chat_id))
            .first()
        )
    finally:
        SESSION.close()

def update_captcha_status(chat_id, captcha_enabled: Boolean):
    with CAPTCHA_INSERTION_LOCK:
        current_setting = SESSION.query(Captcha).filter(Captcha.chat_id == str(chat_id))
        if not current_setting:
            current_setting = Captcha(str(chat_id), captcha_enabled)
        
        current_setting.captcha_enabled = captcha_enabled
        SESSION.merge(current_setting)
        SESSION.commit()

