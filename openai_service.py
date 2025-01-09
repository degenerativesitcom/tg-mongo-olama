import openai
import logging


logging.basicConfig(level=logging.DEBUG)


openai.api_base = 'http://localhost:11434/v1'
openai.api_key = 'ollama'  

def generate_scenario_from_topic(topic):
    logging.debug(f"""///////////////////////////////////////////////////////'{topic}'""")
    

    prompt = f"The topic is: {topic}."

    try:

        response = openai.ChatCompletion.create(
            model="dolphin-llama3:8b",
            messages=[
                {"role": "system", "content": f"""///////////////////////////////////////////////////////////"""
},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7,  
        )
        

        scenario = response.choices[0].message['content'].strip()
        logging.debug(f"Generated scenario: {scenario}")
        return scenario
    except Exception as e:
        logging.error(f"Error generating scenario: {e}")
        return "Error generating scenario."