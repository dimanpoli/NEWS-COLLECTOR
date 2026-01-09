"""
Парсер новостей с сайта RIA.ru (раздел экономики)
"""

import time
import logging
import random
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup as BS
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from parsers.base_parser import BaseParser
from models.news_item import NewsItem

logger = logging.getLogger(__name__)


class RiaParser(BaseParser):
    """Парсер новостей с RIA.ru"""
    
    def __init__(self):
        """Инициализация парсера RIA"""
        super().__init__(source_name="ria")
        self.base_url = "https://ria.ru/economy/"
        
        # Настраиваем HTTP-сессию с ретраями и таймаутами
        self.session = requests.Session()
        
        # Настраиваем ретраи для обработки временных ошибок
        retry_strategy = Retry(
            total=3,  # Количество попыток
            backoff_factor=1,  # Задержка между попытками
            status_forcelist=[429, 500, 502, 503, 504],  # Коды ошибок для ретрая
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # Более реалистичные заголовки браузера
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Referer': 'https://www.google.com/',
        })
        
        # Добавляем куки для имитации реального пользователя
        self.session.cookies.update({
            'acceptCookies': 'true',
            'cookieConsent': '1',
        })
    
    def parse_last_hour(self) -> List[NewsItem]:
        """
        Парсит новости с RIA.ru за последний час
        """
        try:
            logger.info("🚀 Начинаем парсинг новостей с RIA.ru")
            
            # Получаем HTML главной страницы
            html_content = self._fetch_page_with_retry(self.base_url)
            if not html_content:
                logger.error("❌ Не удалось получить главную страницу RIA.ru")
                return []
            
            # Извлекаем ссылки на новости
            news_links = self._extract_news_links(html_content)
            logger.info(f"🔗 Найдено {len(news_links)} ссылок на новости")
            
            if not news_links:
                logger.warning("⚠️ Не найдено ссылок на новости")
                return []
            
            # Парсим каждую новость (ограничиваем количество для скорости)
            news_items = []
            max_news_to_parse = 10  # Парсим только 10 новостей за раз
            
            for i, link in enumerate(news_links[:max_news_to_parse]):
                try:
                    logger.debug(f"📰 Парсинг новости {i+1}/{min(len(news_links), max_news_to_parse)}: {link}")
                    
                    news_item = self._parse_news_page(link)
                    if news_item:
                        news_items.append(news_item)
                        logger.info(f"✅ Добавлена новость: {news_item.title[:60]}...")
                    
                    # Случайная пауза между запросами (1-3 секунды)
                    time.sleep(random.uniform(1.0, 3.0))
                    
                except Exception as e:
                    logger.error(f"⚠️ Ошибка парсинга новости {link}: {e}")
                    continue
            
            # Фильтруем новости за последний час
            filtered_items = self.filter_by_time(news_items, hours_back=1)
            
            logger.info(f"📊 Парсинг завершен. Найдено {len(filtered_items)} новостей за последний час")
            return filtered_items
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка парсинга RIA: {e}")
            return []
    
    def _fetch_page_with_retry(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Загружает HTML-страницу с повторными попытками"""
        for attempt in range(max_retries):
            try:
                # Случайная задержка перед запросом
                time.sleep(random.uniform(0.5, 1.5))
                
                # Делаем запрос с таймаутом
                response = self.session.get(
                    url, 
                    timeout=(10, 30),  # 10 сек на подключение, 30 сек на чтение
                    allow_redirects=True,
                    verify=True  # Включаем проверку SSL
                )
                
                response.raise_for_status()
                
                # Проверяем, что получили HTML, а не страницу с капчей
                if any(x in response.text.lower() for x in ['captcha', 'робот', 'bot', 'доступ ограничен']):
                    logger.warning(f"⚠️ Возможно, страница содержит капчу: {url}")
                    if attempt < max_retries - 1:
                        time.sleep(5)  # Ждем подольше перед повторной попыткой
                        continue
                
                # Проверяем кодировку
                response.encoding = response.apparent_encoding or 'utf-8'
                
                return response.text
                
            except requests.exceptions.SSLError as e:
                logger.warning(f"⚠️ SSL ошибка для {url}, попытка {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Экспоненциальная задержка
                    continue
                    
            except requests.exceptions.Timeout as e:
                logger.warning(f"⚠️ Таймаут для {url}, попытка {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"⚠️ Ошибка соединения для {url}, попытка {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                    
            except requests.exceptions.HTTPError as e:
                logger.error(f"❌ HTTP ошибка {e.response.status_code} для {url}: {e}")
                return None
                
            except Exception as e:
                logger.error(f"❌ Неизвестная ошибка для {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        
        logger.error(f"❌ Не удалось загрузить страницу {url} после {max_retries} попыток")
        return None
    
    def _extract_news_links(self, html: str) -> List[str]:
        """Извлекает ссылки на новости из HTML"""
        soup = BS(html, 'html.parser')
        links = []
        
        # Ищем ссылки на новости экономики
        # Актуальные селекторы для RIA.ru
        selectors = [
            "a[href*='/economy/']",  # Ссылки в разделе экономики
            "a[href*='/20'][href*='.html']",  # Ссылки с датами
            "div.list-item__content a.list-item__title",  # Основные новости
            "a.cell-list__item-link[href*='/20']",  # Альтернативный селектор
            "article a[href*='/20']",  # Новости в статьях
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    href = elem.get('href', '')
                    if href and href.startswith('https://ria.ru/'):
                        # Убираем якоря и параметры
                        href = href.split('#')[0].split('?')[0]
                        if href not in links:
                            links.append(href)
            except Exception as e:
                logger.debug(f"⚠️ Ошибка при поиске селектором {selector}: {e}")
                continue
        
        # Удаляем дубликаты и ограничиваем количество
        unique_links = list(set(links))
        return unique_links[:20]  # Ограничиваем 20 ссылками
    
    def _parse_news_page(self, url: str) -> Optional[NewsItem]:
        """
        Парсит страницу отдельной новости
        """
        try:
            html = self._fetch_page_with_retry(url)
            if not html:
                return None
            
            soup = BS(html, 'html.parser')
            
            # Извлекаем заголовок
            title = self._extract_title(soup)
            if not title:
                logger.warning(f"⚠️ Не найден заголовок для {url}")
                return None
            
            # Извлекаем дату публикации
            published_at = self._extract_date(soup)
            
            # Извлекаем текст новости
            text = self._extract_text(soup)
            
            # Проверяем что текст не пустой
            if not text or len(text.strip()) < 100:
                logger.debug(f"⚠️ Слишком короткий текст для {url}")
                return None
            
            # Создаем объект новости
            news_item = NewsItem(
                source=self.source_name,
                link=url,
                title=title,
                text=text,
                published_at=published_at
            )
            
            return news_item
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга страницы {url}: {e}")
            return None
    
    def _extract_title(self, soup: BS) -> str:
        """Извлекает заголовок новости"""
        # Пробуем различные селекторы для заголовка
        title_selectors = [
            "h1.article__title",
            "h1.m-article__title",
            "meta[property='og:title']",
            "meta[name='title']",
            "title",
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if selector.startswith("meta"):
                        title = element.get('content', '').strip()
                    else:
                        title = element.get_text(strip=True)
                    
                    if title and len(title) > 5:
                        return title
            except:
                continue
        
        return ""
    
    def _extract_date(self, soup: BS) -> Optional[datetime]:
        """Извлекает и парсит дату публикации"""
        # Пробуем различные селекторы для даты
        date_selectors = [
            "meta[property='article:published_time']",
            "meta[name='published_time']",
            "div.article__info-date a",
            "time.article__date",
            "div.article__date",
            "meta[itemprop='datePublished']",
        ]
        
        date_str = ""
        for selector in date_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if selector.startswith("meta"):
                        date_str = element.get('content', '')
                    else:
                        date_str = element.get_text(strip=True)
                    
                    if date_str:
                        break
            except:
                continue
        
        # Парсим дату из строки
        return self._parse_date_string(date_str)
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Парсит строку с датой в объект datetime"""
        if not date_str:
            return None
        
        # Убираем лишние символы
        date_str = date_str.replace('T', ' ').replace('Z', '').strip()
        
        # Список возможных форматов дат на RIA
        date_formats = [
            "%Y-%m-%d %H:%M:%S",        # 2024-01-15 14:30:00
            "%Y-%m-%d %H:%M",           # 2024-01-15 14:30
            "%d.%m.%Y %H:%M",           # 15.01.2024 14:30
            "%Y-%m-%dT%H:%M:%S%z",      # 2024-01-15T14:30:00+0300
            "%H:%M %d.%m.%Y",           # 14:30 15.01.2024
            "%d %B %Y, %H:%M",          # 15 января 2024, 14:30
        ]
        
        for date_format in date_formats:
            try:
                return datetime.strptime(date_str, date_format)
            except ValueError:
                continue
        
        logger.debug(f"⚠️ Не удалось распарсить дату: {date_str}")
        # Если не удалось распарсить, возвращаем текущее время минус 1 час
        return datetime.now()
    
    def _extract_text(self, soup: BS) -> str:
        """Извлекает основной текст новости"""
        # Основной селектор для текста новости на RIA
        text_selectors = [
            "div.article__text",
            "div.article__body",
            "div.article-content",
            "article",
            "div[itemprop='articleBody']",
        ]
        
        for selector in text_selectors:
            try:
                article_body = soup.select_one(selector)
                if article_body:
                    # Удаляем ненужные элементы (реклама, ссылки и т.д.)
                    for unwanted in article_body.select("script, style, iframe, .banner, .ad, .social"):
                        unwanted.decompose()
                    
                    # Собираем текст из параграфов
                    paragraphs = article_body.find_all(['p', 'h2', 'h3', 'h4'])
                    texts = []
                    
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:  # Игнорируем короткие параграфы
                            texts.append(text)
                    
                    if texts:
                        return '\n'.join(texts)
            except:
                continue
        
        # Если не нашли структурированный текст, пробуем собрать со всей страницы
        try:
            all_paragraphs = soup.find_all('p')
            texts = [p.get_text(strip=True) for p in all_paragraphs 
                    if len(p.get_text(strip=True)) > 50]
            
            if texts:
                # Берем первые 15 параграфов
                return '\n'.join(texts[:15])
        except:
            pass
        
        return ""