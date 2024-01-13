# Инструкции к запуску.

## Установка + запуск (**_linux_**):

1. Клонирование репозитория

   ```git clone https://github.com/vnj64/software-engineer-fastapi.git```
2. Переход в директорию software-engineer-fastapi

   ```cd software-engineer-fastapi/```
3. Создание виртуального окружения:

    ```python3 -m venv venv```
4. Активация виртуального окружения:
    
    ```source venv/bin/activate```
5. Установка зависимостей:
    
    ```pip install -r requirements.txt```
6. Внести переменные окружения (_пример .env.dist_):

    ```nano .env```
8. Запуск контейнера базы данных:

    ```docker compose up --build```
