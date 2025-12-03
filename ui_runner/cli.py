import asyncio
import sys
from browser_controller.driver import BrowserDriver

# Импортируем заглушки (в будущем здесь будет логика)
# from orchestrator import Orchestrator 

class AgentCLI:
    def __init__(self):
        self.driver = BrowserDriver()
        self.is_running = True

    async def run(self):
        print("==================================================")
        print("🤖 AI WEB AGENT CLI")
        print("==================================================")
        
        # 1. Запускаем браузер
        await self.driver.start_browser()
        
        # Для демонстрации откроем Google или пустую вкладку
        await self.driver.navigate("https://www.google.com")

        print("\nБраузер запущен. Введите задачу для агента.")
        print("Введите 'exit' или 'quit' для выхода.\n")

        # 2. Цикл взаимодействия с пользователем
        while self.is_running:
            try:
                # Используем run_in_executor для input, чтобы не блокировать event loop
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'quit']:
                    print("Завершение работы...")
                    self.is_running = False
                    break

                # Здесь будет передача управления Оркестратору
                await self.process_command(user_input)

            except KeyboardInterrupt:
                self.is_running = False
                break

        # 3. Очистка ресурсов
        await self.driver.close()

    async def process_command(self, text: str):
        """
        Здесь будет вызов Orchestrator.
        Пока просто эмулируем принятие задачи.
        """
        print(f"\n[USER]: {text}")
        print(f"[AGENT]: Задача принята. (Логика решения пока не реализована)")
        print(f"[AGENT]: Ожидаю следующую команду...\n")