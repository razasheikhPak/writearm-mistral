import psycopg2
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

DB_USER = "matrix"
DB_PASS = "matrix"
DB_NAME = "matrix"
DB_HOST = "/cloudsql/theahq:us-central1:matrix-os-1"  # Cloud SQL socket path

def get_instruction_by_key(key: str):
    """Fetch system instruction content for a specific key."""
    try:
        logging.debug(f"Connecting to database {DB_NAME} at {DB_HOST}")
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASS,
            dbname=DB_NAME,
            host=DB_HOST
        )
        cur = conn.cursor()
        logging.debug(f"Executing query to fetch content for key: {key}")
        cur.execute(
            "SELECT content FROM public.system_instructions WHERE key = %s;",
            (key,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            logging.info(f"Fetched content for key {key}")
            return result[0]  # Return content
        else:
            logging.warning(f"No content found for key {key}")
            return None
    except Exception as e:
        logging.error(f"Error fetching content for key {key}: {e}")
        return None
