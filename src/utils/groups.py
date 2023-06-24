from random import randint, choice
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src import dispatcher
from telegram import Chat


def generate_captcha():
    # Generate a random letter per time
    def gen_uppercase():
        return chr(randint(65, 90)) # ASCII values for A-Z
    
    def gen_lowercase():
        return chr(randint(97, 122)) # ASCII values for a-z 
    
    def gen_numbers():
        return chr(randint(48, 57)) # ASCII values for 0-9
    
    # Generate a random colour per time
    def background_colour():
        return choice([(0, 0, 0), (255, 255, 255)])# RGB values
    
    def font_colour():
        return (randint(32, 127), randint(32, 127), randint(32, 127)) # RGB values


    # Set captcha image parameters

    CAPTCHA_WIDTH = 80 * 5
    CAPTCHA_HEIGHT = 120
    correct_answer = ""
    font_options = ["arial.ttf", "columbia.ttf", "extrabold.ttf", "insightsans.ttf", "newsitalic.ttf", "samson.ttf"]
    #font = ImageFont.truetype("arial.ttf", 80) # TODO bugfix cannot find assets folder
    file = f"assets/captcha/captcha{randint(1, 100000)}.jpg" # TODO bugfix cannot find assets folder
    image = Image.new("RGB", (CAPTCHA_WIDTH, CAPTCHA_HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # First draw random points on the image
    for x in range(CAPTCHA_WIDTH):
        for y in range(CAPTCHA_HEIGHT):
            if x == 0 or y == 0 or x == CAPTCHA_WIDTH - 1 or y == CAPTCHA_HEIGHT - 1:
                draw.point((x, y), fill=(0, 0, 0)) 
            else:
                draw.point((x, y), fill=background_colour())

    # Now generate the text which will be used

    for text in range(6):
        gen_choices = [gen_uppercase(), gen_lowercase(), gen_numbers()]
        character = choice(gen_choices)
        correct_answer += character

        font_choice = ImageFont.truetype(f"assets/fonts/columbia.ttf", 80)
        #print("Font choice: ", font_choice)
        
        #ImageDraw.text(xy, text, fill=None, font=None)
        '''
        :param xy - The anchor coordinates of the text
        :param text - The text to be drawn
        :param fill - The colour to fill the text with
        :param font - The font to use
        '''
        draw.text((60 * text + 10, 25), character, font=font_choice, fill=(0, 0, 0))

    image = image.filter(ImageFilter.BLUR)
    image.save(file, "jpeg")
    print(correct_answer)
    return [file, correct_answer]


async def get_admin_permissions(chat_id: int, user_id: int) -> list:
    admin_permissions = []
    member = await dispatcher.get_chat_member(user_id, chat_id).permissions

    if member.can_edit_messages:
        admin_permissions.append("can_edit_messages")
    if member.can_delete_messages:
        admin_permissions.append("can_delete_messages")
    if member.can_restrict_members:
        admin_permissions.append("can_restrict_members")
    if member.can_promote_members:
        admin_permissions.append("can_promote_members")
    if member.can_pin_messages:
        admin_permissions.append("can_pin_messages")
    if member.can_change_info:
        admin_permissions.append("can_change_info")
    if member.can_invite_users:
        admin_permissions.append("can_invite_users")
    if member.can_post_messages:
        admin_permissions.append("can_post_messages")

    return admin_permissions