
# ---------------------------------------------------------------------------- #

import logging
import sqlmodel
import pydantic
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

    async def ocr_exists(
        self,
        etag: str
    ) -> bool:
        """
        Check if an OCR for a specific E-Tag exists.
        """
        query = sqlmodel.select(sqlmodel.func.count()).where(
            OcrResult.etag == etag)
        ocr = self.session.exec(query).first()
        return (ocr is not None and ocr > 0)

    async def get_labels(
        self,
        project: Project
    ) -> Sequence[Label]:
        """
        Get all possible labels for a project.
        """
        query = sqlmodel.select(Label).where(Label.project_id == project.id)
        return self.session.exec(query).all()

    async def get_user_labels(
        self,
        task: Task
    ) -> Sequence[UserLabel]:
        """
        Get all userlabels for a task.
        """
        query = sqlmodel.select(UserLabel).where(UserLabel.task_id == task.id)
        return self.session.exec(query).all()

    async def swap_user_labels(
        self,
        task: Task,
        user_labels: List[UserLabel]
    ) -> None:
        """
        Get all userlabels for a task.
        """
        query = sqlmodel.select(UserLabel).where(UserLabel.task_id == task.id)
        existing_labels = self.session.exec(query).all()
        for user_label in existing_labels:
            self.session.delete(user_label)

        for user_label in user_labels:
            if user_label.task_id != task.id:
                raise Exception("UserLabel does not match task.")
            self.session.add(user_label)

        self.session.commit()

    async def scan_project(
        self,
        project_id: int
    ) -> None:
        """
        Scan a project's source and update the task list accordingly.
        """
        project = await self.get_project(project_id=project_id)

        if not project:
            raise Exception("Project not found.")

        if project.scan_status != ScanStatus.pending:
            raise Exception("Project is not ready for scanning.")

        self.logger.debug(f"Scan of project {project.name} started.")

        try:
            project.scan_status = ScanStatus.scanning
            self.session.add(project)
            self.session.commit()

            await self._update_tasks(project=project)
        except Exception as exception:
            logging.exception(exception)
            logging.error(f"Scan for {project.name} failed.")
            project.scan_status = ScanStatus.error
            self.session.add(project)
            self.session.commit()

    async def is_scannable(
        self,
        project: Project,
    ) -> bool:
        """
        Determines whether a project is ready to be scanned.
        """
        if project.last_scan:
            since_last_scan = (datetime.datetime.now() -
                               project.last_scan).total_seconds()
        else:
            since_last_scan = 0

        self.logger.debug(f"Time since last scan: {since_last_scan}s.")

        if project.scan_status == ScanStatus.pending and \
                not since_last_scan > 15:
            return False

        if project.scan_status == ScanStatus.scanning and \
                not since_last_scan > 15:
            return False

        return True

    async def _update_tasks(self, project: Project) -> None:
        """
        Update tasks in the database with current file information.
        """
        self.logger.debug(f"Updating tasks for project {project.name}.")
        tasks = await self.get_tasks(project=project)
        files = await self._get_project_files(project=project)

        for task in tasks:
            if task.uri not in [file.uri for file in files]:
                self.logger.debug(f"Task file not found: {task.name}.")
                task.file_status = FileStatus.missing
            else:
                self.logger.debug(f"Task file found: {task.name}.")
                task.file_status = FileStatus.found

            self.session.add(task)

        for file in files:
            if file.uri not in [task.uri for task in tasks]:
                self.logger.debug(f"New task found: {file.name}.")
                task = Task(
                    project=project,
                    ocr=None,
                    name=file.name,
                    created=datetime.datetime.now(),
                    modified=None,
                    uri=file.uri,
                    task_status=TaskStatus.open,
                    file_status=FileStatus.found,
                    ocr_status=OcrStatus.initialized
                )

                self.session.add(task)

        self.session.commit()

        self.logger.debug(f"Tasks updated for {project.name}.")

        await self.run_ocr(project=project)

        project.scan_status = ScanStatus.ready
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
        project: Project,
        provider: str = "tesseract",
        force: bool = False
    ) -> None:
        """
        Run OCR for a project.
        """
        self.logger.debug(f"Running OCR for project {project.name}.")
        tasks = await self.get_tasks(project=project)

        for task in tasks:
            try:
                if task.file_status == FileStatus.missing:
                    continue

                task.ocr_status = OcrStatus.scanning
                self.session.add(task)
                self.session.commit()

                await self._run_task_ocr(task=task)

            except Exception as exception:
                logging.exception(exception)
                logging.error(f"OCR for {task.name} failed.")
                task.ocr_status = OcrStatus.error
                self.session.add(task)
                self.session.commit()

        self.logger.debug(f"OCR finished for {project.name}.")

    async def _run_task_ocr(
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

        ocr_provider = OcrProviderFactory.get_provider(
            provider=provider
        )

        force = True  # todo

        if task.ocr_id and not force:
            self.logger.debug("OCR for this content already exists.")
            return

        etag = file_provider.get_checksum(uri=task.uri)

        # todo: if another task has the same etag, just use that OCR result

        images = file_provider.file_to_image(uri=task.uri)

        ocr = ocr_provider.run_ocr(images=images)

        ocr_result = OcrResult(
            etag=etag,
            provider=provider,
            created=datetime.datetime.now(),
            ocr=ocr.model_dump()
        )

        self.session.add(ocr_result)
        self.session.commit()
        self.session.refresh(ocr_result)

        task.ocr_id = ocr_result.id
        task.ocr_status = OcrStatus.ready

        self.session.add(task)

        self.session.commit()

        self.logger.debug(f"OCR for task with id={task.id} successful.")


# ---------------------------------------------------------------------------- #
