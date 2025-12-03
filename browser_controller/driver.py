import asyncio
import os
from playwright.async_api import async_playwright, Page, Browser, Playwright, BrowserContext
from page_perception.dom_service import DomService

USER_DATA_DIR = "user_data"
STATE_FILE = os.path.join(USER_DATA_DIR, "state.json")

class BrowserDriver:
    def __init__(self):
        self.playwright: Playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        
        if not os.path.exists(USER_DATA_DIR):
            os.makedirs(USER_DATA_DIR)

    async def start_browser(self, width=1280, height=900, position_x=0, position_y=0):
        print("[BrowserController] Launching browser...")
        self.playwright = await async_playwright().start()
        
        args = [
            f"--window-size={width},{height}",
            f"--window-position={position_x},{position_y}",
            "--disable-blink-features=AutomationControlled"
        ]

        self.browser = await self.playwright.chromium.launch(
            headless=False,
            slow_mo=100, # Чуть быстрее, так как мы добавим умные ожидания
            args=args
        )
        
        # Загрузка состояния
        if os.path.exists(STATE_FILE):
            try:
                self.context = await self.browser.new_context(
                    viewport={'width': width, 'height': height},
                    storage_state=STATE_FILE
                )
            except Exception as e:
                print(f"Error loading state: {e}")
                self.context = await self.browser.new_context(viewport={'width': width, 'height': height})
        else:
            self.context = await self.browser.new_context(viewport={'width': width, 'height': height})
        
        # При старте открываем одну вкладку
        self.page = await self.context.new_page()
        return self.page

    async def _ensure_page_active(self):
        """Гарантирует, что мы работаем с живой, активной вкладкой"""
        if not self.browser or not self.browser.is_connected():
            return # Браузер закрыт, ничего не поделаешь

        # 1. Если текущая страница жива и видна - ок
        try:
            if self.page and not self.page.is_closed():
                # Пинг
                await self.page.evaluate("1")
                return 
        except:
            pass # Страница умерла

        # 2. Ищем последнюю активную вкладку
        if self.context.pages:
            # Берем последнюю открытую (обычно это та, на которую смотрит юзер или которая открылась последней)
            self.page = self.context.pages[-1]
            try:
                await self.page.bring_to_front()
            except: pass
        else:
            self.page = await self.context.new_page()

    async def navigate(self, url: str):
        await self._ensure_page_active()
        if not url.startswith('http'): url = 'https://' + url

        # 1. Сначала проверяем ТЕКУЩУЮ страницу
        # Игнорируем разницу в слэшах в конце
        if self.page.url.rstrip('/') == url.rstrip('/'):
             return f"Already on this page: {url}"

        # 2. Проверяем другие вкладки (SMART NAVIGATE)
        # Ищем по домену или полному совпадению
        for page in self.context.pages:
            if url in page.url: # Простое вхождение
                self.page = page
                await self.page.bring_to_front()
                return f"Switched to existing tab: {self.page.url}"

        # 3. Если не нашли, переходим
        try:
            await self.page.goto(url)
            await self.page.wait_for_load_state("domcontentloaded")
            return f"Navigated to {url}"
        except Exception as e:
            return f"Error navigating: {e}"

            

    async def click_element(self, element_id: int):
        await self._ensure_page_active()
        selector = f'[data-agent-id="{element_id}"]'
        
        pages_before = len(self.context.pages)
        
        try:
            await self.page.click(selector, timeout=2500, force=True)
            
            # Ждем чуть-чуть реакции
            await asyncio.sleep(1)
            
            # Проверяем, не открылась ли новая вкладка
            if len(self.context.pages) > pages_before:
                self.page = self.context.pages[-1]
                await self.page.bring_to_front()
                await self.page.wait_for_load_state("domcontentloaded")
                return f"Clicked {element_id}, opened NEW TAB: {self.page.url}"

            return f"Clicked element {element_id}"
        except Exception as e:
            return f"Error clicking {element_id}: {str(e)}"

    async def type_text(self, element_id: int, text: str):
        await self._ensure_page_active()
        selector = f'[data-agent-id="{element_id}"]'
        try:
            await self.page.fill(selector, text, timeout=2000)
            return f"Typed '{text}' into element {element_id}"
        except Exception as e:
            return f"Error typing: {str(e)}"

    async def press_key(self, key: str):
        await self._ensure_page_active()
        try:
            await self.page.keyboard.press(key)
            await asyncio.sleep(0.5)
            return f"Pressed key: {key}"
        except Exception as e:
            return f"Error pressing key: {str(e)}"

    async def wait(self, seconds: int):
        print(f"[Driver] Waiting {seconds}s...")
        await asyncio.sleep(seconds)
        return f"Waited {seconds}s"

    async def read_visible_text(self):
        await self._ensure_page_active()
        try:
            text = await self.page.evaluate("document.body.innerText")
            clean_text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
            return clean_text[:25000]
        except Exception as e:
            return f"Error reading text: {e}"

    async def get_page_content(self):
        await self._ensure_page_active()
        if not self.page: return "Browser not started"
        
        try:
            # Получаем элементы
            items = await self.page.evaluate(DomService.get_accessibility_tree_script())
            
            text_representation = f"Current URL: {self.page.url}\nInteractive Elements:\n"
            for item in items:
                text_representation += f"[{item['id']}] {item['tagName']} '{item['text']}'\n"
            return text_representation
        except Exception as e:
            return f"Error reading DOM: {e}"

    async def close(self):
        # Безопасное закрытие без Traceback
        if self.context:
            try: await self.context.storage_state(path=STATE_FILE)
            except: pass
        
        # Игнорируем ошибки при закрытии (если уже закрыт)
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except:
            pass