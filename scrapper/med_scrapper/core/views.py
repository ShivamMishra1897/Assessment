from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import *
from .serializers import *
from .webscrapper import scrape_search

try:
    MHRA_WEBSITE_OBJ = Website.objects.get(name='MHRA Products')
    print("Successfully retrieved MHRA Website object from DB.")
except Website.DoesNotExist:
    MHRA_WEBSITE_OBJ = None
    print("ERROR: MHRA Website object not found in database. Please create a Website object with name='MHRA Products'. Scraping will fail.")
except Exception as e:
    MHRA_WEBSITE_OBJ = None
    print(f"ERROR: Unexpected error fetching MHRA Website object: {e}. Scraping will fail.")


class SearchAPIView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query_text = serializer.validated_data['query']

        if not MHRA_WEBSITE_OBJ:
             return Response(
                 {"error": "Server configuration error: MHRA Website not found."},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )

        # --- 1. Create SearchQuery record ---
        try:
            search_query = SearchQuery.objects.create(query_text=query_text)    
            print(f"Created SearchQuery ID: {search_query.id} for query: '{query_text}'")
        except Exception as e:
             print(f"Error creating SearchQuery: {e}")
             return Response(
                 {"error": f"Database error creating search query: {e}"},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )

        # --- 2. Trigger Scraping ---
        # This call will take time and block the worker process
        print(f"Starting MHRA scraping for SearchQuery ID {search_query.id}...")
        scraped_results_list, error_message = scrape_search(query_text, search_query, MHRA_WEBSITE_OBJ)
        print(f"Scraping finished for SearchQuery ID {search_query.id}.")

        # --- 3. Handle Scraping Errors ---
        if error_message:
             print(f"Scraping error for SearchQuery ID {search_query.id}: {error_message}")
             return Response(
                 {"search_id": search_query.id, "query": query_text, "error": error_message, "results": []},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR # Indicate a server-side issue with scraping
             )

        # --- 4. Prepare Response ---
        try:
            search_query_with_results = SearchQuery.objects.get(id=search_query.id)
            response_serializer = SearchQueryWithMhraResultsSerializer(search_query_with_results)
            response_data = response_serializer.data
            print(f"Successfully serialized results for SearchQuery ID {search_query.id}")
            return Response(response_data, status=status.HTTP_200_OK)

        except SearchQuery.DoesNotExist:
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

    def post(self, request, *args, **kwargs):
        serializer = FeedbackRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        search_id = serializer.validated_data['search_id']
        selected_result_ids = serializer.validated_data.get('selected_result_ids', [])
        manual_correction_text = serializer.validated_data.get('manual_correction_text', '').strip()

        search_query = get_object_or_404(SearchQuery, id=search_id)
        print(f"Received feedback for SearchQuery ID: {search_id}")

        #--- Process User Feedback ---
        # Mark selected SearchResults
        updated_count = 0
        if selected_result_ids:
            valid_selected_results_qs = SearchResult.objects.filter(
                search_query = search_query,
                id__in = selected_result_ids
            )
            updated_count = valid_selected_results_qs.update(is_user_selected=True)
            print(f"Marked {updated_count} results as user selected for SearchQuery {search_id}")

        # Handle Manual Correction
        manual_correction_instance = None
        if manual_correction_text:
            manual_correction_instance, created = ManualCorrection.objects.update_or_create(
                search_query=search_query,
                defaults={'corrected_text': manual_correction_text}
            )
            print(f"Manual correction {'created' if created else 'updated'} for SearchQuery {search_id}")

        derived_api = ""
        derived_strength = ""
        derived_dosage_form = ""
        source_manual = None
        source_results = [] 

        # Priority: Manual correction
        if manual_correction_instance:
            derived_api = manual_correction_instance.corrected_text
            source_manual = manual_correction_instance
            print(f"Attempting to derive from manual correction.")
        
        # If no manual correction, check selected results
        elif selected_result_ids:
             selected_results_objects = SearchResult.objects.filter(id__in=selected_result_ids, search_query=search_query)

             if selected_results_objects.exists():
                 first_selected_result = selected_results_objects.order_by('position').first()
                 if first_selected_result:
                     derived_api = first_selected_result.title
                     source_results = list(selected_results_objects)
                     print(f"Attempting to derive from selected results.")

        # --- Save LearnedProduct ---
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
                  return Response(
                      {"message": "Feedback received, but an error occurred saving learning data.", "error": str(e)},
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR
                  )

        else:
             print(f"Feedback received for SearchQuery {search_id}, but no structured product could be derived.")
             # You might want to delete any existing LearnedProduct for this search if feedback removed options
             LearnedProduct.objects.filter(search_query=search_id).delete() # Clear old learning data if new feedback is empty
             return Response(
                 {"message": "Feedback received, but no structured product could be derived from the input."},
                 status=status.HTTP_200_OK # Indicate success in receiving feedback, even if no learning resulted
             )