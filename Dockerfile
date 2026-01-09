FROM python:3.11-slim

WORKDIR /app
RUN mkdir -p /app/logs
# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src/ /app/

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1

# Команда запуска
CMD ["python", "main.py", "--interval", "0.5"]