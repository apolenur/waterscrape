import streamlit as st
import pandas as pd
from scraper import BaltimoreWaterScraper
import time

st.set_page_config(
    page_title="Baltimore Water Bill Scraper",
    page_icon="💧",
    layout="wide"
)

def main():
    st.title("Baltimore City Water Bill Scraper 💧")

    st.markdown("""
    Enter account numbers (one per line) to fetch water bill information from 
    [Baltimore City Water](https://pay.baltimorecity.gov/water).
    """)

    # Input area for account numbers
    account_numbers = st.text_area(
        "Enter account numbers (one per line):",
        height=150,
        help="Enter each Baltimore water bill account number on a new line"
    )

    if st.button("Fetch Water Bills"):
        if not account_numbers.strip():
            st.error("Please enter at least one account number.")
            return

        # Parse account numbers
        account_list = account_numbers.strip().split('\n')
        account_list = [acc.strip() for acc in account_list if acc.strip()]

        if not account_list:
            st.error("No valid account numbers to process.")
            return

        # Initialize scraper
        scraper = BaltimoreWaterScraper()

        # Setup progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.empty()

        results = []
        total = len(account_list)

        # Process each account number
        for idx, account in enumerate(account_list, 1):
            status_text.text(f"Processing account {account}...")
            try:
                bill_info = scraper.get_bill_info(account)
                results.append({
                    "Account Number": account,
                    "Current Balance": bill_info.get("Current Balance", "N/A"),
                    "Previous Balance": bill_info.get("Previous Balance", "N/A"),
                    "Last Pay Date": bill_info.get("Last Pay Date", "N/A"),
                    "Last Pay Amount": bill_info.get("Last Pay Amount", "N/A"),
                    "Status": "Success"
                })
            except Exception as e:
                results.append({
                    "Account Number": account,
                    "Current Balance": "Error",
                    "Previous Balance": "Error",
                    "Last Pay Date": "Error",
                    "Last Pay Amount": "Error",
                    "Status": str(e)
                })

            progress_bar.progress(idx / total)

            # Add delay to avoid overwhelming the server
            time.sleep(1)

        # Display results
        df = pd.DataFrame(results)

        # Format currency columns
        for col in ["Current Balance", "Previous Balance", "Last Pay Amount"]:
            df[col] = df[col].apply(lambda x: x if x == "Error" else x)

        status_text.text("Processing complete!")

        # Style the dataframe
        st.dataframe(
            df.style.apply(lambda x: ['background-color: #ffcdd2' if v == 'Error' 
                                    else '' for v in x], axis=1),
            use_container_width=True
        )

        # Download button for results
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Results CSV",
            data=csv,
            file_name="water_bills.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()