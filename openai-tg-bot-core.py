import openai
import mysql.connector
import json
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Load API keys from secrets.json
with open('secrets.json') as f:
    secrets = json.load(f)
    openai.api_key = secrets['openai']['api_key']
    db_password = secrets['mariadb']['password']
    bot_token = secrets['telegram']['token']


# Set up MySQL connection
cnx = mysql.connector.connect(user='ks1v', 
                              password=db_password,
                              host='127.0.0.1',
                              database='openai_tg_bot')
cursor = cnx.cursor()

# Set up Telegram bot
bot = telebot.TeleBot(bot_token)

# Set up keyboard for storing/retrieving chats
chat_buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
store_chat_button = KeyboardButton(text='Store Chat')
retrieve_chat_button = KeyboardButton(text='Retrieve Chat')
chat_buttons.row(store_chat_button, retrieve_chat_button)

# Define function to retrieve chat history
def retrieve_chat_history(chat_id):
    cursor.execute('SELECT * FROM chats WHERE chat_id=%s ORDER BY timestamp ASC', (chat_id,))
    return cursor.fetchall()

# Define function to store chat history
def store_chat_history(chat_id, messages):
    for message in messages:
        cursor.execute('INSERT INTO chats (chat_id, text, is_bot, timestamp) VALUES (%s, %s, %s, %s)',
                       (chat_id, message.text, int(message.from_bot), message.date.timestamp()))
    cnx.commit()

# Define function to generate AI response
def generate_response(input_text):
    response = openai.Completion.create(
        engine='text-davinci-002',
        prompt=input_text,
        max_tokens=60,
        n=1,
        stop=None,
        temperature=0.5,
    )
    return response.choices[0].text.strip()

# Define function to handle incoming messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Generate AI response
    response_text = generate_response(message.text)

    # Send AI response
    bot.send_message(message.chat.id, response_text)

    # Store chat history
    store_chat_history(message.chat.id, [message, telebot.types.Message(0, message.chat.id, message.date, True, response_text)])

# Define function to handle store chat button
@bot.message_handler(func=lambda message: message.text == 'Store Chat')
def handle_store_chat(message):
    # Store chat history
    chat_history = retrieve_chat_history(message.chat.id)
    store_chat_history(message.chat.id, [telebot.types.Message(h[2], message.chat.id, h[3], bool(h[4]), h[1]) for h in chat_history])

    # Send confirmation
    bot.send_message(message.chat.id, 'Chat stored.')

# Define function to handle retrieve chat button
@bot.message_handler(func=lambda message: message.text == 'Retrieve Chat')
def handle_retrieve_chat(message):
    # Retrieve chat history
    chat_history = retrieve_chat_history(message.chat.id)
    response_text = '\n'.join([f"{h[3].strftime('%Y-%m-%d %H:%M:%S')}: {'Bot: ' if h[4] else 'You: '}{h[1]}" for h in chat_history])

    # Send chat history
    bot.send_message(message.chat.id, response_text)

# Start bot
bot.polling()

