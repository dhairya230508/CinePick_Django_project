from django.contrib import admin

from .models import WatchedItem, WishlistItem


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "release_year", "created_at")
    search_fields = ("title", "imdb_id", "user__username")
    list_filter = ("created_at",)


@admin.register(WatchedItem)
class WatchedItemAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "release_year", "created_at")
    search_fields = ("title", "imdb_id", "user__username")
    list_filter = ("created_at",)
