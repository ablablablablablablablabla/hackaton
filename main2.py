from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime


class Track(BaseModel):
    name: str
    number: str
    params: Dict[str, str] | None = None
    status: str
    updated_at: datetime

    model_config = {
        'json_encoders': {
            datetime: lambda v: v.isoformat()
        }
    }

    def model_dump(self, *args, **kwargs):
        kwargs['exclude_none'] = True
        kwargs['exclude_unset'] = True
        data = super().model_dump(*args, **kwargs)
        return {k: v for k, v in data.items() if v is not None}


class Zone(BaseModel):
    name: str
    url: str
    tracks: List[Track]

    def model_dump(self, *args, **kwargs):
        kwargs['exclude_none'] = True
        kwargs['exclude_unset'] = True
        data = super().model_dump(*args, **kwargs)
        return {k: v for k, v in data.items() if v is not None}


BASE_URL = 'https://ski-gv.ru'


def parse_track_params(params) -> Dict[str, str] | None:
    """Парсинг параметров трассы"""
    result = {}

    for param in params:
        icon = param.find('span', class_='icon')
        if not icon or 'class' not in icon.attrs:
            continue

        classes = icon['class']
        param_text = param.text.strip()

        if not param_text or param_text == "None" or param_text == "Не указано":
            continue

        param_mapping = {
            'icon_image_track-length': 'length',
            'icon_image_clock': 'time',
            'icon_image_track-height': 'height',
            'icon_image_lamp': 'lighting',
            'icon_image_snowmachine': 'snow'
        }

        for class_name, param_name in param_mapping.items():
            if class_name in classes:
                result[param_name] = param_text
                break

    return result if result else None


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
            track_name = track_name_elem.text.strip() if track_name_elem else None
            if not track_name:
                continue

            number_elem = track.find('div', class_='track-option__number')
            number = number_elem.text.strip() if number_elem else "Не указано"

            info_block = track.find('div', class_='track-option__info')
            params = info_block.find_all('span', class_='track-param') if info_block else track.find_all('span', class_='track-param')

            status_elem = track.find('p', class_='track-status')
            status = status_elem.text.strip() if status_elem else "Статус неизвестен"

            params_dict = parse_track_params(params)

            track_data = Track(
                name=track_name,
                number=number,
                params=params_dict,
                status=status,
                updated_at=datetime.now()
            )
            tracks_data.append(track_data)

        return tracks_data

    except requests.RequestException as e:
        raise Exception(f"Ошибка при парсинге трасс: {str(e)}")


def get_zones() -> List[Zone]:
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
            raise Exception("Зоны не найдены")

        for zone in zones:
            zone_name = zone.text.strip()
            if '(' in zone_name:
                zone_name = zone_name.split('(')[0].strip()

            zone_url = BASE_URL + zone['href']
            time.sleep(1)

            tracks = parse_tracks(zone_url)

            if tracks:
                zone_data = Zone(
                    name=zone_name,
                    url=zone_url,
                    tracks=tracks
                )
                zones_data.append(zone_data)

        return zones_data

    except requests.RequestException as e:
        raise Exception(f"Ошибка при получении зон: {str(e)}")


def get_zone(zone_name: str) -> Zone:
    """Получение информации о конкретной зоне по имени"""
    zones = get_zones()
    for zone in zones:
        if zone.name.lower() == zone_name.lower():
            return zone
    raise Exception(f"Зона {zone_name} не найдена")


if __name__ == "__main__":
    # Пример использования
    try:
        # Получить все зоны
        all_zones = get_zones()
        print("=== Информация о горнолыжных трассах ===")
        for zone in all_zones:
            print(f"\nЗона: {zone.name}")
            print(f"URL: {zone.url}")
            print("\nСписок трасс:")
            for i, track in enumerate(zone.tracks, 1):
                print(f"\n{i}. Трасса: {track.name}")
                print(f"   Номер: {track.number}")
                print(f"   Статус: {track.status}")
                print("   Параметры трассы:")
                if track.params:
                    param_descriptions = {
                        'length': 'Длина',
                        'time': 'Время спуска',
                        'height': 'Перепад высот',
                        'lighting': 'Освещение',
                        'snow': 'Снежные пушки'
                    }
                    for param, value in track.params.items():
                        print(f"      - {param_descriptions.get(param, param)}: {value}")
                else:
                    print("      Параметры не указаны")
                print(f"   Обновлено: {track.updated_at.strftime('%d.%m.%Y %H:%M:%S')}")
            print("\n" + "="*50)

        # Получить конкретную зону
        try:
            zone_name = "Восточный склон"
            print(f"\nПоиск информации о зоне '{zone_name}'...")
            specific_zone = get_zone(zone_name)
            print(f"Найдена зона: {specific_zone.name}")
            print(f"Количество трасс: {len(specific_zone.tracks)}")
        except Exception as e:
            print(f"Ошибка при получении информации о зоне '{zone_name}': {e}")

    except Exception as e:
        print(f"Произошла ошибка при получении данных: {e}")