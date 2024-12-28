import streamlit as st
import pandas as pd
from scraper import BaltimoreWaterScraper
from utils import validate_addresses, format_currency
import time

st.set_page_config(
    page_title="Baltimore Water Bill Scraper",
    page_icon="💧",
    layout="wide"
)

def main():
    st.title("Baltimore City Water Bill Scraper 💧")
    
    st.markdown("""
    Enter addresses (one per line) to fetch water bill information from 
    [Baltimore City Water](https://pay.baltimorecity.gov/water/bill).
    """)

    # Input area for addresses
    addresses = st.text_area(
        "Enter addresses (one per line):",
        height=150,
        help="Enter each Baltimore address on a new line"
    )

    if st.button("Fetch Water Bills"):
        if not addresses.strip():
            st.error("Please enter at least one address.")
            return

        # Parse and validate addresses
        address_list = addresses.strip().split('\n')
        address_list = [addr.strip() for addr in address_list if addr.strip()]
        
        valid_addresses, invalid_addresses = validate_addresses(address_list)
        
        if invalid_addresses:
            st.warning("Some addresses appear to be invalid:")
            for addr in invalid_addresses:
                st.write(f"❌ {addr}")
        
        if not valid_addresses:
            st.error("No valid addresses to process.")
            return

        # Initialize scraper
        scraper = BaltimoreWaterScraper()
        
        # Setup progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.empty()
        
        results = []
        total = len(valid_addresses)
        
        # Process each address
        for idx, address in enumerate(valid_addresses, 1):
            status_text.text(f"Processing {address}...")
            try:
                bill_info = scraper.get_bill_info(address)
                results.append({
                    "Address": address,
                    "Current Balance": bill_info.get("Current Balance", "N/A"),
                    "Previous Balance": bill_info.get("Previous Balance", "N/A"),
                    "Last Pay Date": bill_info.get("Last Pay Date", "N/A"),
                    "Last Pay Amount": bill_info.get("Last Pay Amount", "N/A"),
                    "Status": "Success"
                })
            except Exception as e:
                results.append({
                    "Address": address,
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
            df[col] = df[col].apply(lambda x: format_currency(x) if x != "Error" else x)
        
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
