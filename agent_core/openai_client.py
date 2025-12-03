import os
import json
from openai import AsyncOpenAI, OpenAIError
from dotenv import load_dotenv

load_dotenv()

class AIClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("WARNING: OPENAI_API_KEY не найден в .env")
            
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "gpt-5.1" # Новая флагманская модель

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "navigate",
                    "description": "Перейти на указанный веб-сайт (URL).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Полный URL"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "click_element",
                    "description": "Кликнуть по элементу, используя его ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_id": {"type": "integer", "description": "ID элемента"}
                        },
                        "required": ["element_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "type_text",
                    "description": "Ввести текст в поле ввода.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_id": {"type": "integer", "description": "ID элемента"},
                            "text": {"type": "string", "description": "Текст для ввода"}
                        },
                        "required": ["element_id", "text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "press_key",
                    "description": "Нажать клавишу (Enter, Tab, Escape, etc).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string", "description": "Название клавиши"}
                        },
                        "required": ["key"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_visible_text",
                    "description": "Прочитать весь видимый текст на странице. Полезно для чтения списков писем, статей или результатов поиска без кликов.",
                    "parameters": {
                        "type": "object",
                        "properties": {}, 
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ask_user",
                    "description": "Спросить пользователя разрешение или уточнить информацию.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string", "description": "Вопрос к пользователю"}
                        },
                        "required": ["question"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "wait",
                    "description": "Подождать указанное количество секунд. ИСПОЛЬЗУЙ ОБЯЗАТЕЛЬНО после кликов, которые открывают новые страницы или меняют интерфейс (фильтры, вход).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "seconds": {"type": "integer", "description": "Время ожидания в секундах (обычно 3-5)"}
                        },
                        "required": ["seconds"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "task_complete",
                    "description": "Вызвать, когда задача полностью выполнена.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string", "description": "Отчет о результате"}
                        },
                        "required": ["summary"]
                    }
                }
            }
        ]

    @staticmethod
    async def validate_api_key():
        key = os.getenv("OPENAI_API_KEY")
        if not key: return False, "Ключ не найден"
        try:
            client = AsyncOpenAI(api_key=key)
            await client.models.list()
            return True, "Ключ активен"
        except Exception as e:
            return False, f"Ошибка API: {str(e)}"

    async def get_next_action(self, history, model_override=None):
        current_model = model_override if model_override else self.model
        try:
            response = await self.client.chat.completions.create(
                model=current_model,
                messages=history,
                tools=self.tools,
                tool_choice="auto"
            )
            return response.choices[0].message
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return None