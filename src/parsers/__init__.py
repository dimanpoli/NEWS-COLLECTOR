"""
Пакет парсеров.
Экспортирует все доступные парсеры.
"""

from parsers.base_parser import BaseParser
from parsers.ria_parser import RiaParser

# Список всех доступных парсеров
AVAILABLE_PARSERS = {
    'ria': RiaParser,
    # Здесь будут добавляться новые парсеры
    # 'telegram': TelegramParser,
}

__all__ = ['BaseParser', 'RiaParser', 'AVAILABLE_PARSERS']