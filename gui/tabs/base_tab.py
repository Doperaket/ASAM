from tkinter import ttk


class BaseTab:
    
    def __init__(self, notebook, main_window, title="Вкладка"):
        self.notebook = notebook
        self.main_window = main_window
        self.title = title
        
        self.frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.frame, text=title)
        
        self.create_interface()
    
    def create_interface(self):
        pass
    
    def get_frame(self):
        return self.frame
    
    def update_status(self, message):
        if hasattr(self.main_window, 'update_status'):
            self.main_window.update_status(message)
