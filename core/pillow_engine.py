from pathlib import Path
from PIL import Image

from .base import BaseConverter, ConversionResult


class PillowImageConverter(BaseConverter):
    """
    Конвертер растровых изображений на основе библиотеки Pillow.
    Поддерживает широкий спектр форматов и легко настраивается.
    """

    # Форматы, сопоставленные с форматами сохранения в Pillow
    FORMAT_MAP = {
        "png": "PNG",
        "webp": "WEBP",
        "jpg": "JPEG",
        "jpeg": "JPEG",
        "bmp": "BMP",
        "ico": "ICO",
        "tiff": "TIFF",
        "gif": "GIF",
    }

    def __init__(
        self,
        sources: tuple[str, ...] = ("webp", "png", "jpg", "jpeg", "bmp", "tiff"),
        targets: tuple[str, ...] = ("png", "webp", "jpg", "jpeg", "bmp", "ico", "tiff"),
    ):
        self._sources = {ext.lower().lstrip(".") for ext in sources}
        self._targets = {ext.lower().lstrip(".") for ext in targets}

    @property
    def name(self) -> str:
        return "Pillow Image Converter"

    def supported_source_formats(self) -> set[str]:
        return self._sources

    def supported_target_formats(self) -> set[str]:
        return self._targets

    def convert(self, source_path: Path, target_path: Path, **options) -> ConversionResult:
        try:
            source_path = Path(source_path)
            target_path = Path(target_path)

            if not source_path.exists():
                return ConversionResult(
                    success=False,
                    source_path=source_path,
                    error_message=f"Исходный файл не найден: {source_path}",
                )

            # Гарантируем наличие целевой папки
            target_path.parent.mkdir(parents=True, exist_ok=True)

            target_ext = target_path.suffix.lower().lstrip(".")
            pillow_format = self.FORMAT_MAP.get(target_ext, target_ext.upper())

            with Image.open(source_path) as img:
                # Если целевой формат не поддерживает альфа-канал (например JPEG),
                # аккуратно преобразуем RGBA в RGB с белым фоном
                if pillow_format in ("JPEG", "JPG") and img.mode in ("RGBA", "LA", "P"):
                    rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    mask = img.split()[-1] if len(img.split()) == 4 else None
                    rgb_img.paste(img, mask=mask)
                    rgb_img.save(target_path, format=pillow_format, **options)
                else:
                    img.save(target_path, format=pillow_format, **options)

            return ConversionResult(
                success=True,
                source_path=source_path,
                target_path=target_path,
            )

        except Exception as e:
            return ConversionResult(
                success=False,
                source_path=source_path,
                error_message=str(e),
            )
