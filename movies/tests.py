from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import WatchedItem, WishlistItem


class AuthViewTests(TestCase):
    def test_register_creates_user_and_logs_them_in(self) -> None:
        response = self.client.post(
            reverse("register"),
            {
                "username": "cinefan",
                "email": "cinefan@example.com",
                "password": "strong-pass-123",
                "confirm_password": "strong-pass-123",
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="cinefan").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_authenticates_existing_user(self) -> None:
        User.objects.create_user(username="cinepick", email="cinepick@example.com", password="secret-123")

        response = self.client.post(
            reverse("login"),
            {
                "username": "cinepick",
                "password": "secret-123",
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_clears_session(self) -> None:
        user = User.objects.create_user(username="logoutuser", password="secret-123")
        self.client.force_login(user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)


class WishlistViewTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="moviebuff", password="secret-123")

    def test_wishlist_requires_login(self) -> None:
        response = self.client.get(reverse("wishlist"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_add_to_wishlist_creates_item(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("add_to_wishlist"),
            {
                "imdb_id": "tt0816692",
                "title": "Interstellar",
                "poster_url": "https://example.com/interstellar.jpg",
                "release_year": "2014",
                "overview": "A team travels through a wormhole.",
                "vote_average": "8.7",
                "next": reverse("wishlist"),
            },
        )

        self.assertRedirects(response, reverse("wishlist"))
        self.assertTrue(WishlistItem.objects.filter(user=self.user, imdb_id="tt0816692").exists())

    def test_add_to_watched_creates_item(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("add_to_watched"),
            {
                "imdb_id": "tt0816692",
                "title": "Interstellar",
                "next": reverse("home"),
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(WatchedItem.objects.filter(user=self.user, imdb_id="tt0816692").exists())

    def test_add_to_wishlist_is_idempotent(self) -> None:
        self.client.force_login(self.user)

        payload = {
            "imdb_id": "tt1375666",
            "title": "Inception",
            "next": reverse("wishlist"),
        }
        self.client.post(reverse("add_to_wishlist"), payload)
        self.client.post(reverse("add_to_wishlist"), payload)

        self.assertEqual(WishlistItem.objects.filter(user=self.user, imdb_id="tt1375666").count(), 1)

    def test_remove_from_wishlist_deletes_owned_item(self) -> None:
        self.client.force_login(self.user)
        item = WishlistItem.objects.create(user=self.user, imdb_id="tt0111161", title="The Shawshank Redemption")

        response = self.client.post(reverse("remove_from_wishlist", args=[item.id]), {"next": reverse("wishlist")})

        self.assertRedirects(response, reverse("wishlist"))
        self.assertFalse(WishlistItem.objects.filter(id=item.id).exists())

    def test_marking_watched_removes_watch_later_entry(self) -> None:
        self.client.force_login(self.user)
        WishlistItem.objects.create(user=self.user, imdb_id="tt1375666", title="Inception")

        self.client.post(reverse("add_to_watched"), {"imdb_id": "tt1375666", "title": "Inception", "next": reverse("home")})

        self.assertFalse(WishlistItem.objects.filter(user=self.user, imdb_id="tt1375666").exists())
        self.assertTrue(WatchedItem.objects.filter(user=self.user, imdb_id="tt1375666").exists())
