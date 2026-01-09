"""
Модели данных (DTO) для новостей.
Используется для типизации данных между компонентами.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class NewsItem:
    """Модель новости"""
    source: str
    link: str
    title: Optional[str] = None
    text: str = ""
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь для сохранения в БД"""
        return {
            'source': self.source,
            'link': self.link,
            'title': self.title or '',
            'text': self.text,
            'published_at': self.published_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NewsItem':
        """Создает объект из словаря (например, из БД)"""
        return cls(
            source=data.get('source', ''),
            link=data.get('link', ''),
            title=data.get('title'),
            text=data.get('text', ''),
            published_at=data.get('published_at'),
            created_at=data.get('created_at')
        )


@dataclass
class NewsAnalysis:
    """Модель анализа новости"""
    news_id: int
    analysis: str
    topic: str
    sentiment: int
    corrected_analysis: Optional[str] = None
    corrected_sentiment: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            'news_id': self.news_id,
            'analysis': self.analysis,
            'topic': self.topic,
            'sentiment': self.sentiment,
            'corrected_analysis': self.corrected_analysis,
            'corrected_sentiment': self.corrected_sentiment
        }