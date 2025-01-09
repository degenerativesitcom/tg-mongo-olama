import logging
import re


logging.basicConfig(level=logging.DEBUG)

def parse_scenario(scenario):
    """Парсит сценарий и возвращает массив объектов с персонажем и текстом."""
    lines = scenario.split('\n')
    parsed_lines = []
    current_character = None
    current_dialogue = []

    for line in lines:

        match = re.match(r'(\w+):\s*(.*)', line)
        if match:
            if current_character: 
                parsed_lines.append({"character": current_character, "line": " ".join(current_dialogue)})
            

            current_character = match.group(1)
            current_dialogue = [match.group(2)]
        elif current_character: 
            current_dialogue.append(line.strip())
        else:
            logging.warning(f"Неправильный формат строки: {line}")


    if current_character:
        parsed_lines.append({"character": current_character, "line": " ".join(current_dialogue)})

    return parsed_lines

