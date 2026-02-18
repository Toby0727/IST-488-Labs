import json
import os

import requests
import streamlit as st
from openai import OpenAI


DEFAULT_LOCATION = 'Syracuse, NY'


def get_current_weather(location, api_key, units='imperial'):
    resolved_location = location.strip() if location and location.strip() else DEFAULT_LOCATION
    url = (
        'https://api.openweathermap.org/data/2.5/weather'
        f'?q={resolved_location}&appid={api_key}&units={units}'
    )
    response = requests.get(url, timeout=20)

    if response.status_code == 401:
        raise Exception('Authentication failed: Invalid API key (401 Unauthorized)')
    if response.status_code == 404:
        error_message = response.json().get('message', 'Location not found')
        raise Exception(f'404 error: {error_message}')
    if response.status_code != 200:
        raise Exception(f'Weather API error: {response.status_code}')

    data = response.json()
    return {
        'location': data.get('name', resolved_location),
        'temperature': round(data['main']['temp'], 2),
        'feels_like': round(data['main']['feels_like'], 2),
        'temp_min': round(data['main']['temp_min'], 2),
        'temp_max': round(data['main']['temp_max'], 2),
        'humidity': data['main']['humidity'],
        'condition': data['weather'][0]['description'],
        'units': 'Fahrenheit' if units == 'imperial' else 'Celsius',
    }


st.set_page_config(page_title='Lab 5: What to Wear Bot', initial_sidebar_state='expanded')
st.title('🧥 What to Wear Bot')
st.write('Enter a city and get clothing suggestions plus outdoor activity ideas.')

openai_api_key = st.secrets.get('OPENAI_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')
weather_api_key = st.secrets.get('OPENWEATHERMAP_API_KEY', '') or os.getenv('OPENWEATHERMAP_API_KEY', '')

if not openai_api_key:
    st.error('Missing OPENAI_API_KEY in .streamlit/secrets.toml or environment variables.')
if not weather_api_key:
    st.error('Missing OPENWEATHERMAP_API_KEY in .streamlit/secrets.toml or environment variables.')

city_input = st.text_input('City', placeholder='Example: Syracuse, NY or London')
submit = st.button('Get What-to-Wear Advice', type='primary')

if submit:
    if not openai_api_key or not weather_api_key:
        st.stop()

    user_location = city_input.strip() if city_input.strip() else DEFAULT_LOCATION
    client = OpenAI(api_key=openai_api_key)

    weather_tool = {
        'type': 'function',
        'function': {
            'name': 'get_current_weather',
            'description': 'Get current weather for a location.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'location': {
                        'type': 'string',
                        'description': "City/state or city/country, like 'Syracuse, NY' or 'London, UK'.",
                    }
                },
                'required': [],
            },
        },
    }

    first_messages = [
        {
            'role': 'system',
            'content': (
                'You are a weather-based clothing assistant. '
                f"If location is missing, use '{DEFAULT_LOCATION}'. "
                'Use the weather tool when weather data is needed.'
            ),
        },
        {
            'role': 'user',
            'content': (
                f"Give clothing and outdoor activity advice for this location: {user_location}. "
                'If weather is needed, call the weather tool.'
            ),
        },
    ]

    try:
        first_response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=first_messages,
            tools=[weather_tool],
            tool_choice='auto',
        )

        message = first_response.choices[0].message
        tool_calls = message.tool_calls or []

        if tool_calls:
            tool_call = tool_calls[0]
            arguments = json.loads(tool_call.function.arguments or '{}')
            requested_location = arguments.get('location', '').strip() if isinstance(arguments, dict) else ''
            resolved_location = requested_location if requested_location else DEFAULT_LOCATION

            weather = get_current_weather(resolved_location, weather_api_key)

            second_messages = [
                {
                    'role': 'system',
                    'content': (
                        'You are a practical style and activity assistant. '
                        'Given weather data, suggest what to wear today and outdoor activities that fit the weather. '
                        'Keep recommendations concise and specific.'
                    ),
                },
                {
                    'role': 'user',
                    'content': (
                        f"Location requested: {user_location}.\n"
                        f"Weather data: {json.dumps(weather)}\n"
                        'Provide:\n'
                        '1) What to wear today\n'
                        '2) Appropriate outdoor activity suggestions'
                    ),
                },
            ]

            second_response = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=second_messages,
            )

            advice = second_response.choices[0].message.content or 'No advice returned.'

            st.subheader(f"Weather Snapshot ({weather['location']})")
            st.markdown(
                f"- Condition: {weather['condition']}\n"
                f"- Temperature: {weather['temperature']}°{weather['units'][0]}\n"
                f"- Feels like: {weather['feels_like']}°{weather['units'][0]}\n"
                f"- Low / High: {weather['temp_min']}°{weather['units'][0]} / {weather['temp_max']}°{weather['units'][0]}\n"
                f"- Humidity: {weather['humidity']}%"
            )

            st.subheader('What to Wear + Outdoor Ideas')
            st.markdown(advice)
        else:
            direct_reply = message.content or 'No response returned.'
            st.subheader('What to Wear + Outdoor Ideas')
            st.markdown(direct_reply)

    except Exception as exc:
        st.error(f'Unable to generate recommendations: {exc}')
