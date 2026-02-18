import requests
import streamlit as st
import os
import json
from openai import OpenAI


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



st.markdown("---")
st.title("👔 What to Wear Bot")
st.write("Enter a city and I'll tell you what to wear and suggest outdoor activities!")

# Initialize OpenAI client
openai_client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ===== DEFINE WEATHER TOOL/FUNCTION FOR OpenAI =====
weather_tool = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather for a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state/country, e.g., 'Syracuse, NY, US' or 'London'",
                }
            },
            "required": ["location"],
        },
    },
}

# User input for "What to Wear" bot
user_city = st.text_input("Enter a city (or leave blank for Syracuse, NY):", key="wear_city")

if st.button("Get Clothing Advice"):
    if not user_city:
        user_city = "Syracuse, NY, US"  # Default location
    
    with st.spinner(f"Getting weather and clothing advice for {user_city}..."):
        # Step 1: Call OpenAI with the tool
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that provides clothing and outdoor activity suggestions based on weather."
            },
            {
                "role": "user",
                "content": f"What should I wear and what outdoor activities can I do in {user_city} today?"
            }
        ]
        
        try:
            # First API call - LLM decides if it needs weather info
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=[weather_tool],
                tool_choice="auto"  # Let the model decide when to call the tool
            )
            
            response_message = response.choices[0].message
            
            # Check if the model wants to call the weather function
            if response_message.tool_calls:
                # Step 2: Execute the weather function
                tool_call = response_message.tool_calls[0]
                function_args = json.loads(tool_call.function.arguments)
                location = function_args.get("location", "Syracuse, NY, US")
                
                st.info(f"🔍 Fetching weather for: {location}")
                
                # Get weather data
                weather_data = get_current_weather(location, weather_api_key)
                
                # Format weather info for the LLM
                weather_info = (
                    f"Current weather in {weather_data['location']}:\n"
                    f"- Condition: {weather_data['condition']}\n"
                    f"- Temperature: {weather_data['temperature']}°F\n"
                    f"- Feels like: {weather_data['feels_like']}°F\n"
                    f"- Low/High: {weather_data['temp_min']}°F / {weather_data['temp_max']}°F\n"
                    f"- Humidity: {weather_data['humidity']}%"
                )
                
                # Step 3: Send weather info back to the model
                messages.append(response_message)  # Add assistant's tool call
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": "get_current_weather",
                        "content": weather_info
                    }
                )
                
                # Second API call - Get clothing/activity suggestions
                second_response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                
                final_response = second_response.choices[0].message.content
                
                # Display results
                st.success("**Clothing & Activity Suggestions:**")
                st.markdown(final_response)
                
            else:
                # Model responded without needing weather data
                st.info(response_message.content)
                
        except Exception as e:
            st.error(f"Error: {str(e)}")

