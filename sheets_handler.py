from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import List, Dict
import os
import json
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetsHandler:
    def __init__(self):
        self.creds = None
        self.service = None
        
    def authenticate(self):
        """Handles Google Sheets authentication process."""
        try:
            if os.environ.get('GOOGLE_CREDENTIALS'):
                creds_data = json.loads(os.environ['GOOGLE_CREDENTIALS'])
                self.creds = Credentials.from_authorized_user_info(creds_data, SCOPES)

            # If there are no (valid) credentials available, let's log that
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    logger.error("No valid credentials found. Please provide Google credentials.")
                    raise Exception("Google Sheets credentials not found or invalid")

            self.service = build('sheets', 'v4', credentials=self.creds)
            logger.info("Successfully authenticated with Google Sheets API")
            
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
        """
        try:
            if not self.service:
                self.authenticate()
                
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
            raise Exception(f"Failed to read account numbers: {str(e)}")

    def export_results(self, spreadsheet_id: str, range_name: str, 
                      data: List[Dict[str, str]], headers: List[str]):
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
                self.authenticate()

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
