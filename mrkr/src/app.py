# ---------------------------------------------------------------------------- #

from fastapi import FastAPI, Request, Response, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from starlette.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarlettHTTPException
from typing import Any, Tuple, List, Annotated, Callable, Optional
import datetime

# ---------------------------------------------------------------------------- #

from .logging import Logger
from .config import config
from .database import Database
from .session import SessionManager

# ---------------------------------------------------------------------------- #

app = FastAPI()

app.mount("/static", StaticFiles(directory="mrkr/static"), name="static")
app.add_middleware(GZipMiddleware, minimum_size=1000)

logger = Logger(name="mrkr.app")
templates = Jinja2Templates(directory="mrkr/templates", autoescape=True)
database = Database(alias="POSTGRES")

HttpSessionDep = Annotated[
    SessionManager, Depends(SessionManager.get_session(database))
]

AuthHttpSessionDep = Annotated[
    SessionManager, Depends(SessionManager.get_authenticated_session(database))
]

# ---------------------------------------------------------------------------- #


@app.middleware("http")
async def add_process_time_header(
    request: Request,
    call_next: Callable
) -> Response:
    """
    Add security headers to the response (if not static).
    """
    response = await call_next(request)

    if request.url.path.startswith("/static"):
        return response

    response.headers["Access-Control-Allow-Origin"] = "https://yoursite.com"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; "
        f"script-src 'self'; "
        f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        f"font-src 'self' https://fonts.gstatic.com; "
        f"object-src 'none';"
    )
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Strict-Transport-Security"] = (
        "max-age=63072000; includeSubDomains; preload"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    return response

# ---------------------------------------------------------------------------- #


@app.middleware("http")
async def add_session_cookie(
    request: Request,
    call_next: Callable
) -> Response:
    """
    Add the session cookie.
    """
    response = await call_next(request)

    if hasattr(request.state, "session_token"):
        response.set_cookie(
            key=config.session_name,
            value=request.state.session_token
        )

    return response

# ---------------------------------------------------------------------------- #


@app.exception_handler(HTTPException)
@app.exception_handler(StarlettHTTPException)
@app.exception_handler(Exception)
@app.exception_handler(RequestValidationError)
async def http_exception_handler(
    request: Request,
    exception: HTTPException | StarlettHTTPException |
    Exception | RequestValidationError
) -> Response:
    """
    Handle exceptions gracefully by returning an error page.
    """
    if isinstance(exception, HTTPException) and exception.status_code == 401:
        return RedirectResponse(
            url=app.url_path_for("login_page"),
            # this is important to change from post to get
            # on invalid login attempt
            status_code=302
        )
    elif isinstance(exception, HTTPException):
        status_code = exception.status_code
        error_message = exception.detail
    elif isinstance(exception, StarlettHTTPException):
        status_code = exception.status_code
        error_message = exception.detail
    elif isinstance(exception, Exception):
        status_code = 500
        error_message = "Internal Server Error"
    elif isinstance(exception, RequestValidationError):
        status_code = 400
        error_message = "Bad Request"
    else:
        status_code = 500
        error_message = "Internal Server Error"

    logger.error(f"Handling error with code {status_code}: {error_message}. "
                 f"Details: {exception}")

    return templates.TemplateResponse(
        request=request,
        name="page-error.jinja",
        context={"status_code": status_code, "error_message": error_message},
        status_code=status_code
    )

# ---------------------------------------------------------------------------- #


@app.get(path="/",
         response_class=RedirectResponse,
         tags=["pages"])
async def home_page(
    session: HttpSessionDep
) -> RedirectResponse:
    """
    Redirect to the caledar or login page.
    """
    if await session.is_authenticated():
        return RedirectResponse(
            url=app.url_path_for("projects_page"),
            status_code=303
        )
    else:
        return RedirectResponse(
            url=app.url_path_for("login_page"),
            status_code=303
        )

# ---------------------------------------------------------------------------- #


@app.get(path="/login",
         response_class=HTMLResponse,
         tags=["pages"])
async def login_page(
    session: HttpSessionDep
) -> Response:
    """
    Display the login page.
    """
    return templates.TemplateResponse(
        request=session.request,
        name="page-login.jinja",
        context={
            "login_url": app.url_path_for("login"),
            "signup_url": app.url_path_for("signup_page"),
            "flash": await session.pop_flash_message()
        },
        headers={"HX-Redirect": app.url_path_for("login_page")}
    )

# ---------------------------------------------------------------------------- #


@app.post("/login",
          response_class=RedirectResponse,
          tags=["actions"])
async def login(
    session: HttpSessionDep,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()]
) -> RedirectResponse:
    """
    Attempt a user login.
    """
    await session.login(
        email=email,
        password=password
    )

    response = RedirectResponse(
        url=app.url_path_for("projects_page"),
        status_code=303
    )

    return response

# ---------------------------------------------------------------------------- #


@app.get("/logout",
         response_class=RedirectResponse,
         tags=["actions"])
async def logout(
    session: HttpSessionDep
) -> RedirectResponse:
    """
    Logout the user.
    """
    await session.logout()

    response = RedirectResponse(
        url=app.url_path_for("login_page"),
        status_code=303
    )

    return response

# ---------------------------------------------------------------------------- #


@app.get(path="/signup",
         response_class=HTMLResponse,
         tags=["pages"])
async def signup_page(
    session: HttpSessionDep
) -> Response:
    """
    Return the signup page.
    """

    return templates.TemplateResponse(
        request=session.request,
        name="page-signup.jinja",
        context={},
        headers={"HX-Redirect": app.url_path_for("signup_page")}
    )

# ---------------------------------------------------------------------------- #


@app.post("/signup",
          response_class=RedirectResponse,
          tags=["actions"])
async def signup(
    session: HttpSessionDep,
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()]
) -> RedirectResponse:
    """
    Attempt a user sign up.
    """
    await session.signup(
        username=username,
        email=email,
        password=password
    )

    response = RedirectResponse(
        url=app.url_path_for("login_page"),
        status_code=303
    )

    return response

# ---------------------------------------------------------------------------- #


@app.get("/projects")
async def projects_page(
    session: AuthHttpSessionDep
) -> Response:
    """
    Display the projects page.
    """
    return templates.TemplateResponse(
        request=session.request,
        name="page-projects.jinja",
        context={
            "logout_url": app.url_path_for("logout"),
        }
    )

# ---------------------------------------------------------------------------- #
