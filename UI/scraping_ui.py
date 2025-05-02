# streamlit_app.py
import streamlit as st
import requests
import json

# --- Configuration ---
# Replace with the actual URL where your Django API is running
# Corrected the URL based on standard Django dev server
DJANGO_API_BASE_URL = 'http://127.0.0.1:8000/api'

# List of websites you plan to support (matching Website.name in Django)
WEBSITES = ["MHRA Products", "BNF", "emc"]

# --- Custom CSS for Scrolling ---
# Inject CSS to make specific containers scrollable
st.markdown("""
    <style>
    .scrollable-container {
        max-height: 500px; /* Set a maximum height for the scrollable area */
        overflow-y: auto;  /* Enable vertical scrolling */
        padding-right: 15px; /* Add some padding to avoid scrollbar overlapping content */
    }
    /* Optional: Style the scrollbar */
    .scrollable-container::-webkit-scrollbar {
        width: 8px;
    }
    .scrollable-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    .scrollable-container::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 10px;
    }
    .scrollable-container::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    </style>
    """, unsafe_allow_html=True)


# --- Session State Initialization ---
# Initialize session state variables
if 'search_id' not in st.session_state:
    st.session_state.search_id = None
if 'search_query_text' not in st.session_state:
    st.session_state.search_query_text = ''
if 'search_results' not in st.session_state:
    st.session_state.search_results = {site: [] for site in WEBSITES}
if 'mhra_filter' not in st.session_state:
    st.session_state.mhra_filter = ''
if 'bnf_filter' not in st.session_state:
    st.session_state.bnf_filter = ''
if 'emc_filter' not in st.session_state:
    st.session_state.emc_filter = ''
if 'manual_correction_text' not in st.session_state:
    st.session_state.manual_correction_text = ''

# --- API Interaction Functions ---
def search_mhra_api(query):
    """Sends the search query to the Django search API."""
    # Ensure the endpoint matches your Django urls.py (e.g., /api/search/mhra/)
    search_url = f'{DJANGO_API_BASE_URL}/search/mhra/' # Corrected endpoint based on previous Django view
    try:
        response = requests.post(search_url, json={'query': query})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling Django search API: {e}")
        return {"error": str(e)}

def send_feedback_api(search_id, selected_result_ids, manual_text):
    """Sends user feedback to the Django feedback API."""
    # Ensure the endpoint matches your Django urls.py (e.g., /api/search/feedback/)
    feedback_url = f'{DJANGO_API_BASE_URL}/search/feedback/' # Corrected endpoint based on previous Django view
    feedback_data = {
        'search_id': search_id,
        'selected_result_ids': selected_result_ids,
        'manual_correction_text': manual_text,
    }
    try:
        response = requests.post(feedback_url, json=feedback_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error sending feedback to Django API: {e}")
        return {"error": str(e)}

# --- UI Layout ---
st.title("Medicine Product Search Tool")

# Search Bar and Button
st.header('Search Product')
query_input = st.text_input(
    'Enter a product name, strength or dosage:',
    st.session_state.search_query_text,
    key= 'query_text_input'
)

st.session_state.search_query_text = query_input

if st.button('Search'):
    if query_input:
        st.info(f'Searching for "{query_input}"...') # Use quotes for clarity
        # Call the API
        api_response = search_mhra_api(query_input)

        # Process API response
        if "error" not in api_response:
            st.success("Search initiated successfully!")

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

            # Clear all checkbox states from the previous search
            keys_to_delete = [key for key in st.session_state.keys() if '_result_checkbox_' in key]
            for key in keys_to_delete:
                 del st.session_state[key]

            # Rerun to display results
            st.experimental_rerun()


        else:
            st.error(f"Search failed: {api_response['error']}")

    else:
        st.warning("Please enter a search query.")

# --- Display Search Results ---
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

        # --- Wrap MHRA results in a scrollable container ---
        with st.container(): # This creates a container
             st.markdown('<div class="scrollable-container">', unsafe_allow_html=True) # Apply custom CSS class

             if not filtered_mhra_results:
                 st.info("No MHRA results found or matched the filter.")
             else:
                 st.write(f"Displaying {len(filtered_mhra_results)} of {len(st.session_state.search_results['MHRA Products'])} results.")
                 # Display filtered results with checkboxes
                 for i, result in enumerate(filtered_mhra_results):
                     # Use the result ID as part of the checkbox key for uniqueness and identification
                     # Ensure result['id'] is used if available, fallback to index if not (though IDs should be present from API)
                     result_id = result.get('id', f"idx_{i}") # Use a fallback key if id is missing
                     checkbox_key = f"mhra_result_checkbox_{result_id}_{st.session_state.search_id}"

                     # Streamlit checkbox returns True/False on click
                     # We will capture the state of ALL checkboxes on the "Save Feedback" button click
                     st.checkbox(
                         f"{result.get('title', 'Untitled Result')}",
                         key=checkbox_key,
                         value=st.session_state.get(checkbox_key, False) # Read initial state from session_state
                     )
                     if result.get('product_url'):
                         st.markdown(f"[{result['product_url']}]({result['product_url']})", unsafe_allow_html=True)

                     st.markdown("---") # Separator

             st.markdown('</div>', unsafe_allow_html=True) # Close the custom div


    # --- Column 2: BNF Results (Placeholder) ---
    with col2:
        st.subheader("BNF")
        st.session_state.bnf_filter = st.text_input(
            "Filter results:",
            st.session_state.bnf_filter,
            key="bnf_filter_input"
        )
        # --- Wrap BNF results in a scrollable container ---
        with st.container(): # This creates a container
             st.markdown('<div class="scrollable-container">', unsafe_allow_html=True) # Apply custom CSS class
             st.info("BNF search results will appear here.")
             # Future: Add scraping for BNF and display results similarly
             st.markdown('</div>', unsafe_allow_html=True) # Close the custom div


    # --- Column 3: emc Results (Placeholder) ---
    with col3:
        st.subheader("emc")
        st.session_state.emc_filter = st.text_input(
            "Filter results:",
            st.session_state.emc_filter,
            key="emc_filter_input"
        )
        # --- Wrap emc results in a scrollable container ---
        with st.container(): # This creates a container
             st.markdown('<div class="scrollable-container">', unsafe_allow_html=True) # Apply custom CSS class
             st.info("emc search results will appear here.")
             # Future: Add scraping for emc and display results similarly
             st.markdown('</div>', unsafe_allow_html=True) # Close the custom div


    # --- Manual Correction Input ---
    st.subheader("Manual Correction")
    st.session_state.manual_correction_text = st.text_area(
        "Enter the correct name if results are not satisfactory:",
        st.session_state.manual_correction_text,
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
                 # Use result.get('id') to handle cases where result might not have an ID yet (shouldn't happen with saved results)
                 result_id = result.get('id')
                 if result_id is not None: # Ensure we have a valid ID from the database
                     checkbox_key = f"{website_name.lower().replace(' ', '_')}_result_checkbox_{result_id}_{st.session_state.search_id}"
                     # Check if this key exists in the current Streamlit widget states
                     # and if its value is True (meaning the checkbox was ticked)
                     if checkbox_key in st.session_state and st.session_state[checkbox_key]:
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
                # Optionally display the response data from the feedback API
                # st.json(feedback_response)

                # --- Reset for Next Search ---
                # Clear session state for a new search
                st.session_state.search_id = None
                st.session_state.search_query_text = ""
                st.session_state.search_results = {site: [] for site in WEBSITES}
                st.session_state.mhra_filter = ""
                st.session_state.bnf_filter = ""
                st.session_state.emc_filter = ""
                st.session_state.manual_correction_text = ""

                # Clear all checkbox states by removing them from session_state
                keys_to_delete = [key for key in st.session_state.keys() if '_result_checkbox_' in key]
                for key in keys_to_delete:
                     del st.session_state[key]

            else:
                st.error(f"Failed to save feedback: {feedback_response['error']}")
        else:
            st.warning("Cannot save feedback. Please perform a search first.")

# Note: The initial page load logic is handled by Streamlit rerunning the script.
# If search_id is None, the results section is simply not displayed.
