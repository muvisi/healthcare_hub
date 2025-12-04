


import logging
from datetime import datetime
from typing import Optional, List, Dict
import requests
from django.conf import settings

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(filename="smart_sync.log", level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")


def fetch_smart_token() -> Optional[str]:
    """
    Fetch OAuth token from Smart API.
    Returns access_token if successful, otherwise None.
    """
    url = (
        f"{settings.SMART_TOKEN_URL}"
        f"?grant_type={settings.SMART_GRANT_TYPE}"
        f"&client_id={settings.SMART_CLIENT_ID}"
        f"&client_secret={settings.SMART_CLIENT_SECRET}"
    )
    print(f"Fetching Smart token from URL: {url}")

    try:
        response = requests.post(url, headers={}, data={}, timeout=10, verify=False)
        print(f"[Smart Token] HTTP {response.status_code}: {response.text}")
        logger.info(f"[Smart Token] HTTP {response.status_code}: {response.text}")

        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")

        if not token:
            print(f"[Smart Token] Failed to get token: {data}")
            logger.error(f"[Smart Token] Failed to get token: {data}")
        return token

    except requests.RequestException as e:
        print(f"[Smart Token] Exception: {e}")
        logger.exception(f"[Smart Token] Exception while fetching token: {e}")
        return None
