import streamlit as st
from openai import OpenAI
import requests

# location in form City, State, Country
# e.g., Syracuse, NY, US
# default units is degrees Fahrenheit


def get_current_weather(location, api_key, units='imperial'):
    url = (
        f'https://api.openweathermap.org/data/2.5/weather'
        f'?q={location}&appid={api_key}&units={units}'
    )
    response = requests.get(url)
    if response.status_code == 401:
        raise Exception('Authentication failed: Invalid API key (401 Unauthorized)')
    if response.status_code == 404:
        error_message = response.json().get('message')
        raise Exception(f'404 error: {error_message}')
    data = response.json()
    temp = data['main']['temp']
    feels_like = data['main']['feels_like']
    temp_min = data['main']['temp_min']
    temp_max = data['main']['temp_max']
    humidity = data['main']['humidity']
    return {'location': location,
        'temperature': round(temp, 2),
        'feels_like': round(feels_like, 2),
        'temp_min': round(temp_min, 2),
        'temp_max': round(temp_max, 2),
        'humidity': round(humidity, 2)
    }


def validate_openai_key(api_key: str) -> tuple[bool, str]:
    if not api_key:
        return False, 'OpenAI key is empty.'
    try:
        client = OpenAI(api_key=api_key)
        client.models.list()
        return True, 'OpenAI key is valid.'
    except Exception as exc:
        return False, f'OpenAI validation failed: {exc}'


def validate_openweather_key(api_key: str) -> tuple[bool, str]:
    if not api_key:
        return False, 'OpenWeatherMap key is empty.'
    try:
        response = requests.get(
            'https://api.openweathermap.org/data/2.5/weather',
            params={'q': 'Syracuse,NY,US', 'appid': api_key, 'units': 'imperial'},
            timeout=15,
        )
        if response.status_code == 200:
            return True, 'OpenWeatherMap key is valid.'
        if response.status_code == 401:
            return False, 'OpenWeatherMap key is invalid (401 Unauthorized).'
        if response.status_code == 404:
            return False, 'Validation location was not found (404).'
        return False, f'OpenWeatherMap validation failed with status {response.status_code}.'
    except Exception as exc:
        return False, f'OpenWeatherMap validation failed: {exc}'


st.set_page_config(page_title='Lab 5: API Setup', initial_sidebar_state='expanded')
st.title('Lab 5: API User Setup')
st.write('Set up credentials for both OpenAI and OpenWeatherMap below.')

if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = st.secrets.get('OPENAI_API_KEY', '')
if 'openweather_api_key' not in st.session_state:
    st.session_state.openweather_api_key = st.secrets.get('OPENWEATHERMAP_API_KEY', '')

st.subheader('OpenAI User')
st.text_input('OpenAI API Key', type='password', key='openai_api_key')
if st.button('Validate OpenAI Key', use_container_width=True):
    ok, message = validate_openai_key(st.session_state.openai_api_key)
    if ok:
        st.success(message)
    else:
        st.error(message)

st.subheader('OpenWeatherMap User')
st.text_input('OpenWeatherMap API Key', type='password', key='openweather_api_key')
if st.button('Validate OpenWeatherMap Key', use_container_width=True):
    ok, message = validate_openweather_key(st.session_state.openweather_api_key)
    if ok:
        st.success(message)
    else:
        st.error(message)

if st.session_state.openai_api_key and st.session_state.openweather_api_key:
    st.info('Both API keys are present in this session. You can now use OpenAI and weather features.')
else:
    st.warning('Enter both API keys to complete setup.')