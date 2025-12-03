import tkinter as tk
from tkinter import ttk, scrolledtext
import asyncio
import json

THEME = {
    "bg": "#1e1e1e", "fg": "#d4d4d4", "panel_bg": "#252526", 
    "input_bg": "#3c3c3c", "input_fg": "#ffffff", "accent": "#007acc", 
    "success": "#89d185", "warning": "#cca700", "error": "#f48771", 
    "user_msg": "#4fc1ff", "tool_call": "#dcdcaa", "tool_res": "#808080",
    "thinking": "#b362ff" # Фиолетовый для "думалки"
}

class AgentSidebar:
    def __init__(self, loop, process_task_callback, check_key_callback):
        self.loop = loop
        self.process_task_callback = process_task_callback
        self.check_key_callback = check_key_callback
        
        self.root = tk.Tk()
        self.root.title("AI Agent DevTools")
        self.root.geometry("450x900+1000+0")
        self.root.configure(bg=THEME["bg"])
        
        self.is_busy = False 
        self.thinking_task = None # Для анимации
        
        self._setup_ui()
        self._setup_tags()
        self._setup_context_menu() # <--- НОВОЕ: Контекстное меню
        
        self.loop.call_soon_threadsafe(self.trigger_key_check)
        self.is_running = True
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_ui(self):
        # (Код UI без изменений, сокращен для краткости)
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TCombobox", fieldbackground=THEME["input_bg"], background=THEME["panel_bg"], foreground=THEME["fg"])
        
        frame_top = tk.Frame(self.root, pady=10, padx=10, bg=THEME["panel_bg"])
        frame_top.pack(fill="x")
        
        tk.Label(frame_top, text="MODEL", bg=THEME["panel_bg"], fg="#888", font=("Consolas", 8, "bold")).grid(row=0, column=0, sticky="w")
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(frame_top, textvariable=self.model_var, width=15)
        self.model_combo['values'] = ('gpt-5.1','o4-mini', 'gpt-4o', 'o1-mini')
        self.model_combo.current(0)
        self.model_combo.grid(row=0, column=1, padx=10, sticky="w")

        self.lbl_key_status = tk.Label(frame_top, text="Checking...", bg=THEME["panel_bg"], fg=THEME["warning"], font=("Consolas", 9))
        self.lbl_key_status.grid(row=0, column=2, sticky="e")

        self.frame_status = tk.Frame(self.root, pady=2, padx=10, bg=THEME["success"])
        self.frame_status.pack(fill="x")
        self.lbl_agent_status = tk.Label(self.frame_status, text="IDLE", bg=THEME["success"], fg="#000", font=("Consolas", 10, "bold"))
        self.lbl_agent_status.pack(side="left")

        frame_log = tk.Frame(self.root, padx=0, bg=THEME["bg"])
        frame_log.pack(fill="both", expand=True)
        
        self.log_area = scrolledtext.ScrolledText(
            frame_log, height=20, state='disabled', font=("Menlo", 10),
            bg=THEME["bg"], fg=THEME["fg"], insertbackground="white",
            selectbackground="#264f78", padx=10, pady=10, relief="flat"
        )
        self.log_area.pack(fill="both", expand=True)

         # --- Ввод ---
        frame_input = tk.Frame(self.root, pady=15, padx=10, bg=THEME["panel_bg"])
        frame_input.pack(fill="x", side="bottom")
        
        self.input_field = tk.Text(frame_input, height=3, font=("Arial", 11), bg=THEME["input_bg"], fg=THEME["input_fg"], relief="flat", insertbackground="white")
        self.input_field.pack(fill="x", pady=(0, 10))
        self.input_field.bind("<Control-Return>", lambda event: self.send_task())
        
        # ДОБАВЛЯЕМ МЕНЮ К INPUT FIELD
        self._setup_input_context_menu()

        self.send_btn = tk.Button(frame_input, text="RUN TASK", command=self.send_task, bg=THEME["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat")
        self.send_btn.pack(fill="x")

    def _setup_input_context_menu(self):
        """Меню для поля ввода (Вставить)"""
        self.input_menu = tk.Menu(self.root, tearoff=0, bg=THEME["panel_bg"], fg=THEME["fg"])
        self.input_menu.add_command(label="Вставить", command=self.paste_to_input)
        self.input_menu.add_command(label="Очистить", command=lambda: self.input_field.delete("1.0", tk.END))
        
        self.input_field.bind("<Button-3>", lambda e: self.input_menu.tk_popup(e.x_root, e.y_root))

    def paste_to_input(self):
        try:
            text = self.root.clipboard_get()
            self.input_field.insert(tk.INSERT, text)
        except:
            pass

    def _setup_tags(self):
        self.log_area.tag_config("USER", foreground=THEME["user_msg"], font=("Menlo", 11, "bold"), spacing1=10, spacing3=5)
        self.log_area.tag_config("AGENT", foreground=THEME["fg"], spacing1=5, spacing3=5)
        self.log_area.tag_config("TOOL_CALL", foreground=THEME["tool_call"], font=("Menlo", 10))
        self.log_area.tag_config("TOOL_RESULT", foreground=THEME["tool_res"], font=("Menlo", 9, "italic"))
        self.log_area.tag_config("SYSTEM", foreground=THEME["warning"], font=("Menlo", 9))
        self.log_area.tag_config("SUCCESS", foreground=THEME["success"], font=("Menlo", 11, "bold"))
        self.log_area.tag_config("ERROR", foreground=THEME["error"], font=("Menlo", 10, "bold"))
        self.log_area.tag_config("THINKING", foreground=THEME["thinking"], font=("Menlo", 10, "italic"))

    # --- НОВОЕ: Контекстное меню ---
    def _setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0, bg=THEME["panel_bg"], fg=THEME["fg"])
        self.context_menu.add_command(label="Копировать", command=self.copy_selection)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Очистить лог", command=self.clear_log)
        
        # Привязка правой кнопки мыши
        self.log_area.bind("<Button-3>", self.show_context_menu) # Windows/Linux
        self.log_area.bind("<Button-2>", self.show_context_menu) # MacOS (иногда)

    def show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def copy_selection(self):
        try:
            # Если есть выделение, копируем его
            sel = self.log_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(sel)
        except tk.TclError:
            # Если выделения нет, копируем всё
            all_text = self.log_area.get("1.0", tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(all_text)

    def clear_log(self):
        self.log_area.config(state='normal')
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state='disabled')

    # --- НОВОЕ: Анимация думалки ---
    def start_thinking(self):
        """Показывает анимацию, что модель думает"""
        self.log_area.config(state='normal')
        # Вставляем метку начала думания
        self.log_area.insert(tk.END, "🧠 Thinking", "THINKING")
        self.thinking_mark = self.log_area.index("end-1c linestart") # Запоминаем строку
        self.log_area.insert(tk.END, "\n")
        self.log_area.config(state='disabled')
        
        self.thinking_dots = 0
        self._animate_thinking()

    def _animate_thinking(self):
        if not self.is_busy: return # Если задача закончилась, стоп
        
        # Обновляем текст в строке thinking_mark
        dots = "." * (self.thinking_dots % 4) # . .. ...
        text = f"🧠 Thinking{dots}"
        
        self.log_area.config(state='normal')
        # Удаляем старую строку и пишем новую
        line_idx = self.log_area.get(self.thinking_mark, f"{self.thinking_mark} lineend")
        if "Thinking" in line_idx:
            self.log_area.delete(self.thinking_mark, f"{self.thinking_mark} lineend")
            self.log_area.insert(self.thinking_mark, text, "THINKING")
        self.log_area.config(state='disabled')
        
        self.thinking_dots += 1
        # Запускаем следующий кадр через 500мс
        self.thinking_task = self.root.after(500, self._animate_thinking)

    def stop_thinking(self):
        """Останавливает анимацию и заменяет на галочку"""
        if self.thinking_task:
            self.root.after_cancel(self.thinking_task)
            self.thinking_task = None
        
        self.log_area.config(state='normal')
        # Находим строку Thinking и меняем на (Thought finished) или просто скрываем
        # Для простоты просто оставим последнюю стадию или добавим время
        # Но лучше просто удалить строку "Thinking..." чтобы не засорять лог, 
        # так как ответ модели придет следом.
        # ИЛИ меняем на "Reasoned."
        
        # Давайте заменим "Thinking..." на пустоту или разделитель, т.к. ответ уже пришел
        # Но чтобы было видно что процесс был, напишем "Reasoning complete."
        line_idx = self.log_area.get(self.thinking_mark, f"{self.thinking_mark} lineend")
        if "Thinking" in line_idx:
            self.log_area.delete(self.thinking_mark, f"{self.thinking_mark} lineend")
            self.log_area.insert(self.thinking_mark, "⚡ Reasoning complete", "TOOL_RESULT")
            
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')


    def set_working_state(self, is_working: bool):
        self.is_busy = is_working
        if is_working:
            self.lbl_agent_status.config(text="RUNNING...", bg=THEME["accent"], fg="white")
            self.frame_status.config(bg=THEME["accent"])
            self.send_btn.config(state="disabled", bg="#444", text="Working...")
            self.input_field.config(state="disabled", bg="#2d2d2d")
        else:
            self.stop_thinking() # На всякий случай
            self.lbl_agent_status.config(text="READY", bg=THEME["success"], fg="#000")
            self.frame_status.config(bg=THEME["success"])
            self.send_btn.config(state="normal", bg=THEME["accent"], text="RUN TASK")
            self.input_field.config(state="normal", bg=THEME["input_bg"])
            self.input_field.focus()

    # Методы добавления логов и остальные (без изменений)...
    def add_log(self, type: str, title: str, content: str = ""):
        self.log_area.config(state='normal')
        
        if type == "user":
            self.log_area.insert(tk.END, f"\n👤 User:\n{title}\n", "USER")
        elif type == "agent":
            self.log_area.insert(tk.END, f"🤖 Assistant: {title}\n", "AGENT")
        elif type == "tool_call":
            self.log_area.insert(tk.END, f"🔧 Call: {title}\n", "TOOL_CALL")
            if content:
                try:
                    parsed = json.loads(content)
                    pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                    self.log_area.insert(tk.END, f"{pretty}\n", "TOOL_CALL")
                except:
                    self.log_area.insert(tk.END, f"{content}\n", "TOOL_CALL")
        elif type == "tool_result":
            preview = content[:300] + "..." if len(content) > 300 else content
            self.log_area.insert(tk.END, f"   ↳ Result: {preview}\n", "TOOL_RESULT")
        elif type == "system":
            self.log_area.insert(tk.END, f"⚙️ {title}\n", "SYSTEM")
        elif type == "success":
            self.log_area.insert(tk.END, f"✅ DONE: {title}\n", "SUCCESS")
        elif type == "error":
            self.log_area.insert(tk.END, f"❌ ERROR: {title}\n", "ERROR")

        self.log_area.insert(tk.END, "-" * 40 + "\n", "TOOL_RESULT")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def trigger_key_check(self):
        asyncio.run_coroutine_threadsafe(self.check_key_callback(), self.loop)

    def update_key_status(self, is_valid: bool, message: str):
        if is_valid:
            self.lbl_key_status.config(text="API KEY OK", fg=THEME["success"])
        else:
            self.lbl_key_status.config(text="INVALID KEY", fg=THEME["error"])
            self.add_log("error", message)

    def send_task(self):
        if self.is_busy: return
        text = self.input_field.get("1.0", tk.END).strip()
        if not text: return
        model = self.model_var.get()
        self.input_field.delete("1.0", tk.END)
        self.add_log("user", text)
        asyncio.run_coroutine_threadsafe(self.process_task_callback(text, model), self.loop)

    def update(self):
        if self.is_running: self.root.update()
    def on_close(self):
        self.is_running = False; self.root.destroy()