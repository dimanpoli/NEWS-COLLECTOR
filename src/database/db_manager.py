"""
Модуль для управления подключением к PostgreSQL и операциями с БД.
Это общий модуль, который будут использовать все парсеры.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Класс для управления подключением к базе данных"""
    
    _instance = None
    
    def __new__(cls):
        """Реализация Singleton для единого подключения к БД"""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Инициализация подключения"""
        self.conn = None
        self.connect()
    
    def connect(self):
        """Устанавливает соединение с PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'news_sentiment'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
            logger.info("✅ Успешное подключение к PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def get_connection(self):
        """Возвращает активное соединение с БД"""
        if self.conn is None or self.conn.closed:
            self.connect()
        return self.conn
    
    def close(self):
        """Закрывает соединение с БД"""
        if self.conn:
            self.conn.close()
            logger.info("🔌 Соединение с PostgreSQL закрыто")


class DatabaseManager:
    """Основной класс для работы с базой данных"""
    
    def __init__(self):
        """Инициализация с подключением к БД"""
        self.db_connection = DatabaseConnection()
        self.create_tables()
    
    def create_tables(self):
        """Создает таблицы в БД если они не существуют"""
        create_table_query = """
        -- Таблица для хранения сырых новостей
        CREATE TABLE IF NOT EXISTS news (
            id SERIAL PRIMARY KEY,
            source VARCHAR(50) NOT NULL,
            link VARCHAR(500) UNIQUE NOT NULL,
            title TEXT,
            text TEXT NOT NULL,
            published_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_processed BOOLEAN DEFAULT FALSE
        );
        
        -- Таблица для хранения анализа новостей
        CREATE TABLE IF NOT EXISTS news_analysis (
            id SERIAL PRIMARY KEY,
            news_id INTEGER REFERENCES news(id) ON DELETE CASCADE,
            analysis TEXT,
            topic VARCHAR(100),
            sentiment INTEGER,
            corrected_analysis TEXT,
            corrected_sentiment INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица для обратной связи из Telegram
        CREATE TABLE IF NOT EXISTS telegram_feedback (
            id SERIAL PRIMARY KEY,
            news_id INTEGER REFERENCES news(id) ON DELETE CASCADE,
            reactions JSONB,
            comments TEXT[],
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Индексы для ускорения запросов
        CREATE INDEX IF NOT EXISTS idx_news_link ON news(link);
        CREATE INDEX IF NOT EXISTS idx_news_published_at ON news(published_at);
        CREATE INDEX IF NOT EXISTS idx_news_is_processed ON news(is_processed);
        CREATE INDEX IF NOT EXISTS idx_news_analysis_news_id ON news_analysis(news_id);
        CREATE INDEX IF NOT EXISTS idx_news_analysis_created_at ON news_analysis(created_at);
        """
        
        conn = self.db_connection.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(create_table_query)
                conn.commit()
                logger.info("✅ Таблицы и индексы успешно созданы/проверены")
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
            conn.rollback()
    
    def save_news(self, news_list: List[Dict]) -> int:
        """
        Сохраняет список новостей в таблицу news
        Возвращает количество сохраненных новостей
        """
        if not news_list:
            return 0
        
        insert_query = """
        INSERT INTO news (source, link, title, text, published_at, created_at)
        VALUES %s
        ON CONFLICT (link) DO NOTHING
        RETURNING id
        """
        
        # Подготавливаем данные для вставки
        news_data = []
        for news in news_list:
            news_data.append((
                news.get('source', 'unknown'),
                news['link'],
                news.get('title', ''),
                news['text'],
                news.get('published_at'),
                datetime.now()
            ))
        
        conn = self.db_connection.get_connection()
        try:
            with conn.cursor() as cursor:
                execute_values(cursor, insert_query, news_data)
                inserted_count = len(cursor.fetchall())
                conn.commit()
                logger.info(f"💾 Сохранено {inserted_count} новых новостей")
                return inserted_count
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения новостей: {e}")
            conn.rollback()
            return 0
    
    def get_unprocessed_news(self, limit: int = 10) -> List[Dict]:
        """
        Получает необработанные новости для анализа
        Возвращает список новостей
        """
        query = """
        SELECT id, source, link, title, text, published_at
        FROM news
        WHERE is_processed = FALSE
        ORDER BY published_at DESC
        LIMIT %s
        """
        
        conn = self.db_connection.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (limit,))
                result = cursor.fetchall()
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"❌ Ошибка получения необработанных новостей: {e}")
            return []
    
    def mark_as_processed(self, news_id: int):
        """Помечает новость как обработанную"""
        query = "UPDATE news SET is_processed = TRUE WHERE id = %s"
        
        conn = self.db_connection.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (news_id,))
                conn.commit()
                logger.debug(f"✅ Новость {news_id} помечена как обработанная")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса новости {news_id}: {e}")
            conn.rollback()
    
    def save_analysis(self, news_id: int, analysis: Dict) -> bool:
        """
        Сохраняет анализ новости в таблицу news_analysis
        Возвращает True если успешно, False если ошибка
        """
        insert_query = """
        INSERT INTO news_analysis 
        (news_id, analysis, topic, sentiment, created_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (news_id) DO UPDATE SET
            analysis = EXCLUDED.analysis,
            topic = EXCLUDED.topic,
            sentiment = EXCLUDED.sentiment,
            updated_at = CURRENT_TIMESTAMP
        """
        
        conn = self.db_connection.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(insert_query, (
                    news_id,
                    analysis.get('analysis', ''),
                    analysis.get('topic', ''),
                    analysis.get('sentiment', 0),
                    datetime.now()
                ))
                conn.commit()
                logger.info(f"📊 Анализ для новости {news_id} сохранен")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения анализа для новости {news_id}: {e}")
            conn.rollback()
            return False
    
    def close(self):
        """Закрывает соединение с БД"""
        self.db_connection.close()