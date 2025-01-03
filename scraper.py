import requests
from bs4 import BeautifulSoup
from typing import Dict
import logging
import json
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaltimoreWaterScraper:
    def __init__(self):
        self.base_url = "https://pay.baltimorecity.gov/water"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded',
        })

    def get_bill_info(self, account_number: str) -> Dict[str, str]:
        """
        Scrapes current water bill information for a given account number.

        Args:
            account_number: The water bill account number to search for

        Returns:
            Dictionary containing current bill information

        Raises:
            Exception: If scraping fails or data cannot be found
        """
        try:
            logger.info(f"Fetching bill information for account number: {account_number}")

            # Initial page load to get session cookies and tokens
            response = self.session.get(
                self.base_url,
                timeout=30
            )
            response.raise_for_status()
            logger.info("Successfully loaded initial page")

            # Extract CSRF token and form data
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form', {'id': 'accountNumberForm'})

            if not form:
                logger.error("Search form not found on page")
                logger.debug(f"Page content: {soup.prettify()[:500]}...")
                raise Exception("Could not find search form")

            # Extract hidden fields
            hidden_fields = {}
            for hidden in form.find_all('input', type='hidden'):
                hidden_fields[hidden.get('name')] = hidden.get('value', '')

            logger.debug(f"Found hidden fields: {json.dumps(hidden_fields, indent=2)}")

            # Prepare search data
            search_data = {
                **hidden_fields,
                'AccountNumber': account_number,
                'searchType': 'account',
                'action': '/water/_getInfoByAccountNumber',
                'submit': 'buttonSubmitAccountNumber'
            }

            logger.info(f"Submitting search with data: {json.dumps(search_data, indent=2)}")

            # Submit search and get water bill details
            search_response = self.session.post(
                self.base_url + '/_getInfoByAccountNumber',
                data=search_data,
                timeout=30,
                headers={
                    'Referer': self.base_url,
                    'Origin': 'https://pay.baltimorecity.gov'
                }
            )

            search_response.raise_for_status()
            logger.info("Search request successful")

            # Parse bill details page
            results_soup = BeautifulSoup(search_response.text, 'html.parser')

            # Extract current bill information
            current_bill_info = {
                'Service Address': self._extract_value(results_soup, 'Service Address'),
                'Current Balance': self._extract_value(results_soup, 'Current Balance'),
                'Previous Balance': self._extract_value(results_soup, 'Previous Balance'),
                'Last Pay Date': self._extract_value(results_soup, 'Last Pay Date'),
                'Last Pay Amount': self._extract_value(results_soup, 'Last Pay Amount'),
                'Current Read Date': self._extract_value(results_soup, 'Current Read Date'),
                'Current Bill Date': self._extract_value(results_soup, 'Current Bill Date'),
                'Penalty Date': self._extract_value(results_soup, 'Penalty Date'),
                'Current Bill Amount': self._extract_value(results_soup, 'Current Bill Amount')
            }

            # Validate extracted data
            if all(v == 'N/A' for v in current_bill_info.values()):
                logger.error("No bill information found in the response")
                raise Exception("No bill information found")

            logger.info(f"Extracted bill information: {current_bill_info}")
            return current_bill_info

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
            # Find all row divs with either class
            rows = soup.find_all('div', class_=['row', 'rowcontenteditable='])

            for row in rows:
                # Find paragraph containing the field name
                p_tag = row.find('p')
                if not p_tag:
                    continue

                # Find bold tag with field name
                b_tag = p_tag.find('b')
                if not b_tag or not re.search(field_name, b_tag.text, re.IGNORECASE):
                    continue

                # Get the full text and remove the field name to get the value
                full_text = p_tag.text.strip()
                value = full_text[len(b_tag.text):].strip()

                logger.debug(f"Found value for {field_name}: {value}")
                return value

            logger.debug(f"Field '{field_name}' not found in any row")
            return 'N/A'

        except Exception as e:
            logger.error(f"Error extracting value for {field_name}: {str(e)}")
            return 'N/A'