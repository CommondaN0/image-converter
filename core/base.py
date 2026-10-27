from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ConversionResult:
    """Результат операции конвертации одного файла."""
    success: bool
    source_path: Path
    target_path: Optional[Path] = None
    error_message: Optional[str] = None


class BaseConverter(ABC):
    """
    Базовый интерфейс для конвертеров.
    Любой новый движок (Pillow, FFmpeg, Vector и др.) может реализовать этот класс
    и зарегистрироваться в системе.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Понятное имя конвертера/движка."""
        pass

    @abstractmethod
    def supported_source_formats(self) -> set[str]:
        """Множество поддерживаемых исходных расширений (в нижнем регистре, без точки)."""
        pass

    @abstractmethod
    def supported_target_formats(self) -> set[str]:
        """Множество поддерживаемых целевых расширений (в нижнем регистре, без точки)."""
        pass

    def can_convert(self, source_ext: str, target_ext: str) -> bool:
        """Проверяет, умеет ли конвертер переводить из source_ext в target_ext."""
        s = source_ext.lower().lstrip(".")
        t = target_ext.lower().lstrip(".")
        return s in self.supported_source_formats() and t in self.supported_target_formats()

    @abstractmethod
    def convert(self, source_path: Path, target_path: Path, **options) -> ConversionResult:
        """
        Выполняет конвертацию одного файла.
        :param source_path: Путь к исходному файлу.
        :param target_path: Путь к результирующему файлу.
        :param options: Дополнительные параметры (качество, сжатие и т.д.).
        :return: Объект ConversionResult.
        """
        pass
