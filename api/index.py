from fastapi import FastAPI
from supabase_client import SupabaseClient
from algorithm import GoogleDistanceMatrixClient
import os

app = FastAPI()
google_client = GoogleDistanceMatrixClient(os.getenv("GOOGLE_MAPS_API_KEY"))
supabase_client = SupabaseClient(os.getenv("SUPABASE_KEY"), os.getenv("SUPABASE_URL"))


@app.get("/api/python")
def hello_world():
    return {"message": "Hello World"}


@app.post("/api/user/")
async def create_user(name: str, email: str, home: str):
    response = supabase_client.create_user(name, email, home)
    return response


@app.get("/api/user/{email}")
async def get_user(email: str):
    user = supabase_client.get_user(email)
    if user:
        return user
    return {"error": "User not found"}


@app.put("/api/user/{email}")
async def update_user_home(email: str, new_home: str):
    response = supabase_client.update_user_home(email, new_home)
    return response


@app.delete("/api/user/{email}")
async def delete_user(email: str):
    response = supabase_client.delete_user(email)
    return response


@app.post("/api/distance/")
async def fetch_distance_matrix(origins: list, destination: str):
    for origin in origins:
        google_client.add_origin(origin)
    google_client.set_destination(destination)
    try:
        results = google_client.fetch_distance_matrix()
        return results
    except Exception as e:
        return {"error": str(e)}
