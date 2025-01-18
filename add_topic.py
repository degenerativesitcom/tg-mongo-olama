import pymongo
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from datetime import datetime, timedelta
from openai_service import generate_scenario_from_topic
from audio import parse_scenario
from database import save_scenario
from dotenv import load_dotenv
import os
import asyncio
import re

load_dotenv()


MONGODB_URI = os.getenv("MONGODB_URI")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


client = pymongo.MongoClient(MONGODB_URI)
db = client['SCENARIO']
topics_collection = db['suggested_topics']
scenarios_collection = db['generated_scenario']  


logging.basicConfig(level=logging.DEBUG)


user_last_submission = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение при использовании команды /start."""
    welcome_message = (
        "Hello! I am your scenario bot. 📝\n"
        "Just enter /addtopic <your_topic> and I will generate a scene for you!\n"
        "If you have any questions, feel free to ask me!\n"
        "web: degenerative-sitcom.online\n"
        "online broadcasts:\n"
        "- x.com/degen_sitcom\n"
        "- youtube.com/@degenerativeSITCOM\n"
        "- t.me/degenerative_sitcom"
    )
    await update.message.reply_text(welcome_message)

async def add_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    username = update.message.from_user.username  
    topic = " ".join(context.args)

    if topic:
        logging.debug(f"Received topic '{topic}' from user {user_id} ({username})")

        current_time = datetime.now()
        if username in user_last_submission:  
            last_submission_time = user_last_submission[username]  
            time_difference = current_time - last_submission_time
            if time_difference < timedelta(seconds=60):
                remaining_time = timedelta(seconds=60) - time_difference
                remaining_time_seconds = remaining_time.total_seconds()
                await update.message.reply_text(f"You need to wait {int(remaining_time_seconds)} seconds before submitting another topic.")
                return

        try:

            existing_topic = topics_collection.find_one({"topic": topic, "user_id": user_id, "processed": False})
            if existing_topic:
                await update.message.reply_text(f"The topic '{topic}' is already waiting for processing.")
                logging.debug(f"The topic '{topic}' from user {user_id} is already added and waiting for processing.")
                return
            

            topic_creation_time = datetime.now()
            topic_data = {
                "topic": topic,
                "user_id": user_id,
                "username": username,
                "creation_time": topic_creation_time,
                "processed": "in_progress"  
            }
            topic_result = topics_collection.insert_one(topic_data)
            logging.debug(f"Topic '{topic}' added to MongoDB")
            await update.message.reply_text(f"The topic '{topic}' has been successfully added. Please wait for the scenario generation.")
            

            generation_time = datetime.now()
            scenario = generate_scenario_from_topic(topic)


            parsed_scenario = parse_scenario(scenario)  

            if parsed_scenario and len(parsed_scenario) > 0: 
                scenario_data = {
                    "topic": topic,
                    "scenario": parsed_scenario,
                    "user_id": user_id,
                    "username": username,
                    "generation_time": generation_time,
                    "unload": False,
                    "processed": False
                }
                if save_scenario(scenario_data):  

                    unprocessed_count = scenarios_collection.count_documents({"processed": False})
                    queue_position = unprocessed_count + 1  


                    await update.message.reply_text(f"Scenario '{topic}' successfully generated.\n"
                                                    f"Your position in the queue: {queue_position}.")  
                    logging.debug(f"Scenario '{topic}' successfully generated and sent to user {user_id}.")
                else:
                    logging.error("Failed to save the scenario.")
                    await update.message.reply_text("An error occurred while saving the scenario.")
            else:
                logging.warning(f"The scenario for the topic '{topic}' is empty, not sending to the user.")
                await update.message.reply_text("The scenario for your topic is empty. Please try again.")
                

            topics_collection.update_one({"_id": topic_result.inserted_id}, {"$set": {"processed": "complete"}})
            user_last_submission[username] = current_time  

        except Exception as e:
            logging.error(f"Error adding topic: {e}")
            await update.message.reply_text("An error occurred while adding the topic.")
    else:
        await update.message.reply_text("Please specify a topic after the /addtopic command.")

from collections import Counter

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Fetch topics generated in last day
    topics_generated_last_day = topics_collection.aggregate([
    {
        "$match": {
            "$expr": {
                "$gte": [
                    "$creation_time", 
                    {
                        "$subtract": ["$$NOW", 86400000] 
                    }
                ]
            }
        }
    }
])
    #Fetch topics generated in last month
    topics_generated_last_month = topics_collection.aggregate([
    {
        "$match": {
            "$expr": {
                "$gte": [
                    "$creation_time", 
                    {
                        "$subtract": ["$$NOW", 30*86400000] 
                    }
                ]
            }
        }
    }
])
    #Get counter object
    user_counts_daily = Counter([data["username"] for data in topics_generated_last_day 
                             if data and "username" in data and data["username"] is not None])
    user_counts_monthly = Counter([data["username"] for data in topics_generated_last_month 
                             if data and "username" in data and data["username"] is not None])

    #Get daily and monthly leaderboard
    leaderboard_daily = user_counts_daily.most_common(5)
    leaderboard_monthly= user_counts_monthly.most_common(5)

    #Create the message with emojis
    message = "\U0001F3C6 Leaderboard:\n\n"
    message += f"\U0001F4C5 *Month*\n"

    for rank, (user_id, count) in enumerate(leaderboard_monthly, 1):
        message += f"{rank}. @{user_id} - {count}\n"

    message += f"\n\U0001F4C5 *Day*\n"
    for rank, (user_id, count) in enumerate(leaderboard_daily, 1):
        message += f"{rank}. @{user_id} - {count}\n"

    #Send the leaderboard
    await update.message.reply_text(format_telegram(message),parse_mode ="markdown")


def format_telegram(input_str):
  #Escapes special characters in a string for use in Telegram messages.
  return re.sub(r"([_])", r"\\\1", input_str) 

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('addtopic', add_topic))
    application.add_handler(CommandHandler('leaderboard', show_leaderboard))
    
    application.run_polling()

if __name__ == '__main__':
    main()
