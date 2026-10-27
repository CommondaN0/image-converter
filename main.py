import tkinter as tk
import sys
from gui.app import ConverterApp
from core.registry import create_default_manager


def main():
    root = tk.Tk()
    
    # Центрируем окно при первом открытии
    window_width = 800
    window_height = 580
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int((screen_width / 2) - (window_width / 2))
    center_y = int((screen_height / 2) - (window_height / 2))
    root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

    manager = create_default_manager()
    app = ConverterApp(root, manager=manager)

    root.mainloop()


if __name__ == "__main__":
    main()
