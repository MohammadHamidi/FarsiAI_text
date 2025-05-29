import firebase_admin
from firebase_admin import credentials
import logging
import httpx
import uuid
from .config import settings

logger = logging.getLogger(__name__)

# Create a persistent httpx client session for connection pooling and performance
# Ensure it's closed properly during application shutdown (though for serverless/short-lived, might not be critical)
# For a long-running FastAPI app, you might manage this client in the app's lifespan events.
# For now, a module-level client is simple.
# Consider adding timeout configurations.
client = httpx.AsyncClient(timeout=10.0)

def initialize_firebase():
    """Initializes the Firebase Admin SDK."""
    if not settings.FIREBASE_ANALYTICS_ENABLED:
        logger.info("Firebase Analytics is disabled. GA Measurement Protocol may still be active if configured.")
        return

    if not settings.FIREBASE_SERVICE_ACCOUNT_KEY_PATH:
        logger.error("Firebase service account key path is not set. Firebase Admin SDK part will be disabled.")
        return

    try:
        if not firebase_admin._apps: # Check if already initialized
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully.")
        else:
            logger.info("Firebase Admin SDK already initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)

async def track_event(event_name: str, event_params: dict = None, user_ip: str = None, user_agent: str = None):
    """
    Tracks a custom event to Google Analytics 4 using the Measurement Protocol.
    Firebase Admin SDK's own analytics capabilities are limited for custom server-side events.
    """
    if not settings.FIREBASE_ANALYTICS_ENABLED:
        logger.debug(f"Firebase Analytics (overall feature) is disabled. Event '{event_name}' not tracked.")
        return

    if not settings.GA_MEASUREMENT_ID or not settings.GA_API_SECRET:
        logger.warning(
            f"GA_MEASUREMENT_ID or GA_API_SECRET is not configured. "
            f"Cannot send event '{event_name}' to Google Analytics."
        )
        return

    # For server-side events, a stable client_id is recommended.
    # This could be a hashed user ID if available, or a randomly generated UUID
    # if you can't tie it to a specific user. For simplicity, we generate one per event.
    # Ideally, you'd want to manage client_id more consistently if tracking user journeys.
    # A common practice is to use a unique ID for the instance or session.
    # Since we don't have user sessions here, we generate a new one each time.
    # Or, if you have a client-side GA instance, you might pass its client_id to the backend.
    client_id = str(uuid.uuid4())

    payload = {
        "client_id": client_id,
        "non_personalized_ads": False, # Adjust as needed based on privacy/consent
        "events": [{
            "name": event_name,
            "params": event_params or {}
        }]
    }
    
    # Add user_ip and user_agent to event_params if available,
    # GA4 might use these for some processing or reporting.
    # Note: Be mindful of PII and privacy regulations when handling IP addresses.
    # GA4 has IP anonymization enabled by default.
    if user_ip:
        payload["events"][0]["params"]["user_ip_address"] = user_ip # Use standard GA4 parameter name if available
    if user_agent:
        payload["events"][0]["params"]["user_agent"] = user_agent

    url = f"https://www.google-analytics.com/mp/collect?measurement_id={settings.GA_MEASUREMENT_ID}&api_secret={settings.GA_API_SECRET}"

    try:
        response = await client.post(url, json=payload)
        response.raise_for_status()  # Raises an exception for 4XX/5XX responses
        logger.info(
            f"Event '{event_name}' sent to Google Analytics. "
            f"Client ID: {client_id}, Status: {response.status_code}"
        )
        # For debugging Measurement Protocol hits:
        # You can use the GA4 Event Debugger or Realtime reports.
        # For more detailed validation, send to:
        # https://www.google-analytics.com/debug/mp/collect?measurement_id=...&api_secret=...
        # The response will be JSON with validation messages.
        # logger.debug(f"GA Response: {response.text}")
        
    except httpx.RequestError as e:
        logger.error(
            f"HTTP request error sending event '{event_name}' to Google Analytics: {e}",
            exc_info=True
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP status error sending event '{event_name}' to Google Analytics: {e.response.status_code} "
            f"Response: {e.response.text}",
            exc_info=True
        )
    except Exception as e:
        logger.error(
            f"Unexpected error sending event '{event_name}' to Google Analytics: {e}",
            exc_info=True
        )

# Consider adding a shutdown event for the httpx.AsyncClient if managing it globally
# async def close_httpx_client():
#    await client.aclose()
# This would typically be registered with FastAPI's "shutdown" event. 