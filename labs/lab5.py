import requests
import streamlit as st
import os
import json
from openai import OpenAI

# ========================================
# PART A: WEATHER DATA FUNCTION
# ========================================

def get_current_weather(location, api_key, units='imperial'):
    """
    Get current weather for a location.
    
    Args:
        location: City name in format "City, State, Country" (e.g., "Syracuse, NY, US")
        api_key: OpenWeatherMap API key
        units: Temperature units ('imperial' for Fahrenheit, 'metric' for Celsius)
    
    Returns:
        Dictionary with weather information
    """
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

# ========================================
# PAGE SETUP
# ========================================

st.set_page_config(page_title='Lab 5: What to Wear Bot', initial_sidebar_state='expanded')

# Get API keys
weather_api_key = st.secrets.get('OPENWEATHERMAP_API_KEY', '') or os.getenv('OPENWEATHERMAP_API_KEY', '')
openai_api_key = st.secrets.get('OPENAI_API_KEY', '')

if not weather_api_key:
    st.error('⚠️ OpenWeather API key not configured. Add OPENWEATHERMAP_API_KEY to secrets.toml')
    st.stop()

if not openai_api_key:
    st.error('⚠️ OpenAI API key not configured. Add OPENAI_API_KEY to secrets.toml')
    st.stop()

# ========================================
# SECTION: "WHAT TO WEAR" BOT
# ========================================

st.title("👔 What to Wear Bot")
st.write("Enter a city and I'll tell you what to wear and suggest outdoor activities!")

# Initialize OpenAI client
openai_client = OpenAI(api_key=openai_api_key)

# Define weather tool for OpenAI function calling
weather_tool = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather for a given location. If no location is provided, use 'Syracuse, NY' as default.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state/country, e.g., 'Syracuse, NY, US' or 'London'. Defaults to 'Syracuse, NY' if not provided.",
                }
            },
        },
    },
}

# User input
user_city = st.text_input("Enter a city (or leave blank for Syracuse, NY):", key="wear_city")

if st.button("Get Clothing Advice"):
    # Use default if no city provided
    if not user_city or not user_city.strip():
        user_city = "Syracuse, NY"
    
    with st.spinner(f"Getting weather and clothing advice for {user_city}..."):
        messages = [
            {
                "role": "system",
                "content": "You are a helpful fashion and outdoor activity advisor. Provide clothing suggestions based on weather and recommend appropriate outdoor activities."
            },
            {
                "role": "user",
                "content": f"What should I wear and what outdoor activities can I do in {user_city} today?"
            }
        ]
        
        try:
            # Step 1: First API call with tool
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=[weather_tool],
                tool_choice="auto"  # Model decides when to call the tool
            )
            
            response_message = response.choices[0].message
            
            # Step 2: Check if model wants to call weather function
            if response_message.tool_calls:
                tool_call = response_message.tool_calls[0]
                function_args = json.loads(tool_call.function.arguments)
                location = function_args.get("location", "Syracuse, NY")
                
                # Handle empty location
                if not location or not str(location).strip():
                    location = "Syracuse, NY"
                
                st.info(f"🔍 Fetching weather for: {location}")
                
                # Step 3: Get weather data
                try:
                    weather_data = get_current_weather(location, weather_api_key)
                except Exception as weather_error:
                    if "404 error" in str(weather_error) and location != "Syracuse, NY":
                        fallback_location = "Syracuse, NY"
                        st.warning(
                            f"Couldn't find weather for '{location}'. Using default location: {fallback_location}."
                        )
                        weather_data = get_current_weather(fallback_location, weather_api_key)
                    else:
                        raise
                
                # Format weather info
                weather_info = (
                    f"Current weather in {weather_data['location']}:\n"
                    f"- Condition: {weather_data['condition']}\n"
                    f"- Temperature: {weather_data['temperature']}°F\n"
                    f"- Feels like: {weather_data['feels_like']}°F\n"
                    f"- Low/High: {weather_data['temp_min']}°F / {weather_data['temp_max']}°F\n"
                    f"- Humidity: {weather_data['humidity']}%"
                )
                
                # Step 4: Add tool response to messages
                messages.append(response_message)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": "get_current_weather",
                    "content": weather_info
                })
                
                # Step 5: Second API call with weather context
                second_response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                
                final_response = second_response.choices[0].message.content
                
                # Display results
                st.success("**Clothing & Activity Suggestions:**")
                st.markdown(final_response)
                
            else:
                # Model responded without needing weather
                st.info(response_message.content)
                
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ========================================
# TESTING SECTION (Optional - can comment out)
# ========================================

with st.expander("🧪 Test Weather Function"):
    st.write("Test the get_current_weather function with different cities:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Test Syracuse, NY, US"):
            try:
                result = get_current_weather("Syracuse, NY, US", weather_api_key)
                st.json(result)
            except Exception as e:
                st.error(str(e))
    
    with col2:
        if st.button("Test Lima, Peru"):
            try:
                result = get_current_weather("Lima, Peru", weather_api_key)
                st.json(result)
            except Exception as e:
                st.error(str(e))