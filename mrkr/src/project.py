
# ---------------------------------------------------------------------------- #

import logging
import sqlmodel
import re
from typing import List, Sequence

# ---------------------------------------------------------------------------- #

from .models import *
from .database import DatabaseSession
from .file import FileProviderFactory, FileObject
from .ocr import OcrProviderFactory

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

    async def list_projects(
        self
    ) -> Sequence[Project]:
        """
        List all projects.
        """
        query = sqlmodel.select(Project).order_by(Project.name)
        return self.session.exec(query).all()

    async def get_project(
        self,
        id: int
    ) -> Project | None:
        """
        Get a project by its ID.
        """
        query = sqlmodel.select(Project).where(Project.id == id)
        return self.session.exec(query).first()

    async def get_task(
        self,
        id: int
    ) -> Task | None:
        """
        Get a task by its ID.
        """
        query = sqlmodel.select(Task).where(Task.id == id)
        return self.session.exec(query).first()

    async def project_is_scannable(
        self,
        project: Project,
    ) -> bool:
        """
        Determines whether a project is ready to be scanned.
        """
        if project.last_scan:
            seconds_since_last_scan = (datetime.datetime.now() -
                                       project.last_scan).total_seconds()
        else:
            seconds_since_last_scan = 0

            if project.status in (
                ProjectStatus.scan_pending,
                ProjectStatus.scan_running
            ) and not seconds_since_last_scan > 5:  # todo
                return False

        return True

    async def task_is_scannable(
        self,
        task: Task,
    ) -> bool:
        """
        Determines whether a task is ready to be scanned (OCR).
        """
        if task.last_ocr:
            seconds_since_last_scan = (datetime.datetime.now() -
                                       task.last_ocr).total_seconds()
        else:
            seconds_since_last_scan = 0

            if task.status in (
                TaskStatus.ocr_pending,
                TaskStatus.ocr_running
            ) and not seconds_since_last_scan > 5:  # todo
                return False

        return True

    async def scan_project(
        self,
        project: Project
    ) -> None:
        """
        Scan a project's tasks.
        """
        try:
            if project.status != ProjectStatus.scan_pending:
                self.logger.debug(
                    f"Project {project.id} is not pending. Aborting.")
                return

            project.status = ProjectStatus.scan_running
            self.session.add(project)
            self.session.commit()

            self.logger.debug(f"Scan of project {project.id} started.")

            connector = FileProviderFactory.get_provider(
                provider=project.provider)
            origin = connector.list_files(uri=project.uri)

            await self._update_existing_tasks(
                project=project, origin=origin
            )
            await self._add_new_tasks(
                project=project, origin=origin
            )

            project.status = ProjectStatus.ready
            self.session.add(project)
            self.session.commit()

            self.logger.debug(f"Scan of project {project.id} finished.")
        except Exception as exception:
            self.logger.exception(exception)
            self.logger.debug(f"Scan of project {project.id} failed.")

            project.status = ProjectStatus.scan_failed
            self.session.add(project)
            self.session.commit()

    async def _update_existing_tasks(
        self,
        project: Project,
        origin: List[FileObject]
    ) -> None:
        """
        Update existing tasks, mark abandoned tasks. Does NOT commit.
        """
        for task in project.tasks:
            file: FileObject | None = next(
                (file for file in origin if file.uri == task.uri), None)

            if not file:
                task.abandoned = True
                continue
            else:
                task.abandoned = False

            if task.name != file.name:
                task.name = file.name

            self.logger.debug(
                f"Task {task.id} for file '{file.name}' updated.")

            self.session.add(task)

    async def _add_new_tasks(
        self,
        project: Project,
        origin: List[FileObject]
    ) -> None:
        """
        Identifiy files in origin and create new tasks. Does NOT commit.
        """
        for file in origin:
            task: Task | None = next(
                (task for task in project.tasks if task.uri == file.uri), None)

            if task:
                continue

            task = Task(
                project=project,
                name=file.name,
                created=datetime.datetime.now(),
                status=TaskStatus.ready,
                abandoned=False,
                uri=file.uri
            )

            self.logger.debug(f"Task for file '{file.name}' added.")

            self.session.add(task)

    async def run_ocr(
        self,
        task: Task,
        provider: OcrProvider = OcrProvider.tesseract,
        force_ocr: bool = False
    ) -> None:
        """
        Run OCR for a task.
        """
        try:
            self.logger.debug(f"OCR for task {task.id} started.")

            file_provider = FileProviderFactory.get_provider(
                provider=task.project.provider)

            etag = file_provider.get_checksum(uri=task.uri)

            if task.ocr and etag == task.ocr.etag and not force_ocr:
                self.logger.debug(
                    f"OCR for task {task.id} already found. Skipping.")
                task.status = TaskStatus.ready
                self.session.add(task)
                self.session.commit()
                return

            ocr_provider = OcrProviderFactory.get_provider(
                provider=provider
            )

            images = file_provider.file_to_image(uri=task.uri)

            ocr = Ocr(
                task=task,
                etag=etag,
                provider=provider,
                created=datetime.datetime.now()
            )
            self.session.add(ocr)

            for index, image in enumerate(images):
                page = Page(
                    ocr=ocr,
                    page=index,
                    width=image.width,
                    height=image.height
                )

                self.session.add(page)

                blocks = ocr_provider.run_ocr(image=image)

                for block in blocks:
                    block = Block(
                        page=page,
                        type=block.type,
                        content=block.content,
                        confidence=block.confidence,
                        left=block.left,
                        top=block.top,
                        width=block.width,
                        height=block.height
                    )

                    self.session.add(block)

            task.status = TaskStatus.ready
            self.session.add(task)
            self.session.commit()

            self.logger.debug(f"OCR for task {task.id} successful.")

        except Exception as exception:
            self.logger.exception(exception)
            self.logger.debug(f"OCR for task {task.id} failed.")

            task.status = TaskStatus.error
            self.session.add(task)
            self.session.commit()

# ---------------------------------------------------------------------------- #
