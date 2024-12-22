from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import Optional
import requests
import uvicorn

app = FastAPI(title="Ski Resort Weather API")


class WeatherData(BaseModel):
    temperature: Optional[str] = None
    condition: Optional[str] = None
    wind: Optional[str] = None
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    humidity: Optional[str] = None
    pressure: Optional[str] = None
    icon_url: Optional[str] = None


async def fetch_weather_data() -> WeatherData:
    """
    Получает данные о погоде с сайта горнолыжного курорта
    """
    url = "https://ski-gv.ru/weather/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        weather_card = soup.find('div', class_='weather__current-part')

        if not weather_card:
            raise HTTPException(status_code=404, detail="Weather data not found")

        weather_data = WeatherData()

        # Парсинг иконки
        icon = weather_card.find('img', class_='weather-card__icon')
        if icon and 'src' in icon.attrs:
            weather_data.icon_url = icon['src']

        # Температура
        temp = weather_card.find('p', class_='weather-card__temp')
        if temp:
            weather_data.temperature = temp.text.strip()

        # Состояние погоды
        condition = weather_card.find('span', class_='weather-condition')
        if condition:
            weather_data.condition = condition.text.strip()

        # Ветер
        wind_info = [p for p in weather_card.find_all('p') if 'Ветер' in p.text]
        if wind_info:
            weather_data.wind = wind_info[0].text.strip()

        # Дополнительные параметры
        params = weather_card.find('ul', class_='weather-card__params')
        if params:
            for param in params.find_all('li'):
                param_items = param.find_all('p')
                if len(param_items) >= 2:
                    name = param_items[0].text.strip().lower()
                    value = param_items[1].text.strip()

                    if 'восход' in name:
                        weather_data.sunrise = value
                    elif 'заход' in name:
                        weather_data.sunset = value
                    elif 'влажность' in name:
                        weather_data.humidity = value
                    elif 'давление' in name:
                        weather_data.pressure = value

        return weather_data

    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Error fetching weather data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/", response_model=WeatherData)
async def get_weather():
    """
    Получить текущие данные о погоде
    """
    return await fetch_weather_data()


@app.get("/health")
async def health_check():
    """
    Проверка работоспособности API
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=8003)
    except Exception as e:
        print(f"Ошибка запуска парсера погоды: {e}")