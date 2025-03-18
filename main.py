from fastapi import FastAPI, HTTPException, Query, status
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
from pydantic import BaseModel, HttpUrl
import openai
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from database import get_db
import models
from pydantic import BaseModel
from models import User
import bcrypt
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from fastapi import Cookie
from fastapi import Response
import traceback







load_dotenv()


app = FastAPI()

port = int(os.getenv("PORT", 8000))  # Use PORT from environment, default to 8000 for local testing


auth_router = APIRouter()
bookmark_router = APIRouter()
app.include_router(bookmark_router, prefix="/bookmarks", tags=["Bookmarks"])

# app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# app.include_router(bookmark_router, prefix="/bookmarks", tags=["Bookmarks"])

AI_HANDBOOKS = [
    {
        "resource_type": "handbook",
        "title": "Deep Learning",
        "url": "https://www.deeplearningbook.org/",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/en/6/68/Deep_Learning_Book_cover.jpg",
        "description": "Comprehensive deep learning book by Ian Goodfellow, Yoshua Bengio, and Aaron Courville.",
        "platform": "Book",
        "author": "Ian Goodfellow, Yoshua Bengio, Aaron Courville",
        "publication_year": "2016"
    },
    {
        "resource_type": "handbook",
        "title": "Stanford CS229 Machine Learning Notes",
        "url": "https://cs229.stanford.edu/",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/commons/8/80/Andrew_Ng.png",
        "description": "Lecture notes from Stanford's CS229 course by Andrew Ng.",
        "platform": "Course Notes",
        "author": "Andrew Ng",
        "publication_year": "Ongoing"
    },
    {
        "resource_type": "handbook",
        "title": "MIT 6.S191: Introduction to Deep Learning",
        "url": "https://introtodeeplearning.com/",
        "thumbnail": "https://introtodeeplearning.com/assets/logo.png",
        "description": "MIT’s official introductory deep learning course materials.",
        "platform": "Course Notes",
        "author": "MIT Deep Learning",
        "publication_year": "Ongoing"
    },
    {
        "resource_type": "handbook",
        "title": "Pattern Recognition and Machine Learning",
        "url": "https://www.microsoft.com/en-us/research/people/cmbishop/prml-book/",
        "thumbnail": "https://www.microsoft.com/en-us/research/uploads/prod/2016/11/prml-cover.jpg",
        "description": "Comprehensive book on probabilistic machine learning by Christopher Bishop.",
        "platform": "Book",
        "author": "Christopher Bishop",
        "publication_year": "2006"
    }
]

def hash_password(password: str) -> str:
    # Generate a salt
    salt = bcrypt.gensalt()
    # Hash the password with the salt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# Initialize the password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Define the verify_password function
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_current_user(user_id: str = Cookie(None), db: Session = Depends(get_db)):
    print(f"Received user_id: {user_id}")

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication")
    
    return user


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

GITHUB_API_URL = "https://api.github.com/search/repositories"
ARXIV_API_URL = "http://export.arxiv.org/api/query"
GITHUB_API_BASE_URL = "https://api.github.com/repos"
COURSERA_API_URL = "https://api.coursera.org/api/courses.v1"


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Ensure API key is set
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API Key is missing. Set it in the .env file.")

# Allow CORS for frontend requests
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://ai-resources-hub-frontend-844nzmki5.vercel.app",
    "https://*.vercel.app",  # Vercel frontend URL

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

class ChatRequest(BaseModel):
    message: str

class SignupRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class BookmarkCreate(BaseModel):
    url: str
    title: str
    description: str = None  # Optional description
    resource_type: str  # Type of resource (e.g., 'GitHub', 'Blog', etc.)

    class Config:
        orm_mode = True

class Bookmark(BookmarkCreate):
    id: int  # The ID is automatically generated by SQLAlchemy

class CommunityUploadCreate(BaseModel):
    title: str
    description: str
    resource_type: str  # Should be one of 'GitHub', 'Course', 'Blog', 'Research Paper'
    url: str 

class CommunityUploadResponse(BaseModel):
    id: int
    title: str
    description: str
    resource_type: str
    status: str
    user_id: int
    url: str

    class Config:
        orm_mode = True


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



async def fetch_coursera_courses(query: str, max_results: int = 10, page: int = 1):
    """Fetch AI-related courses from Coursera API, including descriptions."""
    start_index = (page - 1) * max_results  # Calculate pagination offset

    params = {
        "q": "search",  # The query type
        "query": query,  # The search string (AI, Machine Learning, etc.)
        "limit": max_results,  # Number of results per page
        "start": start_index,  # Pagination offset
        "includes": "partnerIds,photoUrl,description"  # Request additional fields
    }

    print(f"Fetching Coursera courses with query: {query}")  # Debug print to check query string

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(COURSERA_API_URL, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch Coursera data")

    # Debug: print the full response text
    print(f"Response Body: {response.text}")

    try:
        data = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing response JSON: {str(e)}")

    # Debug: check the structure of the response data
    print(f"Response JSON: {data}")

    courses = []
    if 'elements' in data and data['elements']:  # Check if 'elements' is present and not empty
        courses = [
            {
                "resource_type": "courses",
                "title": course["name"],
                "url": f"https://www.coursera.org/learn/{course['slug']}",
                "thumbnail": course.get("photoUrl", "https://www.coursera.org/default-thumbnail.jpg"),
                "platform": "Coursera",
                "description": course.get("description", "No description available")
            }
            for course in data["elements"]
        ]
    else:
        # When 'elements' is missing or empty, extract data from facets
        facets = data.get("paging", {}).get("facets", {})
        
        # Get courses from the most relevant subdomain based on query
        subdomains = facets.get("subdomains", {}).get("facetEntries", [])
        
        if subdomains:
            # Create artificial course entries from subdomain information
            for subdomain in subdomains[:max_results]:
                courses.append({
                    "resource_type": "courses",
                    "title": f"{subdomain.get('name', 'Unknown')} Courses",
                    "url": f"https://www.coursera.org/browse/{subdomain.get('id', '')}",
                    "thumbnail": "https://www.coursera.org/default-thumbnail.jpg",
                    "platform": "Coursera",
                    "description": f"Browse {subdomain.get('count', 0)} courses in {subdomain.get('name', 'this category')}"
                })
        
        print(f"Created {len(courses)} alternate recommendations from facets")

    if not courses:
        print("No courses found for the query")  # Debug print for empty result

    return courses





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

@app.get("/search-blogs")
async def search_arxiv_papers(
    q: str = Query(..., title="Search Query"), 
    max_results: int = Query(10, title="Max Results Per Page"),
):
    """Route for fetching AI research papers from arXiv with pagination."""
    papers =  await fetch_blogs(q, max_results)
    
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
        github_repos, arxiv_papers = await fetch_github_repos(q, max_results), await fetch_arxiv_papers(q, max_results)
        return {"repositories": github_repos, "arxivPapers": arxiv_papers}
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

def rank_results(query: str, resources: List[dict] = None) -> List[dict]:
    if resources is None or len(resources) == 0:
        return []
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
    max_results: int = 20,   # Number of results per page
    page: int = 1
):
    try:
        # Split max_results between GitHub, arXiv, and Blogs
        github_limit = max_results // 4
        arxiv_limit = max_results // 4
        blogs_limit = max_results // 4
        courses_limit = max_results - (github_limit + arxiv_limit + blogs_limit)

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
            courses = await fetch_coursera_courses(query=q, max_results=courses_limit, page=page)
        except Exception as e:
            print("Error fetching courses:", e)
            courses = []

        all_results = github_repos + arxiv_papers + blogs + courses + AI_HANDBOOKS
        ranked_results = rank_results(q, all_results)

        return {
            "results": ranked_results,
            "page": page,
            "max_results": max_results,
        }


    except Exception as e:
        rror_trace = traceback.format_exc()
        print("Error while fetching all resources:", e)
        print("Stack trace:", error_trace)  # Logs the exact issue
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch and rank resources: {str(e)}\n{error_trace}"
        )



@app.get("/get-filtered-resources")
async def get_filtered_resources(
    q: str = Query(..., title="Search Query"),
    filters: str = Query("", title="Filter Categories"),  # Comma-separated filters
    max_results: int = 10,
    page: int = 1
):
    try:
        available_filters = ["github", "research_papers", "blogs", "courses", "handbook"]
        selected_filters = filters.split(",") if filters else available_filters  # Apply all filters if none are selected

        github_repos = []
        arxiv_papers = []
        blogs = []
        courses = []
        handbooks = []

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
            try:
                courses = await fetch_coursera_courses(q, max_results=per_source_limit + (1 if remainder > 0 else 0), page=page)
            except httpx.ReadTimeout:
                print("Timeout occurred while fetching ArXiv papers")
                courses = [] 
        if "handbook" in selected_filters:
            handbooks = AI_HANDBOOKS if page == 1 else []

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
            detail=f"Failed to fetch filtered resources: {str(e)}\n{error_trace}"
        )



@app.post("/chat")
async def chatbot(query: ChatRequest):
    """Chatbot API using OpenAI's GPT model"""
    user_message = query.message

    async def stream_response():
        try:
            response_stream = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": user_message}
                ],
                stream=True  # Enable streaming
            )
            
            # Iterate through the streaming response
            # The OpenAI SDK returns an iterator, not an async iterator
            for chunk in response_stream:
                if chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield f"data: {content}\n\n"
                        
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
            
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )


@app.post("/signup")
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(User).filter(User.email == request.email).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create new user
    hashed_password = hash_password(request.password)
    new_user = User(email=request.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return JSONResponse(status_code=201, content={"message": "User created successfully"})

@app.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # Find the user in the database
    db_user = db.query(User).filter(User.email == request.email).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")
    
    # Verify password
    if not verify_password(request.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")

    # Set session (e.g., store user ID in cookie for simplicity)
    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(key="user_id", value=str(db_user.id), httponly=True, secure=True, samesite="None")
    return response

@app.post("/bookmarks", response_model=Bookmark, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    bookmark: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bookmark for the current user."""
    new_bookmark = models.Bookmark(
        url=bookmark.url,
        title=bookmark.title,
        description=bookmark.description,
        resource_type=bookmark.resource_type,
        user_id=current_user.id
    )
    
    db.add(new_bookmark)
    db.commit()
    db.refresh(new_bookmark)
    
    return new_bookmark

@app.get("/bookmarks", response_model=List[Bookmark])
async def get_bookmarks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get all bookmarks for the current user."""
    bookmarks = db.query(models.Bookmark).filter(
        models.Bookmark.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return bookmarks

@app.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a bookmark if it belongs to the current user."""
    bookmark = db.query(models.Bookmark).filter(
        models.Bookmark.id == bookmark_id,
        models.Bookmark.user_id == current_user.id
    ).first()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bookmark)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/uploads", response_model=CommunityUploadResponse, status_code=status.HTTP_201_CREATED)
async def submit_resource(
    resource: CommunityUploadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow a user to upload a resource for approval."""
    new_resource = models.CommunityUpload(
        title=resource.title,
        description=resource.description,
        resource_type=resource.resource_type,
        status="pending_approval",
        user_id=current_user.id,
        url=str(resource.url)
    )

    db.add(new_resource)
    db.commit()
    db.refresh(new_resource)

    return new_resource
   

@app.put("/uploads/{resource_id}/status", response_model=CommunityUploadResponse)
async def update_resource_status(
    resource_id: int,
    status_update: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow an admin to approve or reject a resource."""
    
    # Check if the current user is an admin (this can be based on a role or permission check)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have the necessary permissions to approve or reject resources"
        )
    
    # Fetch the resource
    resource = db.query(models.CommunityUpload).filter(models.CommunityUpload.id == resource_id).first()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # Validate the status update
    if status_update not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be either 'approved' or 'rejected'."
        )

    # Update the status
    resource.status = status_update
    db.commit()
    db.refresh(resource)

    return resource

@app.get("/uploads/pending_approval", response_model=List[CommunityUploadResponse])
async def get_pending_approval_resources(
    db: Session = Depends(get_db)
):
    """Retrieve all resources with 'pending_approval' status."""
    
    # Query for resources that are pending approval
    pending_resources = db.query(models.CommunityUpload).filter(models.CommunityUpload.status == "pending_approval").all()

    return pending_resources

@app.get("/uploads/approved", response_model=List[CommunityUploadResponse])
async def get_pending_approval_resources(
    db: Session = Depends(get_db)
):    
    approved_resources = db.query(models.CommunityUpload).filter(models.CommunityUpload.status == "approved").all()

    return approved_resources

@app.get("/courses")
async def get_coursera_courses(
    query: str = Query(..., min_length=1),
    max_results: int = Query(10, ge=1, le=50),
    page: int = Query(1, ge=1)
):
    """API to fetch Coursera courses based on search query with pagination."""
    print("query", query)
    courses = await fetch_coursera_courses(query, max_results, page)

    return {"query": query, "page": page, "results": courses}

@app.get("/ai-handbooks")
async def get_ai_handbooks():
    return {"handbooks": AI_HANDBOOKS}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
