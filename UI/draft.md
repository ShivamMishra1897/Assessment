# streamlit_app.py
import streamlit as st
import requests
import json # Needed if your API uses JSONField and returns raw data

# --- Configuration ---
# Replace with the actual URL where your Django API is running
DJANGO_API_BASE_URL = 'http://localhost:8000/api'

# List of websites you plan to support (matching Website.name in Django)
WEBSITES = ["MHRA Products", "BNF", "emc"]

# --- Session State Initialization ---
# Initialize session state variables if they don't exist
if 'search_id' not in st.session_state:
    st.session_state.search_id = None
if 'search_query_text' not in st.session_state:
    st.session_state.search_query_text = ""
if 'search_results' not in st.session_state:
    # Store results from the API call {website_name: [list of result dicts], ...}
    st.session_state.search_results = {site: [] for site in WEBSITES}
if 'mhra_filter' not in st.session_state:
    st.session_state.mhra_filter = ""
if 'bnf_filter' not in st.session_state:
    st.session_state.bnf_filter = ""
if 'emc_filter' not in st.session_state:
    st.session_state.emc_filter = ""
if 'manual_correction_text' not in st.session_state:
    st.session_state.manual_correction_text = ""
# We won't store individual checkbox states here, we'll capture them on Save

# --- API Interaction Functions ---

def search_mhra_api(query):
    """Sends the search query to the Django MHRA search API."""
    search_url = f'{DJANGO_API_BASE_URL}/search/mhra/'
    try:
        response = requests.post(search_url, json={'query': query})
        response.raise_for_status() # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling Django search API: {e}")
        return {"error": str(e)} # Return error structure

def send_feedback_api(search_id, selected_result_ids, manual_text):
    """Sends user feedback to the Django feedback API."""
    feedback_url = f'{DJANGO_API_BASE_URL}/search/feedback/'
    feedback_data = {
        'search_id': search_id,
        'selected_result_ids': selected_result_ids,
        'manual_correction_text': manual_text,
    }
    try:
        response = requests.post(feedback_url, json=feedback_data)
        response.raise_for_status() # Raise an exception for bad status codes
        return response.json() # Should return LearnedProduct or status
    except requests.exceptions.RequestException as e:
        st.error(f"Error sending feedback to Django API: {e}")
        return {"error": str(e)}

# --- UI Layout ---

st.title("Medicine Product Search Tool")

# --- Search Bar and Button ---
st.header("Search Product")
query_input = st.text_input(
    "Enter a product name, active substance, or number:",
    st.session_state.search_query_text, # Use session state to remember last query
    key="query_text_input" # Unique key for this widget
)

# Store the latest query text in session state whenever input changes
st.session_state.search_query_text = query_input

if st.button("Search"):
    if query_input:
        st.info(f"Searching for '{query_input}'...")
        # Call the API
        api_response = search_mhra_api(query_input)

        # Process API response
        if "error" not in api_response:
            st.success("Search initiated successfully!")
            # Store results in session state
            st.session_state.search_id = api_response.get('id')
            # The MHRA results are nested under 'mhra_results' in the response
            mhra_results_list = api_response.get('mhra_results', [])
            st.session_state.search_results["MHRA Products"] = mhra_results_list
            # For other sites (BNF, emc), they would be populated here when implemented
            st.session_state.search_results["BNF"] = [] # Placeholder
            st.session_state.search_results["emc"] = [] # Placeholder

            # Clear previous filters and manual correction on new search
            st.session_state.mhra_filter = ""
            st.session_state.bnf_filter = ""
            st.session_state.emc_filter = ""
            st.session_state.manual_correction_text = ""

            # Clear previous checkbox states by rerunning or explicitly managing
            # Streamlit reruns automatically after button click, clearing simple widget state,
            # but session_state persists. Checkbox state needs careful handling on display.

        else:
            st.error(f"Search failed: {api_response['error']}")

    else:
        st.warning("Please enter a search query.")

# --- Display Search Results (if any) ---
if st.session_state.search_id is not None:
    st.header(f"Results for: '{st.session_state.search_query_text}' (Search ID: {st.session_state.search_id})")

    # Use columns for side-by-side display
    col1, col2, col3 = st.columns(3)

    # --- Column 1: MHRA Results ---
    with col1:
        st.subheader("MHRA Products")
        st.session_state.mhra_filter = st.text_input(
            "Filter results:",
            st.session_state.mhra_filter,
            key="mhra_filter_input"
        )

        # Filter MHRA results based on the filter text
        filtered_mhra_results = [
            res for res in st.session_state.search_results["MHRA Products"]
            if st.session_state.mhra_filter.lower() in res.get('title', '').lower()
        ]

        if not filtered_mhra_results:
            st.info("No MHRA results found or matched the filter.")
        else:
            st.write(f"Displaying {len(filtered_mhra_results)} of {len(st.session_state.search_results['MHRA Products'])} results.")
            # Display filtered results with checkboxes
            for i, result in enumerate(filtered_mhra_results):
                # Use the result ID as part of the checkbox key for uniqueness and identification
                checkbox_key = f"mhra_result_checkbox_{result.get('id', i)}_{st.session_state.search_id}"

                # Streamlit checkbox returns True/False on click
                # We will capture the state of ALL checkboxes on the "Save Feedback" button click
                st.checkbox(
                    f"{result.get('title', 'Untitled Result')}",
                    key=checkbox_key,
                    value=False # Default state is False when first displayed
                    # Add a help text or label explaining what it is
                )
                if result.get('product_url'):
                    st.markdown(f"[{result['product_url']}]({result['product_url']})", unsafe_allow_html=True)
                # Add other details like position if needed
                # st.write(f"Position: {result.get('position', 'N/A')}")

                st.markdown("---") # Separator

    # --- Column 2: BNF Results (Placeholder) ---
    with col2:
        st.subheader("BNF")
        st.session_state.bnf_filter = st.text_input(
            "Filter results:",
            st.session_state.bnf_filter,
            key="bnf_filter_input"
        )
        st.info("BNF search results will appear here.")
        # Future: Add scraping for BNF and display results similarly

    # --- Column 3: emc Results (Placeholder) ---
    with col3:
        st.subheader("emc")
        st.session_state.emc_filter = st.text_input(
            "Filter results:",
            st.session_state.emc_filter,
            key="emc_filter_input"
        )
        st.info("emc search results will appear here.")
        # Future: Add scraping for emc and display results similarly


    # --- Manual Correction Input ---
    st.subheader("Manual Correction")
    st.session_state.manual_correction_text = st.text_area(
        "Enter the correct product name manually if results are not satisfactory:",
        st.session_state.manual_correction_text, # Remember previous manual input
        key="manual_correction_input"
    )

    # --- Save Feedback Button ---
    if st.button("Save Feedback & Next Search"):
        # --- Collect Selected Result IDs ---
        selected_result_ids = []
        # Iterate through ALL search results currently stored in session state
        for website_name, results_list in st.session_state.search_results.items():
             for result in results_list:
                 # Construct the key used for the checkbox when displaying
                 checkbox_key = f"{website_name.lower().replace(' ', '_')}_result_checkbox_{result.get('id', 'no_id')}_{st.session_state.search_id}"
                 # Check if this key exists in the current Streamlit widget states
                 # and if its value is True (meaning the checkbox was ticked)
                 # Use result.get('id') to handle cases where result might not have an ID yet (shouldn't happen with saved results)
                 result_id = result.get('id')
                 if result_id is not None and checkbox_key in st.session_state and st.session_state[checkbox_key]:
                     selected_result_ids.append(result_id)

        st.info(f"Selected Result IDs: {selected_result_ids}")
        st.info(f"Manual Correction: '{st.session_state.manual_correction_text}'")

        # --- Send Feedback to API ---
        if st.session_state.search_id is not None:
            st.info("Sending feedback to Django API...")
            feedback_response = send_feedback_api(
                st.session_state.search_id,
                selected_result_ids,
                st.session_state.manual_correction_text
            )

            if "error" not in feedback_response:
                st.success("Feedback saved and learning data updated!")
                st.json(feedback_response) # Display the response from the feedback API (e.g., LearnedProduct data)

                # --- Reset for Next Search ---
                # Clear session state for a new search
                st.session_state.search_id = None
                st.session_state.search_query_text = "" # Optionally keep the last query
                st.session_state.search_results = {site: [] for site in WEBSITES}
                st.session_state.mhra_filter = ""
                st.session_state.bnf_filter = ""
                st.session_state.emc_filter = ""
                st.session_state.manual_correction_text = ""

                # Clear all checkbox states by removing them from session_state
                keys_to_delete = [key for key in st.session_state.keys() if '_result_checkbox_' in key]
                for key in keys_to_delete:
                     del st.session_state[key]


                st.experimental_rerun() # Rerun the app to show the cleared state

            else:
                st.error(f"Failed to save feedback: {feedback_response['error']}")
        else:
            st.warning("Cannot save feedback. Please perform a search first.")


# --- Initial Page Load / Rerun without search ---
# This part runs if session_state.search_id is None (initial load or after Save & Next)
# The layout and search bar are always displayed. The results section is conditional.