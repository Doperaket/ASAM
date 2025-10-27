import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class BugReportTab(ttk.Frame):
    def __init__(self, parent, send_callback=None):
        super().__init__(parent)
        self.send_callback = send_callback
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Отправить баг-репорт", font=("Helvetica", 15, "bold")).pack(pady=10)
        self.text_entry = tk.Text(self, height=6, width=60)
        self.text_entry.pack(pady=5)

        self.file_paths = []
        self.file_label = ttk.Label(self, text="Файлы не выбраны")
        self.file_label.pack(pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Добавить фото/видео", command=self.add_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отправить", command=self.send_report, style="success.TButton").pack(side=tk.LEFT, padx=5)

    def add_files(self):
        files = filedialog.askopenfilenames(title="Выберите фото/видео", filetypes=[
            ("Фото и видео", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.mp4;*.avi;*.mov;*.mkv"),
            ("Все файлы", "*.*")
        ])
        if files:
            self.file_paths = list(files)
            self.file_label.config(text=f"Выбрано файлов: {len(self.file_paths)}")
        else:
            self.file_label.config(text="Файлы не выбраны")

    def send_report(self):
        text = self.text_entry.get("1.0", tk.END).strip()
        if not text and not self.file_paths:
            messagebox.showwarning("Пустой баг-репорт", "Пожалуйста, опишите проблему или добавьте файл.")
            return
        
        if self.send_callback:
            self.update_idletasks()
            
            success = self.send_callback(text, self.file_paths)
            
            if success:
                messagebox.showinfo("Отправлено", "Ваш баг-репорт успешно отправлен на сервер!")
                self.text_entry.delete("1.0", tk.END)
                self.file_paths = []
                self.file_label.config(text="Файлы не выбраны")
            else:
                messagebox.showerror("Ошибка", "Не удалось отправить баг-репорт. Проверьте подключение к интернету и попробуйте снова.")
        else:
            messagebox.showerror("Ошибка", "Функция отправки не настроена.")
