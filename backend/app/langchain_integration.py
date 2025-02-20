import os
import requests
from langchain.tools import BaseTool
from langchain_community.llms import HuggingFaceHub  # Updated import as recommended
from langchain.agents import initialize_agent
from dotenv import load_dotenv
load_dotenv()

# Import the FAISS store instance from our vector_store module.
from vector_store import faiss_store

# ----------------------------
# OpenWeather API Tool Wrapper
# ----------------------------
class OpenWeatherTool(BaseTool):
    name: str = "OpenWeather"  # Added type annotation
    description: str = "Fetch current weather information for a given location."  # Added type annotation
    
    def _run(self, query: str) -> str:
        # Assume 'query' includes a location (e.g., "Paris")
        api_key = os.getenv("OPENWEATHER_KEY")
        url = f"http://api.openweathermap.org/data/2.5/weather?q={query}&appid={api_key}&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            weather_desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            return f"In {query}, the weather is '{weather_desc}' with a temperature of {temp}°C."
        else:
            return f"Unable to fetch weather data for {query}."
    
    def _arun(self, query: str) -> str:
        raise NotImplementedError("Asynchronous run not implemented")

# --------------------------
# SerpApi Tool Wrapper
# --------------------------
class SerpApiTool(BaseTool):
    name: str = "SerpApi"  # Added type annotation
    description: str = "Fetch travel data (flights/hotels) using SerpApi for a given query."  # Added type annotation
    
    def _run(self, query: str) -> str:
        # For demonstration, we simulate a response.
        # In production, call the actual SerpApi endpoint with your API key.
        return f"Simulated travel data for '{query}'."
    
    def _arun(self, query: str) -> str:
        raise NotImplementedError("Asynchronous run not implemented")

# ----------------------------
# LangChain Agent Configuration
# ----------------------------

# Initialize the LLM using a free alternative from HuggingFaceHub.
# Ensure that you have set HUGGINGFACEHUB_API_TOKEN in your .env file.
llm = HuggingFaceHub(
    repo_id="google/flan-t5-base",
    model_kwargs={"temperature": 0},
    huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN")
)

# Create instances of our tools.
openweather_tool = OpenWeatherTool()
serpapi_tool = SerpApiTool()
tools = [openweather_tool, serpapi_tool]

# Initialize a zero-shot agent that uses our tools.
# Note the addition of handle_parsing_errors=True to handle output parsing issues.
agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    verbose=True,
    handle_parsing_errors=True
)

def process_query(query: str, user_profile: dict) -> str:
    """
    Process a travel query using LangChain and FAISS:
      - Retrieve static profile data and search FAISS for related historical responses.
      - Build a pre-prompt that combines the profile, the query, and any FAISS context.
      - Call the LangChain agent with this pre-prompt.
      - Add the agent's response to the FAISS store.
    """
    # Construct a string from the static profile.
    profile_str = (
        f"Email: {user_profile.get('email')}, "
        f"Full Name: {user_profile.get('full_name')}, "
        f"Preferences: {user_profile.get('travel_preferences')}"
    )
    
    # Query FAISS for similar historical responses.
    faiss_results = faiss_store.search(query, top_k=1)
    faiss_context = ""
    if faiss_results:
        faiss_context = f"Relevant historical data: {faiss_results[0]}"
    
    # Build the pre-prompt.
    pre_prompt = (
        f"User Profile: {profile_str}\n"
        f"User Query: {query}\n"
        f"{faiss_context}\n"
        "Using the above information, fetch relevant weather data and travel details. "
        "Provide a detailed travel recommendation with citations."
    )
    
    # Run the agent with our pre-prompt.
    response = agent.run(pre_prompt)
    
    # After generating the response, store it in FAISS for future context.
    faiss_store.add_text(response)
    
    return response
