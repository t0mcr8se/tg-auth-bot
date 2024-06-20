import os
import telebot
from dotenv import load_dotenv
import sqlite3
import re
from datetime import datetime
load_dotenv()

BOT_TOKEN = os.environ.get('BOT_TOKEN')
POLLING_TIMEOUT = None
WALLET_ADDRESS_REGEX = r'^0x[a-fA-F0-9]{40}$'
pw = os.environ.get('PASSWORD')
# Function to initialize database connection and cursor
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Create the table if it does not exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            wallet_address TEXT,
            chat_id INTEGER,
            visited BOOLEAN,
            completed BOOLEAN,
            created_at DATETIME
        )
    ''')
    conn.commit()

    return conn, cursor
init_db()

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=100)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    print(message.text)
    if message.chat.type != 'private':
        bot.send_message(message.chat.id, 'Sorry, this bot can only be used in private chats!')
    else:
        wallet_address = message.text.split()[-1]
        chat_id = message.chat.id
        if not (re.match(WALLET_ADDRESS_REGEX, wallet_address) is not None):
            bot.send_message(chat_id, 'Invalid wallet address. Please enter a valid Ethereum wallet address.')    
        else:
            conn = sqlite3.connect('bot_database.db')
            cursor = conn.cursor()

            if message.chat.type != 'private':
                bot.send_message(chat_id, 'Sorry, this bot can only be used in private chats!')
            else:
                # Check if the wallet address already exists in the database
                cursor.execute('SELECT * FROM users WHERE wallet_address = ? OR chat_id = ?', (wallet_address, chat_id))
                existing_user = cursor.fetchone()

                if existing_user:
                    # Modify the message based on the visited and completed status
                    if existing_user[3]:  # Visited
                        if existing_user[4]:  # Completed
                            status_message = 'completed'
                        else:
                            status_message = 'in queue'
                        bot.send_message(chat_id, f"Sorry, you have already signed up with wallet: {existing_user[1]}, and it is {status_message}.")
                    else:
                        bot.send_message(chat_id, f'Sorry, you have already signed up with this wallet {existing_user[1]}, but your status is not updated yet.')
                else:
                    # Insert the new user into the database
                    cursor.execute('INSERT INTO users (wallet_address, chat_id, visited, completed, created_at) VALUES (?, ?, ?, ?, ?)',
                                (wallet_address, chat_id, False, False, datetime.now()))
                    conn.commit()
                    bot.send_message(chat_id, 'Request for tokens was added successfully to the queue!')
                    bot.send_message(chat_id, 'Address: ' + wallet_address)
                    bot.send_message(chat_id, 'I will update you soon.')

            # Close the database connection inside the function
            conn.close()

@bot.message_handler(commands=['delete_all'])
def delete_all_records(message):
    # Check if the password is correct
    if message.text.split()[-1] == pw:
        # Connect to SQLite database
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()

        # Delete all records from the 'users' table
        cursor.execute('DELETE FROM users')
        conn.commit()

        bot.send_message(message.chat.id, 'All records deleted successfully.')
        conn.close()
    else:
        bot.send_message(message.chat.id, 'Incorrect password. Deletion aborted.')

@bot.message_handler(commands=['delete'])
def delete_a_record(message):
    # Check if the password is correct
    if message.text.split()[-2] == pw:
        # Connect to SQLite database
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()

        # Delete all records from the 'users' table
        cursor.execute(f'DELETE FROM users WHERE wallet_address = {message.text.split()[-1]}')
        conn.commit()

        bot.send_message(message.chat.id, 'All records deleted successfully.')
        conn.close()
    else:
        bot.send_message(message.chat.id, 'Incorrect password. Deletion aborted.')

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id, 'I am here to help get tMetis!')
    bot.send_message(message.chat.id, 'Just send /start {your wallet address}')


@bot.message_handler(commands=['get_all_records'])
def get_all_records(message):
    # Check if the password is correct
    if message.text.split()[-1] == pw:
        # Connect to SQLite database
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()

        # Retrieve all records from the 'users' table
        cursor.execute('SELECT * FROM users')
        all_records = cursor.fetchall()

        # Send the records as a message
        if all_records:
            records_message = "All records:\n"
            for record in all_records:
                records_message += f"ID: {record[0]}, Wallet: {record[1]}, Chat ID: {record[2]}, Visited: {record[3]}, Completed: {record[4]}\n"
            bot.send_message(message.chat.id, records_message)
        else:
            bot.send_message(message.chat.id, 'No records found.')
        conn.close()
    else:
        bot.send_message(message.chat.id, 'Incorrect password. Retrieval aborted.')

bot.infinity_polling()


