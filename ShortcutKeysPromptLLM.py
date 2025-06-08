import ctypes
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import webbrowser
import keyboard
import pyautogui
import time
import os
import win32con
import win32api
import time



class PromptManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Менеджер промптов для ИИ-моделей")
        self.root.geometry("900x600")

        # Установка иконки приложения (если есть)
        try:
            self.root.iconbitmap('prompt_manager.ico')  # Укажите путь к вашей иконке
        except:
            pass

        # Данные приложения
        self.prompts = []
        self.ai_sites = [
            {"name": "Perplexity AI", "url": "https://playground.perplexity.ai/"},
            {"name": "DeepSeek Chat", "url": "https://chat.deepseek.com/"}
        ]

        # Загрузка сохраненных данных
        self.load_data()

        # Создание меню
        self.create_menu()

        # Создание основного интерфейса
        self.create_interface()

        # Регистрация горячих клавиш
        self.register_hotkeys()

        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Сохранить", command=self.save_data)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_close)

        # Меню "Управление"
        manage_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Управление", menu=manage_menu)
        manage_menu.add_command(label="Добавить промпт", command=self.show_add_prompt_dialog)
        manage_menu.add_command(label="Управление сайтами", command=self.show_manage_sites_dialog)

    def create_interface(self):
        # Создание фреймов
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_frame, padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_frame = ttk.Frame(main_frame, padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Левая часть - список промптов
        ttk.Label(left_frame, text="Список промптов:").pack(anchor=tk.W)

        # Таблица промптов
        columns = ('name', 'hotkeys')
        self.prompt_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=15)
        self.prompt_tree.heading('name', text='Название')
        self.prompt_tree.heading('hotkeys', text='Горячие клавиши')
        self.prompt_tree.column('name', width=200)
        self.prompt_tree.column('hotkeys', width=100)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.prompt_tree.yview)
        self.prompt_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.prompt_tree.pack(fill=tk.BOTH, expand=True)

        # Кнопки под таблицей
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Добавить", command=self.show_add_prompt_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Редактировать", command=self.edit_selected_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_selected_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Вставить", command=self.insert_selected_prompt).pack(side=tk.LEFT, padx=5)

        # Правая часть - текстовый редактор и выбор сайта
        ttk.Label(right_frame, text="Текст промпта:").pack(anchor=tk.W)

        self.prompt_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, height=15, font=('Arial', 10))
        self.prompt_text.pack(fill=tk.BOTH, expand=True, pady=5)

        site_frame = ttk.Frame(right_frame)
        site_frame.pack(fill=tk.X, pady=5)

        ttk.Label(site_frame, text="Выберите сайт:").pack(side=tk.LEFT)

        self.site_var = tk.StringVar()
        self.site_combo = ttk.Combobox(site_frame, textvariable=self.site_var, state="readonly")
        self.site_combo['values'] = [site["name"] for site in self.ai_sites]
        if self.ai_sites:
            self.site_combo.current(0)
        self.site_combo.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Кнопка отправить
        send_btn = ttk.Button(right_frame, text="Отправить на сайт", command=self.send_to_site)
        send_btn.pack(pady=10, fill=tk.X)

        # Привязка событий
        self.prompt_tree.bind("<Double-1>", lambda e: self.insert_selected_prompt())
        self.prompt_tree.bind("<Return>", lambda e: self.insert_selected_prompt())

        # Загрузка промптов в таблицу
        self.update_prompts_list()

    def update_prompts_list(self):
        # Очистка таблицы
        for item in self.prompt_tree.get_children():
            self.prompt_tree.delete(item)

        # Добавление промптов в таблицу
        for prompt in self.prompts:
            self.prompt_tree.insert('', tk.END, values=(prompt['name'], prompt['hotkeys']))

    def show_add_prompt_dialog(self):
        # Создание диалогового окна
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить промпт")
        dialog.geometry("700x600")

        # Центрирование окна
        window_width = 700
        window_height = 600
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")

        dialog.resizable(True, True)  # Позволяем изменять размер окна
        dialog.grab_set()  # Делаем окно модальным

        # Создаем основной фрейм для размещения элементов
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Настраиваем веса для строк и столбцов
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Название
        ttk.Label(main_frame, text="Название:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_entry = ttk.Entry(main_frame, width=40)
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW, columnspan=2)
        name_entry.focus_set()

        # Используйте:
        ttk.Label(main_frame, text="Горячие клавиши:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        hotkeys_frame = ttk.Frame(main_frame)
        hotkeys_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        hotkeys_entry = ttk.Entry(hotkeys_frame, width=30)
        hotkeys_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(hotkeys_frame, text="Записать", command=lambda: self.record_hotkey(hotkeys_entry)).pack(
            side=tk.RIGHT, padx=5)
        ttk.Label(main_frame, text="(Пример: ctrl+alt+p)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        # Текст промпта
        ttk.Label(main_frame, text="Текст промпта:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)

        # Создаем frame для текстового поля, чтобы оно могло растягиваться
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=2, column=1, sticky=tk.NSEW, columnspan=2, padx=5, pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        # Текстовое поле с прокруткой
        prompt_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=60, height=20)
        prompt_text.pack(fill=tk.BOTH, expand=True)

        def save_prompt():
            name = name_entry.get().strip()
            hotkeys = hotkeys_entry.get().strip()
            text = prompt_text.get("1.0", tk.END).strip()

            if not name or not text:
                messagebox.showerror("Ошибка", "Название и текст промпта обязательны!")
                return

            # Проверка уникальности горячих клавиш
            if hotkeys:
                for prompt in self.prompts:
                    if prompt['hotkeys'] == hotkeys:
                        messagebox.showerror("Ошибка", "Такое сочетание клавиш уже используется!")
                        return

            self.prompts.append({
                'name': name,
                'hotkeys': hotkeys,
                'text': text
            })

            self.update_prompts_list()
            self.register_hotkeys()
            self.save_data()
            dialog.destroy()

        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky=tk.E)

        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Сохранить", command=save_prompt).pack(side=tk.RIGHT, padx=5)

    def record_hotkey(self, entry_widget):
        """Функция для записи нажатых клавиш в поле ввода горячих клавиш"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Запись горячей клавиши")
        dialog.geometry("600x400")
        dialog.resizable(False, False)
        dialog.grab_set()

        # Центрирование окна
        window_width = 600
        window_height = 400
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Сохраняем текущие горячие клавиши
        keyboard.unhook_all()

        label = ttk.Label(dialog, text="Нажмите комбинацию клавиш\nНапример: Ctrl+Alt+P", font=("Arial", 12), background='')
        label.pack(pady=20)

        result_var = tk.StringVar()
        result_label = ttk.Label(dialog, textvariable=result_var, font=("Arial", 14, "bold"))
        result_label.pack(pady=10)

        keys_pressed = set()
        key_combination = []

        def on_key_press(e):
            # Игнорируем события от модификаторов (они будут обрабатываться в on_key_release)
            if e.name in ['ctrl', 'alt', 'shift', 'windows']:
                return

            # Добавляем модификаторы, если они нажаты
            key_combination.clear()
            if keyboard.is_pressed('ctrl'):
                key_combination.append('ctrl')
            if keyboard.is_pressed('alt'):
                key_combination.append('alt')
            if keyboard.is_pressed('shift'):
                key_combination.append('shift')
            if keyboard.is_pressed('windows'):
                key_combination.append('windows')

            # Добавляем основную клавишу
            key_combination.append(e.name)

            # Показываем комбинацию
            result_var.set('+'.join(key_combination))

        # Функция для закрытия диалога и сохранения комбинации
        def save_combination():
            if key_combination:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, '+'.join(key_combination))
            dialog.destroy()
            # Восстанавливаем горячие клавиши
            self.register_hotkeys()

        # Привязываем обработчик к событиям клавиатуры
        keyboard.on_press(on_key_press)

        # Кнопки для сохранения/отмены
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, pady=20)

        ttk.Button(button_frame, text="Сохранить", command=save_combination, width=16).pack(side=tk.LEFT, padx=20,                                                                                pady=8)
        ttk.Button(button_frame, text="Отмена", command=lambda: [dialog.destroy(), self.register_hotkeys()],
                   width=16).pack(side=tk.LEFT, padx=20, pady=8)

        # При закрытии окна восстанавливаем горячие клавиши
        dialog.protocol("WM_DELETE_WINDOW", lambda: [dialog.destroy(), self.register_hotkeys()])

    def edit_selected_prompt(self):
        selected = self.prompt_tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите промпт для редактирования")
            return

        item_id = selected[0]
        item_index = self.prompt_tree.index(item_id)
        prompt = self.prompts[item_index]

        # Создание диалогового окна
        dialog = tk.Toplevel(self.root)
        dialog.title("Редактировать промпт")
        dialog.geometry("700x600")
        dialog.resizable(True, True)
        dialog.grab_set()  # Делаем окно модальным

        ttk.Label(dialog, text="Название:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.insert(0, prompt['name'])
        name_entry.grid(row=0, column=1, padx=10, pady=5, sticky=tk.EW, columnspan=2)
        name_entry.focus_set()

        ttk.Label(dialog, text="Горячие клавиши:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        hotkeys_entry = ttk.Entry(dialog, width=40)
        hotkeys_entry.insert(0, prompt['hotkeys'])
        hotkeys_entry.grid(row=1, column=1, padx=10, pady=5, sticky=tk.EW)
        ttk.Label(dialog, text="(Пример: ctrl+alt+p)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        prompt_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, width=80, height=25)
        prompt_text.grid(row=2, column=1, padx=10, pady=5, sticky=tk.NSEW, columnspan=2)
        prompt_text.insert(tk.END, prompt['text'])

        ttk.Label(dialog, text="Текст промпта:").grid(row=2, column=0, sticky=tk.NW, padx=10, pady=5)

        # Настройка веса строк и столбцов для правильного растягивания
        dialog.grid_rowconfigure(2, weight=1)
        dialog.grid_columnconfigure(1, weight=1)

        def save_edits():
            name = name_entry.get().strip()
            hotkeys = hotkeys_entry.get().strip()
            text = prompt_text.get("1.0", tk.END).strip()

            if not name or not text:
                messagebox.showerror("Ошибка", "Название и текст промпта обязательны!")
                return

            # Проверка уникальности горячих клавиш для других промптов
            for idx, p in enumerate(self.prompts):
                if idx != item_index and p['hotkeys'] == hotkeys and hotkeys:
                    messagebox.showerror("Ошибка", "Такое сочетание клавиш уже используется!")
                    return

            self.prompts[item_index] = {
                'name': name,
                'hotkeys': hotkeys,
                'text': text
            }

            self.update_prompts_list()
            self.register_hotkeys()
            self.save_data()
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=1, columnspan=2, pady=10, sticky=tk.E)

        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Сохранить", command=save_edits).pack(side=tk.RIGHT, padx=5)

    def delete_selected_prompt(self):
        selected = self.prompt_tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите промпт для удаления")
            return
        item_id = selected[0]
        item_index = self.prompt_tree.index(item_id)
        response = messagebox.askyesno("Подтверждение", "Удалить выбранный промпт?")
        if response:
            del self.prompts[item_index]
            self.update_prompts_list()
            self.register_hotkeys()
            self.save_data()

    def insert_selected_prompt(self):
        selected = self.prompt_tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите промпт для вставки")
            return
        item_id = selected[0]
        item_index = self.prompt_tree.index(item_id)
        prompt = self.prompts[item_index]
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert(tk.END, prompt['text'])

    def show_manage_sites_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Управление сайтами")
        dialog.geometry("500x350")
        dialog.resizable(False, False)
        dialog.grab_set()

        sites_listbox = tk.Listbox(dialog, width=60, height=10)
        scrollbar = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=sites_listbox.yview)
        sites_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        sites_listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        for site in self.ai_sites:
            sites_listbox.insert(tk.END, f"{site['name']} - {site['url']}")

        def add_site():
            add_win = tk.Toplevel(dialog)
            add_win.title("Добавить сайт")
            add_win.geometry("400x150")
            add_win.resizable(False, False)
            add_win.grab_set()

            ttk.Label(add_win, text="Название:").pack(anchor=tk.W, padx=10, pady=5)
            name_entry = ttk.Entry(add_win, width=40)
            name_entry.pack(padx=10, fill=tk.X)
            name_entry.focus_set()

            ttk.Label(add_win, text="URL:").pack(anchor=tk.W, padx=10, pady=5)
            url_entry = ttk.Entry(add_win, width=40)
            url_entry.pack(padx=10, fill=tk.X)

            def save_site():
                name = name_entry.get().strip()
                url = url_entry.get().strip()
                if not name or not url:
                    messagebox.showerror("Ошибка", "Название и URL обязательны!")
                    return

                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url

                self.ai_sites.append({'name': name, 'url': url})
                self.site_combo['values'] = [site['name'] for site in self.ai_sites]
                sites_listbox.insert(tk.END, f"{name} - {url}")
                self.save_data()
                add_win.destroy()

            btn_frame = ttk.Frame(add_win)
            btn_frame.pack(pady=5, fill=tk.X)

            ttk.Button(btn_frame, text="Отмена", command=add_win.destroy).pack(side=tk.RIGHT, padx=5)
            ttk.Button(btn_frame, text="Сохранить", command=save_site).pack(side=tk.RIGHT, padx=5)

        def delete_site():
            selected = sites_listbox.curselection()
            if not selected:
                messagebox.showinfo("Информация", "Выберите сайт для удаления")
                return
            idx = selected[0]
            if idx >= len(self.ai_sites):
                return

            response = messagebox.askyesno("Подтверждение", "Удалить выбранный сайт?")
            if response:
                del self.ai_sites[idx]
                sites_listbox.delete(idx)
                self.site_combo['values'] = [site['name'] for site in self.ai_sites]
                if self.ai_sites:
                    self.site_combo.current(0)
                else:
                    self.site_combo.set('')
                self.save_data()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=5, fill=tk.X)

        ttk.Button(btn_frame, text="Добавить", command=add_site).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=delete_site).pack(side=tk.LEFT, padx=5)

    def register_hotkeys(self):
        keyboard.unhook_all()  # Очищаем все горячие клавиши
        for prompt in self.prompts:
            hotkeys = prompt.get('hotkeys', '').strip()
            if hotkeys:
                try:
                    keyboard.add_hotkey(hotkeys, lambda p=prompt: self.insert_prompt_to_editor(p))
                except ValueError as e:
                    print(f"Ошибка регистрации горячих клавиш {hotkeys}: {e}")

    def insert_prompt_to_editor(self, prompt):
        self.root.after(0, self._insert_prompt, prompt)

    def _insert_prompt(self, prompt):
        # Вставляем текст в текущую позицию курсора
        self.prompt_text.insert(tk.INSERT, prompt['text'])
        self.root.lift()
        self.root.focus_force()

    def get_current_layout(self):
        """Получаем текущую раскладку клавиатуры"""
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        thread_id = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, 0)
        klid = ctypes.windll.user32.GetKeyboardLayout(thread_id)
        return klid & 0xFFFF

    def set_layout(self, layout_code):
        """Устанавливаем раскладку клавиатуры"""
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.PostMessageW(hwnd, 0x50, 0, layout_code)

    def __enter__(self):
        """Контекстный менеджер для временного переключения раскладки"""
        self.original_layout = self.get_current_layout()
        if self.original_layout != 0x0409:  # Если не английская
            self.set_layout(0x0409)  # Устанавливаем английскую
            time.sleep(0.3)  # Даем время на переключение
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Возвращаем исходную раскладку"""
        if self.original_layout and self.original_layout != 0x0409:
            self.set_layout(self.original_layout)
            time.sleep(0.3)

    def send_to_site(self):
        selected_site = self.site_var.get()
        site_url = None
        for site in self.ai_sites:
            if site['name'] == selected_site:
                site_url = site['url']
                break

        if not site_url:
            messagebox.showerror("Ошибка", "Сайт не выбран!")
            return

        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showerror("Ошибка", "Промпт пуст!")
            return

        # Копируем текст в буфер обмена
        self.root.clipboard_clear()
        self.root.clipboard_append(prompt)
        self.root.update()

        # Функция для выполнения Ctrl+V через win32api (работает при любой раскладке)
        def send_ctrl_v():
            try:
                # Пытаемся импортировать модули win32api
                import win32con
                import win32api

                # Эмулируем нажатие Ctrl+V с использованием виртуальных кодов клавиш
                # VK_CONTROL = 0x11, VK_V = 0x56
                win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)  # Нажать Ctrl
                win32api.keybd_event(0x56, 0, 0, 0)  # Нажать V
                time.sleep(0.05)  # Небольшая пауза
                win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)  # Отпустить V
                win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)  # Отпустить Ctrl

            except ImportError:
                # Если win32api не установлен, используем pyautogui как запасной вариант
                # (хотя это может не сработать при неанглийской раскладке)
                pyautogui.hotkey('ctrl', 'v')

        # Открываем сайт в браузере
        try:
            webbrowser.open(site_url)
            time.sleep(4)  # Даем время для загрузки страницы

            # Для Perplexity Playground:
            if "playground.perplexity.ai/" or "deepseek.com" in site_url:
                # Вставляем текст с помощью Ctrl+V (работает при любой раскладке)
                send_ctrl_v()

                # Попробуем найти и нажать кнопку отправки
                try:
                    send_btn = pyautogui.locateOnScreen('send_button.png', confidence=0.8)
                    if send_btn:
                        pyautogui.click(send_btn)
                    else:
                        # Если кнопка не найдена, пробуем нажать Enter
                        time.sleep(0.5)
                        pyautogui.press('enter')
                except:
                    # Если что-то пошло не так, просто нажимаем Enter
                    pyautogui.press('enter')

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть сайт: {e}")

    def load_data(self):
        data_file = "prompt_manager_data.json"
        if os.path.exists(data_file):
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.prompts = data.get("prompts", [])
                    self.ai_sites = data.get("ai_sites", [
                        {"name": "Perplexity AI", "url": "https://playground.perplexity.ai/"},
                        {"name": "DeepSeek Chat", "url": "https://chat.deepseek.com/"}
                    ])
            except Exception as e:
                messagebox.showerror("Ошибка загрузки",
                                     f"Ошибка при загрузке сохранённых данных:\n{str(e)}\nБудут использованы настройки по умолчанию.")
                self.prompts = []
                self.ai_sites = [
                    {"name": "Perplexity AI", "url": "https://playground.perplexity.ai/"},
                    {"name": "DeepSeek Chat", "url": "https://chat.deepseek.com/"}
                ]
        else:
            self.prompts = []
            self.ai_sites = [
                {"name": "Perplexity AI", "url": "https://playground.perplexity.ai/"},
                {"name": "DeepSeek Chat", "url": "https://chat.deepseek.com/"}
            ]

    def save_data(self):
        data_file = "prompt_manager_data.json"
        try:
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump({
                    "prompts": self.prompts,
                    "ai_sites": self.ai_sites
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Ошибка при сохранении данных:\n{str(e)}")


    def on_close(self):
        """Обработчик закрытия окна"""
        self.save_data()
        keyboard.unhook_all()  # Отключаем все горячие клавиши
        self.root.destroy()



if __name__ == "__main__":
    root = tk.Tk()
    try:
        # Установка темы для более современного вида
        style = ttk.Style()
        style.theme_use('clam')
    except:
        pass

    app = PromptManagerApp(root)
    root.mainloop()