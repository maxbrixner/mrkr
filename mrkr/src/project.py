
# ---------------------------------------------------------------------------- #

import logging
import sqlmodel
from typing import List, Sequence

# ---------------------------------------------------------------------------- #

from .database import *
from .session import SessionManager
from .file import FileProviderFactory, FileObject
from .ocr import OcrProviderFactory, OcrObject

# ---------------------------------------------------------------------------- #


class ProjectManager():
    """
    The ProjectManager class provides queries and operations for projects.
    """
    logger: logging.Logger
    session: DatabaseSession

    def __init__(self, session: DatabaseSession) -> None:
        """
        Initialize the SessionManager class.
        """
        self.logger = logging.getLogger('mrkr.project')

        self.session = session

    async def create_project(
        self,
        project_name: str,
        project_description: str
    ) -> None:
        """
        Create a new project.
        """
        project = Project(
            name=project_name,
            description=project_description,
            creator=self.session.user
        )

        self.session.add(project)
        self.session.commit()

        self.logger.info(f"Project with name = '{project_name}' created.")

    async def get_projects(
        self
    ) -> Sequence[Project]:
        """
        Get all projects.
        """
        query = sqlmodel.select(Project)
        return self.session.exec(query).all()

    async def get_project(
        self,
        project_id: int
    ) -> Project | None:
        """
        Get a project by its ID.
        """
        query = sqlmodel.select(Project).where(Project.id == project_id)
        return self.session.exec(query).first()

    async def get_tasks(
        self,
        project: Project
    ) -> Sequence[Task]:
        """
        Get all tasks for a project.
        """
        query = sqlmodel.select(Task).where(Task.project_id == project.id)
        return self.session.exec(query).all()

    async def get_task(
        self,
        task_id: int
    ) -> Task | None:
        """
        Get a task by its ID.
        """
        query = sqlmodel.select(Task).where(Task.id == task_id)
        return self.session.exec(query).first()

    async def get_ocr(
        self,
        etag: str
    ) -> OcrResult | None:
        """
        Get an OCR result by its E-Tag.
        """
        query = sqlmodel.select(OcrResult).where(OcrResult.etag == etag)
        return self.session.exec(query).first()

    async def ocr_exists(
        self,
        etag: str
    ) -> OcrResult | None:
        """
        Check if an OCR for a specific E-Tag exists.
        """
        query = sqlmodel.select(sqlmodel.func.count()).where(
            OcrResult.etag == etag)
        return self.session.exec(query).first() > 0

    async def scan_project(
        self,
        project: Project
    ) -> None:
        """
        Scan a project's source and update the task list accordingly.
        """
        if not await self._is_scannable(project=project):
            raise Exception(
                f"Project {project.name} is already being scanned.")

        self.logger.debug(f"Scan of project {project.name} started.")

        project.status = ProjectStatus.scanning
        project.last_scan = datetime.datetime.now()
        self.session.add(project)
        self.session.commit()

        try:
            await self._update_tasks(project=project)
        except Exception as exception:
            project.status = ProjectStatus.error
            self.session.add(project)
            self.session.commit()
            raise Exception(exception)

    async def _is_scannable(self, project: Project) -> None:
        if project.status != ProjectStatus.scanning:
            return True

        # todo
        if (datetime.datetime.now() - project.last_scan).total_seconds() < 60:
            return False

        return True

    async def _update_tasks(self, project: Project) -> None:
        """
        Update tasks in the database with current file information.
        """
        tasks = await self.get_tasks(project=project)
        files = await self._get_project_files(project=project)

        for file in files:
            corresponding_tasks = list(
                filter(lambda x: x.uri == file.uri, tasks)
            )

            if len(corresponding_tasks) > 1:
                raise Exception("Inconsistent project database state.")

            if len(corresponding_tasks) == 0:
                self.logger.debug(f"New task found: {file.name}")

                task = Task(
                    project=project,
                    ocr=None,
                    name=file.name,
                    created=datetime.datetime.now(),
                    modified=None,
                    status=TaskStatus.open,
                    etag=file.etag,
                    uri=file.uri
                )

                self.session.add(task)

            else:
                task = corresponding_tasks[0]
                if task.etag == file.etag:
                    self.logger.debug(f"Existing task with unchanged content "
                                      f"found: {file.name}")
                else:
                    self.logger.debug(f"Existing task with updated content "
                                      f"found: {file.name}")
                    task.etag = file.etag
                    self.session.add(task)

        # todo: delete tasks if file not found?

        project.status = ProjectStatus.scanned
        self.session.add(project)

        self.session.commit()

    async def _get_project_files(
        self,
        project: Project
    ) -> Sequence[FileObject]:
        connector = FileProviderFactory.get_provider("local")  # todo

        files = connector.list_files(uri=project.source_uri)

        self.logger.debug(f"Found {len(files)} files in project source.")

        return files

    async def run_ocr(
        self,
        task: Task,
        provider: str = "tesseract",
        force: bool = False
    ) -> None:
        """
        Run OCR for a task.
        """
        self.logger.debug(f"OCR for task with id={task.id} started.")

        file_provider = FileProviderFactory.get_provider(
            provider="local")

        force = True  # todo

        if task.ocr_id and not force:
            self.logger.debug("OCR for this content already exists.")
            return

        etag = file_provider.get_checksum(uri=task.uri)

        if etag != task.etag:
            self.logger.warning("File has changed since last scan.")
            task.etag = etag

        # todo: if another task has the same etag, just use that OCR result

        ocr_provider = OcrProviderFactory.get_provider(
            provider=provider
        )

        images = file_provider.file_to_image(uri=task.uri)

        ocr_result = ocr_provider.run_ocr(images=images)

        ocr_result = OcrResult(
            ocr=ocr_result.model_dump(),
            provider=provider,
            created=datetime.datetime.now()
        )

        self.session.add(ocr_result)
        self.session.commit()
        self.session.refresh(ocr_result)

        task.ocr_id = ocr_result.id

        self.session.add(task)

        self.session.commit()

# ---------------------------------------------------------------------------- #
