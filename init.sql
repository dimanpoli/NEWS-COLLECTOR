-- Инициализационные скрипты для PostgreSQL
-- Выполняются при первом запуске контейнера

-- Создаем расширение для работы с UUID (если понадобится)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Комментарии к таблицам
COMMENT ON TABLE news IS 'Сырые новости из различных источников';
COMMENT ON TABLE news_analysis IS 'Анализ новостей от Mistral AI';
COMMENT ON TABLE telegram_feedback IS 'Обратная связь из Telegram канала';

-- Дополнительные индексы для производительности
CREATE INDEX IF NOT EXISTS idx_news_source_published 
ON news(source, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_news_analysis_sentiment 
ON news_analysis(sentiment);

CREATE INDEX IF NOT EXISTS idx_news_analysis_topic 
ON news_analysis(topic);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at в news_analysis
DROP TRIGGER IF EXISTS update_news_analysis_updated_at ON news_analysis;
CREATE TRIGGER update_news_analysis_updated_at
    BEFORE UPDATE ON news_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();