import pyperclip
import tkinter as tk

def patch_entry_clipboard(entry: tk.Entry):
    def on_ctrl_v(event):
        try:
            text = pyperclip.paste()
            entry.insert(tk.INSERT, text)
            return "break"
        except Exception as e:
            print(f"Ошибка вставки из буфера: {e}")
    entry.bind('<Control-v>', on_ctrl_v)
    entry.bind('<Control-V>', on_ctrl_v)

def patch_text_clipboard(text_widget: tk.Text):
    def on_ctrl_v(event):
        try:
            text = pyperclip.paste()
            text_widget.insert(tk.INSERT, text)
            return "break"
        except Exception as e:
            print(f"Ошибка вставки из буфера: {e}")
    text_widget.bind('<Control-v>', on_ctrl_v)
    text_widget.bind('<Control-V>', on_ctrl_v)
