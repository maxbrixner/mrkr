# ---------------------------------------------------------------------------- #

from fastapi import FastAPI, Request, Response, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from starlette.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarlettHTTPException
from typing import Annotated, Callable, List
import datetime

# ---------------------------------------------------------------------------- #

from .logging import Logger
from .config import config
from .database import Database
from .session import SessionManager
from .project import ProjectManager
from .worker import WorkerManager
from .file import FileProviderFactory
from .models import *

# ---------------------------------------------------------------------------- #

app = FastAPI()

app.mount("/static", StaticFiles(directory="mrkr/static"), name="static")
app.add_middleware(GZipMiddleware, minimum_size=1000)

logger = Logger(name="mrkr.app")
templates = Jinja2Templates(directory="mrkr/templates", autoescape=True)
database = Database(alias="POSTGRES")

worker = WorkerManager()

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

    if "/static" in request.url.path:
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

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

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
            url=app.url_path_for("login_page") + "?unauthorized_redirect=true",
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
        context={
            "projects_url": app.url_path_for("projects_page"),
            "status_code": status_code,
            "error_message": error_message
        },
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
    session: HttpSessionDep,
    unauthorized_redirect: bool = False
) -> Response:
    """
    Display the login page.
    """
    if unauthorized_redirect:
        headers = {"HX-Redirect": app.url_path_for("login_page")}
    else:
        headers = {}

    return templates.TemplateResponse(
        request=session.request,
        name="page-login.jinja",
        context={
            "config": config.htmx_config,
            "flash": await session.pop_flash_message()
        },
        # this makes sure that the login page is always displayed as a
        # full page
        headers=headers
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


@app.post("/logout",
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
        context={
            "config": config.htmx_config,
        }
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
    manager = ProjectManager(session=session.database)

    projects = await manager.list_projects()

    return templates.TemplateResponse(
        request=session.request,
        name="page-projects.jinja",
        context={
            "config": config.htmx_config,
            "projects": projects,
        }
    )


# ---------------------------------------------------------------------------- #


@app.get("/project")
async def project_page(
    session: AuthHttpSessionDep,
    id: int
) -> Response:
    """
    Display the project page.
    """
    manager = ProjectManager(session=session.database)

    project = await manager.get_project(id=id)

    if not project:
        raise HTTPException(status_code=400, detail="Bad Request")

    return templates.TemplateResponse(
        request=session.request,
        name="page-project.jinja",
        context={
            "config": config.htmx_config,
            "project": project,
            "scannable": await manager.project_is_scannable(
                project=project)
        }
    )

# ---------------------------------------------------------------------------- #


@app.post("/scan-project")
async def scan_project(
    session: AuthHttpSessionDep,
    id: int
) -> Response:
    """
    Scan a project's source and update the task list accordingly.
    """
    manager = ProjectManager(session=session.database)

    project = await manager.get_project(id=id)

    if not project:
        raise HTTPException(status_code=400, detail="Bad Request")

    if await manager.project_is_scannable(project=project):
        project.status = ProjectStatus.scan_pending
        project.last_scan = datetime.datetime.now()
        session.database.add(project)
        session.database.commit()

        worker.put("scan-project", id=project.id)
        logger.debug("Project scan queued.")
    else:
        logger.debug("Project is not ready to be scanned.")

    return await project_page(session=session, id=project.id)

# ---------------------------------------------------------------------------- #


@worker.workermethod("scan-project")
async def scan_project_worker(
    id: int
) -> None:
    """
    Scan a project's source and update the task list accordingly.
    """
    with database.session() as session:
        manager = ProjectManager(session=session)

        project = await manager.get_project(id=id)

        if not project:
            logger.error("Project not found.")
            return

        await manager.scan_project(project=project)

# ---------------------------------------------------------------------------- #


@app.get("/task")
async def task_page(
    session: AuthHttpSessionDep,
    id: int,
    page: int = 0
) -> Response:
    """
    Display the task page.
    """
    manager = ProjectManager(session=session.database)

    task = await manager.get_task(id=id)

    if not task:
        raise HTTPException(status_code=400, detail="Bad Request")

    return templates.TemplateResponse(
        request=session.request,
        name="page-task.jinja",
        context={
            "config": config.htmx_config,
            "task": task,
            "page": page,
            "max_pages": len(task.ocr.pages) if task.ocr else 0,
        }
    )


# ---------------------------------------------------------------------------- #


@app.get("/task/image")
async def task_image(
    session: AuthHttpSessionDep,
    id: int,
    page: int = 0
) -> Response:
    """
    Return a source file's page as an image.
    """
    manager = ProjectManager(session=session.database)

    task = await manager.get_task(id=id)

    if not task:
        raise HTTPException(status_code=400, detail="Bad Request")

    content = FileProviderFactory.get_provider(
        task.project.provider).file_to_jpeg_bytes(uri=task.uri, page=page)

    return Response(content=content, media_type="image/jpeg")

# ---------------------------------------------------------------------------- #


@app.post("/run_ocr")
async def run_ocr(
    session: AuthHttpSessionDep,
    id: int
) -> Response:
    """
    Run OCR for a project's task.
    """
    manager = ProjectManager(session=session.database)

    task = await manager.get_task(id=id)

    if not task:
        raise HTTPException(status_code=400, detail="Bad Request")

    if await manager.task_is_scannable(task=task):
        task.status = TaskStatus.ocr_pending
        task.last_ocr = datetime.datetime.now()
        session.database.add(task)
        session.database.commit()

        worker.put("run-ocr", id=task.id)
        logger.debug("Task OCR queued.")
    else:
        logger.debug("Task is not ready for OCR.")

    return await task_page(session=session, id=task.id)

# ---------------------------------------------------------------------------- #


@worker.workermethod("run-ocr")
async def run_ocr_worker(
    id: int
) -> None:
    """
    Run OCR on a task.
    """
    with database.session() as session:
        manager = ProjectManager(session=session)

        task = await manager.get_task(id=id)

        if not task:
            logger.error("Task not found.")
            return

        await manager.run_ocr(task=task)

# ---------------------------------------------------------------------------- #


@app.post("/save-labels")
async def save_labels(
    session: AuthHttpSessionDep,
    id: int,
    labeltype_id: Annotated[List[int], Form()],
    block_ids: Annotated[List[str], Form()],
    user_content: Annotated[List[str], Form()]
) -> Response:

    manager = ProjectManager(session=session.database)

    if len(labeltype_id) != len(block_ids) or \
            len(block_ids) != len(user_content):
        raise HTTPException(status_code=400, detail="Bad Request")

    task = await manager.get_task(id=id)

    if not task:
        raise HTTPException(status_code=400, detail="Bad Request")

    # todo: put code in project manager

    for label in task.labels:
        for link in label.links:
            session.database.delete(link)
        session.database.delete(label)

    for item in zip(labeltype_id, block_ids, user_content):
        block_ids_list = item[1].split(",")
        block_ids_values = [int(block_id) for block_id in block_ids_list]

        label = Label(
            task=task,
            labeltype_id=item[0],
            user_content=item[2]
        )

        session.database.add(label)
        # session.database.commit()

        for block_id in block_ids_values:
            link = LabelLink(
                label=label,
                block_id=block_id
            )

            session.database.add(link)

    session.database.commit()

    # await manager.swap_user_labels(task=task, user_labels=labels)

    return HTMLResponse("Save Changes")

# ---------------------------------------------------------------------------- #
