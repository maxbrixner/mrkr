
# ---------------------------------------------------------------------------- #

import logging
import sqlmodel
from typing import List

# ---------------------------------------------------------------------------- #


from .database import *
from .session import SessionManager

# ---------------------------------------------------------------------------- #


class ProjectManager():

    logger: logging.Logger
    session: SessionManager

    def __init__(self, session: SessionManager) -> None:
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
    ) -> List[Project]:
        """
        Get all projects.
        """
        query = sqlmodel.select(Project)
        return self.session.database.exec(query).all()

    async def get_project(
        self,
        project_id: int
    ) -> Project:
        """
        Get a project by its ID.
        """
        query = sqlmodel.select(Project).where(Project.id == project_id)
        return self.session.database.exec(query).first()

    async def get_tasks(
        self,
        project: Project
    ) -> Project:
        """
        Get all tasks for a project.
        """
        query = sqlmodel.select(Task).where(Task.project_id == project.id)
        return self.session.database.exec(query).all()

# ---------------------------------------------------------------------------- #
