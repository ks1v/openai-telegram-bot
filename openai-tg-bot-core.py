import openai
import telegram
import pymongo
import json

# Read API secrets from secrets.json file
with open('keys.json', 'r') as f:
    secrets = json.load(f)

# Set up OpenAI API credentials
openai.api_key = secrets['openai']['api_key']

# Set up Telegram bot token
bot_token = secrets['telegram']['token']

# Set up MongoDB database
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["mydatabase"]
mongo_collection = mongo_db["chat_sessions"]

# Create Telegram bot instance
bot = telegram.Bot(token=bot_token)

# Define function for sending GPT-3.5 responses
def send_gpt_response(message_text):
    # Send message to GPT-3.5 API and get response
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=message_text,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5
    )
    # Extract response from API output
    response_text = response.choices[0].text.strip()
    return response_text

# Define function for handling incoming messages
def handle_message(update, context):
    # Extract chat ID and message text
    chat_id = update.message.chat_id
    message_text = update.message.text
    # Check if chat session already exists in database
    chat_session = mongo_collection.find_one({"chat_id": chat_id})
    if chat_session:
        # Append message to existing chat session
        chat_session["messages"].append(message_text)
        mongo_collection.update_one({"_id": chat_session["_id"]}, {"$set": {"messages": chat_session["messages"]}})
    else:
        # Create new chat session in database
        chat_session = {"chat_id": chat_id, "messages": [message_text]}
        mongo_collection.insert_one(chat_session)
    # Send message to GPT-3.5 API and get response
    response_text = send_gpt_response("\n".join(chat_session["messages"]))
    # Send response to Telegram chat
    bot.send_message(chat_id=chat_id, text=response_text)

# Define function for handling button presses
def handle_button(update, context):
    # Extract chat ID and button data
    chat_id = update.callback_query.message.chat_id
    button_data = update.callback_query.data
    # Get chat session from database
    chat_session = mongo_collection.find_one({"chat_id": chat_id})
    if chat_session:
        # Get message index from button data
        message_index = int(button_data.split(":")[-1])
        # Retrieve message text from chat session
        message_text = chat_session["messages"][message_index]
        # Send message to GPT-3.5 API and get response
        response_text = send_gpt_response("\n".join(chat_session["messages"][:-1]) + "\n" + message_text)
        # Send response to Telegram chat
        bot.send_message(chat_id=chat_id, text=response_text)
    else:
        # If chat session does not exist, send error message
        bot.send_message(chat_id=chat_id, text="Error: chat session not found")

# Set up handlers for messages and buttons
updater = telegram.ext.Updater(token=bot_token, use_context=True)
updater.dispatcher.add_handler(telegram.ext.MessageHandler(telegram.ext.Filters.text, handle_message))
updater.dispatcher.add_handler(telegram.ext.CallbackQueryHandler(handle_button))

# Start the bot
updater.start_polling()
updater.idle()
