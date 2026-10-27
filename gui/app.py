import os
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from core.base import ConversionResult
from core.registry import ConversionManager, create_default_manager


class ConverterApp:
    def __init__(self, root: tk.Tk, manager: Optional[ConversionManager] = None):
        self.root = root
        self.manager = manager or create_default_manager()

        self.root.title("Универсальный Конвертер Изображений")
        self.root.geometry("780x560")
        self.root.minsize(650, 480)

        # Список добавленных файлов: {path: dict(size, format, status)}
        self.files_map: dict[Path, dict] = {}
        self.is_converting = False

        self._init_styles()
        self._build_ui()
        self._refresh_formats()

    def _init_styles(self):
        style = ttk.Style()
        # Используем современную тему, если доступна
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 9))
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 1. Панель кнопок управления списком файлов ---
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        btn_add_files = ttk.Button(toolbar, text="➕ Добавить файлы...", command=self._add_files)
        btn_add_files.pack(side=tk.LEFT, padx=(0, 6))

        btn_add_folder = ttk.Button(toolbar, text="📁 Добавить папку...", command=self._add_folder)
        btn_add_folder.pack(side=tk.LEFT, padx=(0, 6))

        btn_remove = ttk.Button(toolbar, text="➖ Удалить выбранное", command=self._remove_selected)
        btn_remove.pack(side=tk.LEFT, padx=(0, 6))

        btn_clear = ttk.Button(toolbar, text="🗑 Очистить всё", command=self._clear_all)
        btn_clear.pack(side=tk.LEFT)

        self.lbl_count = ttk.Label(toolbar, text="Файлов: 0", font=("Segoe UI", 9))
        self.lbl_count.pack(side=tk.RIGHT)

        # --- 2. Таблица файлов (Treeview) ---
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("name", "size", "format", "status", "path")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")

        self.tree.heading("name", text="Имя файла", anchor=tk.W)
        self.tree.heading("size", text="Размер", anchor=tk.E)
        self.tree.heading("format", text="Формат", anchor=tk.CENTER)
        self.tree.heading("status", text="Статус", anchor=tk.W)
        self.tree.heading("path", text="Расположение", anchor=tk.W)

        self.tree.column("name", width=220, anchor=tk.W)
        self.tree.column("size", width=80, anchor=tk.E)
        self.tree.column("format", width=70, anchor=tk.CENTER)
        self.tree.column("status", width=130, anchor=tk.W)
        self.tree.column("path", width=240, anchor=tk.W)

        # Полосы прокрутки для таблицы
        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # --- 3. Настройки конвертации ---
        settings_box = ttk.LabelFrame(main_frame, text="Параметры конвертации", padding=10)
        settings_box.pack(fill=tk.X, pady=(0, 10))

        # Выбор формата назначения
        format_frame = ttk.Frame(settings_box)
        format_frame.pack(fill=tk.X, pady=(0, 8))

        lbl_format = ttk.Label(format_frame, text="Конвертировать в:")
        lbl_format.pack(side=tk.LEFT, padx=(0, 8))

        self.target_format_var = tk.StringVar(value="png")
        self.cb_format = ttk.Combobox(
            format_frame,
            textvariable=self.target_format_var,
            state="readonly",
            width=10,
        )
        self.cb_format.pack(side=tk.LEFT)

        # Папка сохранения
        dest_frame = ttk.Frame(settings_box)
        dest_frame.pack(fill=tk.X)

        self.same_folder_var = tk.BooleanVar(value=True)
        self.chk_same_folder = ttk.Checkbutton(
            dest_frame,
            text="Сохранять в ту же папку, где лежит исходный файл",
            variable=self.same_folder_var,
            command=self._toggle_destination_ui,
        )
        self.chk_same_folder.pack(anchor=tk.W, pady=(0, 4))

        custom_folder_frame = ttk.Frame(dest_frame)
        custom_folder_frame.pack(fill=tk.X)

        self.dest_folder_var = tk.StringVar(value="")
        self.entry_dest = ttk.Entry(
            custom_folder_frame,
            textvariable=self.dest_folder_var,
            state=tk.DISABLED,
        )
        self.entry_dest.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.btn_browse_dest = ttk.Button(
            custom_folder_frame,
            text="Обзор...",
            command=self._browse_destination,
            state=tk.DISABLED,
        )
        self.btn_browse_dest.pack(side=tk.RIGHT)

        # --- 4. Прогресс и действие ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(bottom_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        status_action_frame = ttk.Frame(bottom_frame)
        status_action_frame.pack(fill=tk.X)

        self.lbl_status = ttk.Label(
            status_action_frame,
            text="Готово к работе. Добавьте файлы для конвертации.",
            style="Status.TLabel",
        )
        self.lbl_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_open_folder = ttk.Button(
            status_action_frame,
            text="📂 Открыть папку",
            command=self._open_output_folder,
            state=tk.DISABLED,
        )
        self.btn_open_folder.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_convert = ttk.Button(
            status_action_frame,
            text="▶ Начать конвертацию",
            style="Action.TButton",
            command=self._start_conversion,
        )
        self.btn_convert.pack(side=tk.RIGHT)

    def _refresh_formats(self):
        targets = self.manager.get_supported_target_formats()
        self.cb_format["values"] = targets
        if "png" in targets:
            self.target_format_var.set("png")
        elif targets:
            self.target_format_var.set(targets[0])

    def _toggle_destination_ui(self):
        is_custom = not self.same_folder_var.get()
        state = tk.NORMAL if is_custom else tk.DISABLED
        self.entry_dest.config(state=state)
        self.btn_browse_dest.config(state=state)

    def _browse_destination(self):
        folder = filedialog.askdirectory(title="Выберите папку для сохранения файлов")
        if folder:
            self.dest_folder_var.set(folder)

    def _format_size(self, size_bytes: int) -> str:
        for unit in ["Б", "КБ", "МБ", "ГБ"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}" if unit != "Б" else f"{size_bytes} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} ТБ"

    def _add_files(self):
        sources = self.manager.get_supported_source_formats()
        ext_patterns = " ".join(f"*.{ext}" for ext in sources)
        filetypes = [
            ("Поддерживаемые изображения", ext_patterns),
            ("Файлы WebP", "*.webp"),
            ("Все файлы", "*.*"),
        ]

        paths = filedialog.askopenfilenames(
            title="Выберите файлы для конвертации",
            filetypes=filetypes,
        )
        if paths:
            self._append_paths([Path(p) for p in paths])

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с изображениями")
        if not folder:
            return

        supported_sources = set(self.manager.get_supported_source_formats())
        folder_path = Path(folder)
        found_paths: list[Path] = []

        for item in folder_path.iterdir():
            if item.is_file() and item.suffix.lower().lstrip(".") in supported_sources:
                found_paths.append(item)

        if found_paths:
            self._append_paths(found_paths)
        else:
            messagebox.showinfo(
                "Информация",
                f"В выбранной папке не найдено подходящих файлов ({', '.join(sorted(supported_sources))}).",
            )

    def _append_paths(self, paths: list[Path]):
        for p in paths:
            p = p.resolve()
            if p in self.files_map:
                continue

            try:
                size_str = self._format_size(p.stat().st_size)
            except OSError:
                size_str = "—"

            ext = p.suffix.lower().lstrip(".")
            self.files_map[p] = {
                "size": size_str,
                "format": ext.upper(),
                "status": "В очереди",
            }

            self.tree.insert(
                "",
                tk.END,
                iid=str(p),
                values=(p.name, size_str, ext.upper(), "В очереди", str(p.parent)),
            )

        self._update_counter()

    def _remove_selected(self):
        selected_items = self.tree.selection()
        for item_id in selected_items:
            path = Path(item_id)
            self.files_map.pop(path, None)
            self.tree.delete(item_id)
        self._update_counter()

    def _clear_all(self):
        if self.is_converting:
            return
        self.tree.delete(*self.tree.get_children())
        self.files_map.clear()
        self._update_counter()
        self.progress_bar["value"] = 0
        self.lbl_status.config(text="Список очищен.")
        self.btn_open_folder.config(state=tk.DISABLED)

    def _update_counter(self):
        count = len(self.files_map)
        self.lbl_count.config(text=f"Файлов: {count}")

    def _open_output_folder(self):
        folder_to_open = None
        if not self.same_folder_var.get() and self.dest_folder_var.get().strip():
            folder_to_open = self.dest_folder_var.get().strip()
        elif self.files_map:
            # Открываем папку первого файла в списке
            first_file = next(iter(self.files_map.keys()))
            folder_to_open = str(first_file.parent)

        if folder_to_open and os.path.exists(folder_to_open):
            if os.name == "nt":
                subprocess.Popen(["explorer", os.path.normpath(folder_to_open)])
            else:
                subprocess.Popen(["xdg-open", folder_to_open])

    def _set_ui_converting(self, converting: bool):
        self.is_converting = converting
        state = tk.DISABLED if converting else tk.NORMAL
        self.btn_convert.config(state=state)
        self.cb_format.config(state=state if not converting else tk.DISABLED)
        self.chk_same_folder.config(state=state)
        if not self.same_folder_var.get():
            self.entry_dest.config(state=state)
            self.btn_browse_dest.config(state=state)

    def _start_conversion(self):
        if not self.files_map:
            messagebox.showwarning("Внимание", "Список файлов пуст. Добавьте файлы для конвертации.")
            return

        target_format = self.target_format_var.get().strip().lower()
        if not target_format:
            messagebox.showwarning("Внимание", "Выберите целевой формат для конвертации.")
            return

        custom_dir: Optional[Path] = None
        if not self.same_folder_var.get():
            dest_str = self.dest_folder_var.get().strip()
            if not dest_str:
                messagebox.showwarning("Внимание", "Укажите папку для сохранения или включите сохранение в папку оригинала.")
                return
            custom_dir = Path(dest_str)
            try:
                custom_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать папку сохранения: {e}")
                return

        self._set_ui_converting(True)
        self.btn_open_folder.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.progress_bar["maximum"] = len(self.files_map)

        # Сбрасываем статусы в UI
        for p in self.files_map:
            if self.tree.exists(str(p)):
                self.tree.set(str(p), column="status", value="Ожидание...")

        files_to_convert = list(self.files_map.keys())

        # Запускаем конвертацию в фоновом потоке
        worker = threading.Thread(
            target=self._conversion_worker,
            args=(files_to_convert, target_format, custom_dir),
            daemon=True,
        )
        worker.start()

    def _conversion_worker(
        self,
        files: list[Path],
        target_format: str,
        output_dir: Optional[Path],
    ):
        success_count = 0
        error_count = 0
        total = len(files)

        for index, file_path in enumerate(files, start=1):
            result: ConversionResult = self.manager.convert_file(
                source_path=file_path,
                target_format=target_format,
                output_dir=output_dir,
            )

            if result.success:
                success_count += 1
                status_text = "✓ Успешно"
            else:
                error_count += 1
                status_text = f"✗ Ошибка: {result.error_message}"

            # Обновление UI через root.after (потокобезопасно)
            self.root.after(
                0,
                self._update_progress,
                index,
                total,
                str(file_path),
                status_text,
                result.success,
            )

        self.root.after(0, self._conversion_finished, success_count, error_count, total)

    def _update_progress(
        self,
        current: int,
        total: int,
        file_id: str,
        status_text: str,
        success: bool,
    ):
        self.progress_bar["value"] = current
        self.lbl_status.config(text=f"Обработка {current} из {total}...")
        if self.tree.exists(file_id):
            self.tree.set(file_id, column="status", value=status_text)
            self.tree.see(file_id)

    def _conversion_finished(self, success_count: int, error_count: int, total: int):
        self._set_ui_converting(False)
        self.btn_open_folder.config(state=tk.NORMAL)

        if error_count == 0:
            msg = f"Готово! Успешно сконвертировано файлов: {success_count} из {total}."
            self.lbl_status.config(text=msg)
            messagebox.showinfo("Завершено", msg)
        else:
            msg = f"Конвертация завершена с замечаниями.\nУспешно: {success_count}, с ошибками: {error_count}."
            self.lbl_status.config(text=msg)
            messagebox.showwarning("Завершено с ошибками", msg)
