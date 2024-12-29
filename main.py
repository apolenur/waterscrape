import streamlit as st
import pandas as pd
from scraper import BaltimoreWaterScraper
import time
from datetime import datetime
import io

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

        current_results = []
        historical_results = []
        total = len(account_list)

        # Process each account number
        for idx, account in enumerate(account_list, 1):
            status_text.text(f"Processing account {account}...")
            try:
                bill_info = scraper.get_bill_info(account)

                # Add current bill info
                current_results.append({
                    "Account Number": account,
                    "Current Balance": bill_info['current'].get("Current Balance", "N/A"),
                    "Previous Balance": bill_info['current'].get("Previous Balance", "N/A"),
                    "Last Pay Date": bill_info['current'].get("Last Pay Date", "N/A"),
                    "Last Pay Amount": bill_info['current'].get("Last Pay Amount", "N/A"),
                    "Status": "Success"
                })

                # Add historical data
                for history_entry in bill_info.get('history', []):
                    history_entry['Account Number'] = account
                    historical_results.append(history_entry)

            except Exception as e:
                current_results.append({
                    "Account Number": account,
                    "Current Balance": "Error",
                    "Previous Balance": "Error",
                    "Last Pay Date": "Error",
                    "Last Pay Amount": "Error",
                    "Status": str(e)
                })

            progress_bar.progress(idx / total)
            time.sleep(1)  # Add delay to avoid overwhelming the server

        # Create DataFrames
        current_df = pd.DataFrame(current_results)
        historical_df = pd.DataFrame(historical_results) if historical_results else None

        status_text.text("Processing complete!")

        # Display current results
        st.subheader("Current Bill Information")
        st.dataframe(
            current_df.style.apply(lambda x: ['background-color: #ffcdd2' if v == 'Error' 
                                    else '' for v in x], axis=1),
            use_container_width=True
        )

        # Display historical data if available
        if historical_df is not None and not historical_df.empty:
            st.subheader("Bill History")
            st.dataframe(historical_df, use_container_width=True)

        # Export options
        st.subheader("Export Options")

        # Current bills export
        col1, col2 = st.columns(2)

        with col1:
            # Export current bills to CSV
            csv_current = current_df.to_csv(index=False)
            st.download_button(
                label="Download Current Bills (CSV)",
                data=csv_current,
                file_name=f"water_bills_current_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

            if historical_df is not None and not historical_df.empty:
                # Export history to CSV
                csv_history = historical_df.to_csv(index=False)
                st.download_button(
                    label="Download Bill History (CSV)",
                    data=csv_history,
                    file_name=f"water_bills_history_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

        with col2:
            # Export current bills to Excel
            excel_current = export_to_excel(current_df, "current_bills")
            st.download_button(
                label="Download Current Bills (Excel)",
                data=excel_current,
                file_name=f"water_bills_current_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            if historical_df is not None and not historical_df.empty:
                # Export history to Excel
                excel_history = export_to_excel(historical_df, "bill_history")
                st.download_button(
                    label="Download Bill History (Excel)",
                    data=excel_history,
                    file_name=f"water_bills_history_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()