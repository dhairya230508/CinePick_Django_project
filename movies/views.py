from __future__ import annotations

import json
import random
import re
from datetime import date, datetime
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

FRANCHISE_CONFIG: dict[str, dict[str, Any]] = {
    "marvel": {
        "name": "Marvel Movies",
        "kicker": "Official Release Order",
        "collection_kind": "release_order",
        "ai_target_count": 40,
        "expected_type": "movie",
        "count_label": "films",
        "description": "All officially released Marvel movies in theatrical release order. This page excludes one-shots, shorts, and unrelated OMDb search matches.",
        "hero_copy": "A curated Marvel page built for clean browsing. Instead of a raw search for \"marvel,\" CinePick shows only the released Marvel movies in release order.",
        "empty_message": "No Marvel movie titles are available for this page right now.",
    },
    "dc": {
        "name": "DC Movies",
        "kicker": "Official Release Order",
        "collection_kind": "release_order",
        "ai_target_count": 20,
        "expected_type": "movie",
        "count_label": "films",
        "description": "Officially released DC Universe movies in theatrical release order, curated for clean browsing without noisy keyword matches.",
        "hero_copy": "This DC page mirrors the Marvel experience with a curated theatrical release-order lineup instead of a raw search for \"dc comics.\"",
        "empty_message": "No DC movie titles are available for this page right now.",
    },
    "bollywood": {
        "name": "Bollywood Movies",
        "kicker": "Curated Hindi Cinema",
        "collection_kind": "curated",
        "ai_target_count": 24,
        "expected_type": "movie",
        "count_label": "films",
        "description": "A curated Bollywood collection focused on real Hindi feature films instead of literal title matches for the word Bollywood.",
        "hero_copy": "This page is built to show Bollywood movies, not movies that just happen to be named \"Bollywood.\" CinePick now opens a curated Hindi cinema collection here.",
        "empty_message": "No Bollywood movie titles are available for this page right now.",
    },
    "south-indian": {
        "name": "Tamil & Telugu Movies",
        "kicker": "Curated South Indian Cinema",
        "collection_kind": "curated",
        "ai_target_count": 20,
        "expected_type": "movie",
        "count_label": "films",
        "description": "A curated collection of Tamil and Telugu feature films built to avoid noisy OMDb keyword matches.",
        "hero_copy": "This page focuses on Tamil and Telugu movies you actually want to browse, instead of search results that only loosely match a phrase like \"telugu tamil movie.\"",
        "empty_message": "No Tamil and Telugu movie titles are available for this page right now.",
    },
    "indian-drama": {
        "name": "Indian Drama Movies",
        "kicker": "Curated Indian Drama",
        "collection_kind": "curated",
        "ai_target_count": 20,
        "expected_type": "movie",
        "count_label": "films",
        "description": "A curated Indian drama collection spanning acclaimed character-driven films across Hindi and regional cinema.",
        "hero_copy": "This page highlights Indian drama movies worth exploring, rather than literal search matches for the phrase \"indian drama movie.\"",
        "empty_message": "No Indian drama movie titles are available for this page right now.",
    },
    "cinepick-best-movies": {
        "name": "CinePick-Best Movies",
        "kicker": "Top 10 Movies",
        "collection_kind": "curated",
        "expected_type": "movie",
        "count_label": "films",
        "collection_badge": "Top rated movies you should watch",
        "description": "A handpicked CinePick top 10 built from personal all-time favorites across sci-fi, crime, drama, and modern classics.",
        "hero_copy": "A curated top 10 movie list from CinePick, designed as a clean ranking of high-impact films worth watching and revisiting.",
        "empty_message": "No top-rated movie titles are available for this page right now.",
        "home_anchor": "cinepick-picks",
        "ai_target_count": 10,
    },
    "cinepick-best-series": {
        "name": "CinePick-Best Series",
        "kicker": "Top 10 Series",
        "collection_kind": "curated",
        "expected_type": "series",
        "count_label": "series",
        "collection_badge": "top rated series you should watch",
        "description": "A curated CinePick series ranking built around prestige drama, thrillers, sci-fi, and standout long-form storytelling.",
        "hero_copy": "top rated series you should watch",
        "empty_message": "No top-rated series titles are available for this page right now.",
        "home_anchor": "cinepick-picks",
        "ai_target_count": 10,
    },
}

STATIC_PAGE_CONTENT: dict[str, dict[str, Any]] = {
    "contact": {
        "kicker": "Get In Touch",
        "title": "Contact CinePick",
        "intro": "CinePick is a movie discovery project built to make browsing feel cleaner, faster, and more personal. Use this page as the main place for feedback, bug reports, or collaboration inquiries.",
        "sections": [
            {
                "heading": "Project Feedback",
                "body": "If you notice broken movie data, search issues, or design bugs, the best path is to report them through your project repository or your preferred feedback channel.",
            },
            {
                "heading": "Collaboration",
                "body": "CinePick can also work as a portfolio or team project. You can customize this section later with your own email address, LinkedIn profile, or project inquiry form.",
            },
            {
                "heading": "Before Launch",
                "body": "Replace placeholder contact details with your real support email, social links, or GitHub repository before sharing the project publicly.",
            },
        ],
    },
    "privacy": {
        "kicker": "Privacy Policy",
        "title": "Privacy at CinePick",
        "intro": "This page explains, in simple language, how CinePick handles account information, saved movie lists, and third-party movie data. It is a project-friendly privacy page and should be reviewed before any production launch.",
        "sections": [
            {
                "heading": "What CinePick Stores",
                "body": "CinePick stores basic account information such as username, email address, and the movies you save to your wishlist or watched list.",
            },
            {
                "heading": "Third-Party Data",
                "body": "Movie information and posters may come from external services such as OMDb, Wikipedia, Wikidata, and optional AI-powered search integrations. Their data and availability are controlled by those services.",
            },
            {
                "heading": "How Data Is Used",
                "body": "Saved data is used only to power core product features like personalized lists, watched tracking, search, and recommendations inside the CinePick experience.",
            },
            {
                "heading": "Before Production Use",
                "body": "If you deploy CinePick publicly, update this page with your real contact details, data retention rules, hosting setup, cookie usage, and any legal requirements that apply to your region.",
            },
        ],
    },
    "terms": {
        "kicker": "Terms of Use",
        "title": "Terms for Using CinePick",
        "intro": "These terms describe the expected use of CinePick as a movie discovery platform. They are written for the project in its current form and should be refined before any real public release.",
        "sections": [
            {
                "heading": "Use of the Service",
                "body": "CinePick is intended for discovering movies, saving titles, and browsing curated collections. Users should not misuse the app, attempt to damage the service, or abuse authentication features.",
            },
            {
                "heading": "Content and Availability",
                "body": "Movie details shown in CinePick may come from third-party services and can change, disappear, or contain inaccuracies. CinePick does not guarantee that all information will always be complete or available.",
            },
            {
                "heading": "Accounts",
                "body": "Users are responsible for the activity tied to their account credentials. If you launch the project publicly, you should expand this section with password, suspension, and account recovery policies.",
            },
            {
                "heading": "Project Disclaimer",
                "body": "CinePick is currently a project application. Before production launch, review these terms carefully and replace placeholders with language appropriate for your actual deployment and jurisdiction.",
            },
        ],
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

NOISY_TITLE_PATTERNS = (
    "one-shot",
    "behind the scenes",
    "making of",
    "featurette",
    "deleted scene",
    "trailer",
    "teaser",
    "sneak peek",
    "promo",
)

MIN_FEATURE_RUNTIME_MINUTES = 60
COLLECTION_PAGE_SIZE = 5

CURATED_SEARCH_REDIRECTS = {
    "bollywood": "bollywood",
    "bollywood movies": "bollywood",
    "hindi cinema": "bollywood",
    "hindi movies": "bollywood",
    "south indian": "south-indian",
    "south indian movies": "south-indian",
    "tamil telugu": "south-indian",
    "tamil telugu movies": "south-indian",
    "telugu tamil": "south-indian",
    "telugu tamil movie": "south-indian",
    "telugu tamil movies": "south-indian",
    "tamil movies": "south-indian",
    "telugu movies": "south-indian",
    "indian drama": "indian-drama",
    "indian drama movie": "indian-drama",
    "indian drama movies": "indian-drama",
    "marvel": "marvel",
    "marvel movies": "marvel",
}

AI_DYNAMIC_STATIC_PAGE_SLUGS = {"contact", "privacy", "terms"}

AI_DYNAMIC_FRANCHISE_GUIDANCE = {
    "marvel": "Return the officially released Marvel theatrical movies in release order as of today. Exclude shorts, one-shots, and unreleased films.",
    "dc": "Return the officially released DC theatrical movies in release order as of today. Exclude unreleased films and avoid shorts or specials.",
    "bollywood": "Return a strong curated list of notable Hindi-language Bollywood feature films.",
    "south-indian": "Return a curated mix of notable Tamil and Telugu feature films.",
    "indian-drama": "Return acclaimed Indian drama feature films across Hindi and regional cinema.",
    "cinepick-best-movies": "Return a top 10 list of widely respected movies across drama, sci-fi, crime, and classics.",
    "cinepick-best-series": "Return a top 10 list of widely respected TV series across drama, thriller, sci-fi, and prestige television.",
}

TMDB_COMPANY_FALLBACKS = {
    "marvel": 420,
}

STRICT_FRANCHISE_FALLBACKS: dict[str, list[dict[str, str]]] = {
    "dc": [
        {"title": "Man of Steel", "release_date": "2013-06-14"},
        {"title": "Batman v Superman: Dawn of Justice", "release_date": "2016-03-25"},
        {"title": "Suicide Squad", "release_date": "2016-08-05"},
        {"title": "Wonder Woman", "release_date": "2017-06-02"},
        {"title": "Justice League", "release_date": "2017-11-17"},
        {"title": "Aquaman", "release_date": "2018-12-21"},
        {"title": "Shazam!", "release_date": "2019-04-05"},
        {"title": "Birds of Prey", "release_date": "2020-02-07"},
        {"title": "Wonder Woman 1984", "release_date": "2020-12-25"},
        {"title": "The Suicide Squad", "release_date": "2021-08-06"},
        {"title": "Black Adam", "release_date": "2022-10-21"},
        {"title": "Shazam! Fury of the Gods", "release_date": "2023-03-17"},
        {"title": "The Flash", "release_date": "2023-06-16"},
        {"title": "Blue Beetle", "release_date": "2023-08-18"},
        {"title": "Aquaman and the Lost Kingdom", "release_date": "2023-12-22"},
        {"title": "Superman", "release_date": "2025-07-11"},
    ],
    "bollywood": [
        {"title": "Dilwale Dulhania Le Jayenge"},
        {"title": "Kuch Kuch Hota Hai"},
        {"title": "Lagaan: Once Upon a Time in India"},
        {"title": "Kal Ho Naa Ho"},
        {"title": "Swades"},
        {"title": "Rang De Basanti"},
        {"title": "Taare Zameen Par"},
        {"title": "3 Idiots"},
        {"title": "Zindagi Na Milegi Dobara"},
        {"title": "Barfi!"},
        {"title": "Queen"},
        {"title": "PK"},
        {"title": "Bajrangi Bhaijaan"},
        {"title": "Dangal"},
        {"title": "Andhadhun"},
        {"title": "Gully Boy"},
        {"title": "Article 15"},
        {"title": "Gangubai Kathiawadi"},
        {"title": "Pathaan"},
        {"title": "Jawan"},
        {"title": "12th Fail"},
        {"title": "Stree 2"},
    ],
    "south-indian": [
        {"title": "Baahubali: The Beginning"},
        {"title": "Baahubali 2: The Conclusion"},
        {"title": "RRR"},
        {"title": "Eega"},
        {"title": "Magadheera"},
        {"title": "Rangasthalam"},
        {"title": "Mahanati"},
        {"title": "Ala Vaikunthapurramuloo"},
        {"title": "Arjun Reddy"},
        {"title": "Jersey"},
        {"title": "Vikram"},
        {"title": "Kaithi"},
        {"title": "Master"},
        {"title": "Leo"},
        {"title": "Asuran"},
        {"title": "Soorarai Pottru"},
        {"title": "Mersal"},
        {"title": "96"},
    ],
    "indian-drama": [
        {"title": "Pather Panchali"},
        {"title": "Aparajito"},
        {"title": "Charulata"},
        {"title": "The Lunchbox"},
        {"title": "Masaan"},
        {"title": "Udaan"},
        {"title": "Court"},
        {"title": "Sairat"},
        {"title": "Fandry"},
        {"title": "Kumbalangi Nights"},
        {"title": "The Great Indian Kitchen"},
        {"title": "C/o Kancharapalem"},
        {"title": "Visaranai"},
        {"title": "Thithi"},
        {"title": "Ship of Theseus"},
        {"title": "Super Deluxe"},
        {"title": "Article 15"},
        {"title": "12th Fail"},
    ],
}


def _safe_page(raw_page: str | None) -> int:
    try:
        page = int(raw_page or "1")
    except ValueError:
        return 1
    return max(1, min(page, 100))


def _normalized_search_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _get_json(url: str, headers: dict[str, str] | None = None, data: bytes | None = None) -> dict[str, Any]:
    request = Request(url, headers=headers or {}, data=data)
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _gemini_json(prompt: str) -> dict[str, Any]:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {}

    body = {
        "system_instruction": {
            "parts": [
                {
                    "text": (
                        "Return only valid JSON. Do not wrap the JSON in markdown fences. "
                        "Keep copy concise and production-friendly."
                    )
                }
            ]
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    try:
        response = _get_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            data=json.dumps(body).encode("utf-8"),
        )
    except Exception:
        return {}

    candidates = response.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            text = (part.get("text") or "").strip()
            if not text:
                continue
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
    return {}


def _gemini_text(prompt: str) -> str:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return ""

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    }

    try:
        response = _get_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            data=json.dumps(body).encode("utf-8"),
        )
    except Exception:
        return ""

    candidates = response.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            text = (part.get("text") or "").strip()
            if text:
                return text
    return ""


def _omdb_request(params: dict[str, Any]) -> dict[str, Any]:
    api_key = settings.MOVIE_API_KEY
    if not api_key:
        return {"Response": "False", "Error": "Add MOVIE_API_KEY to your .env file to load movie results."}

    query = urlencode({"apikey": api_key, **params})
    try:
        return _get_json(f"{OMDB_BASE_URL}?{query}")
    except Exception:
        return {"Response": "False", "Error": "CinePick could not reach OMDb right now. Please try again shortly."}


def _tmdb_request(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    api_key = settings.TMDB_API_KEY
    if not api_key:
        return {}

    query = urlencode({"api_key": api_key, **(params or {})})
    try:
        return _get_json(f"https://api.themoviedb.org/3/{path}?{query}")
    except Exception:
        return {}


@lru_cache(maxsize=512)
def _movie_detail(imdb_id: str) -> dict[str, Any]:
    details = _omdb_request({"i": imdb_id, "plot": "short"})
    if details.get("Response") == "False":
        return {}
    return details


@lru_cache(maxsize=512)
def _title_detail(title: str) -> dict[str, Any]:
    details = _omdb_request({"t": title})
    if details.get("Response") == "False":
        return {}
    return details


def _normalized_title_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


@lru_cache(maxsize=512)
def _resolved_title_detail(title: str) -> dict[str, Any]:
    detail = _title_detail(title)
    if detail:
        return detail

    search_payload = _omdb_request({"s": title, "type": "movie", "page": 1})
    if search_payload.get("Response") == "False":
        return {}

    target_key = _normalized_title_key(title)
    best_item: dict[str, Any] | None = None

    for item in search_payload.get("Search", []):
        candidate_title = str(item.get("Title") or "").strip()
        if not candidate_title:
            continue
        if _normalized_title_key(candidate_title) == target_key:
            best_item = item
            break
        if best_item is None:
            best_item = item

    if not best_item:
        return {}

    imdb_id = str(best_item.get("imdbID") or "").strip()
    if not imdb_id:
        return {}
    return _movie_detail(imdb_id)


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


def _parse_release_date(value: str | None) -> date | None:
    if not value or value == "N/A":
        return None

    try:
        return datetime.strptime(value, "%d %b %Y").date()
    except ValueError:
        return None


def _parse_release_year(value: str | None) -> int | None:
    if not value:
        return None

    match = re.search(r"(19|20)\d{2}", value)
    if not match:
        return None
    return int(match.group(0))


def _parse_runtime_minutes(value: str | None) -> int | None:
    if not value or value == "N/A":
        return None

    match = re.search(r"(\d+)", value)
    if not match:
        return None
    return int(match.group(1))


def _is_usable_movie(movie: dict[str, Any], detail: dict[str, Any]) -> bool:
    title = (detail.get("Title") or movie.get("Title") or "").strip().lower()
    if not title:
        return False

    if any(pattern in title for pattern in NOISY_TITLE_PATTERNS):
        return False

    detail_type = (detail.get("Type") or movie.get("Type") or "").strip().lower()
    if detail_type and detail_type != "movie":
        return False

    genre_text = (detail.get("Genre") or "").strip().lower()
    if "short" in genre_text:
        return False

    release_date = _parse_release_date(detail.get("Released"))
    if release_date and release_date > date.today():
        return False

    release_year = _parse_release_year(detail.get("Year") or movie.get("Year"))
    if release_year and release_year > date.today().year:
        return False

    runtime_minutes = _parse_runtime_minutes(detail.get("Runtime"))
    if runtime_minutes is not None and runtime_minutes < MIN_FEATURE_RUNTIME_MINUTES:
        return False

    return True


def _normalize_usable_movie(movie: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any] | None:
    if not _is_usable_movie(movie, detail):
        return None
    return _normalize_movie(movie, detail)


def _is_usable_series(movie: dict[str, Any], detail: dict[str, Any]) -> bool:
    title = (detail.get("Title") or movie.get("Title") or "").strip().lower()
    if not title:
        return False

    if any(pattern in title for pattern in NOISY_TITLE_PATTERNS):
        return False

    detail_type = (detail.get("Type") or movie.get("Type") or "").strip().lower()
    if detail_type and detail_type != "series":
        return False

    genre_text = (detail.get("Genre") or "").strip().lower()
    if "short" in genre_text:
        return False

    return True


def _normalize_usable_series(movie: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any] | None:
    if not _is_usable_series(movie, detail):
        return None
    return _normalize_movie(movie, detail)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        normalized = cleaned.casefold()
        if not cleaned or normalized in seen:
            continue
        seen.add(normalized)
        result.append(cleaned)
    return result


def _validated_dynamic_titles(
    raw_titles: list[str],
    *,
    expected_type: str,
    collection_kind: str,
) -> list[dict[str, str]]:
    validated: list[dict[str, str]] = []
    seen: set[str] = set()

    for raw_title in _dedupe_preserve_order(raw_titles):
        detail = _resolved_title_detail(raw_title)
        if not detail:
            continue

        normalized = (
            _normalize_usable_series(detail, detail)
            if expected_type == "series"
            else _normalize_usable_movie(detail, detail)
        )
        if not normalized:
            continue

        clean_title = normalized["title"]
        dedupe_key = clean_title.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        entry: dict[str, str] = {"title": clean_title}
        if collection_kind == "release_order":
            release_date = _parse_release_date(detail.get("Released"))
            if not release_date:
                continue
            entry["release_date"] = release_date.isoformat()
        validated.append(entry)

    if collection_kind == "release_order":
        validated.sort(key=lambda item: item.get("release_date", "9999-12-31"))

    return validated


def _dynamic_franchise(slug: str) -> dict[str, Any] | None:
    fallback = FRANCHISE_CONFIG.get(slug)
    if not fallback:
        return None

    strict_titles = STRICT_FRANCHISE_FALLBACKS.get(slug)
    if strict_titles:
        return {
            **fallback,
            "titles": strict_titles,
            "api_error": None,
        }

    expected_type = fallback.get("expected_type", "movie")
    cleaned_titles = _franchise_ai_titles(slug, fallback)
    if not cleaned_titles and fallback.get("collection_kind") != "release_order":
        cleaned_titles = _fallback_franchise_titles(slug, expected_type=expected_type)

    validated_titles = _validated_dynamic_titles(
        cleaned_titles,
        expected_type=expected_type,
        collection_kind=fallback["collection_kind"],
    )
    if not validated_titles:
        return {
            **fallback,
            "titles": [],
            "api_error": "CinePick could not build this movie list right now. Please try again shortly.",
        }

    return {
        **fallback,
        "titles": validated_titles,
        "api_error": None,
    }


def _cached_franchise_payload(slug: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str | None]:
    franchise = _dynamic_franchise(slug) or FRANCHISE_CONFIG.get(slug)
    if not franchise:
        return None, [], None

    expected_type = franchise.get("expected_type", "movie")
    api_error = franchise.get("api_error")
    if expected_type == "series":
        all_movies, fetch_error = _fetch_collection_series(franchise.get("titles", []))
    else:
        all_movies, fetch_error = _fetch_collection_movies(franchise.get("titles", []))

    if fetch_error and not api_error:
        api_error = fetch_error

    return franchise, all_movies, api_error


@lru_cache(maxsize=8)
def _dynamic_static_page(slug: str) -> dict[str, Any] | None:
    fallback = STATIC_PAGE_CONTENT.get(slug)
    if not fallback or slug not in AI_DYNAMIC_STATIC_PAGE_SLUGS or not settings.ENABLE_AI_DYNAMIC_CONTENT:
        return fallback

    prompt = (
        f"Build JSON for the CinePick static page '{slug}'.\n"
        f"Title: {fallback['title']}\n"
        f"Kicker: {fallback['kicker']}\n"
        "Return this JSON shape exactly:\n"
        '{"intro":"...","sections":[{"heading":"...","body":"..."}]}\n'
        "Keep 3 to 4 sections. Make the language project-friendly, concise, and realistic for a movie discovery app."
    )

    payload = _gemini_json(prompt)
    sections = payload.get("sections")
    if not isinstance(sections, list) or not sections:
        return fallback

    normalized_sections: list[dict[str, str]] = []
    for section in sections[:4]:
        heading = str(section.get("heading") or "").strip()
        body = str(section.get("body") or "").strip()
        if not heading or not body:
            continue
        normalized_sections.append({"heading": heading, "body": body})

    if not normalized_sections:
        return fallback

    return {
        **fallback,
        "intro": str(payload.get("intro") or fallback["intro"]),
        "sections": normalized_sections,
    }


def _paginate_collection_items(items: list[dict[str, Any]], page: int, *, page_size: int = COLLECTION_PAGE_SIZE) -> tuple[list[dict[str, Any]], int, int]:
    if not items:
        return [], 1, 1

    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    current_page = min(page, total_pages)
    start = (current_page - 1) * page_size
    end = start + page_size
    return items[start:end], current_page, total_pages


def _fetch_curated_titles(titles: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    curated: list[dict[str, Any]] = []

    for title in titles:
        detail = _title_detail(title)
        if not detail:
            continue
        movie = _normalize_usable_movie(detail, detail)
        if movie:
            curated.append(movie)

    if curated:
        return curated, None

    return [], "CinePick could not load featured titles for this page right now."


def _fetch_collection_movies(entries: list[dict[str, str]]) -> tuple[list[dict[str, Any]], str | None]:
    prepared_entries: list[tuple[dict[str, str], date | None]] = []
    for entry in entries:
        release_date_value = entry.get("release_date")
        release_date = date.fromisoformat(release_date_value) if release_date_value else None
        if release_date and release_date > date.today():
            continue
        prepared_entries.append((entry, release_date))

    curated: list[dict[str, Any]] = []
    for index, (entry, release_date) in enumerate(prepared_entries, start=1):
        detail = _title_detail(entry["title"])
        if detail:
            movie = _normalize_usable_movie(detail, detail)
            if not movie:
                continue
        else:
            movie = {
                "title": entry["title"],
                "poster_url": None,
                "release_year": str(release_date.year) if release_date else "Unknown",
                "overview": "Curated movie pick.",
                "vote_average": 0.0,
                "imdb_id": "",
            }

        if release_date:
            movie["release_year"] = str(release_date.year)
            movie["release_date_label"] = release_date.strftime("%b %d, %Y")
        else:
            movie["release_date_label"] = ""
        movie["release_order"] = index
        curated.append(movie)

    if curated:
        return curated, None

    return [], "CinePick could not load this curated collection right now."


def _fetch_collection_series(entries: list[dict[str, str]]) -> tuple[list[dict[str, Any]], str | None]:
    curated: list[dict[str, Any]] = []

    for index, entry in enumerate(entries, start=1):
        detail = _title_detail(entry["title"])
        if detail:
            item = _normalize_usable_series(detail, detail)
            if not item:
                continue
        else:
            item = {
                "title": entry["title"],
                "poster_url": None,
                "release_year": "Unknown",
                "overview": "Curated series pick.",
                "vote_average": 0.0,
                "imdb_id": "",
            }

        item["release_date_label"] = ""
        item["release_order"] = index
        curated.append(item)

    if curated:
        return curated, None

    return [], "CinePick could not load this curated series collection right now."


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
        parsed_release_year = _parse_release_year(release_year)
        if parsed_release_year and parsed_release_year > date.today().year:
            continue

        dedupe_key = imdb_id or title.lower()
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        detail = _movie_detail(imdb_id) if imdb_id else _title_detail(title)
        if detail:
            movie = _normalize_usable_movie(
                {
                    "Title": title,
                    "Year": release_year,
                    "imdbID": imdb_id,
                    "Poster": detail.get("Poster"),
                },
                detail,
            )
            if movie:
                movies.append(movie)
        elif not parsed_release_year or parsed_release_year <= date.today().year:
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
        movie = _normalize_usable_movie(item, detail)
        if movie:
            movies.append(movie)

    fallback_notice = None
    if matched_term.lower() != search_term.strip().lower():
        fallback_notice = f'No exact title matches for "{search_term}". Showing results for "{matched_term}" instead.'

    if not movies and search_results:
        quality_notice = "CinePick filtered out non-standard or unreleased titles for this page."
        return [], total_pages, f"{fallback_notice} {quality_notice}".strip() if fallback_notice else quality_notice

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
            movie = _normalize_usable_movie(item, detail)
            if not movie:
                continue
            shuffled_results.append(movie)
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
                    movie = _normalize_usable_movie(item, detail)
                    if not movie:
                        continue
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


def _serialize_ai_titles(titles: list[str]) -> str:
    return "|".join(title for title in titles if title)


def _deserialize_ai_titles(raw_titles: str) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for title in raw_titles.split("|"):
        cleaned = title.strip()
        normalized = cleaned.casefold()
        if not cleaned or normalized in seen:
            continue
        seen.add(normalized)
        titles.append(cleaned)
    return titles


def _clean_ai_title_line(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"^\d+[\).\-\s]+", "", cleaned)
    cleaned = re.sub(r"^[-*•]\s*", "", cleaned)
    cleaned = re.sub(r"\s*\(\d{4}\)\s*$", "", cleaned)
    cleaned = cleaned.strip(" \"'`-\t")

    lower_cleaned = cleaned.casefold()
    if not cleaned:
        return ""
    if lower_cleaned.startswith("here are"):
        return ""
    if lower_cleaned.startswith("sure"):
        return ""
    if lower_cleaned.startswith("certainly"):
        return ""

    return cleaned


def _franchise_ai_titles(slug: str, fallback: dict[str, Any]) -> list[str]:
    expected_type = fallback.get("expected_type", "movie")
    count_hint = int(fallback.get("ai_target_count", 12))
    prompt = (
        f"List about {count_hint} real {'TV series' if expected_type == 'series' else 'movies'} for this CinePick page.\n"
        f"Slug: {slug}\n"
        f"Display name: {fallback['name']}\n"
        f"Collection kind: {fallback['collection_kind']}\n"
        f"Guidance: {AI_DYNAMIC_FRANCHISE_GUIDANCE.get(slug, '')}\n"
        "Return one title per line only. No numbering, no bullets, no commentary."
    )

    output_text = _gemini_text(prompt)
    if not output_text:
        return []

    titles: list[str] = []
    seen: set[str] = set()
    for line in output_text.splitlines():
        cleaned_title = _clean_ai_title_line(line)
        normalized = cleaned_title.casefold()
        if not cleaned_title or normalized in seen:
            continue
        seen.add(normalized)
        titles.append(cleaned_title)
    return titles


def _fallback_franchise_search_terms(slug: str) -> list[str]:
    return {
        "marvel": ["marvel movie", "avengers movie", "iron man"],
        "dc": ["dc movie", "batman movie", "superman movie"],
        "bollywood": ["bollywood movie", "hindi movie", "shah rukh khan movie"],
        "south-indian": ["telugu movie", "tamil movie", "south indian movie"],
        "indian-drama": ["indian drama movie", "hindi drama movie", "award winning indian movie"],
        "cinepick-best-movies": ["top rated movie", "best movie", "classic movie"],
        "cinepick-best-series": ["top rated series", "best tv series", "prestige drama series"],
    }.get(slug, [slug.replace("-", " ")])


@lru_cache(maxsize=16)
def _tmdb_company_fallback_titles(slug: str) -> list[str]:
    company_id = TMDB_COMPANY_FALLBACKS.get(slug)
    if not company_id:
        return []

    titles_with_dates: list[tuple[str, str]] = []
    total_pages = 1

    for page in range(1, 6):
        payload = _tmdb_request(f"company/{company_id}/movies", {"page": page})
        results = payload.get("results") or []
        if not results:
            break

        total_pages = int(payload.get("total_pages", total_pages) or total_pages)
        for item in results:
            title = str(item.get("title") or "").strip()
            release_date = str(item.get("release_date") or "").strip()
            if not title or not release_date:
                continue
            if any(pattern in title.lower() for pattern in NOISY_TITLE_PATTERNS):
                continue
            titles_with_dates.append((title, release_date))

        if page >= total_pages:
            break

    titles_with_dates.sort(key=lambda item: item[1])
    return _dedupe_preserve_order([title for title, _release_date in titles_with_dates])


def _fallback_franchise_titles(slug: str, *, expected_type: str) -> list[str]:
    if slug in {"marvel", "dc"}:
        source_titles = _tmdb_company_fallback_titles(slug)
        if source_titles:
            return source_titles
        return []

    titles: list[str] = []
    seen: set[str] = set()

    for term in _fallback_franchise_search_terms(slug):
        payload = _omdb_request({"s": term, "type": expected_type, "page": 1})
        if payload.get("Response") == "False":
            continue

        for item in payload.get("Search", []):
            title = str(item.get("Title") or "").strip()
            normalized = title.casefold()
            if not title or normalized in seen:
                continue
            seen.add(normalized)
            titles.append(title)

    return titles


def _ai_recommend_titles(prompt: str) -> tuple[list[str], str | None]:
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        return [], None

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return [], "Add GEMINI_API_KEY to your .env file to unlock mood-based AI recommendations."

    body = {
        "system_instruction": {
            "parts": [
                {
                    "text": (
                        "You are a movie recommendation engine. Based on the user's mood, return 8 movie titles that fit well. "
                        "Only include real released feature films. Avoid shorts, series, unreleased movies, documentaries unless clearly requested, "
                        "and avoid numbering or extra commentary. Return one movie title per line."
                    )
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": cleaned_prompt}],
            }
        ],
    }

    try:
        response = _get_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}",
            headers={
                "Content-Type": "application/json",
            },
            data=json.dumps(body).encode("utf-8"),
        )
    except Exception:
        return [], "Gemini was unavailable, so CinePick could not generate mood-based recommendations right now."

    candidates = response.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            output_text = (part.get("text") or "").strip()
            if output_text:
                titles: list[str] = []
                seen: set[str] = set()
                for line in output_text.splitlines():
                    cleaned_title = _clean_ai_title_line(line)
                    normalized = cleaned_title.casefold()
                    if not cleaned_title or normalized in seen:
                        continue
                    seen.add(normalized)
                    titles.append(cleaned_title)
                if titles:
                    return titles, None

    return [], "Gemini did not return usable movie recommendations right now."


def _normalize_ai_search_results(movies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_movies = []
    for movie in movies:
        detail = _movie_detail(movie.get("imdbID", ""))
        normalized_movie = _normalize_usable_movie(movie, detail)
        if not normalized_movie:
            continue
        normalized_movie["overview"] = "Fallback recommendation match based on the mood you described."
        normalized_movies.append(normalized_movie)
    return normalized_movies


def _fetch_ai_movies(search_term: str, page: int) -> tuple[list[dict[str, Any]], int, str | None]:
    movies_payload = _omdb_request({"s": search_term, "type": "movie", "page": page})
    if movies_payload.get("Response") == "False":
        return [], 1, movies_payload.get("Error") or "No AI suggestions were found."

    total_results = int(movies_payload.get("totalResults", 0) or 0)
    total_pages = max(1, min((total_results + 9) // 10, 100))
    return _normalize_ai_search_results(movies_payload.get("Search", [])), total_pages, None


def _fetch_ai_recommendations(titles: list[str], page: int) -> tuple[list[dict[str, Any]], int, int, str | None]:
    recommendations: list[dict[str, Any]] = []

    for title in titles:
        detail = _title_detail(title)
        if not detail:
            continue
        movie = _normalize_usable_movie(detail, detail)
        if not movie:
            continue
        movie["overview"] = "AI recommendation chosen to match the mood or vibe you described."
        recommendations.append(movie)

    if not recommendations:
        return [], 1, 1, "CinePick could not turn that mood into solid movie recommendations right now."

    paginated, current_page, total_pages = _paginate_collection_items(recommendations, page)
    return paginated, current_page, total_pages, None


def _page_url(
    request: HttpRequest,
    *,
    page: int,
    extra_params: dict[str, str] | None = None,
) -> str:
    params = request.GET.copy()

    if extra_params:
        for key, value in extra_params.items():
            if value:
                params[key] = value
            elif key in params:
                del params[key]

    if page <= 1:
        if "page" in params:
            del params["page"]
    else:
        params["page"] = str(page)

    query_string = params.urlencode()
    return f"{request.path}?{query_string}" if query_string else request.path


def _pagination_items(
    request: HttpRequest,
    *,
    current_page: int,
    total_pages: int,
    extra_params: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if total_pages <= 1:
        return []

    pages = {1, total_pages}
    pages.update(range(max(1, current_page - 1), min(total_pages, current_page + 1) + 1))
    ordered_pages = sorted(pages)

    items: list[dict[str, Any]] = []
    previous_page = 0
    for page_number in ordered_pages:
        if previous_page and page_number - previous_page > 1:
            items.append({"is_gap": True, "label": "..."})

        items.append(
            {
                "is_gap": False,
                "label": str(page_number),
                "url": _page_url(request, page=page_number, extra_params=extra_params),
                "is_current": page_number == current_page,
            }
        )
        previous_page = page_number

    return items


def _pagination_context(
    request: HttpRequest,
    *,
    current_page: int,
    total_pages: int,
    extra_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "show_pagination": total_pages > 1,
        "previous_url": _page_url(request, page=current_page - 1, extra_params=extra_params) if current_page > 1 else "",
        "next_url": _page_url(request, page=current_page + 1, extra_params=extra_params) if current_page < total_pages else "",
        "pagination_items": _pagination_items(
            request,
            current_page=current_page,
            total_pages=total_pages,
            extra_params=extra_params,
        ),
    }


def _catalog_context(
    *,
    request: HttpRequest,
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
        **_pagination_context(request, current_page=page, total_pages=total_pages),
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

    redirect_slug = CURATED_SEARCH_REDIRECTS.get(_normalized_search_key(query))
    if redirect_slug:
        return redirect("franchise_view", slug=redirect_slug)

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
            "show_pagination": False,
            "previous_url": "",
            "next_url": "",
            "pagination_items": [],
        }
        return render(request, "movies/home.html", context)

    context = _catalog_context(request=request, request_user=request.user, search_term=query, page=page, query=query)
    context["is_random_page"] = False
    context["recent_releases"] = []
    context["recent_releases_error"] = None
    context["recent_release_label"] = ""
    context["director_cards"] = _director_cards()
    return render(request, "movies/home.html", context)


def about_view(request: HttpRequest) -> HttpResponse:
    return render(request, "movies/about.html")


def _render_static_page(request: HttpRequest, slug: str) -> HttpResponse:
    page = _dynamic_static_page(slug) or STATIC_PAGE_CONTENT[slug]
    return render(request, "movies/static_page.html", {"page": page})


def contact_view(request: HttpRequest) -> HttpResponse:
    return _render_static_page(request, "contact")


def privacy_view(request: HttpRequest) -> HttpResponse:
    return _render_static_page(request, "privacy")


def terms_view(request: HttpRequest) -> HttpResponse:
    return _render_static_page(request, "terms")


def directors_page(request: HttpRequest) -> HttpResponse:
    return render(request, "movies/directors.html", {"director_cards": _director_cards()})


def franchise_view(request: HttpRequest, slug: str) -> HttpResponse:
    franchise, all_movies, api_error = _cached_franchise_payload(slug)
    if not franchise:
        return redirect("home")

    page = _safe_page(request.GET.get("page"))
    movies, current_page, total_pages = _paginate_collection_items(all_movies, page)
    _attach_wishlist_state(request_user=request.user, movies=movies)

    return render(
        request,
        "movies/franchise_detail.html",
        {
            "franchise": franchise,
            "movies": movies,
            "total_movies": len(all_movies),
            "api_error": api_error,
            "current_page": current_page,
            "total_pages": total_pages,
            "back_anchor": franchise.get("home_anchor", "universes"),
            **_pagination_context(request, current_page=current_page, total_pages=total_pages),
        },
    )


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
        request=request,
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
    page = _safe_page(request.GET.get("page"))
    current_page = page
    movies: list[dict[str, Any]] = []
    title_seed = (request.GET.get("titles") or "").strip()
    recommended_titles = _deserialize_ai_titles(title_seed) if title_seed else []
    api_error = None
    total_pages = 1

    if prompt:
        generation_notice = None
        fallback_keywords = _extract_keywords(prompt)
        if not recommended_titles:
            recommended_titles, generation_notice = _ai_recommend_titles(prompt)

        movies, current_page, total_pages, api_error = _fetch_ai_recommendations(recommended_titles, page)
        if not movies:
            movies, total_pages, fallback_error = _fetch_ai_movies(fallback_keywords or prompt, page)
            current_page = page
            if movies:
                api_error = generation_notice or "CinePick could not verify the AI title list, so it fell back to mood-based keyword matches."
            elif fallback_error:
                api_error = fallback_error
        elif generation_notice and not api_error:
            api_error = generation_notice

    _attach_wishlist_state(request_user=request.user, movies=movies)

    return render(
        request,
        "movies/ai.html",
        {
            "query": prompt,
            "recommended_titles": recommended_titles,
            "titles_param": _serialize_ai_titles(recommended_titles),
            "movies": movies,
            "api_error": api_error,
            "current_page": current_page,
            "total_pages": total_pages,
            **_pagination_context(
                request,
                current_page=current_page,
                total_pages=total_pages,
                extra_params={"titles": _serialize_ai_titles(recommended_titles)},
            ),
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
