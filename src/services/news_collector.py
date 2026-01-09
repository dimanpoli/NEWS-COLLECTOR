"""
Сервис-оркестратор для сбора новостей.
"""

import logging
from typing import Dict, Type

# Импорты из корня /app (благодаря sys.path в main.py)
from database.db_manager import DatabaseManager
from parsers import AVAILABLE_PARSERS
from models.news_item import NewsItem

logger = logging.getLogger(__name__)

class NewsCollector:
    """Сервис для сбора новостей из различных источников."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.parsers = self._initialize_parsers()
        
    def _initialize_parsers(self) -> Dict[str, Type]:
        """Инициализирует все доступные парсеры"""
        initialized_parsers = {}
        
        for parser_name, parser_class in AVAILABLE_PARSERS.items():
            try:
                parser_instance = parser_class()
                initialized_parsers[parser_name] = parser_instance
                logger.info(f"✅ Парсер '{parser_name}' инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации парсера '{parser_name}': {e}")
        
        return initialized_parsers
    
    def collect_from_source(self, source_name: str) -> int:
        """Собирает новости из конкретного источника"""
        if source_name not in self.parsers:
            logger.error(f"❌ Парсер для источника '{source_name}' не найден")
            return 0
        
        parser = self.parsers[source_name]
        logger.info(f"🔄 Сбор новостей из источника: {source_name}")
        
        try:
            news_items = parser.parse_last_hour()
            
            if not news_items:
                logger.info(f"📭 Новых новостей из {source_name} не найдено")
                return 0
            
            news_dicts = [item.to_dict() for item in news_items]
            saved_count = self.db_manager.save_news(news_dicts)
            
            logger.info(f"✅ Из {source_name} сохранено {saved_count} новостей")
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка сбора новостей из {source_name}: {e}")
            return 0
    
    def collect_from_all_sources(self) -> Dict[str, int]:
        """Собирает новости из всех доступных источников"""
        results = {}
        
        for source_name in self.parsers.keys():
            collected = self.collect_from_source(source_name)
            results[source_name] = collected
        
        total = sum(results.values())
        logger.info(f"📈 Всего собрано новостей: {total}")
        
        return results