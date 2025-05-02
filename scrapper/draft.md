# medsearch/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404 # Helper for retrieving objects or returning 404

from .models import SearchQuery, Website, SearchResult, ManualCorrection, LearnedProduct
from .serializers import (
    SearchRequestSerializer,
    SearchQueryWithMhraResultsSerializer,
    FeedbackRequestSerializer,
    LearnedProductSerializer,
    SearchResultSerializer # Added import
)
from .scrapers import scrape_mhra_search # Import the scraper function
# from .learning import process_feedback_for_learning # You will need this later for AI logic

# --- Configuration ---
# Assume MHRA Website object exists in DB with name='MHRA Products'
# Fetch this once when the Django app loads
try:
    MHRA_WEBSITE_OBJ = Website.objects.get(name='MHRA Products')
    print("Successfully retrieved MHRA Website object from DB.")
except Website.DoesNotExist:
    MHRA_WEBSITE_OBJ = None
    print("ERROR: MHRA Website object not found in database. Please create a Website object with name='MHRA Products'. Scraping will fail.")
except Exception as e:
    MHRA_WEBSITE_OBJ = None
    print(f"ERROR: Unexpected error fetching MHRA Website object: {e}. Scraping will fail.")

class MhraSearchAPIView(APIView):
    """
    API endpoint to receive search query, trigger synchronous MHRA scraping,
    save results, and return them.

    NOTE: Synchronous scraping within a web request is blocking and
    NOT recommended for production. Consider using a task queue (Celery)
    for asynchronous processing in a production environment.
    """
    def post(self, request, *args, **kwargs):
        # Validate incoming request data
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True) # Raise exception if data is invalid (sends 400 response)
        query_text = serializer.validated_data['query']

        # Check if MHRA Website object is configured
        if not MHRA_WEBSITE_OBJ:
             return Response(
                 {"error": "Server configuration error: MHRA Website not found."},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )

        # --- 1. Create SearchQuery record immediately ---
        try:
            search_query = SearchQuery.objects.create(query_text=query_text)    
            print(f"Created SearchQuery ID: {search_query.id} for query: '{query_text}'")
        except Exception as e:
             print(f"Error creating SearchQuery: {e}")
             return Response(
                 {"error": f"Database error creating search query: {e}"},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )


        # --- 2. Trigger MHRA Scraping (Synchronous and Blocking) ---
        # This call will take time and block the worker process
        print(f"Starting MHRA scraping for SearchQuery ID {search_query.id}...")
        scraped_results_list, error_message = scrape_mhra_search(query_text, search_query, MHRA_WEBSITE_OBJ)
        print(f"Scraping finished for SearchQuery ID {search_query.id}.")

        # --- 3. Handle Scraping Errors ---
        if error_message:
             # If scraping failed, you might want to indicate this.
             # The SearchQuery record exists, and potentially some results were saved before failure.
             print(f"Scraping error for SearchQuery ID {search_query.id}: {error_message}")
             # Decide on response status - 500 for server error, or 200 with error details?
             # Returning 200 with error message and any scraped results might be better for UI
             # status_code = status.HTTP_500_INTERNAL_SERVER_ERROR if "WebDriver error" in error_message else status.HTTP_200_OK # Example
             # For simplicity, let's return 500 for scraping errors that blocked completion
             return Response(
                 {"search_id": search_query.id, "query": query_text, "error": error_message, "results": []},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR # Indicate a server-side issue with scraping
             )


        # --- 4. Prepare Response ---
        # The scraper function already saved the results to the DB.
        # We need to fetch them to serialize them for the response.
        # Using SearchQueryWithMhraResultsSerializer automatically filters for MHRA.
        try:
            # Prefetch related results for efficiency if needed later, though SearchQueryWithMhraResultsSerializer handles fetching
            search_query_with_results = SearchQuery.objects.get(id=search_query.id) # Use get_object_or_404 in production if ID comes from user
            response_serializer = SearchQueryWithMhraResultsSerializer(search_query_with_results)
            response_data = response_serializer.data
            print(f"Successfully serialized results for SearchQuery ID {search_query.id}")
            return Response(response_data, status=status.HTTP_200_OK)

        except SearchQuery.DoesNotExist:
            # This case should ideally not happen if we just created and scraped for it
            return Response(
                {"error": "Internal server error: Search query disappeared after scraping."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
             print(f"Error preparing response for SearchQuery ID {search_query.id}: {e}")
             return Response(
                 {"error": f"Internal server error preparing response: {e}"},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )


class SearchFeedbackAPIView(APIView):
    """
    API endpoint to receive user feedback (selected result IDs or manual entry)
    for a specific search query.

    This view updates the database based on user selections and triggers
    the derivation of the LearnedProduct for the AI component.
    """
    def post(self, request, *args, **kwargs):
        # Validate incoming feedback data
        serializer = FeedbackRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True) # Raise exception if data is invalid (sends 400 response)

        search_id = serializer.validated_data['search_id']
        selected_result_ids = serializer.validated_data.get('selected_result_ids', [])
        manual_correction_text = serializer.validated_data.get('manual_correction_text', '').strip()

        # Retrieve the associated SearchQuery
        # Use get_object_or_404 for cleaner handling if ID doesn't exist
        search_query = get_object_or_404(SearchQuery, id=search_id)
        print(f"Received feedback for SearchQuery ID: {search_id}")

        # --- 1. Process User Feedback ---

        # Reset previous selections for this search query (optional, depending on UI flow)
        # If user can resubmit feedback, you might want to clear previous selections first.
        # SearchResult.objects.filter(search_query=search_query, is_user_selected=True).update(is_user_selected=False)
        # ManualCorrection.objects.filter(search_query=search_query).delete() # Or update

        # Mark selected SearchResults
        updated_count = 0
        if selected_result_ids:
            # Filter to ensure selected IDs belong to this specific search query
            valid_selected_results_qs = SearchResult.objects.filter(
                search_query=search_query,
                id__in=selected_result_ids
            )
            # Update the boolean field in the database efficiently
            updated_count = valid_selected_results_qs.update(is_user_selected=True)
            print(f"Marked {updated_count} results as user selected for SearchQuery {search_id}")


        # Handle Manual Correction
        manual_correction_instance = None
        if manual_correction_text:
            # Create or update a ManualCorrection record for this search query.
            # update_or_create is good if the user might submit feedback multiple times
            manual_correction_instance, created = ManualCorrection.objects.update_or_create(
                search_query=search_query,
                defaults={'corrected_text': manual_correction_text}
            )
            print(f"Manual correction {'created' if created else 'updated'} for SearchQuery {search_id}")


        # --- 2. Trigger Learning/Derivation of LearnedProduct ---
        # This is where your AI/Learning logic comes in to process the feedback
        # and derive the structured product components (API, Strength, Dosage Form).
        # This logic should be in a separate function or module.

        # You need to implement a function like this:
        # derived_product_data = process_feedback_for_learning(
        #     search_query,
        #     valid_selected_results_qs if selected_result_ids else SearchResult.objects.none(), # Pass queryset
        #     manual_correction_instance
        # )
        # This function should return a dictionary like {'api': '...', 'strength': '...', 'dosage_form': '...'}
        # or None if a structured product cannot be derived from the feedback.

        # --- Placeholder Derivation Logic (Replace with actual AI/Parsing) ---
        # For now, let's use a simple example: if manual text exists, use that.
        # Otherwise, if results were selected, try to get API/Strength/Dosage from the first marked result's title.

        derived_api = ""
        derived_strength = ""
        derived_dosage_form = ""
        source_manual = None
        source_results = [] # Store actual result objects

        # Priority: Manual correction
        if manual_correction_instance:
            # Call your parser here:
            # parsed_components = parse_manual_text(manual_correction_instance.corrected_text)
            # derived_api = parsed_components.get('api', '')
            # derived_strength = parsed_components.get('strength', '')
            # derived_dosage_form = parsed_components.get('dosage_form', '')

            # Placeholder: Just use the whole text as API for simplicity now
            derived_api = manual_correction_instance.corrected_text
            source_manual = manual_correction_instance
            print(f"Attempting to derive from manual correction.")


        # If no manual correction, check selected results
        elif selected_result_ids:
             # Need to re-fetch the actual objects if not using the qs from above
             selected_results_objects = SearchResult.objects.filter(id__in=selected_result_ids, search_query=search_query)

             if selected_results_objects.exists():
                 # Call your parser here:
                 # parsed_components = parse_selected_results(selected_results_objects)
                 # derived_api = parsed_components.get('api', '')
                 # derived_strength = parsed_components.get('strength', '')
                 # derived_dosage_form = parsed_components.get('dosage_form', '')

                 # Placeholder: Use the title of the *first* selected result as API (replace with real parsing)
                 first_selected_result = selected_results_objects.order_by('position').first()
                 if first_selected_result:
                     derived_api = first_selected_result.title # Or try to extract from title/subtitle/context
                     source_results = list(selected_results_objects)
                     print(f"Attempting to derive from selected results.")

        # --- 3. Save LearnedProduct (if derivation was successful) ---
        learned_product_instance = None
        if derived_api or derived_strength or derived_dosage_form:
             try:
                 learned_product_instance, created = LearnedProduct.objects.update_or_create(
                     search_query=search_query, # One LearnedProduct entry per search
                     defaults={
                         'api': derived_api,
                         'strength': derived_strength,
                         'dosage_form': derived_dosage_form,
                         'derived_from_manual_entry': source_manual # Link manual source
                     }
                 )
                 # Link selected results (ManyToManyField)
                 if source_results:
                     learned_product_instance.derived_from_results.set(source_results) # Sets the many-to-many relationship
                 else:
                      learned_product_instance.derived_from_results.clear() # Clear if derived from manual after being results-based

                 print(f"LearnedProduct {'created' if created else 'updated'} for SearchQuery {search_id}.")

                 # Serialize the LearnedProduct to include it in the response
                 response_data = LearnedProductSerializer(learned_product_instance).data
                 return Response(response_data, status=status.HTTP_200_OK)

             except Exception as e:
                  print(f"Error saving LearnedProduct for SearchQuery {search_id}: {e}")
                  # Return a response indicating feedback received but learning failed
                  return Response(
                      {"message": "Feedback received, but an error occurred saving learning data.", "error": str(e)},
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR
                  )

        else:
             # Case where feedback was received (e.g., user clicked save with nothing selected/entered)
             # but no structured product could be derived based on the feedback.
             print(f"Feedback received for SearchQuery {search_id}, but no structured product could be derived.")
             # You might want to delete any existing LearnedProduct for this search if feedback removed options
             LearnedProduct.objects.filter(search_query=search_id).delete() # Clear old learning data if new feedback is empty
             return Response(
                 {"message": "Feedback received, but no structured product could be derived from the input."},
                 status=status.HTTP_200_OK # Indicate success in receiving feedback, even if no learning resulted
             )

Making the UI using streamlit
to create the UI choose the best and easy method to implement
Dscription for the layout is as follows :
-consider a window with a search bar and button which the user will use to enter query text which will correspond to the scrapper
 we created for the scrapper has one url otherwise it will have 2 more upon which the search the needs to happen(so a universal search for the user)
-Next below it will be three columns to the search results, each for each url/website for now since the scrapper is working with just one website , populate the 
 results of one window, others will just have the layout.
-Now each column that show the results have text search within them to search the results that have been scraped and displayed.
-each result item will have a checkbox to select the item corresponding to the logic in the backend.
-manually input the correct data according to the  backend logic
-save the results.
