import pymongo
import logging
from datetime import datetime
from openai_service import generate_scenario_from_topic
from audio import parse_scenario
from database import save_scenario
import time
from dotenv import load_dotenv
import os


load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

logging.basicConfig(level=logging.DEBUG)

try:
    client = pymongo.MongoClient(MONGODB_URI)
    db = client['SCENARIO']
    topics_collection = db['suggested_topics']
    scenarios_collection = db['generated_scenario']
    logging.debug("MongoDB connection established successfully.")
except Exception as e:
    logging.error(f"Failed to connect to MongoDB: {e}")
    exit(1)

def get_unprocessed_topics():
    return topics_collection.find({"processed": "in_progress"})

def generate_scenario_from_random_topic():
    count_unprocessed_scenarios = scenarios_collection.count_documents({"processed": False, "unload": True})
    if count_unprocessed_scenarios > 0:
        return  

    random_topic = list(topics_collection.aggregate([{"$sample": {"size": 1}}]))
    if not random_topic:
        return

    topic_data = random_topic[0]
    topic = topic_data.get('topic')
    user_id = topic_data.get('user_id', 'system')  
    username = topic_data.get('username', 'system')

    logging.debug(f"Generating scenario from random topic: {topic}")

    generation_time = datetime.now()
    scenario = generate_scenario_from_topic(topic)

    scenario_data = {
        "topic": topic,
        "scenario": [],
        "user_id": user_id,
        "username": username,
        "generation_time": generation_time,
        "processed": False,
        "unload": False
    }
    result = save_scenario(scenario_data)

    parsed_scenario = parse_scenario(scenario)

    if parsed_scenario:
        scenarios_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {
                "scenario": parsed_scenario,
                "processed": False,
                "unload": False
            }}
        )
        logging.debug(f"Random scenario generated and saved: {topic} (ID: {result.inserted_id})")
    else:
        logging.warning(f"Generated scenario for topic '{topic}' is empty.")

def main():
    while True:
        try:
            topics = get_unprocessed_topics()
            for topic_data in topics:
                topic = topic_data.get('topic')
                user_id = topic_data.get('user_id')
                username = topic_data.get('username')

                if not topic or user_id is None or username is None:
                    continue
                
                logging.debug(f"Processing topic '{topic}' from user {username} ({user_id})")

                generation_time = datetime.now()
                scenario = generate_scenario_from_topic(topic)

                scenario_data = {
                    "topic": topic,
                    "scenario": [],
                    "user_id": user_id,
                    "username": username,
                    "generation_time": generation_time,
                    "unload": False
                }
                result = save_scenario(scenario_data)  

                parsed_scenario = parse_scenario(scenario)  

                if parsed_scenario:  
                    scenarios_collection.update_one(
                        {"_id": result.inserted_id},
                        {"$set": {
                            "scenario": parsed_scenario,
                            "processed": False,
                            "unload": False
                        }}
                    )
                    logging.debug(f"Scenario for topic '{topic}' (ID: {result.inserted_id}) successfully generated and saved in MongoDB.")
                else:
                    logging.warning(f"The scenario for topic '{topic}' is empty; processing completed.")

            generate_scenario_from_random_topic()

            time.sleep(10)

        except Exception as e:
            logging.error(f"Error generating scenario: {e}")
            time.sleep(10)

if __name__ == '__main__':
    main()
