# Используйте официальный Python образ из Docker Hub
FROM python:3.10-slim

# Установите необходимые зависимости
RUN apt-get update && apt-get install -y gcc libpq-dev postgresql-client

# Создайте рабочую директорию
WORKDIR /app

# Скопируйте файлы зависимостей
COPY requirements.txt .

# Установите зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопируйте все файлы приложения в контейнер
COPY . .
COPY ./html /usr/share/nginx/html

# Запустите Uvicorn сервер
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]