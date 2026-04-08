from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import WatchedItem, WishlistItem
from . import views


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


class StaticPageViewTests(TestCase):
    def test_contact_page_loads(self) -> None:
        response = self.client.get(reverse("contact"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contact CinePick")

    def test_privacy_page_loads(self) -> None:
        response = self.client.get(reverse("privacy"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Privacy at CinePick")

    def test_terms_page_loads(self) -> None:
        response = self.client.get(reverse("terms"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Terms for Using CinePick")


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


class PaginationViewTests(TestCase):
    @patch("movies.views._director_cards", return_value=[])
    @patch("movies.views._fetch_recent_releases", return_value=([], None))
    @patch("movies.views._fetch_random_movies", return_value=([], None))
    def test_home_random_page_shows_cinepick_picks_section(
        self,
        _mock_random_movies,
        _mock_recent_releases,
        _mock_director_cards,
    ) -> None:
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CinePick Picks")
        self.assertContains(response, "CinePick-Best Movies")
        self.assertContains(response, "CinePick-Best Series")
        self.assertContains(response, "top rated series you should watch")

    @patch("movies.views._director_cards", return_value=[])
    @patch("movies.views._fetch_movies")
    def test_home_search_next_page_preserves_query(self, mock_fetch_movies, _mock_director_cards) -> None:
        mock_fetch_movies.return_value = (
            [
                {
                    "title": "Interstellar",
                    "poster_url": "",
                    "release_year": "2014",
                    "overview": "A team travels through a wormhole.",
                    "vote_average": 8.7,
                    "imdb_id": "tt0816692",
                }
            ],
            3,
            None,
        )

        response = self.client.get(reverse("home"), {"q": "space opera"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 3")
        self.assertContains(response, "?q=space+opera&amp;page=2")

    @patch("movies.views._fetch_movies")
    def test_genre_pagination_keeps_custom_query(self, mock_fetch_movies) -> None:
        mock_fetch_movies.return_value = (
            [
                {
                    "title": "Heat",
                    "poster_url": "",
                    "release_year": "1995",
                    "overview": "A career thief faces a relentless detective.",
                    "vote_average": 8.3,
                    "imdb_id": "tt0113277",
                }
            ],
            4,
            None,
        )

        response = self.client.get(reverse("genre_view", args=["action"]), {"q": "heist movie", "page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "?q=heist+movie&amp;page=3")
        self.assertContains(response, "?q=heist+movie")

    @patch("movies.views._title_detail")
    @patch("movies.views._ai_recommend_titles")
    def test_ai_suggestions_next_page_uses_stable_recommended_titles(
        self,
        mock_ai_recommend_titles,
        mock_title_detail,
    ) -> None:
        mock_ai_recommend_titles.return_value = (["Dune", "Arrival", "Interstellar"], None)
        mock_title_detail.side_effect = lambda title: {
            "Title": title,
            "Year": "2021",
            "Released": "22 Oct 2021",
            "Poster": "N/A",
            "Plot": f"{title} overview",
            "Runtime": "155 min",
            "Genre": "Sci-Fi, Drama",
            "Type": "movie",
            "imdbRating": "8.0",
            "imdbID": f"id-{title.lower()}",
        }

        response = self.client.get(reverse("ai_suggestions"), {"query": "hopeful space adventure"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 1")
        self.assertContains(response, "Dune, Arrival, Interstellar")

    def test_bollywood_search_redirects_to_curated_page(self) -> None:
        response = self.client.get(reverse("home"), {"q": "bollywood"})

        self.assertRedirects(response, reverse("franchise_view", args=["bollywood"]))

    def test_south_indian_search_redirects_to_curated_page(self) -> None:
        response = self.client.get(reverse("home"), {"q": "telugu tamil movie"})

        self.assertRedirects(response, reverse("franchise_view", args=["south-indian"]))

    def test_indian_drama_search_redirects_to_curated_page(self) -> None:
        response = self.client.get(reverse("home"), {"q": "indian drama movie"})

        self.assertRedirects(response, reverse("franchise_view", args=["indian-drama"]))


class FixedDate(date):
    @classmethod
    def today(cls) -> "FixedDate":
        return cls(2026, 4, 3)


class MovieFilteringTests(TestCase):
    @patch("movies.views.date", FixedDate)
    def test_is_usable_movie_filters_one_shots_and_future_titles(self) -> None:
        self.assertFalse(
            views._is_usable_movie(
                {"Title": "Marvel One-Shot: Item 47"},
                {
                    "Title": "Marvel One-Shot: Item 47",
                    "Released": "25 Sep 2012",
                    "Runtime": "12 min",
                    "Genre": "Short, Action",
                    "Type": "movie",
                },
            )
        )

        self.assertFalse(
            views._is_usable_movie(
                {"Title": "Future Avengers"},
                {
                    "Title": "Future Avengers",
                    "Released": "18 Dec 2026",
                    "Runtime": "130 min",
                    "Genre": "Action, Sci-Fi",
                    "Type": "movie",
                },
            )
        )

        self.assertTrue(
            views._is_usable_movie(
                {"Title": "Iron Man"},
                {
                    "Title": "Iron Man",
                    "Released": "02 May 2008",
                    "Runtime": "126 min",
                    "Genre": "Action, Sci-Fi",
                    "Type": "movie",
                },
            )
        )

    @patch("movies.views.date", FixedDate)
    @patch("movies.views._movie_detail")
    @patch("movies.views._omdb_request")
    def test_fetch_movies_keeps_only_normal_feature_films(self, mock_omdb_request, mock_movie_detail) -> None:
        mock_omdb_request.return_value = {
            "Response": "True",
            "totalResults": "2",
            "Search": [
                {
                    "Title": "Marvel One-Shot: Item 47",
                    "Year": "2012",
                    "Poster": "N/A",
                    "imdbID": "tt2247732",
                },
                {
                    "Title": "Iron Man",
                    "Year": "2008",
                    "Poster": "N/A",
                    "imdbID": "tt0371746",
                },
            ],
        }

        mock_movie_detail.side_effect = lambda imdb_id: {
            "tt2247732": {
                "Title": "Marvel One-Shot: Item 47",
                "Released": "25 Sep 2012",
                "Runtime": "12 min",
                "Genre": "Short, Action",
                "Type": "movie",
                "imdbID": "tt2247732",
                "imdbRating": "6.7",
            },
            "tt0371746": {
                "Title": "Iron Man",
                "Released": "02 May 2008",
                "Runtime": "126 min",
                "Genre": "Action, Sci-Fi",
                "Type": "movie",
                "imdbID": "tt0371746",
                "imdbRating": "7.9",
            },
        }[imdb_id]

        movies, total_pages, api_error = views._fetch_movies("marvel", 1)

        self.assertEqual(total_pages, 1)
        self.assertIsNone(api_error)
        self.assertEqual([movie["title"] for movie in movies], ["Iron Man"])


class FranchiseViewTests(TestCase):
    @patch("movies.views.date", FixedDate)
    @patch("movies.views._title_detail")
    def test_marvel_page_shows_released_movies_only_in_order(self, mock_title_detail) -> None:
        def fake_title_detail(title: str) -> dict[str, str]:
            return {
                "Title": title,
                "Year": "2025",
                "Poster": "N/A",
                "Plot": f"{title} overview",
                "imdbRating": "7.0",
                "imdbID": f"id-{title.lower().replace(' ', '-')}",
            }

        mock_title_detail.side_effect = fake_title_detail

        response = self.client.get(reverse("franchise_view", args=["marvel"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Marvel Movies")
        movies = response.context["movies"]
        titles = [movie["title"] for movie in movies]

        self.assertEqual(titles[0], "Iron Man")
        self.assertEqual(titles[-1], "The Fantastic Four: First Steps")
        self.assertNotIn("Spider-Man: Brand New Day", titles)
        self.assertNotIn("Avengers: Doomsday", titles)
        self.assertNotIn("Avengers: Secret Wars", titles)

    @patch("movies.views.date", FixedDate)
    @patch("movies.views._title_detail")
    def test_dc_page_shows_released_movies_only_in_order(self, mock_title_detail) -> None:
        def fake_title_detail(title: str) -> dict[str, str]:
            return {
                "Title": title,
                "Year": "2025",
                "Poster": "N/A",
                "Plot": f"{title} overview",
                "imdbRating": "7.0",
                "imdbID": f"id-{title.lower().replace(' ', '-').replace(':', '').replace('!', '')}",
            }

        mock_title_detail.side_effect = fake_title_detail

        response = self.client.get(reverse("franchise_view", args=["dc"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DC Movies")
        movies = response.context["movies"]
        titles = [movie["title"] for movie in movies]

        self.assertEqual(titles[0], "Man of Steel")
        self.assertEqual(titles[-1], "Superman")
        self.assertNotIn("Supergirl", titles)
        self.assertNotIn("Clayface", titles)

    @patch("movies.views._title_detail")
    def test_cinepick_best_movies_page_shows_curated_top_ten(self, mock_title_detail) -> None:
        def fake_title_detail(title: str) -> dict[str, str]:
            return {
                "Title": title,
                "Year": "2014",
                "Released": "07 Nov 2014",
                "Poster": "N/A",
                "Plot": f"{title} overview",
                "Runtime": "140 min",
                "Genre": "Drama",
                "Type": "movie",
                "imdbRating": "8.5",
                "imdbID": f"id-{title.lower().replace(' ', '-').replace(':', '').replace(\"'\", '')}",
            }

        mock_title_detail.side_effect = fake_title_detail

        response = self.client.get(reverse("franchise_view", args=["cinepick-best-movies"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CinePick-Best Movies")
        self.assertContains(response, "Top 10 Movies")
        titles = [movie["title"] for movie in response.context["movies"]]
        self.assertEqual(titles[0], "Interstellar")
        self.assertIn("The Dark Knight", titles)

    @patch("movies.views._title_detail")
    def test_cinepick_best_series_page_shows_curated_top_ten(self, mock_title_detail) -> None:
        def fake_title_detail(title: str) -> dict[str, str]:
            return {
                "Title": title,
                "Year": "2015-2022",
                "Released": "08 Feb 2015",
                "Poster": "N/A",
                "Plot": f"{title} overview",
                "Genre": "Drama, Thriller",
                "Type": "series",
                "imdbRating": "8.9",
                "imdbID": f"id-{title.lower().replace(' ', '-').replace(':', '').replace(\"'\", '')}",
            }

        mock_title_detail.side_effect = fake_title_detail

        response = self.client.get(reverse("franchise_view", args=["cinepick-best-series"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CinePick-Best Series")
        self.assertContains(response, "top rated series you should watch")
        titles = [movie["title"] for movie in response.context["movies"]]
        self.assertEqual(titles[0], "Better Call Saul")
        self.assertIn("Breaking Bad", titles)

    @patch("movies.views._title_detail")
    def test_bollywood_page_shows_curated_bollywood_movies(self, mock_title_detail) -> None:
        def fake_title_detail(title: str) -> dict[str, str]:
            return {
                "Title": title,
                "Year": "2010",
                "Released": "01 Jan 2010",
                "Poster": "N/A",
                "Plot": f"{title} overview",
                "Runtime": "150 min",
                "Genre": "Drama",
                "Type": "movie",
                "imdbRating": "7.0",
                "imdbID": f"id-{title.lower().replace(' ', '-')}",
            }

        mock_title_detail.side_effect = fake_title_detail

        response = self.client.get(reverse("franchise_view", args=["bollywood"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bollywood Movies")
        titles = [movie["title"] for movie in response.context["movies"]]
        self.assertIn("3 Idiots", titles)
        self.assertIn("Dangal", titles)
        self.assertNotIn("Bollywood", titles)

    @patch("movies.views._title_detail")
    def test_bollywood_page_has_next_page(self, mock_title_detail) -> None:
        def fake_title_detail(title: str) -> dict[str, str]:
            return {
                "Title": title,
                "Year": "2010",
                "Released": "01 Jan 2010",
                "Poster": "N/A",
                "Plot": f"{title} overview",
                "Runtime": "150 min",
                "Genre": "Drama",
                "Type": "movie",
                "imdbRating": "7.0",
                "imdbID": f"id-{title.lower().replace(' ', '-')}",
            }

        mock_title_detail.side_effect = fake_title_detail

        response = self.client.get(reverse("franchise_view", args=["bollywood"]), {"page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 2 of 2")
        self.assertContains(response, "?page=2")
        titles = [movie["title"] for movie in response.context["movies"]]
        self.assertIn("Stree 2", titles)

    @patch("movies.views._title_detail")
    def test_south_indian_page_shows_curated_movies(self, mock_title_detail) -> None:
        def fake_title_detail(title: str) -> dict[str, str]:
            return {
                "Title": title,
                "Year": "2015",
                "Released": "01 Jan 2015",
                "Poster": "N/A",
                "Plot": f"{title} overview",
                "Runtime": "150 min",
                "Genre": "Drama",
                "Type": "movie",
                "imdbRating": "7.0",
                "imdbID": f"id-{title.lower().replace(' ', '-')}",
            }

        mock_title_detail.side_effect = fake_title_detail

        response = self.client.get(reverse("franchise_view", args=["south-indian"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tamil &amp; Telugu Movies")
        titles = [movie["title"] for movie in response.context["movies"]]
        self.assertIn("RRR", titles)
        self.assertIn("Vikram", titles)

    @patch("movies.views._title_detail")
    def test_indian_drama_page_shows_curated_movies(self, mock_title_detail) -> None:
        def fake_title_detail(title: str) -> dict[str, str]:
            return {
                "Title": title,
                "Year": "2015",
                "Released": "01 Jan 2015",
                "Poster": "N/A",
                "Plot": f"{title} overview",
                "Runtime": "140 min",
                "Genre": "Drama",
                "Type": "movie",
                "imdbRating": "7.0",
                "imdbID": f"id-{title.lower().replace(' ', '-')}",
            }

        mock_title_detail.side_effect = fake_title_detail

        response = self.client.get(reverse("franchise_view", args=["indian-drama"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Indian Drama Movies")
        titles = [movie["title"] for movie in response.context["movies"]]
        self.assertIn("Pather Panchali", titles)
        self.assertIn("The Lunchbox", titles)
