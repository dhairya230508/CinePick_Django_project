from __future__ import annotations

import json
import random
import re
from datetime import date
from functools import lru_cache
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .models import WatchedItem, WishlistItem


GENRE_CONFIG: dict[str, dict[str, str]] = {
    "action": {
        "label": "Action",
        "description": "High-energy stories, daring heroes, and spectacle-heavy crowd pleasers.",
        "search": "action movie",
    },
    "comedy": {
        "label": "Comedy",
        "description": "Light, witty, and feel-good picks for when you want something fun.",
        "search": "comedy movie",
    },
    "romance": {
        "label": "Romance",
        "description": "Sweeping chemistry, tender moments, and stories led by connection.",
        "search": "romantic movie",
    },
    "drama": {
        "label": "Drama",
        "description": "Emotional, story-driven films built around character, conflict, and feeling.",
        "search": "drama movie",
    },
    "mystery": {
        "label": "Mystery",
        "description": "Puzzles, investigations, and slow-burn reveals that keep you guessing.",
        "search": "mystery movie",
    },
    "fantasy": {
        "label": "Fantasy",
        "description": "Magic, unreal worlds, and imaginative adventures beyond ordinary reality.",
        "search": "fantasy movie",
    },
    "animation": {
        "label": "Animation",
        "description": "Stylized storytelling, animated worlds, and family-friendly or artistic favorites.",
        "search": "animated movie",
    },
    "crime": {
        "label": "Crime",
        "description": "Gangs, mafia, police, and underworld stories packed with tension.",
        "search": "crime movie",
    },
    "adventure": {
        "label": "Adventure",
        "description": "Exploration, journeys, and big-screen quests with momentum and wonder.",
        "search": "adventure movie",
    },
    "sci-fi": {
        "label": "Sci-Fi",
        "description": "Big ideas, future worlds, and imaginative stories with cosmic scale.",
        "search": "science fiction movie",
    },
    "horror": {
        "label": "Horror",
        "description": "Dark, eerie, and unsettling films built for suspense and late nights.",
        "search": "horror movie",
    },
    "thriller": {
        "label": "Thriller",
        "description": "Tense, twisty stories packed with mystery, danger, and momentum.",
        "search": "thriller movie",
    },
}

DIRECTOR_CONFIG: dict[str, dict[str, Any]] = {
    "steven-spielberg": {
        "name": "Steven Spielberg",
        "person_type": "director",
        "role": "Master of storytelling",
        "description": "Big wonder, emotional clarity, and blockbuster filmmaking that still feels human.",
        "titles": ["Jurassic Park", "Schindler's List", "Jaws", "E.T. the Extra-Terrestrial"],
    },
    "martin-scorsese": {
        "name": "Martin Scorsese",
        "person_type": "director",
        "role": "Crime + character genius",
        "description": "Sharp character work, restless energy, and iconic crime epics.",
        "titles": ["Goodfellas", "The Wolf of Wall Street", "Taxi Driver", "The Departed"],
    },
    "christopher-nolan": {
        "name": "Christopher Nolan",
        "person_type": "director",
        "role": "Mind-bending films",
        "description": "Time, memory, spectacle, and ambitious stories built like puzzles.",
        "titles": ["Inception", "Interstellar", "The Dark Knight", "Oppenheimer"],
    },
    "quentin-tarantino": {
        "name": "Quentin Tarantino",
        "person_type": "director",
        "role": "Stylish dialogue and violence",
        "description": "Hyper-stylized worlds, electric dialogue, and unforgettable set pieces.",
        "titles": ["Pulp Fiction", "Kill Bill: Vol. 1", "Django Unchained", "Inglourious Basterds"],
    },
    "stanley-kubrick": {
        "name": "Stanley Kubrick",
        "person_type": "director",
        "role": "Perfectionist visionary",
        "description": "Meticulous craft, eerie control, and films that shaped cinema language.",
        "titles": ["The Shining", "2001: A Space Odyssey", "A Clockwork Orange", "Full Metal Jacket"],
    },
    "denis-villeneuve": {
        "name": "Denis Villeneuve",
        "person_type": "director",
        "role": "Deep visuals + sci-fi",
        "description": "Atmospheric world-building, precise tension, and grand visual scale.",
        "titles": ["Dune", "Arrival", "Blade Runner 2049", "Prisoners"],
    },
    "greta-gerwig": {
        "name": "Greta Gerwig",
        "person_type": "director",
        "role": "Fresh storytelling",
        "description": "Modern voice, emotional intelligence, and sharp character-driven writing.",
        "titles": ["Barbie", "Lady Bird", "Little Women"],
    },
    "bong-joon-ho": {
        "name": "Bong Joon-ho",
        "person_type": "director",
        "role": "Genre-blending genius",
        "description": "Social satire, suspense, and tonal shifts that feel completely natural.",
        "titles": ["Parasite", "Memories of Murder", "The Host", "Snowpiercer"],
    },
    "james-cameron": {
        "name": "James Cameron",
        "person_type": "director",
        "role": "Tech + scale king",
        "description": "Big-screen spectacle, technical ambition, and emotional blockbuster craft.",
        "titles": ["Avatar", "Titanic", "Aliens", "Terminator 2: Judgment Day"],
    },
    "david-fincher": {
        "name": "David Fincher",
        "person_type": "director",
        "role": "Dark, precise",
        "description": "Controlled tension, sharp visual precision, and psychologically intense stories.",
        "titles": ["Fight Club", "Gone Girl", "Se7en", "The Social Network"],
    },
    "satyajit-ray": {
        "name": "Satyajit Ray",
        "person_type": "director",
        "role": "One of the greatest globally",
        "description": "Humanist storytelling and timeless cinema that shaped filmmakers worldwide.",
        "titles": ["Pather Panchali", "Charulata", "The World of Apu", "Aparajito"],
    },
    "rajkumar-hirani": {
        "name": "Rajkumar Hirani",
        "person_type": "director",
        "role": "Emotional + meaningful",
        "description": "Accessible storytelling with humor, heart, and social reflection.",
        "titles": ["3 Idiots", "PK", "Munna Bhai M.B.B.S.", "Sanju"],
    },
    "ss-rajamouli": {
        "name": "S. S. Rajamouli",
        "person_type": "director",
        "wikipedia_title": "S. S. Rajamouli",
        "role": "Epic blockbuster king",
        "description": "Mythic scale, crowd-pleasing emotion, and huge cinematic payoff.",
        "titles": ["RRR", "Baahubali: The Beginning", "Baahubali 2: The Conclusion", "Eega"],
    },
    "anurag-kashyap": {
        "name": "Anurag Kashyap",
        "person_type": "director",
        "role": "Raw and realistic",
        "description": "Edgy modern Indian cinema with grit, risk, and street-level intensity.",
        "titles": ["Gangs of Wasseypur", "Black Friday", "Ugly", "Raman Raghav 2.0"],
    },
    "sanjay-leela-bhansali": {
        "name": "Sanjay Leela Bhansali",
        "person_type": "director",
        "role": "Visual grandeur",
        "description": "Lavish frames, musical emotion, and operatic romantic storytelling.",
        "titles": ["Padmaavat", "Bajirao Mastani", "Devdas", "Goliyon Ki Rasleela Ram-Leela"],
    },
    "sandeep-reddy-vanga": {
        "name": "Sandeep Reddy Vanga",
        "person_type": "director",
        "role": "Intense modern drama",
        "description": "Provocative emotional volatility, aggression, and high-impact star vehicles.",
        "titles": ["Arjun Reddy", "Kabir Singh", "Animal"],
    },
    "aditya-dhar": {
        "name": "Aditya Dhar",
        "person_type": "director",
        "role": "Military action storyteller",
        "description": "Nationalistic action, sharp tension, and modern Hindi blockbuster energy.",
        "titles": ["Uri: The Surgical Strike"],
    },
    "george-rr-martin": {
        "name": "George R. R. Martin",
        "person_type": "creator",
        "wikipedia_title": "George R. R. Martin",
        "role": "Dark fantasy creator",
        "description": "Master of dark fantasy, political drama, and vast world-building.",
        "titles": ["Game of Thrones", "House of the Dragon"],
    },
    "vince-gilligan": {
        "name": "Vince Gilligan",
        "person_type": "creator",
        "role": "Prestige crime creator",
        "description": "Careful escalation, brilliant character arcs, and crime storytelling at peak form.",
        "titles": ["Breaking Bad", "Better Call Saul", "El Camino: A Breaking Bad Movie"],
    },
    "duffer-brothers": {
        "name": "Duffer Brothers",
        "person_type": "creator",
        "role": "Sci-fi mystery creators",
        "description": "Nostalgia, mystery-box storytelling, and supernatural genre worlds with strong ensemble energy.",
        "titles": ["Stranger Things"],
    },
    "russo-brothers": {
        "name": "Russo Brothers",
        "person_type": "director",
        "role": "High-scale blockbuster duo",
        "description": "Large ensemble action, slick pacing, and major franchise event filmmaking.",
        "titles": ["Avengers: Infinity War", "Avengers: Endgame", "Captain America: The Winter Soldier", "The Gray Man"],
    },
    "zoya-akhtar": {
        "name": "Zoya Akhtar",
        "person_type": "director",
        "role": "Urban storytelling",
        "description": "Modern relationships, layered ensembles, and stylish contemporary Indian storytelling.",
        "titles": ["Gully Boy", "Zindagi Na Milegi Dobara", "Dil Dhadakne Do", "Luck by Chance"],
    },
    "nitesh-tiwari": {
        "name": "Nitesh Tiwari",
        "person_type": "director",
        "role": "Emotional mass",
        "description": "Crowd-pleasing drama built around family, aspiration, and emotional payoff.",
        "titles": ["Dangal", "Chhichhore", "Bawaal"],
    },
    "amar-kaushik": {
        "name": "Amar Kaushik",
        "person_type": "director",
        "role": "Horror-comedy",
        "description": "Accessible genre fun mixing comedy, folklore, and mainstream entertainment.",
        "titles": ["Stree", "Bhediya", "Bala"],
    },
    "vikramaditya-motwane": {
        "name": "Vikramaditya Motwane",
        "person_type": "director",
        "role": "Experimental storyteller",
        "description": "Risk-taking structure, strong atmosphere, and modern Indian screen language.",
        "titles": ["Udaan", "Lootera", "Trapped", "Bhavesh Joshi Superhero"],
    },
    "rohit-shetty": {
        "name": "Rohit Shetty",
        "person_type": "director",
        "role": "Pure mass entertainment",
        "description": "Big action, comedy, spectacle, and unapologetically commercial crowd-pleasers.",
        "titles": ["Chennai Express", "Singham", "Simmba", "Golmaal Again"],
    },
    "lokesh-kanagaraj": {
        "name": "Lokesh Kanagaraj",
        "person_type": "director",
        "role": "Stylish action universe builder",
        "description": "Lean action storytelling, strong screen presence, and connected cinematic universe energy.",
        "titles": ["Kaithi", "Vikram", "Master", "Leo"],
    },
}

OMDB_BASE_URL = "https://www.omdbapi.com/"
RANDOM_SEARCH_SEEDS = [
    "love",
    "war",
    "night",
    "moon",
    "dark",
    "star",
    "city",
    "king",
    "queen",
    "fire",
    "blue",
    "red",
    "lost",
    "future",
    "dream",
    "game",
    "last",
    "secret",
    "ghost",
    "road",
]

RECENT_RELEASE_SEARCH_SEEDS = [
    "love",
    "night",
    "dead",
    "girl",
    "man",
    "last",
    "dark",
    "city",
]

SEARCH_NOISE_WORDS = {
    "movie",
    "movies",
    "film",
    "films",
    "cinema",
    "best",
    "top",
}


def _safe_page(raw_page: str | None) -> int:
    try:
        page = int(raw_page or "1")
    except ValueError:
        return 1
    return max(1, min(page, 100))


def _get_json(url: str, headers: dict[str, str] | None = None, data: bytes | None = None) -> dict[str, Any]:
    request = Request(url, headers=headers or {}, data=data)
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _omdb_request(params: dict[str, Any]) -> dict[str, Any]:
    api_key = settings.MOVIE_API_KEY
    if not api_key:
        return {"Response": "False", "Error": "Add MOVIE_API_KEY to your .env file to load movie results."}

    query = urlencode({"apikey": api_key, **params})
    try:
        return _get_json(f"{OMDB_BASE_URL}?{query}")
    except Exception:
        return {"Response": "False", "Error": "CinePick could not reach OMDb right now. Please try again shortly."}


def _movie_detail(imdb_id: str) -> dict[str, Any]:
    details = _omdb_request({"i": imdb_id, "plot": "short"})
    if details.get("Response") == "False":
        return {}
    return details


def _title_detail(title: str) -> dict[str, Any]:
    details = _omdb_request({"t": title})
    if details.get("Response") == "False":
        return {}
    return details


def _person_profile(page_title: str) -> dict[str, str]:
    encoded_title = quote(page_title, safe="")
    try:
        payload = _get_json(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}",
            headers={"User-Agent": "CinePick/1.0"},
        )
    except Exception:
        return {"image_url": "", "summary": ""}

    thumbnail = payload.get("thumbnail", {})
    return {
        "image_url": thumbnail.get("source", ""),
        "summary": payload.get("extract", "") or "",
    }


@lru_cache(maxsize=64)
def _cached_person_profile(page_title: str) -> tuple[str, str]:
    profile = _person_profile(page_title)
    return profile.get("image_url", ""), profile.get("summary", "")


def _director_cards() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for slug, person in DIRECTOR_CONFIG.items():
        page_title = person.get("wikipedia_title") or person["name"]
        image_url, _summary = _cached_person_profile(page_title)
        cards.append(
            {
                "slug": slug,
                "name": person["name"],
                "role": person["role"],
                "titles": person["titles"],
                "person_type": person.get("person_type", "director"),
                "image_url": image_url,
            }
        )
    return cards


def _normalize_movie(movie: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    rating = detail.get("imdbRating")
    try:
        vote_average = float(rating) if rating and rating != "N/A" else 0.0
    except ValueError:
        vote_average = 0.0

    return {
        "title": movie.get("Title") or detail.get("Title") or "Untitled",
        "poster_url": None if movie.get("Poster") in {None, "", "N/A"} else movie.get("Poster"),
        "release_year": movie.get("Year") or detail.get("Year") or "Unknown",
        "overview": detail.get("Plot") if detail.get("Plot") not in {None, "", "N/A"} else "Plot details are not available for this title yet.",
        "vote_average": vote_average,
        "imdb_id": movie.get("imdbID") or detail.get("imdbID"),
    }


def _fetch_curated_titles(titles: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    curated: list[dict[str, Any]] = []

    for title in titles:
        detail = _title_detail(title)
        if not detail:
            continue
        curated.append(_normalize_movie(detail, detail))

    if curated:
        return curated, None

    return [], "CinePick could not load featured titles for this page right now."


def _fetch_director_filmography(name: str) -> tuple[list[dict[str, Any]], str | None]:
    query = f"""
SELECT ?filmLabel ?imdbId ?publication WHERE {{
  ?sitelink schema:about ?director ;
            schema:isPartOf <https://en.wikipedia.org/> ;
            schema:name "{name}"@en .
  ?film wdt:P57 ?director ;
        wdt:P31/wdt:P279* wd:Q11424 .
  OPTIONAL {{ ?film wdt:P345 ?imdbId . }}
  OPTIONAL {{ ?film wdt:P577 ?publication . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
ORDER BY DESC(?publication) ?filmLabel
"""
    try:
        payload = _get_json(
            f"https://query.wikidata.org/sparql?format=json&query={quote(query, safe='')}",
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": "CinePick/1.0",
            },
        )
    except Exception:
        return [], "CinePick could not load this director's full filmography right now."

    bindings = payload.get("results", {}).get("bindings", [])
    movies: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for item in bindings:
        title = item.get("filmLabel", {}).get("value", "").strip()
        if not title:
            continue

        imdb_id = item.get("imdbId", {}).get("value", "").strip()
        year_value = item.get("publication", {}).get("value", "")
        release_year = year_value[:4] if year_value else "Unknown"
        dedupe_key = imdb_id or title.lower()
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        detail = _movie_detail(imdb_id) if imdb_id else _title_detail(title)
        if detail:
            movies.append(
                _normalize_movie(
                    {
                        "Title": title,
                        "Year": release_year,
                        "imdbID": imdb_id,
                        "Poster": detail.get("Poster"),
                    },
                    detail,
                )
            )
        else:
            movies.append(
                {
                    "title": title,
                    "poster_url": None,
                    "release_year": release_year,
                    "overview": "Part of this filmmaker's wider body of work.",
                    "vote_average": 0.0,
                    "imdb_id": imdb_id,
                }
            )

    if movies:
        return movies, None

    return [], "No filmography entries were available for this page right now."


def _fetch_movies(search_term: str, page: int) -> tuple[list[dict[str, Any]], int, str | None]:
    attempts = [search_term.strip()]
    words = [word for word in re.findall(r"[a-zA-Z0-9']+", search_term) if word.lower() not in SEARCH_NOISE_WORDS]

    if len(words) >= 2:
        attempts.append(" ".join(words[:-1]))
        attempts.append(" ".join(words[-2:]))
    if words:
        attempts.append(words[0])

    seen_terms: set[str] = set()
    filtered_attempts: list[str] = []
    for attempt in attempts:
        normalized = attempt.strip()
        key = normalized.lower()
        if not normalized or key in seen_terms:
            continue
        seen_terms.add(key)
        filtered_attempts.append(normalized)

    payload: dict[str, Any] = {"Response": "False", "Error": "No movie results were found."}
    matched_term = search_term
    for attempt in filtered_attempts:
        payload = _omdb_request({"s": attempt, "type": "movie", "page": page})
        if payload.get("Response") != "False":
            matched_term = attempt
            break

    if payload.get("Response") == "False":
        return [], 1, payload.get("Error") or "No movie results were found."

    search_results = payload.get("Search", [])
    total_results = int(payload.get("totalResults", 0) or 0)
    total_pages = max(1, min((total_results + 9) // 10, 100))

    movies = []
    for item in search_results:
        detail = _movie_detail(item.get("imdbID", ""))
        movies.append(_normalize_movie(item, detail))

    fallback_notice = None
    if matched_term.lower() != search_term.strip().lower():
        fallback_notice = f'No exact title matches for "{search_term}". Showing results for "{matched_term}" instead.'

    return movies, total_pages, fallback_notice


def _fetch_random_movies(count: int = 10) -> tuple[list[dict[str, Any]], str | None]:
    seeds = random.sample(RANDOM_SEARCH_SEEDS, k=min(4, len(RANDOM_SEARCH_SEEDS)))
    shuffled_results: list[dict[str, Any]] = []

    for seed in seeds:
        random_page = random.randint(1, 3)
        payload = _omdb_request({"s": seed, "type": "movie", "page": random_page})
        if payload.get("Response") == "False":
            continue

        results = payload.get("Search", [])
        random.shuffle(results)

        for item in results:
            if any(movie.get("imdb_id") == item.get("imdbID") for movie in shuffled_results):
                continue
            detail = _movie_detail(item.get("imdbID", ""))
            shuffled_results.append(_normalize_movie(item, detail))
            if len(shuffled_results) >= count:
                return shuffled_results, None

    if shuffled_results:
        return shuffled_results, None

    return [], "CinePick could not load random movies right now. Please try again shortly."


def _fetch_recent_releases(count: int = 8) -> tuple[list[dict[str, Any]], str | None]:
    current_year = date.today().year
    recent_years = [current_year, current_year - 1]
    releases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for year in recent_years:
        for seed in RECENT_RELEASE_SEARCH_SEEDS:
            for page in (1, 2):
                payload = _omdb_request({"s": seed, "type": "movie", "y": year, "page": page})
                if payload.get("Response") == "False":
                    continue

                for item in payload.get("Search", []):
                    imdb_id = item.get("imdbID", "")
                    if not imdb_id or imdb_id in seen_ids:
                        continue

                    detail = _movie_detail(imdb_id)
                    movie = _normalize_movie(item, detail)
                    release_year = str(movie.get("release_year", ""))[:4]
                    if release_year != str(year):
                        continue

                    seen_ids.add(imdb_id)
                    releases.append(movie)
                    if len(releases) >= count:
                        return releases, None

    if releases:
        return releases, None

    return [], "CinePick could not load recent releases right now. Please try again shortly."


def _extract_keywords(prompt: str) -> str:
    words = re.findall(r"[a-zA-Z0-9']+", prompt.lower())
    stop_words = {
        "a",
        "an",
        "and",
        "for",
        "from",
        "i",
        "if",
        "in",
        "is",
        "it",
        "like",
        "movie",
        "movies",
        "of",
        "or",
        "something",
        "that",
        "the",
        "to",
        "with",
    }
    keywords = [word for word in words if word not in stop_words]
    unique_keywords = list(dict.fromkeys(keywords))
    return " ".join(unique_keywords[:4]) or prompt.strip()


def _ai_keyword_search(prompt: str) -> tuple[str, str | None]:
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        return "", None

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return _extract_keywords(cleaned_prompt), None

    body = {
        "model": settings.OPENAI_MODEL,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Convert a movie mood into 2 to 5 simple search keywords for OMDb. Return keywords only.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": cleaned_prompt}],
            },
        ],
    }

    try:
        response = _get_json(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(body).encode("utf-8"),
        )
    except Exception:
        return _extract_keywords(cleaned_prompt), "OpenAI was unavailable, so CinePick used a local keyword fallback."

    output_text = response.get("output_text", "").strip()
    if output_text:
        return output_text, None

    return _extract_keywords(cleaned_prompt), "OpenAI did not return keywords, so CinePick used a local keyword fallback."


def _catalog_context(
    *,
    request_user: Any,
    search_term: str,
    page: int,
    query: str,
    is_genre_page: bool = False,
    genre_slug: str = "",
    genre_name: str = "",
    genre_description: str = "",
) -> dict[str, Any]:
    movies, total_pages, api_error = _fetch_movies(search_term, page)
    _attach_wishlist_state(request_user=request_user, movies=movies)
    has_previous = page > 1
    has_next = page < total_pages

    return {
        "movies": movies,
        "query": query,
        "api_error": api_error,
        "current_page": page,
        "total_pages": total_pages,
        "previous_page": page - 1,
        "next_page": page + 1,
        "has_previous": has_previous,
        "has_next": has_next,
        "is_genre_page": is_genre_page,
        "genre_slug": genre_slug,
        "genre_name": genre_name,
        "genre_description": genre_description,
    }


def _attach_wishlist_state(*, request_user: Any, movies: list[dict[str, Any]]) -> None:
    if not getattr(request_user, "is_authenticated", False) or not movies:
        return

    imdb_ids = [movie.get("imdb_id") for movie in movies if movie.get("imdb_id")]
    saved_ids = set(
        WishlistItem.objects.filter(user=request_user, imdb_id__in=imdb_ids)
        .values_list("imdb_id", flat=True)
    )
    watched_ids = set(
        WatchedItem.objects.filter(user=request_user, imdb_id__in=imdb_ids)
        .values_list("imdb_id", flat=True)
    )
    for movie in movies:
        movie["is_in_watch_later"] = movie.get("imdb_id") in saved_ids
        movie["is_watched"] = movie.get("imdb_id") in watched_ids


def home(request: HttpRequest) -> HttpResponse:
    query = (request.GET.get("q") or "").strip()
    page = _safe_page(request.GET.get("page"))

    if not query:
        movies, api_error = _fetch_random_movies()
        recent_releases, recent_releases_error = _fetch_recent_releases()
        _attach_wishlist_state(request_user=request.user, movies=movies)
        _attach_wishlist_state(request_user=request.user, movies=recent_releases)
        context = {
            "movies": movies,
            "recent_releases": recent_releases,
            "recent_releases_error": recent_releases_error,
            "recent_release_label": f"{date.today().year} and {date.today().year - 1}",
            "query": "",
            "api_error": api_error,
            "current_page": 1,
            "total_pages": 1,
            "previous_page": 1,
            "next_page": 1,
            "has_previous": False,
            "has_next": False,
            "is_genre_page": False,
            "genre_slug": "",
            "genre_name": "",
            "genre_description": "",
            "is_random_page": True,
            "director_cards": _director_cards(),
        }
        return render(request, "movies/home.html", context)

    context = _catalog_context(request_user=request.user, search_term=query, page=page, query=query)
    context["is_random_page"] = False
    context["recent_releases"] = []
    context["recent_releases_error"] = None
    context["recent_release_label"] = ""
    context["director_cards"] = _director_cards()
    return render(request, "movies/home.html", context)


def about_view(request: HttpRequest) -> HttpResponse:
    return render(request, "movies/about.html")


def directors_page(request: HttpRequest) -> HttpResponse:
    return render(request, "movies/directors.html", {"director_cards": _director_cards()})


def director_view(request: HttpRequest, slug: str) -> HttpResponse:
    director = DIRECTOR_CONFIG.get(slug)
    if not director:
        return redirect("home")

    page_title = director.get("wikipedia_title") or director["name"]
    profile = _person_profile(page_title)
    movies: list[dict[str, Any]]
    api_error: str | None

    if director.get("person_type") == "director":
        movies, api_error = _fetch_director_filmography(page_title)
        if not movies:
            movies, api_error = _fetch_curated_titles(director["titles"])
    else:
        movies, api_error = _fetch_curated_titles(director["titles"])

    _attach_wishlist_state(request_user=request.user, movies=movies)

    return render(
        request,
        "movies/director_detail.html",
        {
            "director": director,
            "movies": movies,
            "api_error": api_error,
            "director_image_url": profile.get("image_url", ""),
            "director_summary": profile.get("summary", ""),
        },
    )


def genre_view(request: HttpRequest, slug: str) -> HttpResponse:
    genre = GENRE_CONFIG.get(slug)
    if not genre:
        return redirect("home")

    query = (request.GET.get("q") or genre["search"]).strip()
    page = _safe_page(request.GET.get("page"))
    context = _catalog_context(
        search_term=query,
        request_user=request.user,
        page=page,
        query=query,
        is_genre_page=True,
        genre_slug=slug,
        genre_name=genre["label"],
        genre_description=genre["description"],
    )
    context["is_random_page"] = False
    return render(request, "movies/home.html", context)


def ai_suggestions(request: HttpRequest) -> HttpResponse:
    prompt = (request.GET.get("query") or "").strip()
    movies: list[dict[str, Any]] = []
    keywords = ""
    api_error = None

    if prompt:
        keywords, fallback_notice = _ai_keyword_search(prompt)
        movies_payload = _omdb_request({"s": keywords or prompt, "type": "movie"})

        if movies_payload.get("Response") == "False":
            api_error = movies_payload.get("Error") or "No AI suggestions were found."
        else:
            movies = movies_payload.get("Search", [])

        if fallback_notice and not api_error:
            api_error = fallback_notice

    normalized_movies = []
    for movie in movies:
        normalized_movies.append(
            {
                "title": movie.get("Title") or "Untitled",
                "poster_url": None if movie.get("Poster") in {None, "", "N/A"} else movie.get("Poster"),
                "release_year": movie.get("Year") or "Unknown",
                "overview": "AI suggestion results show quick OMDb matches. Open a title on the main catalog for richer details.",
                "vote_average": 0.0,
                "imdb_id": movie.get("imdbID"),
            }
        )
    _attach_wishlist_state(request_user=request.user, movies=normalized_movies)

    return render(
        request,
        "movies/ai.html",
        {
            "query": prompt,
            "keywords": keywords,
            "movies": normalized_movies,
            "api_error": api_error,
        },
    )


def _next_url(request: HttpRequest) -> str:
    candidate = request.POST.get("next") or request.GET.get("next") or ""
    if candidate and url_has_allowed_host_and_scheme(candidate, {request.get_host()}, require_https=request.is_secure()):
        return candidate
    return ""


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("home")

    error = None
    next_url = _next_url(request)
    submitted_username = ""

    if request.method == "POST":
        submitted_username = (request.POST.get("username") or request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=submitted_username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}.")
            return redirect(next_url or "home")

        error = "Invalid username or password."

    return render(
        request,
        "login.html",
        {
            "error": error,
            "next": next_url,
            "submitted_username": submitted_username,
        },
    )


def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("home")

    error = None
    next_url = _next_url(request)
    form_data = {"username": "", "email": ""}

    if request.method == "POST":
        username = (request.POST.get("username") or request.POST.get("email") or "").strip()
        email = (request.POST.get("email") or username).strip()
        password = request.POST.get("password") or ""
        confirm_password = request.POST.get("confirm_password") or ""
        form_data = {"username": username, "email": email}

        if not username or not password:
            error = "Username and password are required."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif User.objects.filter(username=username).exists():
            error = "That username already exists."
        elif email and User.objects.filter(email=email).exists():
            error = "That email is already registered."
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect(next_url or "home")

    return render(
        request,
        "register.html",
        {
            "error": error,
            "next": next_url,
            "form_data": form_data,
        },
    )


def logout_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        messages.success(request, "You have been logged out.")
    logout(request)
    return redirect(_next_url(request) or "home")


@login_required
def wishlist_view(request: HttpRequest) -> HttpResponse:
    items = WishlistItem.objects.filter(user=request.user)
    return render(request, "movies/wishlist.html", {"wishlist_items": items})


@login_required
def add_to_wishlist(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("home")

    imdb_id = (request.POST.get("imdb_id") or "").strip()
    title = (request.POST.get("title") or "").strip()
    if not imdb_id or not title:
        messages.error(request, "CinePick could not save that movie to your wishlist.")
        return redirect(_next_url(request) or "home")

    item, created = WishlistItem.objects.get_or_create(
        user=request.user,
        imdb_id=imdb_id,
        defaults={
            "title": title,
            "poster_url": (request.POST.get("poster_url") or "").strip(),
            "release_year": (request.POST.get("release_year") or "").strip(),
            "overview": (request.POST.get("overview") or "").strip(),
            "vote_average": float(request.POST.get("vote_average") or 0.0),
        },
    )

    if created:
        messages.success(request, f'"{item.title}" was added to your wishlist.')
    else:
        messages.info(request, f'"{item.title}" is already in your wishlist.')
    return redirect(_next_url(request) or "wishlist")


@login_required
def add_to_watched(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("home")

    imdb_id = (request.POST.get("imdb_id") or "").strip()
    title = (request.POST.get("title") or "").strip()
    if not imdb_id or not title:
        messages.error(request, "CinePick could not save that movie to your watched list.")
        return redirect(_next_url(request) or "home")

    item, created = WatchedItem.objects.get_or_create(
        user=request.user,
        imdb_id=imdb_id,
        defaults={
            "title": title,
            "poster_url": (request.POST.get("poster_url") or "").strip(),
            "release_year": (request.POST.get("release_year") or "").strip(),
            "overview": (request.POST.get("overview") or "").strip(),
            "vote_average": float(request.POST.get("vote_average") or 0.0),
        },
    )
    WishlistItem.objects.filter(user=request.user, imdb_id=imdb_id).delete()

    if created:
        messages.success(request, f'"{item.title}" was marked as watched.')
    else:
        messages.info(request, f'"{item.title}" is already in your watched list.')
    return redirect(_next_url(request) or "home")


@login_required
def remove_from_wishlist(request: HttpRequest, item_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("wishlist")

    item = get_object_or_404(WishlistItem, id=item_id, user=request.user)
    title = item.title
    item.delete()
    messages.success(request, f'"{title}" was removed from your wishlist.')
    return redirect(_next_url(request) or "wishlist")
