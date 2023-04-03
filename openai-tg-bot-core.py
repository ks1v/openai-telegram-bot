import telegram
import mysql.connector
import json
import datetime
import openai
from telegram.ext import Updater, MessageHandler, Filters

# Load the API secrets from a JSON file
with open('keys.json') as f:
    secrets = json.load(f)

# Set up the MariaDB connection
cnx = mysql.connector.connect(
    user=secrets['mariadb']['user'],
    password=secrets['mariadb']['password'],
    host=secrets['127.0.0.1'],
    database=['mariadb']['database']
)
cursor = cnx.cursor()

# Set up the OpenAI API
openai.api_key = secrets['openai']['api_key']

# Set up the Telegram bot updater and dispatcher
updater = Updater(token=secrets['telegram']['token'], use_context=True)
dispatcher = updater.dispatcher

# Define a function to handle incoming messages
def handle_message(update, context):
    # Get the incoming message and chat ID
    message = update.message.text
    chat_id = update.message.chat_id

    # Save the incoming message to the database
    save_message(chat_id, message, False)

    # Pass the message to the GPT-3.5 model
    response = openai.Completion.create(
        engine="davinci-2",
        prompt=message,
        temperature=0.7,
        max_tokens=60
    )

    # Get the response text from the GPT-3.5 model
    response_text = response.choices[0].text.strip()

    # Send the response back to the user
    context.bot.send_message(chat_id=chat_id, text=response_text)

    # Save the response to the database
    save_message(chat_id, response_text, True)

# Define a function to save a message to the database
def save_message(chat_id, text, is_bot):
    now = datetime.datetime.now()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    insert_query = f"INSERT INTO messages (chat_id, text, is_bot, timestamp) VALUES ({chat_id}, '{text}', {is_bot}, '{timestamp}')"
    cursor.execute(insert_query)
    cnx.commit()

# Create a message handler that responds to all text messages
message_handler = MessageHandler(Filters.text, handle_message)

# Add the message handler to the dispatcher
dispatcher.add_handler(message_handler)

# Start the bot
updater.start_polling()

# Run the bot until Ctrl-C is pressed or the process receives SIGINT, SIGTERM or SIGABRT
updater.idle()

# Close the database connection when the bot is stopped
cursor.close()
cnx.close()


