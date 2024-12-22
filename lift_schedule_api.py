from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
import requests
from dataclasses import dataclass
from typing import List, Dict
import re
from pydantic import BaseModel
import uvicorn


# Модели данных
class Schedule(BaseModel):
    workdays: str | None = None
    saturday: str | None = None
    sunday: str | None = None


class LiftResponse(BaseModel):
    name: str
    schedule: Schedule


@dataclass
class LiftInfo:
    name: str
    schedule: dict


# Инициализация приложения
app = FastAPI(
    title="Ski Lift Schedule API",
    description="API для получения расписания работы подъемников",
    version="1.0.0"
)

def extract_schedule(rows, lift_name) -> dict:
    """Извлекает расписание из строк таблицы"""
    schedule = {}

    for row in rows:
        text = row.get_text(strip=True)
        if 'Понедельник-пятница' in text:
            time = re.search(r'с (\d+:\d+) до (\d+:\d+)', text)
            if time:
                schedule['workdays'] = f"{time.group(1)}-{time.group(2)}"
        elif 'Суббота и воскресенье' in text:
            time = re.search(r'с (\d+:\d+) до (\d+:\d+)', text)
            if time:
                # Переносим время выходных на субботу и воскресенье
                weekend_time = f"{time.group(1)}-{time.group(2)}"
                schedule['saturday'] = weekend_time
                schedule['sunday'] = weekend_time
        elif 'Суббота:' in text:
            time = re.search(r'с (\d+:\d+) до (\d+:\d+)', text)
            if time:
                schedule['saturday'] = f"{time.group(1)}-{time.group(2)}"
        elif 'Воскресенье:' in text:
            time = re.search(r'с (\d+:\d+) до (\d+:\d+)', text)
            if time:
                schedule['sunday'] = f"{time.group(1)}-{time.group(2)}"

    # Особая обработка для "Запад низ" и "Запад верх"
    if 'Запад' in lift_name:
        if 'sunday' not in schedule:
            schedule['sunday'] = '09:00-21:00'
        if 'saturday' not in schedule:
            schedule['saturday'] = '09:00-22:00'

    return schedule


def parse_html(html_content: str) -> List[LiftInfo]:
    """Парсит HTML и возвращает информацию о подъемниках"""
    soup = BeautifulSoup(html_content, 'html.parser')
    lifts = []

    tables = soup.find_all('table')
    for table in tables:
        caption = table.find('caption')
        if not caption:
            continue

        name = caption.find('p').text.strip()
        rows = table.find_all('tr')
        schedule = extract_schedule(rows, name)

        lift_info = LiftInfo(
            name=name,
            schedule=schedule
        )
        lifts.append(lift_info)

    return lifts


async def fetch_lifts() -> List[LiftInfo]:
    """Получает данные о подъемниках с сайта"""
    URL = "https://ski-gv.ru/about-us/schedule/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
        return parse_html(response.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Ошибка при получении данных: {str(e)}")


@app.get("/", response_model=List[LiftResponse])
async def get_all_lifts():
    """
    Получить расписание всех подъемников
    """
    lifts = await fetch_lifts()
    return [LiftResponse(name=lift.name, schedule=Schedule(**lift.schedule)) for lift in lifts]


@app.get("/lifts/{lift_name}", response_model=LiftResponse)
async def get_lift_by_name(lift_name: str):
    """
    Получить расписание конкретного подъемника по имени
    """
    lifts = await fetch_lifts()
    for lift in lifts:
        if lift.name.lower() == lift_name.lower():
            return LiftResponse(name=lift.name, schedule=Schedule(**lift.schedule))
    raise HTTPException(status_code=404, detail="Подъемник не найден")


if __name__ == "__main__":
    import asyncio

    # Для запуска без uvicorn можно использовать hypercorn
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:8002"]

    asyncio.run(hypercorn.asyncio.serve(app, config))

if __name__ == "__main__":

    try:
        uvicorn.run(app, host="0.0.0.0", port=8002)
    except Exception as e:
        print(f"Ошибка запуска парсера подъемников: {e}")
