import streamlit as st
import pandas as pd
from scraper import BaltimoreWaterScraper
import time
from datetime import datetime
import io
from sheets_handler import GoogleSheetsHandler
import os
from google.oauth2 import service_account
import json
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Baltimore Water Bill Scraper",
    page_icon="💧",
    layout="wide"
)

def export_to_excel(df: pd.DataFrame, filename: str) -> bytes:
    """
    Export DataFrame to Excel bytes buffer
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def troubleshoot_sheets_auth() -> Tuple[bool, Dict[str, str]]:
    """
    Performs a series of checks to diagnose Google Sheets authentication issues.
    """
    diagnostics = {}

    if not os.environ.get('GOOGLE_CREDENTIALS'):
        return False, {
            "status": "error",
            "message": "GOOGLE_CREDENTIALS environment variable not found",
            "fix": "Add your Google service account credentials to the GOOGLE_CREDENTIALS secret"
        }

    try:
        creds_data = json.loads(os.environ['GOOGLE_CREDENTIALS'])
        diagnostics["json_format"] = "✅ Credentials JSON format is valid"

        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [f for f in required_fields if f not in creds_data]

        if missing_fields:
            return False, {
                "status": "error",
                "message": f"Missing required fields: {', '.join(missing_fields)}",
                "fix": "Ensure your service account credentials contain all required fields"
            }

        diagnostics["required_fields"] = "✅ All required credential fields present"

        if creds_data['type'] != 'service_account':
            return False, {
                "status": "error",
                "message": "Invalid credential type. Found: " + creds_data['type'],
                "fix": "Use a service account credential JSON from Google Cloud Console"
            }

        diagnostics["credential_type"] = "✅ Using service account credentials"

        creds = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        diagnostics["credential_creation"] = "✅ Successfully created credentials"

        diagnostics["service_account_email"] = f"🔑 Service Account Email: {creds_data.get('client_email', 'Not found')}"
        diagnostics["sharing_instructions"] = """
        To grant access to your spreadsheet:
        1. Copy the service account email above
        2. Open your Google Sheet
        3. Click 'Share' in the top-right corner
        4. Paste the email and give 'Editor' access
        5. Click 'Send' (no email notification needed)
        """

        return True, diagnostics

    except json.JSONDecodeError:
        return False, {
            "status": "error",
            "message": "Invalid JSON format in credentials",
            "fix": "Verify that your credentials JSON is properly formatted"
        }
    except Exception as e:
        return False, {
            "status": "error",
            "message": str(e),
            "fix": "Check the error message and ensure your credentials are correct"
        }

def main():
    st.title("Baltimore City Water Bill Scraper 💧")

    # Initialize session state for storing results
    if 'current_results' not in st.session_state:
        st.session_state.current_results = []
    if 'spreadsheet_id' not in st.session_state:
        st.session_state.spreadsheet_id = None
    if 'range_name' not in st.session_state:
        st.session_state.range_name = None

    # Add troubleshooting section in sidebar
    with st.sidebar:
        st.header("🔧 Troubleshooting")
        if st.button("Check Google Sheets Setup"):
            success, results = troubleshoot_sheets_auth()

            if success:
                st.success("✅ Google Sheets authentication is properly configured!")
                for check, status in results.items():
                    st.write(status)
            else:
                st.error("❌ Authentication issues detected")
                st.write("**Error:**", results["message"])
                st.write("**How to fix:**", results["fix"])
                st.markdown("""
                **Need help?**
                1. Verify you have created a service account in Google Cloud Console
                2. Ensure the Google Sheets API is enabled
                3. Download and use the complete service account JSON
                4. Share your Google Sheet with the service account email
                """)

    # Initialize Google Sheets handler
    sheets_handler = None
    try:
        sheets_handler = GoogleSheetsHandler()
        sheets_handler.authenticate()
        has_sheets_access = True
    except Exception as e:
        has_sheets_access = False
        st.warning("Google Sheets integration is not available. Please check your credentials.")

    st.markdown("""
    Enter account numbers directly or import them from Google Sheets to fetch water bill information from 
    [Baltimore City Water](https://pay.baltimorecity.gov/water).
    """)

    # Input method selection
    input_method = st.radio(
        "Choose input method:",
        ["Manual Input", "Google Sheets Import"] if has_sheets_access else ["Manual Input"]
    )

    account_list = []

    if input_method == "Manual Input":
        # Input area for account numbers
        account_numbers = st.text_area(
            "Enter account numbers (one per line):",
            height=150,
            help="Enter each Baltimore water bill account number on a new line"
        )
        if account_numbers.strip():
            account_list = [acc.strip() for acc in account_numbers.strip().split('\n') if acc.strip()]
    else:
        # Google Sheets input
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.spreadsheet_id = st.text_input(
                "Enter Google Spreadsheet ID:",
                help="You can find this in the spreadsheet URL"
            )
        with col2:
            st.session_state.range_name = st.text_input(
                "Enter Range (e.g., Sheet1!A2:A10):",
                help="Specify the range containing account numbers"
            )

        if st.session_state.spreadsheet_id and st.session_state.range_name:
            try:
                account_list = sheets_handler.read_accounts(st.session_state.spreadsheet_id, st.session_state.range_name)
                st.success(f"Successfully loaded {len(account_list)} account numbers from Google Sheets")
            except Exception as e:
                st.error(f"Error reading from Google Sheets: {str(e)}")
                account_list = []

    if st.button("Fetch Water Bills"):
        if not account_list:
            st.error("Please enter at least one account number.")
            return

        # Initialize scraper
        scraper = BaltimoreWaterScraper()

        # Setup progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.empty()

        st.session_state.current_results = []
        total = len(account_list)

        # Process each account number
        for idx, account in enumerate(account_list, 1):
            status_text.text(f"Processing account {account}...")
            try:
                bill_info = scraper.get_bill_info(account)

                # Add current bill info
                st.session_state.current_results.append({
                    "Account Number": account,
                    "Address": bill_info.get("Service Address", "N/A"),
                    "Current Balance": bill_info.get("Current Balance", "N/A"),
                    "Previous Balance": bill_info.get("Previous Balance", "N/A"),
                    "Last Pay Date": bill_info.get("Last Pay Date", "N/A"),
                    "Last Pay Amount": bill_info.get("Last Pay Amount", "N/A"),
                    "Status": "Success"
                })

            except Exception as e:
                st.session_state.current_results.append({
                    "Account Number": account,
                    "Current Balance": "Error",
                    "Previous Balance": "Error",
                    "Last Pay Date": "Error",
                    "Last Pay Amount": "Error",
                    "Status": str(e)
                })

            progress_bar.progress(idx / total)
            time.sleep(1)  # Add delay to avoid overwhelming the server

    # Display results if available
    if st.session_state.current_results:
        # Create DataFrame
        current_df = pd.DataFrame(st.session_state.current_results)

        # Display results
        st.subheader("Water Bill Information")
        st.dataframe(
            current_df.style.apply(lambda x: ['background-color: #ffcdd2' if v == 'Error'
                                            else '' for v in x], axis=1),
            use_container_width=True
        )

        # Export options
        st.subheader("Export Options")

        # Google Sheets export
        if has_sheets_access and input_method == "Google Sheets Import" and st.session_state.spreadsheet_id:
            if st.button("Export Results to Google Sheets"):
                try:
                    logging.info(f"Exporting results to Google Sheets: {st.session_state.spreadsheet_id}")

                    # Calculate export range more reliably
                    sheet_name = st.session_state.range_name.split('!')[0]
                    export_range = f"{sheet_name}!A1:{chr(65 + len(st.session_state.current_results[0].keys()) - 1)}{len(st.session_state.current_results) + 1}"

                    logging.info(f"Calculated export range: {export_range}")

                    export_result = sheets_handler.export_results(
                        st.session_state.spreadsheet_id,
                        export_range,
                        st.session_state.current_results,
                        list(st.session_state.current_results[0].keys())
                    )

                    if export_result:
                        st.success(f"Successfully exported {len(st.session_state.current_results)} rows to Google Sheets")
                        st.info(f"Data exported to sheet: {sheet_name}")

                except ValueError as e:
                    st.error(f"Export failed: {str(e)}")
                    if "PERMISSION_DENIED" in str(e):
                        st.info("Please check that you've shared the spreadsheet with the service account email (shown in the troubleshooting section)")
                except Exception as e:
                    st.error(f"Error exporting to Google Sheets: {str(e)}")
                    logging.error(f"Export error details: {str(e)}")

        # File downloads
        col1, col2 = st.columns(2)

        with col1:
            # Export to CSV
            csv_data = current_df.to_csv(index=False)
            st.download_button(
                label="Download Results (CSV)",
                data=csv_data,
                file_name=f"water_bills_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

        with col2:
            # Export to Excel
            excel_data = export_to_excel(current_df, "water_bills")
            st.download_button(
                label="Download Results (Excel)",
                data=excel_data,
                file_name=f"water_bills_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()