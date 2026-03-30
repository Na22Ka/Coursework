# Dockerfile — описывает как собрать Docker-образ бэкенда

# Базовый образ: Python 3.11 (лёгкий slim-вариант)
FROM python:3.11-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Сначала копируем только requirements.txt
# Docker кэширует этот слой — зависимости не переустанавливаются при каждой сборке
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Создаём папку для загрузок
RUN mkdir -p uploads/products uploads/categories

# Открываем порт
EXPOSE 8000

# Команда по умолчанию
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
