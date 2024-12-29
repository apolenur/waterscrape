from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List, Dict, Any
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetsHandler:
    def __init__(self):
        self.creds = None
        self.service = None

    def authenticate(self) -> None:
        """Handles Google Sheets authentication process."""
        try:
            if not os.environ.get('GOOGLE_CREDENTIALS'):
                raise ValueError("Google Sheets credentials not found in environment")

            creds_data = json.loads(os.environ['GOOGLE_CREDENTIALS'])

            if creds_data['type'] != 'service_account':
                raise ValueError(f"Unsupported credential type: {creds_data['type']}")

            self.creds = service_account.Credentials.from_service_account_info(
                creds_data,
                scopes=SCOPES
            )

            self.service = build('sheets', 'v4', credentials=self.creds)
            logger.info("Successfully authenticated with Google Sheets API")

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise

    def read_accounts(self, spreadsheet_id: str, range_name: str) -> List[str]:
        """Reads account numbers from specified Google Sheet range."""
        try:
            if not self.service:
                self.authenticate()

            logger.info(f"Reading from spreadsheet {spreadsheet_id}, range {range_name}")

            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            if not values:
                logger.warning("No data found in specified range")
                return []

            # Extract account numbers from the first column
            account_numbers = [row[0].strip() for row in values if row]
            logger.info(f"Successfully read {len(account_numbers)} account numbers")
            return account_numbers

        except Exception as e:
            logger.error(f"Error reading from Google Sheet: {str(e)}")
            raise

    def export_results(self, spreadsheet_id: str, range_name: str, 
                      data: List[Dict[str, Any]], headers: List[str]) -> Any:
        """Exports results back to the Google Sheet."""
        try:
            if not self.service:
                self.authenticate()

            if not data:
                logger.warning("No data to export")
                return

            # Prepare data for export
            values = [headers]  # First row is headers
            for item in data:
                row = [str(item.get(header, '')) for header in headers]
                values.append(row)

            body = {
                'values': values,
                'majorDimension': 'ROWS'
            }

            # Update the sheet
            logger.info(f"Updating range {range_name}")
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()

            logger.info(f"Updated {result.get('updatedCells')} cells in Google Sheet")
            return result

        except Exception as e:
            logger.error(f"Error exporting to Google Sheet: {str(e)}")
            raise