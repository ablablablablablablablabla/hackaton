from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import sys
import os
import signal
import time
import requests
from typing import List
import httpx
from pyngrok import ngrok

# Создание главного приложения
app = FastAPI(
    title="Ski Resort Unified API",
    description="Объединенный API для горнолыжного комплекса",
    version="1.0.0"
)

# Глобальные переменные
parser_processes: List[subprocess.Popen] = []
ngrok_tunnels = {}

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В случае с ngrok разрешаем все источники
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_ngrok_tunnel(port: int) -> str:
    """Создает ngrok туннель для указанного порта"""
    tunnel = ngrok.connect(port)
    return tunnel.public_url


def check_service(url: str, retries: int = 5) -> bool:
    """Проверяет доступность сервиса"""
    for _ in range(retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def start_parsers():
    # Конфигурация парсеров
    parsers = {
        "restaurant": ("restaurant_parser_api.py", 8001),
        "lift": ("lift_schedule_api.py", 8002),
        "weather": ("wether.py", 8003),
        "ecoTracs": ("ecoTracs.py", 8004),
        "winter": ("winter.py", 8005)
    }

    # Запуск парсеров и создание туннелей
    for name, (script, port) in parsers.items():
        # Запуск парсера
        process = subprocess.Popen([
            sys.executable,
            script
        ])
        parser_processes.append(process)

        # Создание туннеля
        tunnel_url = create_ngrok_tunnel(port)
        ngrok_tunnels[name] = tunnel_url
        print(f"Сервис {name} доступен по адресу: {tunnel_url}")

        # Проверка доступности
        if not check_service(f"http://localhost:{port}/docs"):
            print(f"Ошибка: Сервис {name} не запустился")
            stop_parsers()
            sys.exit(1)

    print("Все сервисы успешно запущены")


def stop_parsers():
    """Останавливает все парсеры и закрывает туннели"""
    # Остановка процессов
    for process in parser_processes:
        try:
            if sys.platform == 'win32':
                process.terminate()
            else:
                os.kill(process.pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            continue
    parser_processes.clear()

    # Закрытие туннелей
    ngrok.kill()


@app.on_event("startup")
async def startup_event():
    start_parsers()


@app.on_event("shutdown")
async def shutdown_event():
    stop_parsers()


# Прокси-эндпоинты с использованием туннелей
@app.get("/restaurant/")
async def proxy_restaurant():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ngrok_tunnels['restaurant']}/")
        return response.json()


@app.get("/lifts/")
async def proxy_lifts():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ngrok_tunnels['lift']}/")
        return response.json()


@app.get("/weather/")
async def proxy_weather():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ngrok_tunnels['weather']}/")
        return response.json()


@app.get("/ecoTracs/")
async def proxy_ecotracs():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ngrok_tunnels['ecoTracs']}/")
        return response.json()


@app.get("/winter/")
async def proxy_winter():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ngrok_tunnels['winter']}/")
        return response.json()


@app.get("/tunnels")
async def get_tunnels():
    """Возвращает список всех активных туннелей"""
    return ngrok_tunnels


@app.get("/")
async def root():
    return {
        "message": "Главный API работает",
        "tunnels": ngrok_tunnels
    }


if __name__ == "__main__":
    import uvicorn
    import nest_asyncio

    # Установка токена ngrok (необходимо заменить на ваш токен)
    ngrok.set_auth_token("2qYgcjvyyeBTvqA9X70YkyKSRAj_7i7fYJMqRQB3ydeSzuGFJ")

    nest_asyncio.apply()

    try:
        # Создаем туннель для основного API
        main_tunnel = create_ngrok_tunnel(8000)
        print(f"Основной API доступен по адресу: {main_tunnel}")

        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        stop_parsers()
    except Exception as e:
        print(f"Ошибка при запуске сервера: {e}")
        stop_parsers()