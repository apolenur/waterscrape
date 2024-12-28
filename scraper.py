import requests
from bs4 import BeautifulSoup
from typing import Dict
import time
import re

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
            # Initial page load to get session cookies and tokens
            response = self.session.get(
                self.base_url,
                timeout=30
            )
            response.raise_for_status()
            
            # Extract CSRF token or other required form fields
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form')
            if not form:
                raise Exception("Could not find search form")

            # Prepare search data
            search_data = {
                'address': address,
                'search_type': 'address'
                # Add any other required form fields here
            }

            # Submit search
            search_response = self.session.post(
                self.base_url,
                data=search_data,
                timeout=30,
                headers={'Referer': self.base_url}
            )
            search_response.raise_for_status()

            # Parse results
            results_soup = BeautifulSoup(search_response.text, 'html.parser')
            
            # Extract bill information
            bill_info = {
                'Current Balance': self._extract_value(results_soup, 'Current Balance'),
                'Previous Balance': self._extract_value(results_soup, 'Previous Balance'),
                'Last Pay Date': self._extract_value(results_soup, 'Last Pay Date'),
                'Last Pay Amount': self._extract_value(results_soup, 'Last Pay Amount')
            }

            # Validate extracted data
            if all(v == 'N/A' for v in bill_info.values()):
                raise Exception("No bill information found")

            return bill_info

        except requests.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            raise Exception(f"Scraping error: {str(e)}")

    def _extract_value(self, soup: BeautifulSoup, field_name: str) -> str:
        """
        Extracts specific field value from the page.
        This is a placeholder implementation - actual implementation would need to match
        the website's HTML structure.
        """
        # Find the field in the page
        field_element = soup.find(
            lambda tag: tag.name and field_name.lower() in tag.text.lower()
        )
        
        if not field_element:
            return 'N/A'

        # Extract the value
        value = field_element.find_next()
        if not value:
            return 'N/A'

        return value.text.strip()
