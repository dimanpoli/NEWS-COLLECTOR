"""
Точка входа микросервиса сбора новостей.
Запускает периодический сбор новостей.
"""

import sys
import os

# Добавляем /app в путь Python
sys.path.insert(0, '/app')

# # Добавляем текущую директорию (/app) в путь Python
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Теперь импорты будут искать модули в /app
from database.db_manager import DatabaseManager
from services.news_collector import NewsCollector

import time
import logging
import signal
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/news_collector.log')
    ]
)
logger = logging.getLogger(__name__)

class NewsCollectorService:
    """Микросервис для периодического сбора новостей"""
    
    def __init__(self, interval_hours: float = 1.0):
        self.interval_hours = interval_hours
        self.is_running = True
        
        # Инициализация компонентов
        self.db_manager = DatabaseManager()
        self.news_collector = NewsCollector(self.db_manager)
        
        # Настройка обработчиков сигналов
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        logger.info(f"📩 Получен сигнал {signum}. Останавливаю сервис...")
        self.is_running = False
    
    def run_single_collection(self):
        """Выполняет однократный сбор новостей"""
        try:
            logger.info("🚀 Запуск сбора новостей")
            start_time = datetime.now()
            
            # Сбор из всех источников
            results = self.news_collector.collect_from_all_sources()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Сбор завершен за {elapsed:.2f} секунд")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка при сборе новостей: {e}")
            return {}
    
    def run_periodically(self):
        """Запускает бесконечный цикл периодического сбора"""
        logger.info(f"⏰ Запуск периодического сбора каждые {self.interval_hours} часов")
        logger.info("🛑 Для остановки нажмите Ctrl+C")
        
        try:
            while self.is_running:
                self.run_single_collection()
                
                if self.is_running:
                    logger.info(f"⏳ Ожидание {self.interval_hours} часов до следующего сбора...")
                    
                    interval_seconds = int(self.interval_hours * 3600)
                    for _ in range(interval_seconds):
                        if not self.is_running:
                            break
                        time.sleep(1)
                        
        except KeyboardInterrupt:
            logger.info("🛑 Остановка по команде пользователя")
        except Exception as e:
            logger.error(f"💥 Критическая ошибка в сервисе: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Корректное завершение работы сервиса"""
        logger.info("👋 Завершение работы микросервиса...")
        self.db_manager.close()
        logger.info("✅ Микросервис остановлен корректно")

def main():
    """Основная функция запуска микросервиса"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Микросервис сбора новостей')
    parser.add_argument('--interval', type=float, default=1.0,
                       help='Интервал между сборами в часах (по умолчанию: 1.0)')
    parser.add_argument('--once', action='store_true',
                       help='Запустить однократный сбор и выйти')
    
    args = parser.parse_args()
    
    service = NewsCollectorService(interval_hours=args.interval)
    
    if args.once:
        service.run_single_collection()
    else:
        service.run_periodically()

if __name__ == "__main__":
    main()