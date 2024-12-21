# import re
# import requests
# from bs4 import BeautifulSoup
# import time
# from typing import List, Dict, Optional
# import json
#
#
# class TrackParams:
#     def __init__(self, length=None, time=None, height=None, lighting=None,
#                  snow=None, lift_type=None, capacity=None):
#         self.length = length
#         self.time = time
#         self.height = height
#         self.lighting = lighting
#         self.snow = snow
#         self.lift_type = lift_type
#         self.capacity = capacity
#
#     def to_dict(self):
#         params = {
#             'длина': self.length,
#             'время': self.time,
#             'высота': self.height,
#             'освещение': self.lighting,
#             'снег': self.snow,
#             'тип_подъемника': self.lift_type,
#             'вместимость': self.capacity
#         }
#         # Фильтруем пустые значения
#         return {k: v for k, v in params.items()
#                 if v and v != "Не указано" and v != "None" and v != "null"}
#
#
# class Track:
#     def __init__(self, name: str, number: str, params: TrackParams, status: str, url: str = None,
#                  difficulty: str = None):
#         self.name = name
#         self.number = number
#         self.params = params
#         self.status = status
#         self.url = url
#         self.difficulty = difficulty
#
#     def to_dict(self):
#         result = {
#             'название': self.name,
#             'номер': self.number,
#             'параметры': self.params.to_dict(),
#             'статус': self.status,
#             'ссылка': self.url
#         }
#
#         # Добавляем сложность, если она указана
#         if self.difficulty:
#             result['сложность'] = self.difficulty
#
#         # Фильтруем пустые значения и "Не указано"
#         filtered_result = {k: v for k, v in result.items()
#                            if v and v != "Не указано" and v != "None" and v != "null"}
#
#         # Особая обработка для параметров
#         if 'параметры' in filtered_result and not filtered_result['параметры']:
#             del filtered_result['параметры']
#
#         return filtered_result
#
#
# def find_url_pattern(html_text: str) -> str:
#     pattern = r'/hills/\d+/\d+/'
#     match = re.search(pattern, html_text)
#     if match:
#         return match.group(0)
#     return None
#
#
# def print_track(track_data: dict) -> None:
#     """Выводит информацию о трассе"""
#     print("\n" + "=" * 50)
#
#     if 'название' in track_data:
#         print(f"Название: {track_data['название']}")
#     if 'номер' in track_data:
#         print(f"Номер: {track_data['номер']}")
#     if 'сложность' in track_data:
#         print(f"Сложность: {track_data['сложность']}")
#
#     if 'параметры' in track_data and track_data['параметры']:
#         print("\nПараметры:")
#         params = track_data['параметры']
#         for key, value in params.items():
#             print(f"  {key.replace('_', ' ').title()}: {value}")
#
#     if 'статус' in track_data:
#         print(f"\nСтатус: {track_data['статус']}")
#
#     print("=" * 50)
#
#
# def print_zone(zone_data: dict) -> None:
#     """Выводит информацию о зоне"""
#     print("\n" + "=" * 80)
#     print(f"ЗОНА: {zone_data['название']}")
#     print("=" * 80)
#
#     if 'трассы' in zone_data:
#         print(f"\nВсего трасс/подъемников: {len(zone_data['трассы'])}")
#         for track in zone_data['трассы']:
#             print_track(track)
#
#     print("\n" + "=" * 80)
#
#
# def parse_tracks(url: str) -> List[Track]:
#     base_url = 'https://ski-gv.ru'
#     try:
#         print(f"\nПолучаем трассы/подъемники с URL: {url}")
#         print(f"Сезон: лето")
#
#         response = requests.get(url)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, 'html.parser')
#
#         tracks_data = []
#
#         tracks = soup.find_all(['div'], class_=['lift-option'])
#
#         print(f"Найдено объектов: {len(tracks)}")
#
#         for track in tracks:
#             track_name_elem = track.find(['div'], class_=['lift-option__name'])
#             track_name = track_name_elem.text.strip() if track_name_elem else None
#
#             number = None
#             difficulty = None
#
#             # Параметры
#             length = time = height = lighting = snow = capacity = lift_type = None
#
#             # Ищем все параметры
#             params = track.find_all(['span'], class_=['lift-param'])
#
#             for param in params:
#                 icon = param.find('span', class_='icon')
#                 if icon and 'class' in icon.attrs:
#                     classes = icon['class']
#                     param_text = param.text.strip()
#
#                     if 'icon_image_track-length' in classes:
#                         length = param_text
#                     elif 'icon_image_clock' in classes or 'icon_image_hourglass' in classes:
#                         time = param_text
#                     elif 'icon_image_track-height' in classes:
#                         height = param_text
#                     elif 'icon_image_lamp' in classes:
#                         lighting = param_text
#                     elif 'icon_image_snowmachine' in classes:
#                         snow = param_text
#                     elif 'icon_image_cabine' in classes:
#                         lift_type = param_text
#                     elif 'icon_image_people' in classes:
#                         capacity = param_text
#
#             status = None
#             status_elem = track.find('p', class_='lift-status')
#             if status_elem:
#                 status = status_elem.text.strip()
#
#             # Ссылка на подъемник
#             info_button = track.find('a', class_='button button_style_default button_type_2')
#             lift_url = base_url + info_button['href'] if info_button else None
#
#             track_params = TrackParams(
#                 length=length,
#                 time=time,
#                 height=height,
#                 lighting=lighting,
#                 snow=snow,
#                 lift_type=lift_type,
#                 capacity=capacity
#             )
#
#             track_data = Track(
#                 name=track_name,
#                 number=number,
#                 params=track_params,
#                 status=status,
#                 url=lift_url,
#                 difficulty=difficulty
#             )
#
#             print(f"\nИнформация о трассе/подъемнике:")
#             print_track(track_data.to_dict())
#
#             tracks_data.append(track_data)
#
#         return tracks_data
#
#     except requests.RequestException as e:
#         print(f"Ошибка при выполнении запроса: {str(e)}")
#         return []
#
#
# def get_zones():
#     print(f"\nПолучаем информацию о зонах для сезона: лето")
#     base_url = 'https://ski-gv.ru'
#
#     session = requests.Session()
#     session.cookies.set('season', 'summer', domain='ski-gv.ru')
#
#     try:
#         print("\nОтправляем запрос к главной странице...")
#         response = session.get(base_url)
#         response.raise_for_status()
#
#         url_path = find_url_pattern(response.text)
#         if not url_path:
#             print("Ссылка на подъемники не найдена")
#             return None
#
#         main_url = f"{base_url}{url_path}"
#         print(f"Найдена ссылка на подъемники: {main_url}")
#
#         response = session.get(main_url)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, 'html.parser')
#
#         zones = soup.find_all('a', class_=['gv-select__option option', 'gv-selectoption option'])
#
#         if not zones:
#             gv_select = soup.find('div', class_='gv-select')
#             if gv_select:
#                 zones = gv_select.find_all('a', class_='option')
#
#         if not zones:
#             print("Зоны не найдены")
#             return None
#
#         print(f"\nНайдено зон: {len(zones)}")
#         zones_data = []
#
#         for zone in zones:
#             zone_name = zone.text.strip()
#             if '(' in zone_name:
#                 zone_name = zone_name.split('(')[0].strip()
#
#             zone_url = base_url + zone['href']
#
#             print(f"\nОбрабатываем зону: {zone_name}")
#             print(f"Ссылка на зону: {zone_url}")
#
#             tracks = parse_tracks(zone_url)
#
#             zone_data = {
#                 'название': zone_name,
#                 'ссылка': zone_url,
#                 'трассы': [track.to_dict() for track in tracks],
#                 'найденная_ссылка': main_url
#             }
#
#             zones_data.append(zone_data)
#             print(f"Завершена обработка зоны: {zone_name}")
#             print("-" * 50)
#
#             time.sleep(1)
#
#         return zones_data
#
#     except requests.RequestException as e:
#         print(f"Ошибка при выполнении запроса: {str(e)}")
#         return None
#
#
# if __name__ == "__main__":
#     print("=== Работа со склоном ===")
#     print("\n1. Получение информации о всех зонах...")
#     zones = get_zones()
#     if zones:
#         print("\nСписок всех зон и подъемников:")
#         for zone in zones:
#             print_zone(zone)
