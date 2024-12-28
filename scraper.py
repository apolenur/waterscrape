import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import time
import re
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaltimoreWaterScraper:
    def __init__(self):
        self.base_url = "https://pay.baltimorecity.gov/water/bill"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded',
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

            # Extract CSRF token and form data
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form', {'method': 'POST'})

            if not form:
                logger.error("Search form not found on page")
                logger.debug(f"Page content: {soup.prettify()[:500]}...")
                raise Exception("Could not find search form")

            # Extract all hidden fields
            hidden_fields = {}
            for hidden in form.find_all('input', type='hidden'):
                hidden_fields[hidden.get('name')] = hidden.get('value', '')

            logger.debug(f"Found hidden fields: {json.dumps(hidden_fields, indent=2)}")

            # Find the Service Address input field
            service_address_input = form.find('input', {'id': 'serviceAddress'}) or form.find('input', {'name': 'serviceAddress'})
            if not service_address_input:
                logger.error("Service Address input field not found")
                raise Exception("Could not find Service Address input field")

            # Get the actual field name from the input
            address_field_name = service_address_input.get('name', 'serviceAddress')

            # Prepare search data with all required fields
            search_data = {
                **hidden_fields,
                address_field_name: address,
                'searchType': 'address',
                'action': 'search',  # This typically indicates the search button action
                'submit': 'Search'
            }

            logger.info(f"Submitting search with data: {json.dumps(search_data, indent=2)}")

            # Submit search
            search_response = self.session.post(
                self.base_url,
                data=search_data,
                timeout=30,
                headers={
                    'Referer': self.base_url,
                    'Origin': 'https://pay.baltimorecity.gov'
                }
            )

            # Log response details for debugging
            logger.debug(f"Response status: {search_response.status_code}")
            logger.debug(f"Response headers: {json.dumps(dict(search_response.headers), indent=2)}")

            search_response.raise_for_status()
            logger.info("Search request successful")

            # Parse results
            results_soup = BeautifulSoup(search_response.text, 'html.parser')

            # Save response HTML for debugging
            logger.debug(f"Response HTML: {results_soup.prettify()[:1000]}...")

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
            logger.debug(f"Request exception details: {str(e.__dict__)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Scraping error occurred: {str(e)}")
            raise Exception(f"Scraping error: {str(e)}")

    def _extract_value(self, soup: BeautifulSoup, field_name: str) -> str:
        """
        Extracts specific field value from the page.
        """
        try:
            # Try multiple approaches to find the value

            # Approach 1: Direct text search
            elements = soup.find_all(string=re.compile(field_name, re.IGNORECASE))

            # Approach 2: Search in table cells
            if not elements:
                elements = soup.find_all('td', string=re.compile(field_name, re.IGNORECASE))

            # Approach 3: Search in div elements
            if not elements:
                elements = soup.find_all('div', string=re.compile(field_name, re.IGNORECASE))

            if not elements:
                logger.debug(f"Field '{field_name}' not found in page")
                return 'N/A'

            for element in elements:
                # Get the parent element
                parent = element.parent

                # Try different ways to find the value
                value_element = (
                    parent.find_next_sibling() or
                    parent.find_next() or
                    (parent.parent and parent.parent.find_next_sibling())
                )

                if value_element:
                    value = value_element.text.strip()
                    logger.debug(f"Found value for {field_name}: {value}")
                    return value

            return 'N/A'

        except Exception as e:
            logger.error(f"Error extracting value for {field_name}: {str(e)}")
            return 'N/A'