from supabase import create_client, Client


class SupabaseClient:
    def __init__(self, url: str, key: str):
        self.supabase: Client = create_client(url, key)

    def create_user(self, name: str, email: str, home: str):
        """Create a new user with their home address."""
        data = {"name": name, "email": email, "home": home}
        response = self.supabase.table("users").insert(data).execute()
        return response

    def get_user(self, email: str):
        """Retrieve a user by their email."""
        response = self.supabase.table("users").select("*").eq("email", email).execute()
        return response.data

    def update_user_home(self, email: str, new_home: str):
        """Update a user's home address."""
        response = (
            self.supabase.table("users")
            .update({"home": new_home})
            .eq("email", email)
            .execute()
        )
        return response

    def delete_user(self, email: str):
        """Delete a user by their email."""
        response = self.supabase.table("users").delete().eq("email", email).execute()
        return response
