from django.db import models
from django.utils import timezone
# Create your models here.

class Website(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
    

class SearchQuery(models.Model):
    query_text = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.query
    

class SearchResult(models.Model):
    search_query = models.ForeignKey(SearchQuery, on_delete=models.CASCADE, related_name='results')
    website = models.ForeignKey(Website, on_delete=models.CASCADE)
    title = models.TextField(help_text="Main title or the product name displayed")
    position = models.PositiveSmallIntegerField(null=True, blank=True)
    product_url = models.URLField(max_length=1000, null=True, blank=True, help_text="url of the product page")
    raw_data = models.JSONField(null=True, blank=True)
    is_user_selected = models.BooleanField(default=False, help_text="is the product ticked by the user")

    def __str__(self):
        return f"Result for '{self.search_query.query_text[:30]}...' from {self.website.name}: {self.title[:50]}..."
    
    class Meta:
        ordering = ['search_query', 'website']


class ManualCorrection(models.Model):
    search_query = models.OneToOneField(SearchQuery, on_delete=models.CASCADE)
    corrected_text = models.TextField()
    correction_timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Manual Correction for '{self.search_query.query_text[:50]}...': {self.corrected_text[:50]}..."
    

class LearnedProduct(models.Model):
    search_query = models.OneToOneField(SearchQuery, on_delete=models.CASCADE)
    api = models.CharField(max_length=255)
    strength = models.CharField(max_length=255)
    dosage_form = models.CharField(max_length=255)
    derived_from_results = models.ManyToManyField(SearchResult, blank=True)
    derived_from_manual_entry = models.OneToOneField(ManualCorrection, on_delete=models.CASCADE, null=True, blank=True)
    learning_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Learned: {self.api} {self.strength} {self.dosage_form} (from Search ID {self.search_query.id})"

    
