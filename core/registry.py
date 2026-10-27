from collections.abc import Callable
from pathlib import Path
from typing import Optional

from .base import BaseConverter, ConversionResult
from .pillow_engine import PillowImageConverter


class ConversionManager:
    """
    Менеджер реестра конвертеров.
    Отвечает за подбор подходящего конвертера и выполнение операций.
    Позволяет регистрировать новые кастомные конвертеры в будущем.
    """

    def __init__(self):
        self._converters: list[BaseConverter] = []

    def register_converter(self, converter: BaseConverter) -> None:
        """Зарегистрировать новый конвертер."""
        self._converters.append(converter)

    def find_converter(self, source_ext: str, target_ext: str) -> Optional[BaseConverter]:
        """Находит первый конвертер, поддерживающий данную пару форматов."""
        for conv in self._converters:
            if conv.can_convert(source_ext, target_ext):
                return conv
        return None

    def get_supported_target_formats(self, source_ext: Optional[str] = None) -> list[str]:
        """Возвращает список поддерживаемых целевых форматов (отсортированный)."""
        targets = set()
        for conv in self._converters:
            if source_ext is None:
                targets.update(conv.supported_target_formats())
            else:
                s = source_ext.lower().lstrip(".")
                if s in conv.supported_source_formats():
                    targets.update(conv.supported_target_formats())
        return sorted(targets)

    def get_supported_source_formats(self) -> list[str]:
        """Возвращает список всех поддерживаемых исходных расширений."""
        sources = set()
        for conv in self._converters:
            sources.update(conv.supported_source_formats())
        return sorted(sources)

    def convert_file(
        self,
        source_path: Path,
        target_format: str,
        output_dir: Optional[Path] = None,
        **options,
    ) -> ConversionResult:
        """
        Конвертирует один файл в указанный формат.
        :param source_path: Путь к исходному файлу.
        :param target_format: Расширение целевого формата (например 'png').
        :param output_dir: Папка для сохранения (если None, сохраняется рядом с оригиналом).
        :param options: Дополнительные параметры для конвертера.
        """
        source_path = Path(source_path)
        source_ext = source_path.suffix.lower().lstrip(".")
        target_ext = target_format.lower().lstrip(".")

        converter = self.find_converter(source_ext, target_ext)
        if not converter:
            return ConversionResult(
                success=False,
                source_path=source_path,
                error_message=f"Нет доступного конвертера из .{source_ext} в .{target_ext}",
            )

        destination_dir = Path(output_dir) if output_dir else source_path.parent
        target_path = destination_dir / f"{source_path.stem}.{target_ext}"

        # Предотвращаем перезапись того же файла, если формат совпадает и папка та же
        if source_path.resolve() == target_path.resolve():
            target_path = destination_dir / f"{source_path.stem}_converted.{target_ext}"

        return converter.convert(source_path, target_path, **options)

    def batch_convert(
        self,
        files: list[Path],
        target_format: str,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int, ConversionResult], None]] = None,
        **options,
    ) -> list[ConversionResult]:
        """
        Пакетная конвертация списка файлов.
        :param files: Список путей к файлам.
        :param target_format: Целевой формат (например 'png').
        :param output_dir: Папка для сохранения (если None, то рядом с каждым оригиналом).
        :param progress_callback: Функция обратного вызова (текущий_индекс, всего, результат).
        """
        results: list[ConversionResult] = []
        total = len(files)

        for index, file_path in enumerate(files, start=1):
            result = self.convert_file(file_path, target_format, output_dir=output_dir, **options)
            results.append(result)
            if progress_callback:
                progress_callback(index, total, result)

        return results


def create_default_manager() -> ConversionManager:
    """Создает менеджер с зарегистрированным стандартным Pillow конвертером."""
    manager = ConversionManager()
    manager.register_converter(PillowImageConverter())
    return manager
