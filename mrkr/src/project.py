
# ---------------------------------------------------------------------------- #

import logging
import sqlmodel
from typing import List, Sequence

# ---------------------------------------------------------------------------- #

from .database import *
from .session import SessionManager

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

    async def is_scannable(self, project: Project) -> bool:
        """
        Check if a project is scannable.
        """
        if project.scan_status == ScanStatus.pending or \
                project.scan_status == ScanStatus.scanning:
            if project.last_scan is None:
                raise Exception("Project is in an invalid state.")
            if datetime.datetime.now() < \
                    project.last_scan + datetime.timedelta(minutes=5):
                return False

        return True

    async def scan_project(
        self,
        project_id: int
    ) -> None:
        """
        Get a task by its ID.
        """
        # todo: make better
        project = await self.get_project(project_id=project_id)

        if await self.is_scannable(project=project):
            raise Exception("Project is not ready to be scanned.")

        tasks = await self.get_tasks(project=project)

        from .connectors import LocalConnector  # todo

        connector = LocalConnector()

        files = connector.list_files(uri=project.source_uri)

        self.logger.debug(f"{len(files)} files found.")

        for file in files:
            try:
                task = next(filter(lambda x: x.uri == file.uri, tasks))
            except StopIteration:
                task = None

            if not task:
                self.logger.debug(f"New task found: {file.name}")
                task = Task(
                    project=project,
                    name=file.name,
                    created=datetime.datetime.now(),
                    modified=None,
                    task_status=TaskStatus.open,
                    uri=file.uri,
                    etag=file.etag
                )

                self.session.add(task)

            else:
                self.logger.debug(f"Existing task found: {file.name}")

                if task.etag == file.etag:
                    self.logger.debug(f"File content unchanged.")
                    continue

                self.logger.debug(f"File content changed. Updating tag.")

                task.etag = file.etag
                self.session.add(task)

        project.scan_status = ScanStatus.scanned
        self.session.add(project)

        self.session.commit()

# ---------------------------------------------------------------------------- #
