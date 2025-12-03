import asyncio
from browser_controller.driver import BrowserDriver
from ui_runner.sidebar import AgentSidebar
from orchestrator.engine import Orchestrator
from agent_core.openai_client import AIClient

async def run_agent():
    driver = BrowserDriver()
    loop = asyncio.get_running_loop()
    
    # Храним экземпляр оркестратора здесь, чтобы он жил между нажатиями кнопки
    orchestrator = None

    # --- Callbacks ---

    async def on_user_task(task_text, model_name):
        nonlocal orchestrator
        
        sidebar.set_working_state(True)
        
        # Создаем адаптер для логов
        def log_adapter(type_msg, title, content=""):
            if type_msg == "thinking_start":
                sidebar.start_thinking()
            elif type_msg == "thinking_end":
                sidebar.stop_thinking()
            else:
                sidebar.add_log(type_msg, title, content)

        # Логика сброса памяти
        if task_text.lower() in ["reset", "clear", "сброс", "новая задача"]:
            orchestrator = Orchestrator(driver, log_adapter)
            sidebar.add_log("system", "♻️ Память агента очищена. Готов к новой задаче.", "")
            sidebar.set_working_state(False)
            return

        # Инициализация оркестратора при первом запуске
        if orchestrator is None:
            orchestrator = Orchestrator(driver, log_adapter)
        
        try:
            # Запускаем обработку (или продолжаем диалог)
            await orchestrator.process_task(task_text, model_name=model_name)
        except Exception as e:
            sidebar.add_log("error", f"Critical Error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            sidebar.set_working_state(False)

    async def on_check_key():
        is_valid, msg = await AIClient.validate_api_key()
        sidebar.update_key_status(is_valid, msg)

    # --- Init ---
    
    sidebar = AgentSidebar(loop, on_user_task, on_check_key)
    
    print("Запуск системы...")
    # Открываем браузер
    await driver.start_browser(width=1280, height=900, position_x=0, position_y=0)
    
    try:
        while sidebar.is_running:
            sidebar.update()
            await asyncio.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        await driver.close()
        print("Система остановлена.")

if __name__ == "__main__":
    asyncio.run(run_agent())