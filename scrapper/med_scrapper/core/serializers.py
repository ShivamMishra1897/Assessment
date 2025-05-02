# medsearch/serializers.py
from rest_framework import serializers
from .models import *


class WebsiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Website
        fields = ['id', 'name', 'url']


class SearchResultSerializer(serializers.ModelSerializer):

    class Meta:
        model = SearchResult
        fields = ['id', 'title', 'product_url', 'position', 'is_user_selected']


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)


class SearchQueryWithMhraResultsSerializer(serializers.ModelSerializer):
    mhra_results = serializers.SerializerMethodField()

    class Meta:
        model = SearchQuery
        fields = ['id', 'query_text', 'timestamp', 'mhra_results']

    def get_mhra_results(self, obj):
        # This method retrieves and serializes only the results from the MHRA website
        mhra_results = obj.results.filter(website__name='MHRA Products').order_by('position')
        return SearchResultSerializer(mhra_results, many=True).data

# --- Serializers for Feedback (Needed later) ---
class FeedbackRequestSerializer(serializers.Serializer):
    search_id = serializers.IntegerField()
    selected_result_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=[]
    )
    manual_correction_text = serializers.CharField(
        max_length=500, required=False, allow_blank=True, allow_null=True
    )

class LearnedProductSerializer(serializers.ModelSerializer):
     class Meta:
         model = LearnedProduct
         fields = ['id', 'api', 'strength', 'dosage_form', 'learning_timestamp']