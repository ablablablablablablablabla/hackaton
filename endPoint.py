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

# Создание главного приложения
app = FastAPI(
    title="Ski Resort Unified API",
    description="Объединенный API для горнолыжного комплекса",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные переменные для хранения процессов
parser_processes: List[subprocess.Popen] = []


def check_service(url: str, retries: int = 5) -> bool:
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
    # Запускаем ресторанный парсер

    # Запускаем парсер подъемников
    lift_parser = subprocess.Popen([
        sys.executable,
        "lift_schedule_api.py"
    ])
    parser_processes.append(lift_parser)

    wether_parser = subprocess.Popen([
        sys.executable,
        "wether.py"
    ])
    parser_processes.append(wether_parser)

    ecoTracs_parser = subprocess.Popen([
        sys.executable,
        "ecoTracs.py"
    ])
    parser_processes.append(ecoTracs_parser)

    winter_parser = subprocess.Popen([
        sys.executable,
        "winter.py"
    ])
    parser_processes.append(winter_parser)

    restaurant_parser = subprocess.Popen([
        sys.executable,
        "restaurant_parser_api.py"
    ])
    parser_processes.append(restaurant_parser)


    # Проверяем доступность сервисов
    services = {
        "restaurant": "http://localhost:8001/docs",
        "lift": "http://localhost:8002/docs",
        "wether": "http://localhost:8003/docs",
        "ecoTracs": "http://localhost:8004/docs",
        "winter": "http://localhost:8005/docs"
    }

    for name, url in services.items():
        if not check_service(url):
            print(f"Ошибка: Сервис {name} не запустился")
            stop_parsers()
            sys.exit(1)

    print("Все сервисы успешно запущены")


def stop_parsers():
    for process in parser_processes:
        try:
            if sys.platform == 'win32':
                process.terminate()
            else:
                os.kill(process.pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            continue
    parser_processes.clear()


@app.on_event("startup")
async def startup_event():
    start_parsers()


@app.on_event("shutdown")
async def shutdown_event():
    stop_parsers()


# Добавляем прокси-эндпоинты для ресторанов
@app.get("/restaurant/")
async def proxy_lifts():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8001/")
        return response.json()


# Добавляем прокси-эндпоинты для подъемников
@app.get("/lifts/")
async def proxy_lifts():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8002/")
        return response.json()

@app.get("/wether/")
async def proxy_lifts():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8003/")
        return response.json()

@app.get("/ecoTracs/")
async def proxy_lifts():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8004/")
        return response.json()

@app.get("/winter/")
async def proxy_lifts():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8005/")
        return response.json()


@app.get("/")
async def root():
    return {"message": "Главный API работает"}


if __name__ == "__main__":
    import uvicorn
    import nest_asyncio

    nest_asyncio.apply()

    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        stop_parsers()
    except Exception as e:
        print(f"Ошибка при запуске сервера: {e}")
        stop_parsers()