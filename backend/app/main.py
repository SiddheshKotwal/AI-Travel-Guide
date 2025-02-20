import os
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import bcrypt
import jwt
from supabase import create_client, Client

# Import the LangChain integration function that now uses FAISS and Google Gemini
from langchain_integration import process_query

# Load environment variables from .env
load_dotenv()

# Environment variables and configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Pydantic models for user data, tokens, and chat queries
class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: str = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: str = None
    email: EmailStr
    full_name: str = None
    travel_preferences: dict = {}

class Token(BaseModel):
    access_token: str
    token_type: str

class ChatQuery(BaseModel):
    query: str

# Create FastAPI app
app = FastAPI()

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Utility functions for password hashing and token generation
def get_password_hash(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency: Retrieve the current user from JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    result = supabase.table("users").select("*").eq("email", email).execute()
    if not result.data:
        raise credentials_exception
    return result.data[0]

# Endpoint: User Signup
@app.post("/signup", response_model=UserProfile)
async def signup(user: UserSignup):
    result = supabase.table("users").select("*").eq("email", user.email).execute()
    if result.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    user_data = {
        "email": user.email,
        "hashed_password": hashed_password,
        "full_name": user.full_name,
        "travel_preferences": {}  # Default empty preferences
    }
    response = supabase.table("users").insert(user_data).execute()
    if response.error:
        raise HTTPException(status_code=500, detail="User could not be created")
    return response.data[0]

# Endpoint: User Login (OAuth2PasswordRequestForm)
@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    result = supabase.table("users").select("*").eq("email", form_data.username).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    user = result.data[0]
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["email"]}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# Endpoint: Get User Profile
@app.get("/profile", response_model=UserProfile)
async def read_profile(current_user: dict = Depends(get_current_user)):
    return current_user

# Endpoint: Update User Profile
@app.put("/profile", response_model=UserProfile)
async def update_profile(updated_profile: UserProfile, current_user: dict = Depends(get_current_user)):
    response = supabase.table("users").update({
        "full_name": updated_profile.full_name,
        "travel_preferences": updated_profile.travel_preferences
    }).eq("email", current_user["email"]).execute()
    if response.error:
        raise HTTPException(status_code=500, detail="Profile update failed")
    updated = supabase.table("users").select("*").eq("email", current_user["email"]).execute()
    return updated.data[0]

# Final Integrated Chat Endpoint using LangChain + FAISS orchestration
@app.post("/chat")
async def chat(query_data: ChatQuery, current_user: dict = Depends(get_current_user)):
    query = query_data.query
    if not query:
        raise HTTPException(status_code=400, detail="Query is required.")
    
    # Prepare a simple user profile dictionary for our integration function.
    user_profile = {
         "email": current_user["email"],
         "full_name": current_user.get("full_name", ""),
         "travel_preferences": current_user.get("travel_preferences", {})
    }
    
    # Process the query using the LangChain orchestration function.
    final_response = process_query(query, user_profile)
    return {"response": final_response}

# Run the app with Uvicorn if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
