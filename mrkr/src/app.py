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
        raise Exception("Project not found.")

    if await manager.is_scannable(project=project):
        for source in project.sources:
            source.status = SourceStatus.pending
            source.last_scan = datetime.datetime.now()
            session.database.add(source)
        session.database.commit()

        worker.put("scan-project", id=project.id)
        logger.debug("Project scan initialized.")
    else:
        logger.debug("Project is not ready to be scanned.")

    return await tasks_page(session=session, id=project.id)

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

        await manager.scan_project(project=project)

        worker.put("run-project-ocr", id=project.id)

# ---------------------------------------------------------------------------- #


@worker.workermethod("run-project-ocr")
async def scan_project_worker(
    id: int
) -> None:
    """
    Run OCR for a project's tasks anf files.
    """
    with database.session() as session:
        manager = ProjectManager(session=session)

        project = await manager.get_project(id=id)

        await manager.run_project_ocr(
            project=project,
            provider=OcrProvider.tesseract,  # todo
            force_ocr=False
        )

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

    project = await manager.get_project(id=id)

    if not project:
        raise Exception("Project not found.")

    return templates.TemplateResponse(
        request=session.request,
        name="page-tasks.jinja",
        context={
            "config": config.htmx_config,
            "project": project,
            "ready": await manager.has_status(project=project,
                                              status=SourceStatus.ready),
            "scannable": await manager.is_scannable(project=project)
        }
    )

# ---------------------------------------------------------------------------- #


@app.get("/label")
async def label_page(
    session: AuthHttpSessionDep,
    id: int,
    file_id: Optional[int] = None,
    page_id: Optional[int] = None
) -> Response:
    """
    Display the labeling page.
    """
    manager = ProjectManager(session=session.database)

    task = await manager.get_task(id=id)

    if not task:
        raise Exception("Task not found.")

    if file_id:
        file: File | None = next(
            (file for file in task.files if file.id == file_id), None)
    else:
        file = task.files[0]

    if not file or file.status == FileStatus.missing:
        raise Exception("File not found.")

    ocr = await manager.get_ocr(file=file)

    def label_associated_with(block_id: int) -> Label | None:
        for label in file.labels:
            for association in label.associations:
                if association.block_id == block_id:
                    return label
        return None

    return templates.TemplateResponse(
        request=session.request,
        name="page-label.jinja",
        context={
            "config": config.htmx_config,
            "task": task,
            "file": file,
            "ocr": ocr,
            "label_associated_with": label_associated_with
        }
    )


# ---------------------------------------------------------------------------- #


@app.get("/label-image")
async def label_image(
    session: AuthHttpSessionDep,
    id: int
) -> Response:
    manager = ProjectManager(session=session.database)

    file = await manager.get_file(id=id)

    if not file or file.status == FileStatus.missing:
        raise Exception("File not found.")

    # todo: allow for pdfs or multiple files

    with FileProviderFactory.get_provider("local").read_file(file.uri) as file:
        content = file.read()

    return Response(content=content, media_type="image/jpeg")

# ---------------------------------------------------------------------------- #


@app.post("/save-labels")
async def save_labels(
    session: AuthHttpSessionDep,
    file_id: int,
    label_definition_id: Annotated[List[int], Form()],
    block_ids: Annotated[List[str], Form()],
    user_content: Annotated[List[str], Form()]
) -> Response:

    manager = ProjectManager(session=session.database)

    if len(label_definition_id) != len(block_ids) or \
            len(block_ids) != len(user_content):
        raise HTTPException(status_code=400, detail="Bad Request")

    file = await manager.get_file(id=file_id)

    if not file:
        raise Exception("File not found.")

    for label in file.labels:
        for association in label.associations:
            session.database.delete(association)
        session.database.delete(label)

    session.database.commit()

    labels = []
    associations = []
    for item in zip(label_definition_id, block_ids, user_content):
        block_ids_list = item[1].split(",")
        block_ids_values = [int(block_id) for block_id in block_ids_list]

        label = Label(
            file_id=file_id,
            label_definition_id=item[0],
            user_content=item[2]
        )

        labels.append(
            label
        )

        session.database.add(label)

        session.database.commit()
        session.database.refresh(label)

        print("aaa", label)

        for block_id in block_ids_values:
            association = LabelAssociation(
                label_id=label.id,
                block_id=block_id
            )

            associations.append(
                association
            )
            session.database.add(association)

    session.database.commit()

    # await manager.swap_user_labels(task=task, user_labels=labels)

    return HTMLResponse("Save Changes")

# ---------------------------------------------------------------------------- #
