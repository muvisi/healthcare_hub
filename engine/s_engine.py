from typing import List, Dict
import requests
import logging
from django.conf import settings

from smart.models import BenefitCategory
from smart.smartauth import fetch_smart_token

logger = logging.getLogger(__name__)

def push_benefits_to_smart_api(benefits: List) -> Dict[str, any]:

    """
    Push a list of BenefitCategory instances to Smart API in bulk.

    Args:
        benefits: List of BenefitCategory instances

    Returns:
        Dict with success status, message, and optional response or error
    """
    if not benefits:
        
        return {"success": False, "error": "No benefits to push"}

    try:
        # Fetch authentication token
        token = fetch_smart_token()
        if not token:
            error_msg = "Failed to fetch Smart API token"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        url = settings.SMART_BENEFITS_API_URL
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        payload = []
        for benefit in benefits:
            # bencode=benefit.clnBenCode 
            payload.append({
                "clnPolCode": str(benefit.clnPolCode or ""),
                "catCode": str(benefit.catCode or ""),
                "benTypeId": str(benefit.benTypeId or "1"),
                "subLimitAmt": float(benefit.subLimitAmt or 0),
                "serviceType": int(benefit.serviceType or 2),
                "clnBenCode": str(benefit.bencode),
                # "clnBenCode": "23",

                "benLinked2Tqcode": str(benefit.benLinked2Tqcode or ""),
                "benefitDesc": str(benefit.benefitDesc or ""),
                "memAssignedBenefit": str(benefit.memAssignedBenefit or "-1")
            })
        # print(payload)

        logger.info(f"[Smart Benefits API] Pushing {len(payload)} benefits in bulk")

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        logger.info(f"[Smart Benefits API] HTTP {response.status_code}: {response.text}")
        response.raise_for_status()
        response_data = response.json()

        return {
            "success": True,
            "message": f"Successfully pushed {len(payload)} benefits",
            "response": response_data
        }

    except requests.exceptions.Timeout:
        error_msg = "Timeout while pushing benefits to Smart API"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    except requests.exceptions.RequestException as e:
        error_msg = f"Request error while pushing benefits: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    except Exception as e:
        error_msg = f"Unexpected error while pushing benefits: {str(e)}"
        logger.exception(error_msg)
        return {"success": False, "error": error_msg}
import requests
import logging
from django.db import connections, DatabaseError, transaction
from django.conf import settings
from celery import shared_task

from smart.smartauth import fetch_smart_token
from smart.email import send_test_email
# from .models import BenefitCategory, Corporate

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="benefit_categories_sync.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

SMART_API_URL = "https://data.smartapplicationsgroup.com/api/v2/integqa/benefitCategories"
COUNTRY = "KE"
CUSTOMER_ID = settings.SMART_CUSTOMER_ID

def push_benefit_category_to_smart_api(obj: BenefitCategory):
    """
    Push a single BenefitCategory record to Smart API.
    """

    try:
        # Fetch token
        token = fetch_smart_token()
        if not token:
            msg = f"Failed to fetch Smart API token for category {obj.clnCatCode}"
            logger.error(msg)
            return {"success": False, "error": msg}

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Prepare payload
        payload = {
            "catDesc": obj.catDesc,
            "userId": obj.userId,
            "clnCatCode": obj.clnCatCode,
            "clnPolCode": obj.clnPolCode,
            "customerid": CUSTOMER_ID,
            "country": COUNTRY
        }

        logger.info(f"[Benefit Category API] Pushing {obj.clnCatCode} ({obj.clnPolCode})")

        # POST request
        response = requests.post(
            SMART_API_URL,
            params=payload,  
            json=payload,     # Smart API wants both
            headers=headers,
            timeout=30
        )

        logger.info(
            f"[Benefit Category API] HTTP {response.status_code} for {obj.clnCatCode}: {response.text}"
        )

        response.raise_for_status()  # Raises error if not 200

        return {
            "success": True,
            "message": f"Successfully synced benefit {obj.clnCatCode}",
            "response": response.json()
        }

    except requests.exceptions.Timeout:
        msg = f"Timeout while pushing benefit {obj.clnCatCode}"
        logger.error(msg)
        return {"success": False, "error": msg}

    except requests.exceptions.RequestException as e:
        msg = f"Request failed for {obj.clnCatCode}: {str(e)}"
        logger.error(msg)
        return {"success": False, "error": msg}

    except Exception as e:
        msg = f"Unexpected error pushing benefit {obj.clnCatCode}: {str(e)}"
        logger.exception(msg)
        return {"success": False, "error": msg}