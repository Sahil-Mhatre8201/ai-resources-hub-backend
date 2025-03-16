from fastapi import FastAPI, HTTPException, Query
import httpx
from fastapi.middleware.cors import CORSMiddleware
import xml.etree.ElementTree as ET
from typing import List
from functools import cmp_to_key
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import feedparser
import ssl
import certifi
import urllib.request 
import praw
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import openai

load_dotenv()


app = FastAPI()

GITHUB_API_URL = "https://api.github.com/search/repositories"
ARXIV_API_URL = "http://export.arxiv.org/api/query"
GITHUB_API_BASE_URL = "https://api.github.com/repos"

COURSERA_API_URL = "https://api.coursera.org/api/courses.v1"
EDX_API_URL = "https://www.edx.org/api/catalog/v1/courses"



GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Ensure API key is set
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API Key is missing. Set it in the .env file.")

# Allow CORS for frontend requests
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")


reddit = praw.Reddit(
    client_id=CLIENT_ID,  # Your client_id
    client_secret=CLIENT_SECRET,  # Your client_secret
    user_agent="python:ai-hub:v1.0 (by /u/Last_Internet_9156)"  # Your custom user agent
)

openai.api_key = OPENAI_API_KEY

#AI handbooks static data
AI_HANDBOOKS = [
    {
        "title": "Deep Learning",
        "url": "https://www.deeplearningbook.org/",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/en/6/68/Deep_Learning_Book_cover.jpg",
        "description": "Comprehensive deep learning book by Ian Goodfellow, Yoshua Bengio, and Aaron Courville.",
        "platform": "Book",
        "author": "Ian Goodfellow, Yoshua Bengio, Aaron Courville",
        "publication_year": "2016"
    },
    {
        "title": "Stanford CS229 Machine Learning Notes",
        "url": "https://cs229.stanford.edu/",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/commons/8/80/Andrew_Ng.png",
        "description": "Lecture notes from Stanford's CS229 course by Andrew Ng.",
        "platform": "Course Notes",
        "author": "Andrew Ng",
        "publication_year": "Ongoing"
    },
    {
        "title": "MIT 6.S191: Introduction to Deep Learning",
        "url": "https://introtodeeplearning.com/","thumbnail": "https://introtodeeplearning.com/assets/logo.png",
        "description": "MIT’s official introductory deep learning course materials.",
        "platform": "Course Notes",
        "author": "MIT Deep Learning",
        "publication_year": "Ongoing"
    },
    {
        "title": "Pattern Recognition and Machine Learning",
        "url": "https://www.microsoft.com/en-us/research/people/cmbishop/prml-book/",
        "thumbnail": "https://www.microsoft.com/en-us/research/uploads/prod/2016/11/prml-cover.jpg",
        "description": "Comprehensive book on probabilistic machine learning by Christopher Bishop.",
        "platform": "Book",
        "author": "Christopher Bishop",
        "publication_year": "2006"
    }
]


class ChatRequest(BaseModel):
    message: str



async def fetch_github_repos(query: str, per_page: int = 30, page: int = 1):
    """Fetch AI repositories from GitHub along with their top contributors (with profile pictures)."""
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "page": page,
        "per_page": per_page
    }

    async with httpx.AsyncClient() as client:
        try:
            # Fetch repositories
            response = await client.get(GITHUB_API_URL, params=params, headers=HEADERS)

            if response.status_code == 403:
                raise HTTPException(status_code=403, detail="GitHub API rate limit exceeded. Try again later.")

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"GitHub API Error: {response.text}")

            data = response.json()
            repositories = []

            for repo in data.get("items", []):
                owner, repo_name = repo["owner"]["login"], repo["name"]
                contributors_url = f"https://api.github.com/repos/{owner}/{repo_name}/contributors"

                # Fetch top 3 contributors (including profile pictures)
                contributors = []
                try:
                    contrib_response = await client.get(contributors_url, params={"per_page": 3}, headers=HEADERS)

                    if contrib_response.status_code == 403:
                        print("GitHub API rate limit reached while fetching contributors.")
                        break  # Stop fetching further contributors to avoid API blocking

                    if contrib_response.status_code == 204:
                        print(f"No contributors found for {repo_name}.")  # Debugging
                        contributors = []  # No content, so keep contributors empty

                    elif contrib_response.status_code == 200:
                        contributors = [
                            {
                                "username": user.get("login", "Unknown"),
                                "contributions": user.get("contributions", 0),
                                "avatar_url": user.get("avatar_url", "")
                            }
                            for user in contrib_response.json()
                        ]

                    else:
                        print(f"Error fetching contributors for {repo_name}: {contrib_response.status_code}, {contrib_response.text}")

                except httpx.RequestError as e:
                    print(f"Network error while fetching contributors for {repo_name}: {e}")
                except Exception as e:
                    print(f"Unexpected error while fetching contributors for {repo_name}: {e}")

                repositories.append({
                    "resource_type": "github",
                    "name": repo["name"],
                    "owner": repo["owner"]["login"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description", "No description available"),
                    "stars": repo["stargazers_count"],
                    "url": repo["html_url"],
                    "language": repo.get("language", "Unknown"),
                    "contributors": contributors
                })

            return repositories

        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Network error while fetching GitHub repositories: {e}")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {e}")


async def fetch_arxiv_papers(query: str, max_results: int = 30, page: int = 1):
    """Fetch AI research papers from arXiv."""
    start_index = (page - 1) * max_results

    params = {
        "search_query": f"all:{query}",
        "start": start_index,
        "max_results": max_results
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(ARXIV_API_URL, params=params)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch arXiv data")

    root = ET.fromstring(response.text)
    papers = []
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        summary = entry.find("{http://www.w3.org/2005/Atom}summary").text
        link = entry.find("{http://www.w3.org/2005/Atom}id").text
        authors = [author.find("{http://www.w3.org/2005/Atom}name").text for author in entry.findall("{http://www.w3.org/2005/Atom}author")]
        published_date = entry.find("{http://www.w3.org/2005/Atom}published").text 

        papers.append({
            "resource_type": "arxiv paper",
            "title": title,
            "summary": summary,
            "link": link,
            "authors": authors,
            "published_date": published_date
        })
    return papers


import requests

async def fetch_coursera_courses(query: str, max_results: int = 10):
    """Fetch AI-related courses from Coursera API, including thumbnails & descriptions."""
    try:
        params = {"query": query, "limit": max_results}
        response = requests.get(COURSERA_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        courses = [
            {
                "resource_type": "courses",
                "title": course["name"],
                "url": f"https://www.coursera.org/learn/{course['slug']}",
                "thumbnail": course.get("photoUrl", "https://www.coursera.org/default-thumbnail.jpg"),
                #"description": course.get("description", "No description available"),
                "platform": "Coursera",
                #"duration": f"{course.get('workload', 'Unknown')} hours"
            }
            for course in data.get("elements", [])
        ]
        return courses
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Coursera courses: {e}")
        return []


async def fetch_edx_courses(query: str, max_results: int = 10):
    """Fetch AI-related courses from edX API, including thumbnails & descriptions."""
    try:
        params = {"search_query": query, "limit": max_results}
        response = requests.get(EDX_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        courses = [
            {
                "resource_type": "courses",
                "title": course["title"],
                "url": course["marketing_url"],
                "thumbnail": course["image"]["src"] if "image" in course and "src" in course["image"] else "https://www.edx.org/default-thumbnail.jpg",
                "description": course.get("full_description", "No description available"),
                "platform": "edX",
                "duration": course.get("effort", "Unknown")
            }
            for course in data.get("results", [])
        ]
        return courses
    except requests.exceptions.RequestException as e:
        print(f"Error fetching edX courses: {e}")
        return []

async def fetch_courses(query: str, max_results: int = 10):
    """Fetch AI courses from multiple platforms: Coursera, edX, Udacity, Fast.ai"""
    coursera_courses = await fetch_coursera_courses(query, max_results)
    edx_courses = await fetch_edx_courses(query, max_results)
    
    return coursera_courses + edx_courses 

async def fetch_blogs(query: str, max_results: int = 5):
    try:
        # Search Reddit for posts matching the query in relevant subreddits
        search_results = reddit.subreddit("datascience").search(query, limit=max_results)

        filtered_posts = []
        for submission in search_results:
            filtered_posts.append({
                'resource_type': "blog",
                'title': submission.title,
                'url': submission.url,
                'description': submission.selftext if submission.selftext else "No summary available"
            })

        if not filtered_posts:
            print(f"No blog posts matched query: {query}")

        return filtered_posts

    except Exception as e:
        print(f"Error fetching blogs: {e}")
        return []

async def fetch_ai_handbooks(query: str, max_results: int = 10):
    """Fetch AI-related handbooks & documentation based on query."""
    try:
        # Simple text-based search in static AI_HANDBOOKS list
        results = [
            book for book in AI_HANDBOOKS
            if query.lower() in book["title"].lower() or query.lower() in book["description"].lower()
        ]

        return results[:max_results]  # Limit results
    except Exception as e:
        print(f"Error fetching AI handbooks: {e}")
        return []


@app.get("/search-ai-repos")
async def search_ai_repositories(q: str = Query(..., title="Search Query"),
    max_results: int = Query(10, title="Max Results Per Page"),
    page: int = Query(1, title="Page Number")):
    """Route for fetching AI repositories from GitHub."""
    repos = await fetch_github_repos(q, per_page=max_results, page=page)
    return {
        "page": page,
        "max_results": max_results,
        "repos": repos
    }


@app.get("/search-arxiv-papers")
async def search_arxiv_papers(
    q: str = Query(..., title="Search Query"), 
    max_results: int = Query(10, title="Max Results Per Page"),
    page: int = Query(1, title="Page Number")
):
    """Route for fetching AI research papers from arXiv with pagination."""
    papers = await fetch_arxiv_papers(q, max_results, page)
    
    return {
        "page": page,
        "max_results": max_results,
        "papers": papers
    }

@app.get("/search-courses")
async def search_courses(
    q: str = Query(..., title="Search Query"),
    max_results: int = Query(10, title="Max Results Per Page"),
    page: int = Query(1, title="Page Number")
):
    """Fetch AI courses from Coursera & edX."""
    try:
        courses = await fetch_courses(q, max_results)

        return {
            "page": page,
            "max_results": max_results,
            "courses": courses
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch courses: {str(e)}")

@app.get("/search-blogs")
async def search_arxiv_papers(
    q: str = Query(..., title="Search Query"), 
    max_results: int = Query(10, title="Max Results Per Page"),
):
    """Route for fetching AI research papers from arXiv with pagination."""
    papers = await fetch_blogs(q, max_results)
    
    return {
        "max_results": max_results,
        "blogs": papers
    }

@app.get("/get-resources")
async def get_resources(q: str = Query(..., title="Search Query"), max_results: int = 50):
    """
    Fetch both GitHub repositories and arXiv research papers for the given query.
    Returns a JSON object containing both types of resources.
    """
    try:
        github_repos, arxiv_papers, courses, handbooks = await fetch_github_repos(q, max_results), await fetch_arxiv_papers(q, max_results), await fetch_courses(q, max_results),await fetch_ai_handbooks(q, max_results)
        return {"repositories": github_repos, "arxivPapers": arxiv_papers,"courses":courses,"handbooks":handbooks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch resources: {str(e)}")


@app.get("/repo-details")
async def get_repo_details(owner: str, repo: str):
    """
    Fetch detailed information about a GitHub repository.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Fetch repository details
            repo_response = await client.get(f"{GITHUB_API_BASE_URL}/{owner}/{repo}", headers=HEADERS)
            if repo_response.status_code != 200:
                raise HTTPException(status_code=repo_response.status_code, detail="Failed to fetch repo details")

            # Fetch README
            readme_response = await client.get(f"{GITHUB_API_BASE_URL}/{owner}/{repo}/readme", headers=HEADERS)
            readme_content = readme_response.json().get("content", "") if readme_response.status_code == 200 else ""

            # Fetch contributors
            contributors_response = await client.get(f"{GITHUB_API_BASE_URL}/{owner}/{repo}/contributors", headers=HEADERS)
            contributors = [
                {
                    "login": c["login"],
                    "avatar_url": c["avatar_url"],
                    "contributions": c["contributions"]
                } for c in contributors_response.json() if contributors_response.status_code == 200
            ]

            # Fetch languages
            languages_response = await client.get(f"{GITHUB_API_BASE_URL}/{owner}/{repo}/languages", headers=HEADERS)
            languages = list(languages_response.json().keys()) if languages_response.status_code == 200 else []

            return {
                "repo": repo_response.json(),
                "readme": readme_content,
                "contributors": contributors,
                "languages": languages
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching repo details: {str(e)}")

def rank_results(query: str, resources: List[dict]) -> List[dict]:
    query = query.lower().strip()

    # Extract titles and descriptions
    resource_texts = [
        (resource.get("title") or resource.get("name") or "") + " " + 
        (resource.get("summary") or resource.get("description") or "")
        for resource in resources
    ]

    # Include query in the list for comparison
    all_texts = [query] + resource_texts

    # Convert text into TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    # Compute cosine similarity between query and resources
    query_vector = tfidf_matrix[0]  # The first vector is the query
    resource_vectors = tfidf_matrix[1:]  # Remaining vectors are resource texts

    similarities = cosine_similarity(query_vector, resource_vectors).flatten()

    # Attach scores to resources and sort by similarity
    for i, resource in enumerate(resources):
        resource["similarity_score"] = similarities[i]

    ranked_resources = sorted(resources, key=lambda x: x["similarity_score"], reverse=True)

    return ranked_resources

# @app.get("/v2-get-resources")
# async def v2_get_resources(
#     q: str = Query(..., title="Search Query"), 
#     max_results: int = 20,   # Increase default page size
#     page: int = 1
# ):
#     try:
#         github_repos = await fetch_github_repos(q, per_page=30)  # Increase GitHub fetch limit
#         arxiv_papers = await fetch_arxiv_papers(q, max_results=30)  # Increase arXiv fetch limit

#         all_results = github_repos + arxiv_papers
#         ranked_results = rank_results(q, all_results)

#         start_idx = (page - 1) * max_results
#         end_idx = start_idx + max_results
#         paginated_results = ranked_results[start_idx:end_idx]

#         return {
#             "results": paginated_results,
#             "total_results": len(ranked_results),
#             "page": page,
#             "max_results": max_results,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to fetch and rank resources: {str(e)}")


@app.get("/v2-get-resources")
async def v2_get_resources(
    q: str = Query(..., title="Search Query"), 
    max_results: int = 25,   # Number of results per page
    page: int = 1
):
    try:
        # Split max_results between GitHub, arXiv, and Blogs
        github_limit = max_results // 5
        arxiv_limit = max_results // 5
        blogs_limit = max_results//5 # Ensures we always get 'max_results' total
        handbooks_limit=max_results//5
        courses_limit = max_results - (github_limit + arxiv_limit + blogs_limit+handbooks_limit)


        # Fetch only required results for the requested page
        try:
            github_repos = await fetch_github_repos(q, per_page=github_limit, page=page)
        except Exception as e:
            print("Error fetching GitHub repos:", e)
            github_repos = []

        try:
            arxiv_papers = await fetch_arxiv_papers(q, max_results=arxiv_limit, page=page)
        except Exception as e:
            print("Error fetching Arxiv papers:", e)
            arxiv_papers = []

        try:
            blogs = await fetch_blogs(q, max_results=blogs_limit)  # Fetch blogs from Towards Data Science
        except Exception as e:
            print("Error fetching Blogs:", e)
            blogs = []

        try:
            courses = await fetch_courses(q, max_results=courses_limit)
        except Exception as e:
            print("Error fetching Courses:", e)
            courses = []

        try:
            handbooks = await fetch_ai_handbooks(q, max_results=handbooks_limit)
        except Exception as e:
            print("Error fetching Courses:", e)
            courses = []

        all_results = github_repos + arxiv_papers + blogs + courses + handbooks
        ranked_results = rank_results(q, all_results)

        return {
            "results": ranked_results,
            "page": page,
            "max_results": max_results,
        }


    except Exception as e:
        error_trace = traceback.format_exc()
        print("Error while fetching all resources:", e)
        print("Stack trace:", error_trace)  # Logs the exact issue
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch and rank resources: {str(e)}\n{error_trace}"
        )


# @app.get("/get-filtered-resources")
# async def get_filtered_resources(
#     q: str = Query(..., title="Search Query"),
#     filters: str = Query("", title="Filter Categories"),  # Comma-separated filters
#     max_results: int = 20,
#     page: int = 1
# ):
#     try:
#         selected_filters = filters.split(",") if filters else []
#         results = []

#         if "github" in selected_filters:
#             results += await fetch_github_repos(q, per_page=30)

#         if "research_papers" in selected_filters:
#             results += await fetch_arxiv_papers(q, max_results=30)

#         # Add more conditions for other data sources if needed

#         ranked_results = rank_results(q, results)
        
#         start_idx = (page - 1) * max_results
#         end_idx = start_idx + max_results
#         paginated_results = ranked_results[start_idx:end_idx]

#         return {
#             "results": paginated_results,
#             "total_results": len(ranked_results),
#             "page": page,
#             "max_results": max_results,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to fetch filtered resources: {str(e)}")

@app.get("/get-filtered-resources")
async def get_filtered_resources(
    q: str = Query(..., title="Search Query"),
    filters: str = Query("", title="Filter Categories"),  # Comma-separated filters
    max_results: int = 10,
    page: int = 1
):
    try:
        available_filters = ["github", "research_papers", "blogs", "courses","handbooks"]
        selected_filters = filters.split(",") if filters else available_filters  # Apply all filters if none are selected

        github_repos = []
        arxiv_papers = []
        blogs = []
        courses=[]
        handbooks=[]

        # Compute resource limits correctly
        source_count = len(selected_filters)
        per_source_limit = max_results // source_count
        remainder = max_results % source_count

        if "github" in selected_filters:
            github_repos = await fetch_github_repos(q, per_page=per_source_limit + (1 if remainder > 0 else 0), page=page)
            remainder -= 1  # Distribute remainder fairly

        if "research_papers" in selected_filters:
            try:
                arxiv_papers = await fetch_arxiv_papers(q, max_results=per_source_limit + (1 if remainder > 0 else 0), page=page)
            except httpx.ReadTimeout:
                print("Timeout occurred while fetching ArXiv papers")
                arxiv_papers = [] 

        if "blogs" in selected_filters:
            blogs = await fetch_blogs(q, max_results=per_source_limit + (1 if remainder > 0 else 0))

        if "courses" in selected_filters:
            courses = await fetch_courses(q, max_results=per_source_limit + (1 if remainder > 0 else 0))

        if "handbooks" in selected_filters:
            handbooks = await fetch_ai_handbooks(q, max_results)

        all_results = github_repos + arxiv_papers + blogs+ courses +handbooks
        ranked_results = rank_results(q, all_results)

        return {
            "results": ranked_results,
            "page": page,
            "max_results": max_results,
        }

    except Exception as e:
        error_trace = traceback.format_exc()
        print("Error while fetching all resources:", e)
        print("Stack trace:", error_trace)  # Logs the exact issue
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch filtered resources: {str(e)}\n{error_trace}"
        )



@app.post("/chat")
async def chatbot(query: ChatRequest):
    """Chatbot API using OpenAI's GPT model"""
    user_message = query.message

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": user_message}
            ],
            # max_tokens=100
        )

        reply = response.choices[0].message.content
        return {"response": reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))