# Микросервис сбора новостей

Микросервис для сбора новостей из различных источников и сохранения в PostgreSQL.

## Архитектура
```
src/
├── database/ # Работа с БД
│ └── db_manager.py
├── models/ # Модели данных (DTO)
│ └── news_item.py
├── parsers/ # Парсеры новостей
│ ├── init.py
│ ├── base_parser.py
│ └── ria_parser.py
├── services/ # Сервисные классы
│ └── news_collector.py
└── main.py # Точка входа
```

## Установка

1. Установите Docker и Docker Compose
2. Склонируйте репозиторий
3. Создайте файл `.env` (см. `.env.example`)
4. Запустите PostgreSQL:
```bash
docker-compose up -d
```
5. Установите зависимости Python:
```bash
pip install -r requirements.txt
```

# Использование
```bash
# Однократный запуск:
python src/main.py --once

# Периодический сбор (каждый час):
python src/main.py --interval 1.0

# Сбор с кастомным интервалом (каждые 2 часа):
python src/main.py --interval 2.0
```