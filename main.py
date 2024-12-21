# main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import re
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime

# Создаем экземпляр FastAPI
app = FastAPI(
    title="Горнолыжный курорт API",
    description="API для получения информации о трассах и зонах горнолыжного курорта",
    version="1.0.0"
)


# Тот же код моделей и функций что и раньше...
# Pydantic модели для валидации данных
class TrackParams(BaseModel):
    length: Optional[str] = None
    time: Optional[str] = None
    height: Optional[str] = None
    lighting: Optional[str] = None
    snow: Optional[str] = None
    difficulty: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in self.dict().items() if v is not None}


class Track(BaseModel):
    name: str
    number: str
    params: Optional[TrackParams]
    status: str
    url: Optional[str] = None
    updated_at: datetime = datetime.now()

    def to_dict(self):
        result = self.dict(exclude_none=True)
        if 'params' in result and result['params']:
            result['params'] = self.params.to_dict()
        return result


class Zone(BaseModel):
    name: str
    url: str
    tracks: List[Track]


async def parse_tracks(url: str, season: str = 'winter') -> List[Track]:
    base_url = 'https://ski-gv.ru'
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        tracks_data = []
        tracks = soup.find_all(['div'], class_=['scheme-select__option track-option', 'track-option'])

        for track in tracks:
            track_name_elem = track.find('div', class_='track-option__name')
            track_name = track_name_elem.text.strip() if track_name_elem else None
            if not track_name:
                continue

            number_elem = track.find('div', class_='track-option__number')
            number = number_elem.text.strip() if number_elem else "Не указано"

            # Определение сложности
            difficulty = "Не указано"
            if number_elem and number_elem.get('class'):
                classes = number_elem['class']
                if any('track-option__number_style_1' in c for c in classes):
                    difficulty = 'Простая'
                elif any('track-option__number_style_2' in c for c in classes):
                    difficulty = 'Средняя'
                elif any('track-option__number_style_3' in c for c in classes):
                    difficulty = 'Сложная'
                elif any('track-option__number_style_4' in c for c in classes):
                    difficulty = 'Очень сложная'

            # Параметры трассы
            params = {}
            params_elems = track.find_all(['span'], class_=['track-param'])

            for param in params_elems:
                icon = param.find('span', class_='icon')
                if icon and 'class' in icon.attrs:
                    classes = icon['class']
                    param_text = param.text.strip()

                    if 'icon_image_track-length' in classes:
                        params['length'] = param_text
                    elif 'icon_image_clock' in classes or 'icon_image_hourglass' in classes:
                        params['time'] = param_text
                    elif 'icon_image_track-height' in classes:
                        params['height'] = param_text
                    elif 'icon_image_lamp' in classes:
                        params['lighting'] = param_text
                    elif 'icon_image_snowmachine' in classes:
                        params['snow'] = param_text

            params['difficulty'] = difficulty

            status_elem = track.find('p', class_='track-status')
            status = status_elem.text.strip() if status_elem else "Статус неизвестен"

            info_button = track.find('a', class_='button button_style_default button_type_2')
            lift_url = base_url + info_button['href'] if info_button else None

            track_data = Track(
                name=track_name,
                number=number,
                params=TrackParams(**params),
                status=status,
                url=lift_url
            )

            tracks_data.append(track_data)

        return tracks_data

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при выполнении запроса: {str(e)}")


async def get_zones(season: str = 'winter') -> List[Zone]:
    base_url = 'https://ski-gv.ru'
    session = requests.Session()
    session.cookies.set('season', season, domain='ski-gv.ru')

    try:
        response = session.get(base_url)
        if not response.ok:
            raise HTTPException(status_code=response.status_code,
                                detail="Ошибка при запросе к главной странице")

        main_url = f"{base_url}/hills/1/1/"
        response = session.get(main_url)
        if not response.ok:
            raise HTTPException(status_code=response.status_code,
                                detail="Ошибка при запросе зон")

        soup = BeautifulSoup(response.text, 'html.parser')
        zones = soup.find_all('a', class_=['gv-select__option option', 'gv-selectoption option'])

        if not zones:
            gv_select = soup.find('div', class_='gv-select')
            if gv_select:
                zones = gv_select.find_all('a', class_='option')

        if not zones:
            raise HTTPException(status_code=404, detail="Зоны не найдены")

        zones_data = []
        for zone in zones:
            zone_name = zone.text.strip()
            if '(' in zone_name:
                zone_name = zone_name.split('(')[0].strip()

            zone_url = base_url + zone['href']
            tracks = await parse_tracks(zone_url, season)

            zone_data = Zone(
                name=zone_name,
                url=zone_url,
                tracks=tracks
            )
            zones_data.append(zone_data)
            time.sleep(1)

        return zones_data

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при выполнении запроса: {str(e)}")


# Эндпоинты API
@app.get("/", response_model=dict)
async def root():
    """
    Корневой эндпоинт с информацией об API
    """
    return {
        "название": "API горнолыжного курорта",
        "версия": "1.0.0",
        "эндпоинты": [
            "/zones - Получение информации о всех зонах",
            "/zones/{zone_name} - Получение информации о конкретной зоне",
            "/tracks - Получение информации о всех трассах"
        ]
    }


@app.get("/zones", response_model=List[Zone])
async def get_all_zones(
        season: str = Query("winter", enum=["winter", "summer"],
                            description="Сезон (winter/summer)")
):
    """
    Получение информации о всех зонах курорта
    """
    return await get_zones(season)


@app.get("/zones/{zone_name}", response_model=Zone)
async def get_zone_by_name(
        zone_name: str,
        season: str = Query("winter", enum=["winter", "summer"])
):
    """
    Получение информации о конкретной зоне по её названию
    """
    zones = await get_zones(season)
    for zone in zones:
        if zone.name.lower() == zone_name.lower():
            return zone
    raise HTTPException(status_code=404, detail=f"Зона '{zone_name}' не найдена")


@app.get("/tracks", response_model=List[Track])
async def get_all_tracks(
        season: str = Query("winter", enum=["winter", "summer"]),
        difficulty: Optional[str] = Query(None, enum=["Простая", "Средняя", "Сложная", "Очень сложная"])
):
    """
    Получение информации о всех трассах с возможностью фильтрации по сложности
    """
    zones = await get_zones(season)
    all_tracks = []
    for zone in zones:
        all_tracks.extend(zone.tracks)

    if difficulty:
        all_tracks = [track for track in all_tracks
                      if track.params and track.params.difficulty == difficulty]

    return all_tracks


# Обработчики ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Внутренняя ошибка сервера: {str(exc)}"}
    )