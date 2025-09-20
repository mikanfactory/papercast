from supabase import Client, create_client

from papercast.config import SUPABASE_API_KEY, SUPABASE_PROJECT_URL

supabase_client: Client = create_client(SUPABASE_PROJECT_URL, SUPABASE_API_KEY)
