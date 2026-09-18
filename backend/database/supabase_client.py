import os
from typing import Optional
from supabase import create_client, Client

# Read from environment variables, with fallback to your project credentials
SUPABASE_URL: str = os.getenv(
    "SUPABASE_URL", 
    "https://cfpvxqwtrjdifittfwji.supabase.co"
)
SUPABASE_KEY: str = os.getenv(
    "SUPABASE_KEY", 
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmcHZ4cXd0cmpkaWZpdHRmd2ppIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk3MjMwOTUsImV4cCI6MjEwNTI5OTA5NX0.ggsjUrN7AlgPDp1qNGALRg9thXu3oYwLnB-yEIsIFEA"
)

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """
    Initializes and returns a singleton Supabase client.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[TraceAI DB] Supabase URL or Key missing.")
        return None

    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _supabase_client
    except Exception as e:
        print(f"[TraceAI DB] Failed to initialize Supabase client: {e}")
        return None