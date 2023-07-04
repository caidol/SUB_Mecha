import re
from src import dispatcher, LOGGER

from telegram import ( # telegram module imports
    KeyboardButton, 
    KeyboardButtonPollType, 
    Poll,
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove, 
    Update
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

_MODULE_ = "Poll/Quiz"
_HELP = """
/preview - Create a preview for a poll to be displayed
/createPoll - Create a poll
/createQuiz - Create a quiz
/poll - Send a poll
/quiz - Send a quiz
/cancelPoll - Cancel the poll creation
"""

LOGGER.info("Polls Module: Started initialisation.")

TOTAL_VOTER_COUNT = 3 # must be left a constant
answer_dict = {}

POLL_QUESTION, POLL_ANSWERS = range(2) # for poll creation
QUIZ_QUESTION, QUIZ_ANSWERS, CORRECT_ANSWER = range(3) # for quiz creation


async def configure_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # start poll config
    try:
        # ask for question
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Please enter the question for your poll:",
        )
        LOGGER.info("Polls Module: Question input message has been sent to chat.")
    except:
        LOGGER.info("Polls Module: Question input message was unable to be sent to chat.")
    
    return POLL_QUESTION # receive poll question data


async def poll_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # receive poll question
    global poll_question
    poll_question = update.message.text # update message

    # store question as key
    context.user_data[poll_question] = None # store question as key in user data
    #poll_dict[poll_question] = None
    LOGGER.info("Polls Module: Poll question is -> ", poll_question)
    
    try:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Please enter your responses separated by commas AND A WHITESPACE: ",
        )
        LOGGER.info("Polls Module: Response input message has been sent to chat.")
    except:
        LOGGER.info("Polls Module: Response input message was unable to be sent to chat.")

    return POLL_ANSWERS # receive poll answer data


async def poll_answers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # receive poll answers
    global poll_answers
    poll_answers = update.message.text # update message

    # store responses as values
    context.user_data[poll_question] = poll_answers # store poll answer in user data with corresponding poll question key
    LOGGER.info("Polls Module: Poll answers are -> ", poll_answers)

    # TRY FIX THIS: splits the data only by a comma and whitespace, but should allow to do just comma
    for i in context.user_data.keys(): 
        if i == poll_question:
            context.user_data[poll_question] = poll_answers.split(re.compile('[, ]||[,]')) # TODO test this
    
    try:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Thanks for configuring your poll! Now run the /poll command anywhere you wish to send it."
        )
        LOGGER.info("Polls Module: Completion message has been sent to chat.")
    except:
        LOGGER.info("Polls Module: Completion message was unable to be sent to chat.")

    return ConversationHandler.END # return the end of the conversation


async def configure_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # start quiz config
    if str(update.effective_chat.id)[0] == '-':
        await update.message.reply_text(
            """
            Please run the command again in a private chat
            
            https://t.me/sub_mecha_bot/
            """
        )
        
    else:
        await update.message.reply_text(
            "Please enter a question for your quiz: ",
        )

        return QUIZ_QUESTION # receive quiz question data


async def quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # receive quiz question
    global quiz_question
    quiz_question = update.message.text # update the message
    
    context.user_data[quiz_question] = None # set quiz question as key for user data
    #quiz_dict[quiz_question] = None
    #answer_dict[quiz_question] = None
    await update.message.reply_text(
        "Please enter the answers for your quiz separated by a commas AND A WHITESPACE: ",
    )

    return QUIZ_ANSWERS # receive quiz answers data


async def quiz_answers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # receive quiz answers
    global quiz_answers
    quiz_answers = update.message.text
    
    context.user_data[quiz_question] = quiz_answers

    for i in context.user_data.keys():
        if i == quiz_question:
            context.user_data[quiz_question] = quiz_answers.split(', ')

    print("quiz answers: ", quiz_answers)
    
    #for i in quiz_dict:
    #    quiz_dict[i] = quiz_answers.split(', ')

    await update.message.reply_text(
        "Please enter the answer of your quiz that will be the correct answer for your quiz: ",
    )

    return CORRECT_ANSWER # receive correct quiz answer data


async def correct_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # receive correct quiz answer
    correct_answer = update.message.text # update message

    global answer_dict
    answer_dict[quiz_question] = correct_answer # set the quiz question with the correct answer in answer_dict dictionary
    
    await update.message.reply_text(
        "Thank you for configuring your quiz information. To run the quiz please run the /quiz command.",
    )

    return ConversationHandler.END # return the end of the conversation


async def cancel_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # cancel command
    """Cancels and ends the conversation."""
    user = update.message.from_user # user id
    LOGGER.info("User %s canceled the conversation.", user.first_name)
    # send message below with information
    await update.message.reply_text(
        "That's alright! Just call the /createPoll or /createQuiz command if you'd like to create another poll/quiz again.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END # return end of the conversation


async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive the poll information and parse the information into a payload"""

    #print(context.user_data)
    for key, value in context.user_data.items():
        if key == poll_question and context.user_data[poll_question] == poll_answers.split(', '):
            question = key
            responses = value
    print(question, responses)

    message = await context.bot.send_poll(
        update.effective_chat.id,
        question,
        responses,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    # Save some info about the poll in bot data for later use in receive_poll_answer
    payload = {
        message.poll.id: {
            "questions": responses,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload) # update bot data with payload


async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Summarize a users poll vote"""
    answer = update.poll_answer # update the poll answer
    answered_poll = context.bot_data[answer.poll_id] # get the bot data relating to the specific poll id key
    try:
        questions = answered_poll["questions"]
    # otherwise the poll answer update is from an old poll, so we are unable to answer in that case
    except KeyError:
        return
    
    selected_options = answer.option_ids # retrieve selected options
    answer_string = ""
    for question_id in selected_options:
        if question_id != selected_options[-1]: # if it is not the last value
            answer_string += questions[question_id] + " and "
        else:
            answer_string += questions[question_id]
    
    await context.bot.send_message(
        answered_poll["chat_id"],
        f"{update.effective_user.mention_html()} says {answer_string}.",
        parse_mode=ParseMode.HTML,
    )
    answered_poll["answers"] += 1 # update the number of answers
    # Close poll after three participants have voted
    if answered_poll["answers"] == TOTAL_VOTER_COUNT:
        await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])


async def receive_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """On receiving polls, reply to it by a closed poll that will copy the received poll"""
    actual_poll = update.effective_message.poll
    # Only questions and options need to be set, as the other parameters don't matter for
    # a closed poll
    await update.effective_message.reply_poll(
        question=actual_poll.question,
        options=[o.text for o in actual_poll.options],
        # with is_closed true, the poll/quiz is immediately closed
        is_closed=True,
        reply_markup=ReplyKeyboardRemove(),
    )


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    """Sends a quiz with configured data"""

    for key, value in context.user_data.items():
        if key == quiz_question and value == quiz_answers.split(', '):
            question = key
            answers = value
    print(question, answers)

    for key, value in answer_dict.items():
        if key == quiz_question:
            correct_answer = value
    print(correct_answer)

    # test
    for i in range(len(answers)):
        if correct_answer == answers[i]:
            correct_id = i
            print("correct_id: ", correct_id) 

    message = await update.effective_message.reply_poll(
        question, answers, type=Poll.QUIZ, correct_option_id=correct_id, 
    )
    # Save some info about the poll that the bot_data can later use in receive_quiz_answer
    payload = {
        message.poll.id: {"chat_id": update.effective_chat.id, "message_id": message.message_id}
    }
    context.bot_data.update(payload)


async def receive_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Close the quiz after three participants took it."""
    # the bot can receive closed poll updates that we don't care about
    if update.poll.is_closed:
        return
    if update.poll.total_voter_count == TOTAL_VOTER_COUNT:
        try:
            quiz_data = context.bot_data[update.poll.id]
            # this means this poll answer update is from an old poll, we can't stop it then
        except KeyError:
            return
        await context.bot.stop_poll(quiz_data["chat_id"], quiz_data["message_id"])


async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to create a poll and display a preview of it"""
    # using this without a type lets the user to choose whether they want (quiz and a poll)
    button = [[KeyboardButton("Create preview", request_poll=KeyboardButtonPollType())]]
    message = "Press the button to let the bot generate a preview for you."
    # using one_time_keyboard to hide the keyboard
    await update.effective_message.reply_text(
        message, reply_markup=ReplyKeyboardMarkup(button, one_time_keyboard=True)
    )


async def cancel_operation() -> int:
    """Cancels the current conversation without returning a message -> assumed this is used if the user didn't directly call the cancel command"""
    
    return ConversationHandler.END


def main():
    # Add a conversation handler with multiple states
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
    dispatcher.run_polling()


if __name__ == '__main__':
    main()
