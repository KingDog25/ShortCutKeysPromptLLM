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
import subprocess
import sys
from ctypes import windll, wintypes


# Маппинг кириллических символов на латинские для горячих клавиш
CYRILLIC_TO_LATIN = {
    'й': 'q', 'ц': 'w', 'у': 'e', 'к': 'r', 'е': 't', 'н': 'y', 'г': 'u',
    'ш': 'i', 'щ': 'o', 'з': 'p', 'х': '[', 'ъ': ']', 'ф': 'a', 'ы': 's',
    'в': 'd', 'а': 'f', 'п': 'g', 'р': 'h', 'о': 'j', 'л': 'k', 'д': 'l',
    'ж': ';', 'э': "'", 'я': 'z', 'ч': 'x', 'с': 'c', 'м': 'v', 'и': 'b',
    'т': 'n', 'ь': 'm', 'б': ',', 'ю': '.',
}


def normalize_hotkey(hotkey_str):
    """Нормализует строку горячих клавиш, заменяя кириллицу на латиницу."""
    parts = hotkey_str.lower().split('+')
    norm_parts = []
    for part in parts:
        part = part.strip()
        if part in CYRILLIC_TO_LATIN:
            part = CYRILLIC_TO_LATIN[part]
        norm_parts.append(part)
    return '+'.join(norm_parts)


class PromptManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Менеджер промптов для ИИ-моделей")
        self.root.geometry("900x600")

        try:
            self.root.iconbitmap('prompt_manager.ico')
        except:
            pass

        self.delete_confirmation_active = False
        self.prompts = []
        self.ai_sites = [
            {"name": "Perplexity AI", "url": "https://playground.perplexity.ai/"},
            {"name": "DeepSeek Chat", "url": "https://chat.deepseek.com/"}
        ]

        # Настройки (создаём ДО load_data)
        self.always_on_top = tk.BooleanVar(value=False)
        self.auto_send_after_insert = tk.BooleanVar(value=False)

        self.load_data()

        self.create_menu()
        self.create_interface()
        self.register_hotkeys()

        # Глобальный перехват Ctrl+C/V/Z/A на уровне виртуальных кодов
        self._setup_global_clipboard_bindings()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ─────────────────────────────────────────────
    # Глобальный перехват Ctrl+C/V/Z/A для любой раскладки
    # ─────────────────────────────────────────────
    def _setup_global_clipboard_bindings(self):
        """
        Привязывает обработку Ctrl+C/V/Z/A через виртуальные коды клавиш,
        что работает независимо от раскладки клавиатуры.
        Виртуальные коды: C=0x43, V=0x56, Z=0x5A, A=0x41
        """
        def on_key(event):
            # Проверяем что зажат Ctrl (state & 0x4)
            ctrl_pressed = (event.state & 0x4) != 0
            if not ctrl_pressed:
                return

            widget = event.widget
            vk = event.keycode

            # Ctrl+C (keycode 67)
            if vk == 67:
                self._do_copy(widget)
                return "break"
            # Ctrl+V (keycode 86)
            elif vk == 86:
                self._do_paste(widget)
                return "break"
            # Ctrl+Z (keycode 90)
            elif vk == 90:
                self._do_undo(widget)
                return "break"
            # Ctrl+A (keycode 65)
            elif vk == 65:
                self._do_select_all(widget)
                return "break"

        # Привязываем к корневому окну — перехватывает все нажатия
        self.root.bind_all('<KeyPress>', on_key)

    def _do_copy(self, widget):
        """Копирование из любого виджета"""
        try:
            if isinstance(widget, tk.Text):
                text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            elif isinstance(widget, ttk.Entry) or isinstance(widget, tk.Entry):
                if widget.selection_present():
                    text = widget.selection_get()
                else:
                    return
            else:
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except tk.TclError:
            pass

    def _do_paste(self, widget):
        """Вставка в любой виджет"""
        try:
            text = self.root.clipboard_get()
            if isinstance(widget, tk.Text):
                try:
                    widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass
                widget.insert(tk.INSERT, text)
            elif isinstance(widget, ttk.Entry) or isinstance(widget, tk.Entry):
                try:
                    widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass
                widget.insert(tk.INSERT, text)
        except tk.TclError:
            pass

    def _do_undo(self, widget):
        """Отмена в текстовом виджете"""
        try:
            if isinstance(widget, tk.Text):
                widget.edit_undo()
        except tk.TclError:
            pass

    def _do_select_all(self, widget):
        """Выделить всё"""
        try:
            if isinstance(widget, tk.Text):
                widget.tag_add(tk.SEL, "1.0", tk.END)
                widget.mark_set(tk.INSERT, "1.0")
                widget.see(tk.INSERT)
            elif isinstance(widget, ttk.Entry) or isinstance(widget, tk.Entry):
                widget.select_range(0, tk.END)
                widget.icursor(tk.END)
        except tk.TclError:
            pass

    # ─────────────────────────────────────────────
    # Меню
    # ─────────────────────────────────────────────
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Сохранить", command=self.save_data)
        file_menu.add_separator()
        file_menu.add_command(label="Настройки", command=self.show_settings_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_close)

        manage_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Управление", menu=manage_menu)
        manage_menu.add_command(label="Добавить промпт", command=self.show_add_prompt_dialog)
        manage_menu.add_command(label="Управление сайтами", command=self.show_manage_sites_dialog)

    # ─────────────────────────────────────────────
    # Настройки
    # ─────────────────────────────────────────────
    def show_settings_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки")
        dialog.geometry("420x220")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.root)
        self._center_window(dialog, 420, 220)
        self._make_topmost_safe(dialog)

        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Checkbutton(
            main_frame,
            text="Поверх остальных окон",
            variable=self.always_on_top,
            command=self._apply_always_on_top
        ).pack(anchor=tk.W, pady=8)

        ttk.Checkbutton(
            main_frame,
            text="Автоматически отправить после вставки",
            variable=self.auto_send_after_insert
        ).pack(anchor=tk.W, pady=8)

        # Кнопка ОК — внизу, широкая, привязана к bottom
        ok_btn = ttk.Button(dialog, text="OK", command=lambda: [self.save_data(), dialog.destroy()])
        ok_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=15)

    def _apply_always_on_top(self):
        """Применяет настройку поверх остальных окон"""
        self.root.attributes('-topmost', self.always_on_top.get())
        # Если включено — сразу снимаем topmost чтобы свои окна были выше
        # (topmost будет восстановлен после закрытия дочерних окон)
        self.save_data()

    def _make_topmost_safe(self, dialog):
        """
        Делает дочернее окно поверх главного, не конфликтуя с topmost главного окна.
        Временно снимает topmost с главного окна, чтобы диалог был виден.
        """
        # Временно убираем topmost с главного окна
        if self.always_on_top.get():
            self.root.attributes('-topmost', False)

        dialog.attributes('-topmost', True)

        def on_dialog_close():
            # Восстанавливаем topmost главного окна
            if self.always_on_top.get():
                self.root.attributes('-topmost', True)
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        # Возвращаем оригинальный обработчик закрытия, если нужен
        dialog._on_safe_close = on_dialog_close

    # ─────────────────────────────────────────────
    # Интерфейс
    # ─────────────────────────────────────────────
    def create_interface(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_frame, padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_frame = ttk.Frame(main_frame, padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Левая часть — список промптов
        ttk.Label(left_frame, text="Список промптов:").pack(anchor=tk.W)

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

        # Кнопки
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Добавить", command=self.show_add_prompt_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Редактировать", command=self.edit_selected_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_selected_prompt).pack(side=tk.LEFT, padx=5)

        # Правая часть — редактор
        ttk.Label(right_frame, text="Текст промпта:").pack(anchor=tk.W)
        self.prompt_text = scrolledtext.ScrolledText(
            right_frame, wrap=tk.WORD, height=15, font=('Arial', 10), undo=True
        )
        self.prompt_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Выбор сайта
        site_frame = ttk.Frame(right_frame)
        site_frame.pack(fill=tk.X, pady=5)
        ttk.Label(site_frame, text="Выберите сайт:").pack(side=tk.LEFT)
        self.site_var = tk.StringVar()
        self.site_combo = ttk.Combobox(site_frame, textvariable=self.site_var, state="readonly")
        self.site_combo['values'] = [site["name"] for site in self.ai_sites]
        if self.ai_sites:
            self.site_combo.current(0)
        self.site_combo.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Кнопка отправки
        send_btn = ttk.Button(right_frame, text="Отправить на сайт", command=self.send_to_site)
        send_btn.pack(pady=10, fill=tk.X)

        # Двойной клик — открытие редактирования
        self.prompt_tree.bind("<Double-1>", lambda e: self.edit_selected_prompt())
        self.prompt_tree.bind("<Return>", lambda e: self.edit_selected_prompt())

        self.update_prompts_list()

    # ─────────────────────────────────────────────
    # Работа с промптами
    # ─────────────────────────────────────────────
    def update_prompts_list(self):
        for item in self.prompt_tree.get_children():
            self.prompt_tree.delete(item)
        for prompt in self.prompts:
            self.prompt_tree.insert('', tk.END, values=(prompt['name'], prompt['hotkeys']))

    def show_add_prompt_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить промпт")
        dialog.geometry("700x600")
        self._center_window(dialog, 700, 600)
        dialog.resizable(True, True)
        dialog.grab_set()
        dialog.transient(self.root)
        self._make_topmost_safe(dialog)

        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        ttk.Label(main_frame, text="Название:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_entry = ttk.Entry(main_frame, width=40)
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW, columnspan=2)
        name_entry.focus_set()

        ttk.Label(main_frame, text="Горячие клавиши:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        hotkeys_frame = ttk.Frame(main_frame)
        hotkeys_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        hotkeys_entry = ttk.Entry(hotkeys_frame, width=30)
        hotkeys_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            hotkeys_frame, text="Записать",
            command=lambda: self.record_hotkey(hotkeys_entry, dialog)
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Label(main_frame, text="(Пример: ctrl+alt+p)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        ttk.Label(main_frame, text="Текст промпта:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=2, column=1, sticky=tk.NSEW, columnspan=2, padx=5, pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        prompt_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=60, height=20, undo=True)
        prompt_text.pack(fill=tk.BOTH, expand=True)

        def save_prompt():
            name = name_entry.get().strip()
            hotkeys = hotkeys_entry.get().strip()
            text = prompt_text.get("1.0", tk.END).strip()
            if not name or not text:
                self._show_error_dialog(dialog, "Ошибка", "Название и текст промпта обязательны!")
                return
            if hotkeys:
                for p in self.prompts:
                    if p['hotkeys'] == hotkeys:
                        self._show_error_dialog(dialog, "Ошибка", "Такое сочетание клавиш уже используется!")
                        return
            self.prompts.append({'name': name, 'hotkeys': hotkeys, 'text': text})
            self.update_prompts_list()
            self.register_hotkeys()
            self.save_data()
            if hasattr(dialog, '_on_safe_close'):
                # Восстанавливаем topmost главного окна
                if self.always_on_top.get():
                    self.root.attributes('-topmost', True)
            dialog.destroy()

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky=tk.E)
        ttk.Button(btn_frame, text="Отмена", command=lambda: dialog._on_safe_close() if hasattr(dialog, '_on_safe_close') else dialog.destroy()).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Сохранить", width=20, command=save_prompt).pack(side=tk.RIGHT, padx=5)

    def record_hotkey(self, entry_widget, parent_dialog):
        dialog = tk.Toplevel(self.root)
        dialog.title("Запись горячей клавиши")
        dialog.geometry("600x400")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.root)
        self._center_window(dialog, 600, 400)
        dialog.attributes('-topmost', True)

        keyboard.unhook_all()

        label = ttk.Label(dialog, text="Нажмите комбинацию клавиш\nНапример: Ctrl+Alt+P", font=("Arial", 12))
        label.pack(pady=20)
        result_var = tk.StringVar()
        result_label = ttk.Label(dialog, textvariable=result_var, font=("Arial", 14, "bold"))
        result_label.pack(pady=10)
        key_combination = []

        def on_key_press(e):
            if e.name in ['ctrl', 'alt', 'shift', 'windows']:
                return
            key_combination.clear()
            if keyboard.is_pressed('ctrl'):
                key_combination.append('ctrl')
            if keyboard.is_pressed('alt'):
                key_combination.append('alt')
            if keyboard.is_pressed('shift'):
                key_combination.append('shift')
            if keyboard.is_pressed('windows'):
                key_combination.append('windows')
            key_combination.append(e.name)
            result_var.set('+'.join(key_combination))

        def save_combination():
            if key_combination:
                normalized = normalize_hotkey('+'.join(key_combination))
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, normalized)
            dialog.destroy()
            self.register_hotkeys()

        def cancel():
            dialog.destroy()
            self.register_hotkeys()

        keyboard.on_press(on_key_press)

        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, pady=20)
        ttk.Button(button_frame, text="Сохранить", command=save_combination, width=16).pack(side=tk.LEFT, padx=20, pady=8)
        ttk.Button(button_frame, text="Отмена", command=cancel, width=16).pack(side=tk.LEFT, padx=20, pady=8)
        dialog.protocol("WM_DELETE_WINDOW", cancel)

    def edit_selected_prompt(self):
        selected = self.prompt_tree.selection()
        if not selected:
            self._show_info_dialog(self.root, "Информация", "Выберите промпт для редактирования")
            return
        item_id = selected[0]
        item_index = self.prompt_tree.index(item_id)
        prompt = self.prompts[item_index]

        dialog = tk.Toplevel(self.root)
        dialog.title("Редактировать промпт")
        dialog.geometry("700x600")
        dialog.resizable(True, True)
        dialog.grab_set()
        dialog.transient(self.root)
        self._center_window(dialog, 700, 600)
        self._make_topmost_safe(dialog)

        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        ttk.Label(main_frame, text="Название:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_entry = ttk.Entry(main_frame, width=40)
        name_entry.insert(0, prompt['name'])
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW, columnspan=2)
        name_entry.focus_set()

        ttk.Label(main_frame, text="Горячие клавиши:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        hotkeys_frame = ttk.Frame(main_frame)
        hotkeys_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        hotkeys_entry = ttk.Entry(hotkeys_frame, width=30)
        hotkeys_entry.insert(0, prompt['hotkeys'])
        hotkeys_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            hotkeys_frame, text="Записать",
            command=lambda: self.record_hotkey(hotkeys_entry, dialog)
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Label(main_frame, text="(Пример: ctrl+alt+p)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        ttk.Label(main_frame, text="Текст промпта:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=2, column=1, sticky=tk.NSEW, columnspan=2, padx=5, pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        prompt_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=80, height=25, undo=True)
        prompt_text.pack(fill=tk.BOTH, expand=True)
        prompt_text.insert(tk.END, prompt['text'])

        def save_edits():
            name = name_entry.get().strip()
            hotkeys = hotkeys_entry.get().strip()
            text = prompt_text.get("1.0", tk.END).strip()
            if not name or not text:
                self._show_error_dialog(dialog, "Ошибка", "Название и текст промпта обязательны!")
                return
            for idx, p in enumerate(self.prompts):
                if idx != item_index and p['hotkeys'] == hotkeys and hotkeys:
                    self._show_error_dialog(dialog, "Ошибка", "Такое сочетание клавиш уже используется!")
                    return
            self.prompts[item_index] = {'name': name, 'hotkeys': hotkeys, 'text': text}
            self.update_prompts_list()
            self.register_hotkeys()
            self.save_data()
            if hasattr(dialog, '_on_safe_close'):
                if self.always_on_top.get():
                    self.root.attributes('-topmost', True)
            dialog.destroy()

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=1, columnspan=2, pady=10, sticky=tk.E)
        ttk.Button(btn_frame, text="Отмена", command=lambda: dialog._on_safe_close() if hasattr(dialog, '_on_safe_close') else dialog.destroy()).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Сохранить", width=20, command=save_edits).pack(side=tk.RIGHT, padx=5)

    def delete_selected_prompt(self):
        selected = self.prompt_tree.selection()
        if not selected:
            self._show_info_dialog(self.root, "Информация", "Выберите промпт для удаления")
            return
        if self.delete_confirmation_active:
            return
        self.delete_confirmation_active = True

        item_id = selected[0]
        item_index = self.prompt_tree.index(item_id)

        confirm_dialog = tk.Toplevel(self.root)
        confirm_dialog.title("Подтверждение удаления")
        confirm_dialog.geometry("350x150")
        confirm_dialog.resizable(False, False)
        confirm_dialog.grab_set()
        confirm_dialog.transient(self.root)
        self._center_window(confirm_dialog, 350, 150)

        # Временно снимаем topmost с главного окна
        if self.always_on_top.get():
            self.root.attributes('-topmost', False)
        confirm_dialog.attributes('-topmost', True)

        ttk.Label(confirm_dialog, text="Удалить выбранный промпт?", font=("Arial", 11)).pack(pady=20)

        def on_yes():
            del self.prompts[item_index]
            self.update_prompts_list()
            self.register_hotkeys()
            self.save_data()
            self.delete_confirmation_active = False
            if self.always_on_top.get():
                self.root.attributes('-topmost', True)
            confirm_dialog.destroy()

        def on_no():
            self.delete_confirmation_active = False
            if self.always_on_top.get():
                self.root.attributes('-topmost', True)
            confirm_dialog.destroy()

        btn_frame = ttk.Frame(confirm_dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Да", command=on_yes, width=10).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Нет", command=on_no, width=10).pack(side=tk.LEFT, padx=10)
        confirm_dialog.protocol("WM_DELETE_WINDOW", on_no)

    def load_selected_prompt_to_editor(self):
        """Загружает текст промпта в редактор (одиночный клик)"""
        selected = self.prompt_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        item_index = self.prompt_tree.index(item_id)
        prompt = self.prompts[item_index]
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert(tk.END, prompt['text'])

    # ─────────────────────────────────────────────
    # Управление сайтами
    # ─────────────────────────────────────────────
    def show_manage_sites_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Управление сайтами")
        dialog.geometry("500x350")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.root)
        self._center_window(dialog, 500, 350)
        self._make_topmost_safe(dialog)

        sites_listbox = tk.Listbox(dialog, width=60, height=10)
        scrollbar_sb = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=sites_listbox.yview)
        sites_listbox.configure(yscrollcommand=scrollbar_sb.set)
        scrollbar_sb.pack(side=tk.RIGHT, fill=tk.Y)
        sites_listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        for site in self.ai_sites:
            sites_listbox.insert(tk.END, f"{site['name']} - {site['url']}")

        def add_site():
            add_win = tk.Toplevel(dialog)
            add_win.title("Добавить сайт")
            add_win.geometry("400x180")
            add_win.resizable(False, False)
            add_win.grab_set()
            add_win.transient(dialog)
            add_win.attributes('-topmost', True)
            self._center_window(add_win, 400, 180)

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
                    self._show_error_dialog(add_win, "Ошибка", "Название и URL обязательны!")
                    return
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                self.ai_sites.append({'name': name, 'url': url})
                self.site_combo['values'] = [s['name'] for s in self.ai_sites]
                sites_listbox.insert(tk.END, f"{name} - {url}")
                self.save_data()
                add_win.destroy()

            bf = ttk.Frame(add_win)
            bf.pack(pady=8, fill=tk.X, padx=10)
            ttk.Button(bf, text="Отмена", command=add_win.destroy).pack(side=tk.RIGHT, padx=5)
            ttk.Button(bf, text="Сохранить", command=save_site).pack(side=tk.RIGHT, padx=5)

        def edit_site():
            sel = sites_listbox.curselection()
            if not sel:
                self._show_info_dialog(dialog, "Информация", "Выберите сайт для редактирования")
                return
            idx = sel[0]
            if idx >= len(self.ai_sites):
                return
            site = self.ai_sites[idx]

            edit_win = tk.Toplevel(dialog)
            edit_win.title("Редактировать сайт")
            edit_win.geometry("400x180")
            edit_win.resizable(False, False)
            edit_win.grab_set()
            edit_win.transient(dialog)
            edit_win.attributes('-topmost', True)
            self._center_window(edit_win, 400, 180)

            ttk.Label(edit_win, text="Название:").pack(anchor=tk.W, padx=10, pady=5)
            name_entry = ttk.Entry(edit_win, width=40)
            name_entry.insert(0, site['name'])
            name_entry.pack(padx=10, fill=tk.X)
            name_entry.focus_set()
            ttk.Label(edit_win, text="URL:").pack(anchor=tk.W, padx=10, pady=5)
            url_entry = ttk.Entry(edit_win, width=40)
            url_entry.insert(0, site['url'])
            url_entry.pack(padx=10, fill=tk.X)

            def save_edits():
                name = name_entry.get().strip()
                url = url_entry.get().strip()
                if not name or not url:
                    self._show_error_dialog(edit_win, "Ошибка", "Название и URL обязательны!")
                    return
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                self.ai_sites[idx] = {'name': name, 'url': url}
                self.site_combo['values'] = [s['name'] for s in self.ai_sites]
                sites_listbox.delete(0, tk.END)
                for s in self.ai_sites:
                    sites_listbox.insert(tk.END, f"{s['name']} - {s['url']}")
                self.save_data()
                edit_win.destroy()

            bf = ttk.Frame(edit_win)
            bf.pack(pady=8, fill=tk.X, padx=10)
            ttk.Button(bf, text="Отмена", command=edit_win.destroy).pack(side=tk.RIGHT, padx=5)
            ttk.Button(bf, text="Сохранить", command=save_edits).pack(side=tk.RIGHT, padx=5)

        def delete_site():
            sel = sites_listbox.curselection()
            if not sel:
                self._show_info_dialog(dialog, "Информация", "Выберите сайт для удаления")
                return
            idx = sel[0]
            if idx >= len(self.ai_sites):
                return
            response = self._show_yes_no_dialog(dialog, "Подтверждение", "Удалить выбранный сайт?")
            if response:
                del self.ai_sites[idx]
                sites_listbox.delete(idx)
                self.site_combo['values'] = [s['name'] for s in self.ai_sites]
                if self.ai_sites:
                    self.site_combo.current(0)
                else:
                    self.site_combo.set('')
                self.save_data()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=5, fill=tk.X)
        ttk.Button(btn_frame, text="Добавить", command=add_site).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Редактировать", command=edit_site).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=delete_site).pack(side=tk.LEFT, padx=5)

    # ─────────────────────────────────────────────
    # Горячие клавиши (библиотека keyboard)
    # ─────────────────────────────────────────────
    def register_hotkeys(self):
        keyboard.unhook_all()
        for prompt in self.prompts:
            hotkeys = prompt.get('hotkeys', '').strip()
            if hotkeys:
                try:
                    normalized = normalize_hotkey(hotkeys)
                    keyboard.add_hotkey(normalized, lambda p=prompt: self.insert_prompt_to_editor(p))
                except ValueError as e:
                    print(f"Ошибка регистрации горячих клавиш '{hotkeys}' -> '{normalize_hotkey(hotkeys)}': {e}")

    def insert_prompt_to_editor(self, prompt):
        self.root.after(0, self._insert_prompt, prompt)

    def _insert_prompt(self, prompt):
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert(tk.END, prompt['text'])
        self.root.lift()
        self.root.focus_force()

        if self.auto_send_after_insert.get():
            self.root.after(500, self.send_to_site)

    # ─────────────────────────────────────────────
    # Отправка на сайт
    # ─────────────────────────────────────────────
    def send_to_site(self):
        selected_site = self.site_var.get()
        site_url = None
        for site in self.ai_sites:
            if site['name'] == selected_site:
                site_url = site['url']
                break
        if not site_url:
            self._show_error_dialog(self.root, "Ошибка", "Сайт не выбран!")
            return

        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            self._show_error_dialog(self.root, "Ошибка", "Промпт пуст!")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(prompt)

        def send_ctrl_v():
            try:
                win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
                win32api.keybd_event(0x56, 0, 0, 0)
                time.sleep(0.05)
                win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            except Exception as e:
                print(f"Ошибка при отправке Ctrl+V: {e}")
                pyautogui.hotkey('ctrl', 'v')

        try:
            webbrowser.open(site_url)
            time.sleep(4)
            send_ctrl_v()

            if self.auto_send_after_insert.get():
                time.sleep(1)
                try:
                    send_btn = pyautogui.locateOnScreen('send_button.png', confidence=0.8)
                    if send_btn:
                        pyautogui.click(send_btn)
                    else:
                        time.sleep(0.5)
                        pyautogui.press('enter')
                except:
                    time.sleep(0.5)
                    pyautogui.press('enter')
        except Exception as e:
            self._show_error_dialog(self.root, "Ошибка", f"Не удалось открыть сайт: {e}")

    # ─────────────────────────────────────────────
    # Утилиты
    # ─────────────────────────────────────────────
    def _center_window(self, window, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

    def _show_error_dialog(self, parent, title, message):
        messagebox.showerror(title, message, parent=parent)

    def _show_info_dialog(self, parent, title, message):
        messagebox.showinfo(title, message, parent=parent)

    def _show_yes_no_dialog(self, parent, title, message):
        return messagebox.askyesno(title, message, parent=parent)

    # ─────────────────────────────────────────────
    # Сохранение / Загрузка
    # ─────────────────────────────────────────────
    def load_data(self):
        data_file = "prompt_manager_data.json"
        if os.path.exists(data_file):
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.prompts = data.get("prompts", [])
                    self.ai_sites = data.get("ai_sites", self.ai_sites)

                    settings = data.get("settings", {})
                    self.always_on_top.set(settings.get("always_on_top", False))
                    self.auto_send_after_insert.set(settings.get("auto_send_after_insert", False))

                    # Применяем настройку
                    self.root.attributes('-topmost', self.always_on_top.get())
            except Exception as e:
                print(f"Ошибка загрузки данных: {e}")
                self.prompts = []

    def save_data(self):
        data_file = "prompt_manager_data.json"
        try:
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump({
                    "prompts": self.prompts,
                    "ai_sites": self.ai_sites,
                    "settings": {
                        "always_on_top": self.always_on_top.get(),
                        "auto_send_after_insert": self.auto_send_after_insert.get()
                    }
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._show_error_dialog(self.root, "Ошибка сохранения", f"Ошибка:\n{str(e)}")

    def on_close(self):
        self.save_data()
        keyboard.unhook_all()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        style = ttk.Style()
        style.theme_use('clam')
    except:
        pass
    app = PromptManagerApp(root)
    root.mainloop()
