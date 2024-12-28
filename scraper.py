import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import time
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaltimoreWaterScraper:
    def __init__(self):
        self.base_url = "https://pay.baltimorecity.gov/water/bill"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_bill_info(self, address: str) -> Dict[str, str]:
        """
        Scrapes water bill information for a given address.

        Args:
            address: The address to search for

        Returns:
            Dictionary containing bill information

        Raises:
            Exception: If scraping fails or data cannot be found
        """
        try:
            logger.info(f"Fetching bill information for address: {address}")

            # Initial page load to get session cookies and tokens
            response = self.session.get(
                self.base_url,
                timeout=30
            )
            response.raise_for_status()
            logger.info("Successfully loaded initial page")

            # Extract CSRF token or other required form fields
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form')
            if not form:
                logger.error("Search form not found on page")
                raise Exception("Could not find search form")

            # Prepare search data
            search_data = {
                'address': address,
                'search_type': 'address'
            }
            logger.info(f"Submitting search with data: {search_data}")

            # Submit search
            search_response = self.session.post(
                self.base_url,
                data=search_data,
                timeout=30,
                headers={'Referer': self.base_url}
            )
            search_response.raise_for_status()
            logger.info("Search request successful")

            # Parse results
            results_soup = BeautifulSoup(search_response.text, 'html.parser')

            # Extract bill information
            bill_info = {
                'Current Balance': self._extract_value(results_soup, 'Current Balance'),
                'Previous Balance': self._extract_value(results_soup, 'Previous Balance'),
                'Last Pay Date': self._extract_value(results_soup, 'Last Pay Date'),
                'Last Pay Amount': self._extract_value(results_soup, 'Last Pay Amount')
            }

            logger.info(f"Extracted bill information: {bill_info}")

            # Validate extracted data
            if all(v == 'N/A' for v in bill_info.values()):
                logger.error("No bill information found in the response")
                raise Exception("No bill information found")

            return bill_info

        except requests.RequestException as e:
            logger.error(f"Network error occurred: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Scraping error occurred: {str(e)}")
            raise Exception(f"Scraping error: {str(e)}")

    def _extract_value(self, soup: BeautifulSoup, field_name: str) -> str:
        """
        Extracts specific field value from the page.
        """
        try:
            # Find elements containing the field name
            elements = soup.find_all(string=re.compile(field_name, re.IGNORECASE))

            if not elements:
                logger.debug(f"Field '{field_name}' not found in page")
                return 'N/A'

            # Get the parent element
            field_element = elements[0].parent
            if not field_element:
                return 'N/A'

            # Find the next sibling or child containing the value
            value_element = field_element.find_next_sibling() or field_element.find_next()
            if not value_element:
                return 'N/A'

            value = value_element.text.strip()
            logger.debug(f"Extracted value for {field_name}: {value}")
            return value

        except Exception as e:
            logger.error(f"Error extracting value for {field_name}: {str(e)}")
            return 'N/A'