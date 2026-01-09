.PHONY: help build up down logs ps restart clean db-shell collector-shell

# Цвета для вывода
GREEN := \033[0;32m
NC := \033[0m

help: ## Показать эту справку
	@echo "Использование:"
	@echo "  make [цель]"
	@echo ""
	@echo "Цели:"
	@awk -F ':|##' '/^[^\t].+?:.*?##/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$NF}' $(MAKEFILE_LIST)

build: ## Собрать Docker образы
	@echo "$(GREEN)Сборка Docker образов...$(NC)"
	docker-compose build

up: ## Запустить все сервисы в фоновом режиме
	@echo "$(GREEN)Запуск микросервисов...$(NC)"
	docker-compose up -d

down: ## Остановить все сервисы
	@echo "$(GREEN)Остановка микросервисов...$(NC)"
	docker-compose down

logs: ## Показать логи всех сервисов
	@echo "$(GREEN)Логи сервисов:$(NC)"
	docker-compose logs -f

logs-collector: ## Показать логи сборщика новостей
	@echo "$(GREEN)Логи сборщика новостей:$(NC)"
	docker-compose logs -f news-collector

logs-db: ## Показать логи базы данных
	@echo "$(GREEN)Логи базы данных:$(NC)"
	docker-compose logs -f postgres

ps: ## Показать статус контейнеров
	@echo "$(GREEN)Статус контейнеров:$(NC)"
	docker-compose ps

restart: ## Перезапустить все сервисы
	@echo "$(GREEN)Перезапуск сервисов...$(NC)"
	docker-compose restart

clean: ## Остановить сервисы и удалить тома
	@echo "$(GREEN)Очистка...$(NC)"
	docker-compose down -v

db-shell: ## Подключиться к оболочке PostgreSQL
	@echo "$(GREEN)Подключение к оболочке PostgreSQL...$(NC)"
	docker-compose exec postgres psql -U postgres -d news_sentiment

collector-shell: ## Подключиться к оболочке контейнера сборщика
	@echo "$(GREEN)Подключение к оболочке сборщика новостей...$(NC)"
	docker-compose exec news-collector /bin/bash

test-connection: ## Проверить подключение к БД
	@echo "$(GREEN)Проверка подключения к БД...$(NC)"
	docker-compose exec news-collector python -c "
import sys
sys.path.append('/app/src')
from database.db_manager import DatabaseManager
db = DatabaseManager()
print('✅ Подключение к БД успешно')
db.close()
"

stats: ## Показать статистику по новостям в БД
	@echo "$(GREEN)Статистика по новостям:$(NC)"
	docker-compose exec postgres psql -U postgres -d news_sentiment -c "
SELECT 
    source,
    COUNT(*) as total,
    COUNT(CASE WHEN is_processed THEN 1 END) as processed,
    COUNT(CASE WHEN NOT is_processed THEN 1 END) as pending,
    MIN(published_at) as oldest,
    MAX(published_at) as newest
FROM news 
GROUP BY source
ORDER BY total DESC;
"