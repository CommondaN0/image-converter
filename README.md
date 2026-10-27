# Universal Image Converter (WEBP to PNG & more)

Простое, модульное и расширяемое приложение на Python с графическим интерфейсом (GUI) для конвертации изображений (включая **WEBP → PNG**).

---

## 🚀 Особенности
- **Простой интерфейс**: добавление отдельных файлов или целых папок, таблица очереди, статус каждого файла.
- **Пакетная обработка**: конвертация сотен файлов за раз без зависания интерфейса (многопоточность).
- **Выбор папки**: сохранение рядом с оригинальным файлом либо в выбранную пользовательскую папку.
- **Легкая расширяемость**: модульная архитектура на основе паттернов Registry / Strategy. Новые форматы и кастомные конвертеры добавляются за пару строк кода.
- **Поддержка прозрачности**: корректная обработка RGBA/альфа-каналов при конвертации между форматами.

---

## 📂 Структура проекта

```text
Converter/
├── core/
│   ├── __init__.py
│   ├── base.py             # Базовый абстрактный класс BaseConverter и ConversionResult
│   ├── registry.py         # Менеджер реестра конвертеров (ConversionManager)
│   └── pillow_engine.py    # Реализация конвертера растровых изображений на Pillow
├── gui/
│   ├── __init__.py
│   └── app.py              # Tkinter/TTK графический интерфейс
├── main.py                 # Точка входа в приложение
├── requirements.txt        # Зависимости проекта (Pillow)
└── README.md               # Документация
```

---

## 🛠 Запуск

1. Убедитесь, что установлен Python 3.10+ и зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Запустите приложение:
   ```bash
   python main.py
   ```

---

## 🧩 Как расширять функционал

### 1. Добавление форматов в стандартный Pillow-конвертер
В файле [`core/pillow_engine.py`](core/pillow_engine.py) достаточно добавить расширение в `sources` и `targets` класса `PillowImageConverter`:
```python
# Например, добавить поддержку формата WebP, JPEG, PNG, BMP, TIFF, GIF, ICO, AVIF
FORMAT_MAP = {
    "png": "PNG",
    "webp": "WEBP",
    "jpg": "JPEG",
    "avif": "AVIF",
    ...
}
```

### 2. Создание нового кастомного конвертера
Если вам нужен специфический конвертер (например, векторный SVG через `cairosvg`, PDF-страницы через `pdf2image` или видео-конвертер через `ffmpeg`), просто унаследуйтесь от `BaseConverter`:

```python
from pathlib import Path
from core.base import BaseConverter, ConversionResult

class SvgToPngConverter(BaseConverter):
    @property
    def name(self) -> str:
        return "SVG to PNG Converter"

    def supported_source_formats(self) -> set[str]:
        return {"svg"}

    def supported_target_formats(self) -> set[str]:
        return {"png"}

    def convert(self, source_path: Path, target_path: Path, **options) -> ConversionResult:
        try:
            import cairosvg
            cairosvg.svg2png(url=str(source_path), write_to=str(target_path))
            return ConversionResult(success=True, source_path=source_path, target_path=target_path)
        except Exception as e:
            return ConversionResult(success=False, source_path=source_path, error_message=str(e))
```

И зарегистрируйте его в `ConversionManager` перед запуском интерфейса:
```python
manager = create_default_manager()
manager.register_converter(SvgToPngConverter())
app = ConverterApp(root, manager=manager)
```
После этого новые форматы автоматически появятся в выпадающем списке интерфейса и фильтрах выбора файлов!
