from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about_view, name="about"),
    path("contact/", views.contact_view, name="contact"),
    path("privacy/", views.privacy_view, name="privacy"),
    path("terms/", views.terms_view, name="terms"),
    path("ai-suggestions/", views.ai_suggestions, name="ai_suggestions"),
    path("franchises/<slug:slug>/", views.franchise_view, name="franchise_view"),
    path("directors/", views.directors_page, name="directors"),
    path("directors/<slug:slug>/", views.director_view, name="director_view"),
    path("genres/<slug:slug>/", views.genre_view, name="genre_view"),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/add/", views.add_to_wishlist, name="add_to_wishlist"),
    path("watched/add/", views.add_to_watched, name="add_to_watched"),
    path("wishlist/remove/<int:item_id>/", views.remove_from_wishlist, name="remove_from_wishlist"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
]
