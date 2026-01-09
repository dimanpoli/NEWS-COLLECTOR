"""
Базовый класс для всех парсеров.
Определяет интерфейс, который должен реализовать каждый парсер.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime, timedelta

from models.news_item import NewsItem

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Абстрактный базовый класс для парсеров новостей"""
    
    def __init__(self, source_name: str):
        """
        Инициализация парсера
        
        Args:
            source_name: Имя источника (ria, telegram и т.д.)
        """
        self.source_name = source_name
    
    @abstractmethod
    def parse_last_hour(self) -> List[NewsItem]:
        """
        Абстрактный метод для парсинга новостей за последний час.
        Должен быть реализован в каждом конкретном парсере.
        
        Returns:
            Список объектов NewsItem
        """
        pass
    
    def filter_by_time(self, news_items: List[NewsItem], 
                    hours_back: int = 1) -> List[NewsItem]:
        """
        Фильтрует новости по времени публикации
        """
        if not news_items:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        logger.info(f"📅 Фильтрация новостей. Отсечка времени: {cutoff_time}")
        
        filtered = []
        for item in news_items:
            if item.published_at:
                logger.info(f"📅 Новость: {item.title[:50]}... | Дата: {item.published_at} | {'✓' if item.published_at >= cutoff_time else '✗'}")
                if item.published_at >= cutoff_time:
                    filtered.append(item)
            else:
                logger.info(f"📅 Новость: {item.title[:50]}... | Дата: НЕТ ДАТЫ")
        
        logger.info(f"📅 Из {len(news_items)} новостей {len(filtered)} "
                f"за последние {hours_back} час(ов)")
        return filtered