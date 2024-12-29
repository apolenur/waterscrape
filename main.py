import streamlit as st
import pandas as pd
from scraper import BaltimoreWaterScraper
import time
from datetime import datetime
import io
import pytz
import hashlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
#SPREADSHEET_ID = "1yFqPWBMOAOm3O_Nr8tHcrnxfV7lccpCyDhQoJ_C5pKY"
#SHEET_RANGE = "Sheet1!A3:A20"

# Hardcoded credentials (username: admin, password: baltimore2024)
CREDENTIALS = {
    'admin': 'c2d5f6374c253ae1677361d33df8a85943dc8c3dc016f44b062ce608ae3da6e2'  # hashed 'baltimore2024'
}

st.set_page_config(
    page_title="Baltimore Water Bill Scraper",
    page_icon="💧",
    layout="wide"
)

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username: str, password: str) -> bool:
    """Verify username and password against hardcoded credentials"""
    if username not in CREDENTIALS:
        logger.info(f"Login attempt with invalid username: {username}")
        return False

    hashed_password = hash_password(password)
    is_valid = CREDENTIALS[username] == hashed_password

    if is_valid:
        logger.info(f"Successful login for user: {username}")
    else:
        logger.info(f"Failed login attempt for user: {username}")

    return is_valid

def show_login_page():
    """Display login form"""
    st.title("Baltimore City Water Bill Scraper 💧")
    st.markdown("### Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

    st.markdown("""
    ---
    Default credentials:
    - Username: admin
    - Password: baltimore2024
    """)

def export_to_excel(df: pd.DataFrame) -> bytes:
    """Export DataFrame to Excel bytes buffer"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def show_main_app():
    """Display main application content"""
    st.title("Baltimore City Water Bill Scraper 💧")

    # Initialize session state for storing results
    if 'current_results' not in st.session_state:
        st.session_state.current_results = []

    st.markdown(f"""
    Welcome {st.session_state.username}! This tool fetches water bill information from 
    [Baltimore City Water](https://pay.baltimorecity.gov/water).
    """)

    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.current_results = []
        st.rerun()

    if st.button("Fetch Water Bills"):
        try:
            st.info("Starting water bill fetch process...")

            # Setup progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()

            scraper = BaltimoreWaterScraper()
            st.session_state.current_results = []

            # Sample account numbers for testing
            account_list = ["12345", "67890"]  # Replace with actual account numbers
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
                        "Timestamp": datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M"),
                        "Status": "Success"
                    })
                except Exception as e:
                    st.session_state.current_results.append({
                        "Timestamp": datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M"),
                        "Account Number": account,
                        "Status": str(e)
                    })

                progress_bar.progress(idx / total)
                time.sleep(1)  # Add delay to avoid overwhelming the server

            status_text.text("Processing complete!")

        except Exception as e:
            st.error(f"Failed to process accounts: {str(e)}")
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

        # Download as Excel
        excel_data = export_to_excel(current_df)
        st.download_button(
            label="Download as Excel",
            data=excel_data,
            file_name=f"water_bills_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def main():
    """Main application entry point"""
    # Initialize session state if not already done
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.current_results = []

    # Show login page if not authenticated
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()

if __name__ == "__main__":
    main()