import webbrowser

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from threading import Thread

app = FastAPI(
    title="Ski Track Parser API",
    description="API для получения информации о горнолыжных трассах",
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

# Модели данных
class TrackParam(BaseModel):
    length: Optional[str] = None
    time: Optional[str] = None
    height: Optional[str] = None
    lighting: Optional[str] = None
    snow: Optional[str] = None
    color: Optional[str] = None

class Track(BaseModel):
    name: str
    number: str
    params: TrackParam
    status: str
    updated_at: datetime

class Zone(BaseModel):
    name: str
    url: str
    tracks: List[Track]

# Конфигурация
BASE_URL = 'https://ski-gv.ru'

# Вспомогательные функции
def parse_track_params(params, number_elem) -> TrackParam:
    """Парсинг параметров трассы"""
    length = time = height = lighting = snow = color = None

    if number_elem and 'class' in number_elem.attrs:
        classes = number_elem['class']
        if 'track-option__number_style_1' in classes:
            color = '#429867'
        elif 'track-option__number_style_3' in classes:
            color = '#cd0b0b'
        elif 'track-option__number_style_4' in classes:
            color = '#000'

    for param in params:
        icon = param.find('span', class_='icon')
        if icon and 'class' in icon.attrs:
            classes = icon['class']
            param_text = param.text.strip()

            if 'icon_image_track-length' in classes:
                length = param_text
            elif 'icon_image_clock' in classes:
                time = param_text
            elif 'icon_image_track-height' in classes:
                height = param_text
            elif 'icon_image_lamp' in classes:
                lighting = param_text
            elif 'icon_image_snowmachine' in classes:
                snow = param_text

    return TrackParam(
        length=length,
        time=time,
        height=height,
        lighting=lighting,
        snow=snow,
        color=color
    )

def parse_tracks(url: str) -> List[Track]:
    """Парсинг трасс для конкретной зоны"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        tracks_data = []
        tracks = soup.find_all(['div'], class_=['scheme-select__option track-option', 'track-option'])

        for track in tracks:
            track_name_elem = track.find('div', class_='track-option__name')
            track_name = track_name_elem.text.strip() if track_name_elem else "Не указано"

            number_elem = track.find('div', class_='track-option__number')
            number = number_elem.text.strip() if number_elem else "Не указано"

            info_block = track.find('div', class_='track-option__info')
            params = info_block.find_all('span', class_='track-param') if info_block else track.find_all('span', class_='track-param')

            status_elem = track.find('p', class_='track-status')
            status = status_elem.text.strip() if status_elem else "Статус неизвестен"

            track_data = Track(
                name=track_name,
                number=number,
                params=parse_track_params(params, number_elem),
                status=status,
                updated_at=datetime.now()
            )
            tracks_data.append(track_data)

        return tracks_data

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при парсинге трасс: {str(e)}")

# Роуты
@app.get("/", response_model=List[Zone])
async def get_zones():
    """Получение списка всех зон с их трассами"""
    try:
        main_url = f"{BASE_URL}/hills/1/1/"
        response = requests.get(main_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        zones_data = []
        zones = soup.find_all('a', class_=['gv-select__option option', 'gv-selectoption option'])

        if not zones:
            gv_select = soup.find('div', class_='gv-select')
            if gv_select:
                zones = gv_select.find_all('a', class_='option')

        if not zones:
            raise HTTPException(status_code=404, detail="Зоны не найдены")

        for zone in zones:
            zone_name = zone.text.strip()
            if '(' in zone_name:
                zone_name = zone_name.split('(')[0].strip()

            zone_url = BASE_URL + zone['href']

            # Добавляем задержку между запросами
            time.sleep(1)

            tracks = parse_tracks(zone_url)

            zone_data = Zone(
                name=zone_name,
                url=zone_url,
                tracks=tracks
            )
            zones_data.append(zone_data)

        return zones_data

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении зон: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(app, host="0.0.0.0", port=8005)
    except Exception as e:
        print(f"Ошибка запуска парсера трасс: {e}")