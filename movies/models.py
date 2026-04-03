from django.conf import settings
from django.db import models


class WishlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    imdb_id = models.CharField(max_length=20)
    title = models.CharField(max_length=255)
    poster_url = models.URLField(blank=True)
    release_year = models.CharField(max_length=20, blank=True)
    overview = models.TextField(blank=True)
    vote_average = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "imdb_id")

    def __str__(self) -> str:
        return f"{self.user} - {self.title}"


class WatchedItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watched_items")
    imdb_id = models.CharField(max_length=20)
    title = models.CharField(max_length=255)
    poster_url = models.URLField(blank=True)
    release_year = models.CharField(max_length=20, blank=True)
    overview = models.TextField(blank=True)
    vote_average = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "imdb_id")

    def __str__(self) -> str:
        return f"{self.user} watched {self.title}"
