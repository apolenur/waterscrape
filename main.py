import streamlit as st
import pandas as pd
from scraper import BaltimoreWaterScraper
import time
from datetime import datetime
import io
from sheets_handler import GoogleSheetsHandler
import logging

logger = logging.getLogger(__name__)

# Constants
SPREADSHEET_ID = "1yFqPWBMOAOm3O_Nr8tHcrnxfV7lccpCyDhQoJ_C5pKY"
SHEET_RANGE = "Sheet1!B2:B"

st.set_page_config(
    page_title="Baltimore Water Bill Scraper",
    page_icon="💧",
    layout="wide"
)

def export_to_excel(df: pd.DataFrame) -> bytes:
    """Export DataFrame to Excel bytes buffer"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def main():
    st.title("Baltimore City Water Bill Scraper 💧")

    # Initialize session state for storing results
    if 'current_results' not in st.session_state:
        st.session_state.current_results = []

    # Initialize Google Sheets handler
    sheets_handler = None
    try:
        sheets_handler = GoogleSheetsHandler()
        sheets_handler.authenticate()
        has_sheets_access = True
    except Exception as e:
        has_sheets_access = False
        st.error("❌ Google Sheets integration unavailable. Please check credentials.")
        return

    st.markdown("""
    This tool fetches water bill information from [Baltimore City Water](https://pay.baltimorecity.gov/water)
    using account numbers stored in [this Google Sheet](https://docs.google.com/spreadsheets/d/1yFqPWBMOAOm3O_Nr8tHcrnxfV7lccpCyDhQoJ_C5pKY).
    """)

    if st.button("Fetch Water Bills"):
        try:
            # Read account numbers from sheet
            account_list = sheets_handler.read_accounts(SPREADSHEET_ID, SHEET_RANGE)
            if not account_list:
                st.warning("No account numbers found in the spreadsheet.")
                return

            st.info(f"Found {len(account_list)} account numbers to process")

            # Setup progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()

            scraper = BaltimoreWaterScraper()
            st.session_state.current_results = []
            total = len(account_list)

            # Process each account number
            for idx, account in enumerate(account_list, 1):
                status_text.text(f"Processing account {account}...")
                try:
                    bill_info = scraper.get_bill_info(account)
                    st.session_state.current_results.append({
                        "Account Number": account,
                        "Address": bill_info.get("Service Address", "N/A"),
                        "Current Read Date": bill_info.get("Current Read Date", "N/A"),
                        "Current Bill Date": bill_info.get("Current Bill Date", "N/A"),
                        "Penalty Date": bill_info.get("Penalty Date", "N/A"),
                        "Current Bill Amount": bill_info.get("Current Bill Amount", "N/A"),
                        "Previous Balance": bill_info.get("Previous Balance", "N/A"),
                        "Current Balance": bill_info.get("Current Balance", "N/A"),
                        "Last Pay Date": bill_info.get("Last Pay Date", "N/A"),
                        "Last Pay Amount": bill_info.get("Last Pay Amount", "N/A"),
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Status": "Success"
                    })
                except Exception as e:
                    st.session_state.current_results.append({
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Account Number": account,
                        "Status": str(e)
                    })

                progress_bar.progress(idx / total)
                time.sleep(1)  # Add delay to avoid overwhelming the server

            status_text.text("Processing complete")

        except Exception as e:
            st.error(f"Failed to read account numbers: {str(e)}")
            return

    # Display results if available
    if st.session_state.current_results:
        current_df = pd.DataFrame(st.session_state.current_results)

        st.subheader("Water Bill Information")
        st.dataframe(
            current_df.style.apply(lambda x: ['background-color: #ffcdd2' if v == 'Error'
                                          else '' for v in x], axis=1),
            use_container_width=True
        )

        # Export options
        st.subheader("Export Options")

        # Add container for export status
        status_container = st.empty()
        message_container = st.empty()
        details_container = st.empty()

        if st.button("Save Results to Sheet"):
            with status_container.container():
                with st.spinner("Saving data to Google Sheets..."):
                    try:
                        # Calculate export range
                        sheet_name = SHEET_RANGE.split('!')[0]
                        #export_range = f"{sheet_name}!B1:{chr(65 + len(st.session_state.current_results[0].keys()) - 1)}{len(st.session_state.current_results) + 1}"
                        export_range = f"{sheet_name}!B1:M{len(st.session_state.current_results) + 1}"

                        export_result = sheets_handler.export_results(
                            SPREADSHEET_ID,
                            export_range,
                            st.session_state.current_results,
                            list(st.session_state.current_results[0].keys())
                        )

                        if export_result:
                            message_container.markdown("### ✅ Save Successful")
                            details_container.success(f"Saved {len(st.session_state.current_results)} rows to sheet")
                        else:
                            message_container.markdown("### ❌ Save Failed")
                            details_container.error("No response from Google Sheets API")

                    except Exception as e:
                        message_container.markdown("### ❌ Save Failed")
                        details_container.error(f"Error: {str(e)}")

        # Download as Excel
        excel_data = export_to_excel(current_df)
        st.download_button(
            label="Download as Excel",
            data=excel_data,
            file_name=f"water_bills_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()