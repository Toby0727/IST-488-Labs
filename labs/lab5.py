import requests
import streamlit as st
import os


# location in form City, State, Country
# e.g., Syracuse, NY, US
# default units is degrees Fahrenheit

def get_current_weather(location, api_key, units='imperial'):
    url = (
        f'https://api.openweathermap.org/data/2.5/weather'
        f'?q={location}&appid={api_key}&units={units}'
    )
    response = requests.get(url, timeout=20)
    if response.status_code == 401:
        raise Exception('Authentication failed: Invalid API key (401 Unauthorized)')
    if response.status_code == 404:
        error_message = response.json().get('message')
        raise Exception(f'404 error: {error_message}')
    if response.status_code != 200:
        raise Exception(f'Weather API error: {response.status_code}')

    data = response.json()
    temp = data['main']['temp']
    feels_like = data['main']['feels_like']
    temp_min = data['main']['temp_min']
    temp_max = data['main']['temp_max']
    humidity = data['main']['humidity']
    condition = data['weather'][0]['description']

    return {
        'location': location,
        'temperature': round(temp, 2),
        'feels_like': round(feels_like, 2),
        'temp_min': round(temp_min, 2),
        'temp_max': round(temp_max, 2),
        'humidity': round(humidity, 2),
        'condition': condition,
    }


st.set_page_config(page_title='Lab 5: Weather Chatbot', initial_sidebar_state='expanded')
st.title('🌤️ Weather Chatbot')
st.write('Type a city name and get current weather info.')

if 'weather_messages' not in st.session_state:
    st.session_state.weather_messages = [
        {
            'role': 'assistant',
            'content': 'Hi! Enter a city like "Syracuse, NY, US" or "London".',
        }
    ]

weather_api_key = st.secrets.get('OPENWEATHERMAP_API_KEY', '') or os.getenv('OPENWEATHERMAP_API_KEY', '')

if not weather_api_key:
    st.warning(
        'OpenWeather API key not configured. Add OPENWEATHERMAP_API_KEY in .streamlit/secrets.toml '
        'or set the OPENWEATHERMAP_API_KEY environment variable.'
    )

for message in st.session_state.weather_messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

if city := st.chat_input('Enter a city...'):
    st.session_state.weather_messages.append({'role': 'user', 'content': city})
    with st.chat_message('user'):
        st.markdown(city)

    with st.chat_message('assistant'):
        if not weather_api_key:
            response = (
                'Missing OpenWeather API key. Add OPENWEATHERMAP_API_KEY to .streamlit/secrets.toml '
                'or set the OPENWEATHERMAP_API_KEY environment variable, then refresh the app.'
            )
            st.error(response)
            st.session_state.weather_messages.append({'role': 'assistant', 'content': response})
            st.stop()

        try:
            weather = get_current_weather(city, weather_api_key)
            response = (
                f"**Weather for {weather['location']}**\n\n"
                f"- Condition: {weather['condition']}\n"
                f"- Temperature: {weather['temperature']}°F\n"
                f"- Feels like: {weather['feels_like']}°F\n"
                f"- Low / High: {weather['temp_min']}°F / {weather['temp_max']}°F\n"
                f"- Humidity: {weather['humidity']}%"
            )
            st.markdown(response)
        except Exception as exc:
            response = f"I couldn't get weather for '{city}'. {exc}"
            st.error(response)

    st.session_state.weather_messages.append({'role': 'assistant', 'content': response})
