# ---------------------------------------------------------------------------- #

from fastapi import FastAPI, Request, Response, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from starlette.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarlettHTTPException
from typing import Annotated, Callable
import datetime

# ---------------------------------------------------------------------------- #

from .logging import Logger
from .config import config
from .database import *
from .session import SessionManager
from .project import ProjectManager
from .worker import WorkerManager
from .file import FileProviderFactory

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

    projects = await manager.get_projects()

    return templates.TemplateResponse(
        request=session.request,
        name="page-projects.jinja",
        context={
            "config": config.htmx_config,
            "projects": projects,
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

    project = await manager.get_project(project_id=id)

    if not project:
        raise Exception("Project not found.")

    if await manager.is_scannable(project=project):
        project.scan_status = ScanStatus.pending
        project.last_scan = datetime.datetime.now()
        session.database.add(project)
        session.database.commit()

        worker.put("scan-project", project_id=project.id)
        logger.debug("Project scan initialized.")
    else:
        logger.debug("Project is not ready to be scanned.")

    return await tasks_page(session=session, id=project.id)

# ---------------------------------------------------------------------------- #


@worker.workermethod("scan-project")
async def scan_project_worker(
    project_id: int
) -> None:
    """
    Scan a project's source and update the task list accordingly.
    """
    with database.session() as session:
        manager = ProjectManager(session=session)

        await manager.scan_project(project_id=project_id)

# ---------------------------------------------------------------------------- #


@app.get("/tasks")
async def tasks_page(
    session: AuthHttpSessionDep,
    id: int
) -> Response:
    """
    Display the projects page.
    """
    manager = ProjectManager(session=session.database)

    project = await manager.get_project(project_id=id)

    if not project:
        raise Exception("Project not found.")

    tasks = await manager.get_tasks(project=project)

    return templates.TemplateResponse(
        request=session.request,
        name="page-tasks.jinja",
        context={
            "config": config.htmx_config,
            "project": project,
            "tasks": tasks,
            "scannable": await manager.is_scannable(project=project)
        }
    )

# ---------------------------------------------------------------------------- #


@app.get("/label")
async def label_page(
    session: AuthHttpSessionDep,
    id: int
) -> Response:
    """
    Display the labeling page.
    """
    manager = ProjectManager(session=session.database)

    task = await manager.get_task(task_id=id)

    if not task:
        raise Exception("Task not found.")

    project = await manager.get_project(project_id=task.project_id)

    if not project:
        raise Exception("Project not found.")

    labels = await manager.get_labels(project=project)

    user_labels = await manager.get_user_labels(task=task)

    def get_user_label(ocr_id: int) -> UserLabel | None:
        for user_label in user_labels:
            if not user_label.label:
                continue
            # todo: this is wrong somehow (linter)
            if ocr_id in user_label.label["ocr_ids"]:
                return user_label
        return None

    def get_label(id: int) -> Label | None:
        for label in labels:
            if label.id == id:
                return label
        return None

    return templates.TemplateResponse(
        request=session.request,
        name="page-label.jinja",
        context={
            "config": config.htmx_config,
            "project": project,
            "task": task,
            "labels": labels,
            "user_labels": user_labels,
            "get_label": get_label,
            "get_user_label": get_user_label
        }
    )


# ---------------------------------------------------------------------------- #


@app.get("/label-image")
async def label_image(
    session: AuthHttpSessionDep,
    id: int
) -> Response:
    manager = ProjectManager(session=session.database)

    task = await manager.get_task(task_id=id)

    if not task:
        raise Exception("Task not found.")

    with FileProviderFactory.get_provider("local").read_file(task.uri) as file:
        content = file.read()

    return Response(content=content, media_type="image/jpeg")

# ---------------------------------------------------------------------------- #


@app.post("/save-labels")
async def save_labels(
    session: AuthHttpSessionDep,
    task_id: Annotated[int, Form()],
    label_id: Annotated[List[int], Form()],
    ocr_ids: Annotated[List[str], Form()],
    user_content: Annotated[List[str], Form()]
) -> Response:

    manager = ProjectManager(session=session.database)

    task = await manager.get_task(task_id=task_id)

    if not task:
        raise Exception("Task not found.")

    if len(label_id) != len(ocr_ids) or len(ocr_ids) != len(user_content):
        raise HTTPException(status_code=400, detail="Bad Request")

    labels = []
    for item in zip(label_id, ocr_ids, user_content):
        ocr_ids_list = item[1].split(",")
        ocr_ids_values = [int(ocr_id) for ocr_id in ocr_ids_list]
        labels.append(
            UserLabel(
                task_id=task_id,
                label=LabelObject(
                    label_id=item[0],
                    ocr_ids=ocr_ids_values,
                    user_content=item[2]
                ).model_dump()
            )
        )

    await manager.swap_user_labels(task=task, user_labels=labels)

    return HTMLResponse("Save Changes")

# ---------------------------------------------------------------------------- #
