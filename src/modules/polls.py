import re

from src import dispatcher, LOGGER, BOT_USERNAME

from telegram import ( # telegram module imports
    KeyboardButton, 
    KeyboardButtonPollType, 
    Poll,
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup, 
    Update,
    helpers
)
from telegram.constants import ParseMode
from telegram.ext import ( # telegram.ext module imports
    CommandHandler, 
    ContextTypes, 
    MessageHandler,
    PollAnswerHandler,
    PollHandler, 
    ConversationHandler,
    filters
)

LOGGER.info("Polls: Started initialisation.")
_MODULE_ = "Poll/Quiz"
_HELP = """
/preview - Create a preview for a poll to be displayed
/createPoll - Create a poll
/createQuiz - Create a quiz
/poll - Send a poll
/quiz - Send a quiz
/cancelPoll - Cancel the poll creation
"""

TOTAL_VOTER_COUNT = 3 # must be left a constant
answer_dict = {}

POLL_QUESTION, POLL_ANSWERS = range(2) # for poll creation
QUIZ_QUESTION, QUIZ_ANSWERS, CORRECT_ANSWER = range(3) # for quiz creation


async def configure_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # start poll config
    LOGGER.info("Polls: Poll configuration started.")
    
    # Remove all user data in context if present in order to prevent lots of data
    # from being stored up

    if len(context.user_data) > 0:
        context.user_data.clear()
    
    try:
        # ask for question
        await update.message.reply_text(
            text="Please enter the question for your poll:",
        )
        LOGGER.info("Polls: Poll question request sent to chat ")
    except:
        LOGGER.error("Polls: Poll question request unable to be sent to chat.")

    return POLL_QUESTION # receive poll question data


async def poll_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # receive poll question
    global poll_question
    poll_question = update.message.text # update message
    LOGGER.info("Polls: Poll question retrieved from update object.")

    # store question as key
    LOGGER.info("Polls: Question has been stored as a key in user data.")
    context.user_data[poll_question] = None # store question as key in user data
    
    try:
        await update.message.reply_text(
            text="Please enter your responses separated by commas: ",
        )
        LOGGER.info("Polls: Poll responses request sent to chat.")
    except: 
        LOGGER.error("Polls: Poll responses request was unable to be sent to chat.")

    return POLL_ANSWERS # receive poll answer data


async def poll_answers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # receive poll answers
    global poll_answers
    poll_answers = update.message.text # update message
    LOGGER.info("Polls: Poll responses retrieved from update object.")

    # store responses as values
    LOGGER.info("Polls: Poll question and responses are being stored in user data.")
    context.user_data[poll_question] = poll_answers # store poll answer in user data with corresponding poll question key
    
    # TRY FIX THIS: splits the data only by a comma and whitespace, but should allow to do just comma
    for i in context.user_data.keys(): 
        if i == poll_question:
            LOGGER.info("Polls: Storing the poll question and separated values in user data.")
            regex_expression = re.compile(r"[, ]\s?")
            global delimiter
            delimiter = regex_expression.search(poll_answers)
            context.user_data[poll_question] = poll_answers.split(delimiter.group(0))
    try:
        await update.message.reply_text(
            text="Thanks for configuring your poll! Now run the /poll command anywhere you wish to send it."
        )
        LOGGER.info("Polls: Poll completion message has been sent to chat.")
    except:
        LOGGER.error("Polls: Poll completion message was unable to be sent to chat.")

    return ConversationHandler.END # return the end of the conversation


async def configure_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # start quiz config
    if str(update.effective_chat.id)[0] == '-':
        keyboard = [[InlineKeyboardButton(text="Run /createQuiz in private chat", url = f"https://t.me/{BOT_USERNAME}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await update.message.reply_text(
                text = "Press the button below to create a quiz in private chat.",
                reply_markup=reply_markup,
            )
            LOGGER.info("Polls: Quiz redirect message has been sent to chat.") 
        except:
            LOGGER.error("Polls: Quiz redirect message was unable to be sent to chat.")

        return ConversationHandler.END
    else:
        try:
            await update.message.reply_text(
                "Please enter a question for your quiz: ",
            )
            LOGGER.info("Polls: Quiz question request has been sent to chat.")
        except:
            LOGGER.error("Polls: Quiz question request was unable to be sent to chat.")

        return QUIZ_QUESTION # receive quiz question data


async def quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # receive quiz question
    global quiz_question
    quiz_question = update.message.text # update the message
    LOGGER.info("Polls: Quiz question retrieved from update object.")    

    context.user_data[quiz_question] = None # set quiz question as key for user data
    try:
        await update.message.reply_text(
            "Please enter the answers for your quiz separated by commas: ",
        )
        LOGGER.info("Polls: Quiz answers request has been sent to chat.")
    except:
        LOGGER.error("Polls: Quiz answers request was unable to be sent to chat.")

    return QUIZ_ANSWERS # receive quiz answers data


async def quiz_answers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # receive quiz answers
    global quiz_answers
    quiz_answers = update.message.text
    LOGGER.info("Polls: Quiz answers retrieved from update object.")

    context.user_data[quiz_question] = quiz_answers

    for i in context.user_data.keys():
        if i == quiz_question:
            LOGGER.info("Polls: Storing the quiz question and separated answers in user data.")
            regex_expression = re.compile(r"[, ]\s?")
            global delimiter
            delimiter = regex_expression.search(quiz_answers)
            context.user_data[quiz_question] = quiz_answers.split(delimiter.group(0))

    try:
        await update.message.reply_text(
            "Please enter the answer of your quiz that will be the correct answer for your quiz: ",
        )
        LOGGER.info("Polls: Quiz correct answer message has been sent to chat.")
    except:
        LOGGER.error("Polls: Quiz correct answer message was unable to be sent to chat.")

    return CORRECT_ANSWER # receive correct quiz answer data


async def correct_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # receive correct quiz answer
    bot = context.bot
    correct_answer = update.message.text # update message
    LOGGER.info("Polls: Correct answer retrieved from update message object.")

    global answer_dict
    LOGGER.info("Polls: Correct answer stored in the answer dictionary.")
    answer_dict[quiz_question] = correct_answer # set the quiz question with the correct answer in answer_dict dictionary
    
    try:
        await update.message.reply_text(
            "Thank you for configuring your quiz information. You can now select a group to run the /quiz command in"
        )
        LOGGER.info("Polls: Quiz completion message has been sent to chat.")
    except:
        LOGGER.error("Polls: Quiz completion message was unable to be sent to chat.")

    return ConversationHandler.END # return the end of the conversation


async def cancel_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # cancel command
    """Cancels and ends the conversation."""
    user = update.message.from_user # user id
    LOGGER.info("Polls: User %s canceled the conversation.", user.first_name)
    # send message below with information

    try:
        await update.message.reply_text(
            "That's alright! Just call the /createPoll or /createQuiz command if you'd like to create another poll/quiz again.", reply_markup=ReplyKeyboardRemove()
        )
        LOGGER.info("Polls: Cancel poll message was sent to chat.")
    except:
        LOGGER.error("Polls: Cancel poll message was unable to be sent to chat.")

    return ConversationHandler.END # return end of the conversation


async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive the poll information and parse the information into a payload"""    
    for key, value in context.user_data.items():
        if key == poll_question and value == poll_answers.split(delimiter.group(0)):
            LOGGER.info("Polls: Poll question and poll answer located in user_data.")
            question = key
            responses = value

    try:
        message = await context.bot.send_poll(
            update.effective_chat.id,
            question,
            responses,
            is_anonymous=False,
            allows_multiple_answers=True,
        )
        LOGGER.info("Polls: Poll was able to be sent to chat.")
    except:
        LOGGER.error("Polls: Poll was unable to be sent to chat.")
    
    # Save some info about the poll in bot data for later use in receive_poll_answer
    payload = {
        message.poll.id: {
            "questions": responses,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    LOGGER.info("Polls: Poll payload information stored in bot_data")
    context.bot_data.update(payload) # update bot data with payload


async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Summarize a users poll vote"""
    answer = update.poll_answer # update the poll answer
    LOGGER.info("Polls: The poll answer was retreived from the update object.")
    answered_poll = context.bot_data[answer.poll_id] # get the bot data relating to the specific poll id key
    try:
        LOGGER.info("Polls: Retrieving the poll via the questions.")
        questions = answered_poll["questions"]
    # otherwise the poll answer update is from an old poll, so we are unable to answer in that case
    except KeyError:
        LOGGER.error("Polls: Unable to retrieve te poll question because of a KeyError.")
        return
    
    selected_options = answer.option_ids # retrieve selected options
    answer_string = ""
    for question_id in selected_options:
        if question_id != selected_options[-1]: # if it is not the last value
            answer_string += questions[question_id] + " and "
        else:
            answer_string += questions[question_id]
    
    try:
        await context.bot.send_message(
            answered_poll["chat_id"],
            f"{update.effective_user.mention_html()} says {answer_string}.",
            parse_mode=ParseMode.HTML,
        )
        LOGGER.info("Polls: The poll answer user was sent to chat.")
    except:
        LOGGER.error("Polls: The poll answer user was unable to be sent to chat.")

    answered_poll["answers"] += 1 # update the number of answers
    # Close poll after three participants have voted
    if answered_poll["answers"] == TOTAL_VOTER_COUNT:
        LOGGER.warning("Polls: The poll answers has reached the maximum voter limit.")
        await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])


async def receive_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """On receiving polls, reply to it by a closed poll that will copy the received poll"""
    actual_poll = update.effective_message.poll
    LOGGER.info("Polls: The poll message was retrieved from the update object.")
    # Only questions and options need to be set, as the other parameters don't matter for
    # a closed poll

    try:
        await update.effective_message.reply_poll(
            question=actual_poll.question,
            options=[o.text for o in actual_poll.options],
            is_closed=True, # with is_closed true, the poll/quiz is immediately closed
            reply_markup=ReplyKeyboardRemove(),
        )
        LOGGER.info("Polls: The closed poll was sent to chat.")
    except:
        LOGGER.error("Polls: The closed poll was unable to be sent to chat.")


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    """Sends a quiz with configured data"""

    for key, value in context.user_data.items():
        if key == quiz_question and value == quiz_answers.split(delimiter.group(0)):
            LOGGER.info("Polls: Quiz question and quiz answers located in user_data.")
            question = key
            answers = value

    for key, value in answer_dict.items():
        if key == quiz_question:
            LOGGER.info("Polls: Quiz question has been located for correct answer.")
            correct_answer = value

    for i in range(len(answers)):
        if correct_answer == answers[i]:
            LOGGER.info("Polls: Correct id for quiz answer has been located.")
            correct_id = i

    message = await update.effective_message.reply_poll(
        question, answers, type=Poll.QUIZ, correct_option_id=correct_id, 
    )

    # Save some info about the poll that the bot_data can later use in receive_quiz_answer
    payload = {
        message.poll.id: {"chat_id": update.effective_chat.id, "message_id": message.message_id}
    }
    LOGGER.info("Polls: Quiz payload information stored in bot_data.")
    context.bot_data.update(payload)


async def receive_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Close the quiz after three participants took it."""
    # the bot can receive closed poll updates that we don't care about
    if update.poll.is_closed:
        return
    if update.poll.total_voter_count == TOTAL_VOTER_COUNT:
        LOGGER.warning("Polls: The quiz answers has reached the maximum voter limit.")
        try:
            quiz_data = context.bot_data[update.poll.id]
            LOGGER.info("Polls: Quiz payload information has been retrieved from bot data given the id.")
            # this means this poll answer update is from an old poll, we can't stop it then
        except KeyError:
            LOGGER.error("Polls: Unable to retrieve quiz payload information given id.")
            return
        
        try:
            await context.bot.stop_poll(quiz_data["chat_id"], quiz_data["message_id"])
            LOGGER.info("Polls: Quiz was able to be stopped.")
        except:
            LOGGER.error("Polls: Quiz was unable to be stopped.")

async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to create a poll and display a preview of it"""
    # using this without a type lets the user to choose whether they want (quiz and a poll)
    button = [[KeyboardButton("Create preview", request_poll=KeyboardButtonPollType())]]
    message = "Press the button to let the bot generate a preview for you."
    # using one_time_keyboard to hide the keyboard
    try:
        await update.effective_message.reply_text(
            message, reply_markup=ReplyKeyboardMarkup(button, one_time_keyboard=True)
        )
        LOGGER.info("Polls: Poll preview was sent to chat.")
    except:
        LOGGER.error("Polls: Poll preview wsa unable to be sent to chat.")


def main():
    # Add a conversation handler with multiple states
    LOGGER.info("Polls: Creating and adding handlers.")
    poll_creation_handler = ConversationHandler(
        entry_points=[CommandHandler("createPoll", configure_poll)], 
        states={
            POLL_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, poll_question)],
            POLL_ANSWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, poll_answers)],
        }, 
        fallbacks=[CommandHandler("cancelPoll", cancel_poll)])
    
    quiz_creation_handler = ConversationHandler(
        entry_points=[CommandHandler("createQuiz", configure_quiz)], 
        states={
            QUIZ_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_question)],
            QUIZ_ANSWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_answers)],
            CORRECT_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, correct_quiz_answer)]
        }, 
        fallbacks=[CommandHandler("cancelPoll", cancel_poll)])

    dispatcher.add_handler(poll_creation_handler)
    dispatcher.add_handler(quiz_creation_handler)
    dispatcher.add_handler(CommandHandler("poll", poll))
    dispatcher.add_handler(CommandHandler("quiz", quiz))
    dispatcher.add_handler(CommandHandler("preview", preview))
    dispatcher.add_handler(MessageHandler(filters.POLL, receive_poll))
    dispatcher.add_handler(PollAnswerHandler(receive_poll_answer))
    dispatcher.add_handler(PollHandler(receive_quiz_answer))
    #dispatcher.run_polling()

if __name__ == '__main__':
    main()