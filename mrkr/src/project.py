
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
        Get all projects.
        """
        query = sqlmodel.select(Project).order_by(Project.name)
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

    async def is_scannable(
        self,
        project: Project,
    ) -> bool:
        """
        Determines whether a project is ready to be scanned.
        """
        for source in project.sources:
            if source.last_scan:
                seconds_since_last_scan = (datetime.datetime.now() -
                                           source.last_scan).total_seconds()
            else:
                seconds_since_last_scan = 0

            if source.status in (SourceStatus.pending, SourceStatus.scanning) \
                    and not seconds_since_last_scan > 5:  # todo
                return False

        return True

    async def is_pending(
        self,
        project: Project,
    ) -> bool:
        """
        Determines whether a project's scan is pending.
        """
        for source in project.sources:
            if source.status != SourceStatus.pending:
                return False

        return True

    async def is_ready(
        self,
        project: Project,
    ) -> bool:
        """
        Determines whether a project is ready to be displayed.
        """
        for source in project.sources:
            if source.status != SourceStatus.ready:
                return False

        return True

    async def scan_project(
        self,
        project: Project
    ) -> None:
        """
        Scan a project's sources.
        """
        if not await self.is_pending(project=project):
            self.logger.debug(f"Project {project.name} is not pending.")
            return

        self.logger.debug(f"Scan of project {project.name} started.")

        for source in project.sources:
            source.status = SourceStatus.scanning
            self.session.add(project)
            self.session.commit()

            try:
                self.logger.debug(f"Scan of source '{source.id}' started.")
                await self._scan_source(
                    source=source,
                    ocr_provider=OcrProvider.tesseract
                )
                self.logger.debug(f"Scan of source '{source.id}' successful.")

                source.status = SourceStatus.ready
                self.session.add(project)
                self.session.commit()
            except Exception as exception:
                self.logger.exception(exception)
                self.logger.debug(f"Scan of source {source.uri} failed.")
                source.status = SourceStatus.error
                self.session.add(project)
                self.session.commit()

    async def _scan_source(
        self,
        source: Source,
        ocr_provider: OcrProvider | None = None,
        force_ocr: bool = False
    ) -> None:
        """
        Scan a source for files.
        """
        files = source.files
        for file in files:
            file.status = FileStatus.missing
            self.session.add(file)

        connector = FileProviderFactory.get_provider(provider=source.type)
        connector_files = connector.list_files(uri=source.uri)

        for connector_file in connector_files:
            database_file: File | None = next(
                (file for file in files
                 if file.uri == connector_file.uri),
                None
            )

            if not database_file:
                self.logger.debug(f"New file '{connector_file.uri}' "
                                  f"found. Adding.")
                file = await self._add_file(source=source, file=connector_file)
            else:
                self.logger.debug(f"Existing file '{connector_file.uri}' "
                                  f"found. Updating.")
                database_file.status = FileStatus.found
                self.session.add(database_file)
                file = database_file

            try:
                await self._run_ocr(
                    file=file,
                    provider=ocr_provider,
                    force_ocr=force_ocr
                )
            except Exception as exception:
                self.logger.exception(exception)
                self.logger.debug(f"OCR for file {file.name} failed.")

        self.session.commit()

    async def _add_file(
        self,
        source: Source,
        file: FileObject
    ) -> File:
        """
        Add a file to a source.
        """
        new_file = File(
            source=source,
            name=file.name,
            uri=file.uri,
            etag=file.etag,
            status=FileStatus.found
        )

        task: Task | None = None
        for task in source.project.tasks:
            # todo: test this
            if re.fullmatch(task.pattern, file.name):
                association = TaskFileAssociation(
                    task=task,
                    file=file
                )

        if not task:
            task = Task(
                project=source.project,
                name=file.name,
                created=datetime.datetime.now(),
                modified=None,
                status=TaskStatus.open,
                pattern=file.name  # todo
            )

        self.session.add(task)
        self.session.add(new_file)

        association = TaskFileAssociation(
            task=task,
            file=new_file
        )

        self.session.add(association)

        return new_file

    async def _run_ocr(
        self,
        file: File,
        provider: OcrProvider | None,
        force_ocr: bool = False
    ) -> None:
        """
        Run OCR for a file.
        """
        if not provider:
            return

        file_provider = FileProviderFactory.get_provider(
            provider=file.source.type)

        ocr_provider = OcrProviderFactory.get_provider(
            provider=provider
        )

        query = sqlmodel.select(OcrResult).where(
            OcrResult.etag == file.etag and OcrResult.provider == provider)
        ocr_result = self.session.exec(query).first()

        if ocr_result and not force_ocr:
            self.logger.debug(
                f"OCR for file '{file.name}' already found. Skipping.")
            return

        ocr_result = OcrResult(
            etag=file.etag,
            provider=provider,
            created=datetime.datetime.now()
        )

        images = file_provider.file_to_image(uri=file.uri)

        for index, image in enumerate(images):
            page = OcrPage(
                ocr_result=ocr_result,
                page=index,
                width=image.width,
                height=image.height
            )

            ocr = ocr_provider.run_ocr(image=image)

            self.session.add(page)

            for block in ocr:
                block = OcrBlock(
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

        self.session.add(ocr_result)

# ---------------------------------------------------------------------------- #
