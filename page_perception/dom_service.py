class DomService:
    @staticmethod
    def get_accessibility_tree_script():
        """
        JS-скрипт, который находит все интерактивные элементы, 
        вешает на них временные атрибуты и возвращает их список.
        """
        return """
        () => {
            const elements = document.querySelectorAll('a, button, input, textarea, [role="button"], [role="link"]');
            const items = [];
            let counter = 1;

            elements.forEach((el) => {
                // Пропускаем невидимые элементы
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0 || window.getComputedStyle(el).visibility === 'hidden') return;

                // Генерируем уникальный ID для этой сессии
                const id = counter++;
                el.setAttribute('data-agent-id', id);

                let text = el.innerText || el.getAttribute('placeholder') || el.getAttribute('aria-label') || "";
                text = text.replace(/\\s+/g, ' ').trim().substring(0, 100); // Обрезаем длинный текст

                // Формируем описание элемента
                items.push({
                    id: id,
                    tagName: el.tagName.toLowerCase(),
                    text: text,
                    type: el.getAttribute('type') || '',
                    role: el.getAttribute('role') || ''
                });
            });

            return items;
        }
        """