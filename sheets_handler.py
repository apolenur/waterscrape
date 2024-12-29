from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import List, Dict, Optional, Any
import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Changed to DEBUG for more detailed logs
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetsHandler:
    def __init__(self):
        self.creds = None
        self.service = None

    def authenticate(self) -> None:
        """Handles Google Sheets authentication process."""
        try:
            if os.environ.get('GOOGLE_CREDENTIALS'):
                logger.info("Found GOOGLE_CREDENTIALS in environment")
                try:
                    creds_data = json.loads(os.environ['GOOGLE_CREDENTIALS'])
                    logger.info(f"Credential type: {creds_data.get('type', 'unknown')}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse credentials JSON: {e}")
                    raise ValueError("Invalid credentials JSON format")

                required_fields = ['type', 'project_id', 'private_key', 'client_email']
                if not all(field in creds_data for field in required_fields):
                    missing = [f for f in required_fields if f not in creds_data]
                    logger.error(f"Missing required fields in credentials: {missing}")
                    raise ValueError(f"Missing required fields in credentials: {missing}")

                try:
                    if creds_data['type'] == 'service_account':
                        logger.info("Using service account credentials")
                        self.creds = service_account.Credentials.from_service_account_info(
                            creds_data,
                            scopes=SCOPES
                        )
                        logger.debug("Service account credentials created successfully")
                    else:
                        logger.error(f"Unsupported credential type: {creds_data['type']}")
                        raise ValueError(f"Unsupported credential type: {creds_data['type']}")
                except Exception as e:
                    logger.error(f"Error creating service account credentials: {str(e)}")
                    raise ValueError(f"Failed to create credentials: {str(e)}")

                try:
                    self.service = build('sheets', 'v4', credentials=self.creds)
                    logger.info("Successfully authenticated with Google Sheets API")
                except Exception as e:
                    logger.error(f"Error building sheets service: {str(e)}")
                    raise
            else:
                logger.error("GOOGLE_CREDENTIALS environment variable not found")
                raise ValueError("Google Sheets credentials not found in environment")

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise Exception(f"Failed to authenticate with Google Sheets: {str(e)}")

    def read_accounts(self, spreadsheet_id: str, range_name: str) -> List[str]:
        """
        Reads account numbers from specified Google Sheet range.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation of the range to read

        Returns:
            List of account numbers

        Raises:
            ValueError: If there are permission issues or invalid spreadsheet access
        """
        try:
            if not self.service:
                logger.info("Service not initialized, authenticating first")
                self.authenticate()

            logger.info(f"Reading from spreadsheet {spreadsheet_id}, range {range_name}")
            try:
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
            except Exception as e:
                if "PERMISSION_DENIED" in str(e):
                    logger.error(f"Permission denied accessing spreadsheet: {str(e)}")
                    raise ValueError(
                        "Permission denied. Please share the spreadsheet with the service account email "
                        "and ensure it has editor access."
                    )
                raise

            values = result.get('values', [])
            if not values:
                logger.warning("No data found in specified range")
                return []

            # Extract account numbers from the first column
            account_numbers = [row[0].strip() for row in values if row]
            logger.info(f"Successfully read {len(account_numbers)} account numbers")
            return account_numbers

        except ValueError as e:
            # Re-raise ValueError with permission guidance
            raise
        except Exception as e:
            logger.error(f"Error reading from Google Sheet: {str(e)}")
            if "HttpError 404" in str(e):
                raise ValueError("Spreadsheet not found. Please check the spreadsheet ID.")
            raise Exception(f"Failed to read account numbers: {str(e)}")

    def export_results(self, spreadsheet_id: str, range_name: str, 
                      data: List[Dict[str, Any]], headers: List[str]) -> None:
        """
        Exports results back to the Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation of the range to update
            data: List of dictionaries containing the results
            headers: List of column headers
        """
        try:
            if not self.service:
                logger.info("Service not initialized, authenticating first")
                self.authenticate()

            if not data:
                logger.warning("No data to export")
                return

            logger.info(f"Preparing to export {len(data)} rows to sheet {spreadsheet_id}")

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

        except Exception as e:
            logger.error(f"Error exporting to Google Sheet: {str(e)}")
            raise Exception(f"Failed to export results: {str(e)}")