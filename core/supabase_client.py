import os
from pathlib import Path
# pyrefly: ignore [missing-import]
from supabase import create_client, Client

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent.parent

# Define the helper to parse .env file if it exists, without needing external dependencies
def load_dotenv():
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#') or '=' not in line:
                    continue
                # Split at the first '='
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip("'\"") # strip quotes
                os.environ.setdefault(key, val)

# Execute load_dotenv
load_dotenv()

# Read Supabase parameters from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Initialize supabase client safely
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase client initialization failed: {e}")
else:
    print("Warning: SUPABASE_URL and/or SUPABASE_KEY environment variables are missing.")


def upload_file(bucket_name, file_name, file_data, content_type):
    """
    Uploads a file to a Supabase storage bucket.
    Automatically tries to create the bucket if it does not exist.
    If the bucket exists but is private, attempts to update it to public.
    Returns the public URL of the uploaded file.
    """
    if not supabase:
        raise Exception("Supabase client is not initialized. Check your SUPABASE_URL and SUPABASE_KEY in .env.")

    # 1. Try to ensure the bucket exists and is public
    try:
        bucket = supabase.storage.get_bucket(bucket_name)
        # If it exists but is private, try to make it public
        if not getattr(bucket, 'public', False):
            try:
                supabase.storage.update_bucket(bucket_name, options={"public": True})
            except Exception as update_err:
                raise Exception(
                    f"The Supabase bucket '{bucket_name}' is set to PRIVATE. "
                    f"Please go to your Supabase Dashboard -> Storage, edit the '{bucket_name}' bucket, "
                    "and toggle the 'Public' option to ON (so images can be viewed publicly)."
                ) from update_err
    except Exception as get_err:
        # If we got a PRIVATE error during get_bucket, or it doesn't exist, handle it
        err_msg = str(get_err)
        if "Bucket is not public" in err_msg or "private" in err_msg.lower():
            raise Exception(
                f"The Supabase bucket '{bucket_name}' is set to PRIVATE. "
                f"Please go to your Supabase Dashboard -> Storage, edit the '{bucket_name}' bucket, "
                "and toggle the 'Public' option to ON (so images can be viewed publicly)."
            ) from get_err
            
        # Try to create it if it didn't exist
        try:
            supabase.storage.create_bucket(bucket_name, options={"public": True})
        except Exception as create_err:
            # Log the creation error, but proceed to try upload anyway
            print(f"Note: Could not verify or create bucket '{bucket_name}': {create_err}")

    # 2. Upload the file
    try:
        supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file_data,
            file_options={"content-type": content_type}
        )
    except Exception as upload_err:
        err_msg = str(upload_err)
        if "Bucket not found" in err_msg or "404" in err_msg:
            raise Exception(
                f"Bucket '{bucket_name}' not found. Please create a public bucket named '{bucket_name}' "
                "in your Supabase Console -> Storage."
            ) from upload_err
        elif "row violates row-level security" in err_msg or "Unauthorized" in err_msg or "403" in err_msg:
            raise Exception(
                f"Unauthorized upload to bucket '{bucket_name}'. Please ensure that:\n"
                f"1. The bucket '{bucket_name}' is set to Public in Supabase.\n"
                f"2. You have added storage RLS policies to allow uploads, OR you use the 'service_role' key in your .env."
            ) from upload_err
        elif "Bucket is not public" in err_msg or "400" in err_msg:
            raise Exception(
                f"The Supabase bucket '{bucket_name}' is set to PRIVATE. "
                f"Please go to your Supabase Dashboard -> Storage, edit the '{bucket_name}' bucket, "
                "and toggle the 'Public' option to ON (so images can be viewed publicly)."
            ) from upload_err
        else:
            raise upload_err

    # 3. Get and return the public URL
    try:
        return supabase.storage.from_(bucket_name).get_public_url(file_name)
    except Exception as url_err:
        raise Exception(f"Failed to retrieve public URL for '{file_name}': {url_err}") from url_err

