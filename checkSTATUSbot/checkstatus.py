import pymongo
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from datetime import datetime
from dotenv import load_dotenv
import os


load_dotenv()


MONGODB_URI = os.getenv("MONGODB_URI")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


client = pymongo.MongoClient(MONGODB_URI)
db = client['SCENARIO']
scenarios_collection = db['generated_scenario']  


logging.basicConfig(level=logging.DEBUG)

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id  
    username = update.message.from_user.username  
    chat_id = update.message.chat.id  


    logging.debug(f"Received message from chat: {chat_id}, user: {username} ({user_id})")

    try:

        unprocessed_scenarios = list(
            scenarios_collection.find({"processed": False}).sort("generation_time", 1)
        )

        if not unprocessed_scenarios:

            await update.message.reply_text("There are currently no scenarios waiting to be processed.")
            return


        user_scenarios = [
            (index + 1, scenario)  
            for index, scenario in enumerate(unprocessed_scenarios)
            if scenario["username"] == username
        ]

        if user_scenarios:

            response = "Your scenarios in the queue:\n"
            for position, scenario in user_scenarios:
                response += f"Scenario ID: {scenario['_id']}, Position: {position}\n"
            await update.message.reply_text(response)
            logging.debug(f"User {username} ({user_id}) has {len(user_scenarios)} scenarios in the queue.")
        else:

            await update.message.reply_text("You currently have no scenarios waiting to be processed.")

    except Exception as e:
        logging.error(f"Error checking status: {e}")
        await update.message.reply_text("An error occurred while checking your status. Please try again later.")

def main():
    """Запуск бота."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    

    application.add_handler(CommandHandler('checkstatus', check_status))
    

    application.run_polling()

if __name__ == '__main__':
    main()
