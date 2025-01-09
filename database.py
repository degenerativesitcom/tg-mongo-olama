import pymongo
import logging
from dotenv import load_dotenv
import os


load_dotenv()


MONGODB_URI = os.getenv("MONGODB_URI")


client = pymongo.MongoClient(MONGODB_URI)
db = client['SCENARIO']
scenarios_collection = db['generated_scenario']

def save_scenario(scenario_data, scenario_id=None):
    if scenario_id:
        try:
            scenarios_collection.update_one(
                {"_id": scenario_id},
                {"$set": {"scenario": scenario_data}}
            )
            logging.debug("Сценарий обновлен в MongoDB")
        except Exception as e:
            logging.error(f"Ошибка при обновлении сценария в MongoDB: {e}")
    else:
        try:
            result = scenarios_collection.insert_one(scenario_data)
            logging.debug("Сценарий сохранен в MongoDB")
            return result
        except Exception as e:
            logging.error(f"Ошибка при сохранении сценария в MongoDB: {e}")
            return None
