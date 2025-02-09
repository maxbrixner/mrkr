
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

    async def get_file(
        self,
        id: int
    ) -> File | None:
        """
        Get a file by its ID.
        """
        query = sqlmodel.select(File).where(File.id == id)
        return self.session.exec(query).first()

    async def get_ocr(
        self,
        file: File
    ) -> OcrResult | None:
        """
        Get an OCR result by its ID.
        """
        query = sqlmodel.select(OcrResult).where(
            OcrResult.etag == file.etag)
        return self.session.exec(query).first()

    async def get_labels(
        self,
        file: File
    ) -> List[Label]:
        """
        Get labels for a file.
        """
        query = sqlmodel.select(Label).where(Label.file_id == file.id)
        return self.session.exec(query).all()

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

            if source.status in (
                SourceStatus.pending,
                SourceStatus.scanning
            ) and not seconds_since_last_scan > 5:  # todo
                return False

        return True

    async def has_status(
        self,
        project: Project,
        status: SourceStatus
    ) -> bool:
        """
        Determines whether a project's scan is pending.
        """
        for source in project.sources:
            if source.status != status:
                return False

        return True

    async def scan_project(
        self,
        project: Project
    ) -> None:
        """
        Scan a project by scanning each source. Does commit.
        """
        if not await self.has_status(
            project=project,
            status=SourceStatus.pending
        ):
            self.logger.debug(f"Project {project.name} is not pending.")
            return

        self.logger.debug(f"Scan of project {project.name} started.")

        for source in project.sources:
            self.logger.debug(f"Scan of source '{source.id}' started.")

            source.status = SourceStatus.scanning
            self.session.add(project)
            self.session.commit()

            try:
                await self._scan_source(source=source)

                source.status = SourceStatus.ready
                self.session.add(project)
                self.session.commit()
            except Exception as exception:
                self.logger.exception(exception)
                self.logger.debug(f"Scan of source {source.uri} failed.")

                source.status = SourceStatus.error
                self.session.add(project)
                self.session.commit()

            self.logger.debug(f"Scan of source '{source.id}' finished.")

        self.logger.debug(f"Scan of project {project.name} finished.")

    async def _scan_source(
        self,
        source: Source
    ) -> None:
        """
        Scan a source by scanning each task. Does NOT commit.
        """
        connector = FileProviderFactory.get_provider(provider=source.type)
        files_origin = connector.list_files(uri=source.uri)

        # Scan existing tasks and update
        self.logger.debug(f"Scanning existing tasks of source '{source.id}'.")
        for task in source.tasks:
            await self._scan_task(
                task=task,
                files_origin=files_origin
            )

        # Look for new tasks and files
        self.logger.debug(f"Scanning new files for source '{source.id}'.")
        new_files = await self._find_new_files(
            source=source,
            files_origin=files_origin
        )

        # Add new files and tasks
        for new_file in new_files:
            await self._add_file(
                source=source,
                new_file=new_file
            )

    async def _scan_task(
        self,
        task: Task,
        files_origin: List[FileObject]
    ) -> None:
        """
        Scan a task by comparing the origin files with the task's files and
        patterns. Does NOT commit.
        """
        origin_file: FileObject | None = None
        for file in task.files:
            origin_file = next((origin_file for origin_file in files_origin
                                if origin_file.uri == file.uri), None)
            if not origin_file:
                self.logger.debug(
                    f"File '{file.name}' not found. "
                    f"Marking as missing.")
                file.status = FileStatus.missing
                self.session.add(file)
                continue

            self.logger.debug(f"Existing file '{file.name}' found.")

            if not file.status == FileStatus.found:
                self.logger.debug(
                    f"Formerly missing file '{file.name}' found. "
                    f"Marking as found.")
                file.status = FileStatus.found
                self.session.add(file)

            if file.etag != origin_file.etag:
                self.logger.debug(
                    f"Etag of file '{file.name}' expired. Updating")
                file.etag = origin_file.etag
                self.session.add(file)

    async def _find_new_files(
        self,
        source: Source,
        files_origin: List[FileObject]
    ) -> List[FileObject]:
        """
        Find new files in a source.
        """
        new_files = []
        file: File | None = None
        for file_origin in files_origin:
            for task in source.tasks:
                file = next((file for file in task.files
                             if file.uri == file_origin.uri), None)
                if file:
                    break

            if not file:
                new_files.append(file_origin)

        return new_files

    async def _add_file(
        self,
        source: Source,
        new_file: FileObject
    ) -> File:
        """
        Add a file to a source. Does NOT commit.
        """
        task: Task | None = None
        for existing_task in source.tasks:
            # todo: test this
            if re.fullmatch(existing_task.pattern, new_file.name):
                task = existing_task

        if not task:
            self.logger.debug(
                f"No task found for file '{new_file.name}'. Creating new task.")
            task = Task(
                source=source,
                name=new_file.name,  # todo
                created=datetime.datetime.now(),
                modified=None,
                status=TaskStatus.open,
                pattern=new_file.name  # todo
            )
            self.session.add(task)
        else:
            self.logger.debug(
                f"Existing task found for file '{new_file.name}'. Adding file.")

        file = File(
            task=task,
            name=new_file.name,
            uri=new_file.uri,
            etag=new_file.etag,
            status=FileStatus.found
        )

        self.session.add(file)

    async def run_project_ocr(
        self,
        project: Project,
        provider: OcrProvider | None,
        force_ocr: bool = False
    ) -> None:
        """
        Run OCR for a project.
        """
        for source in project.sources:
            for task in source.tasks:
                for file in task.files:
                    self.logger.debug(f"OCR for file '{file.name}' started.")
                    try:
                        await self.run_file_ocr(
                            file=file,
                            provider=provider,
                            force_ocr=force_ocr
                        )
                    except Exception as exception:
                        self.logger.exception(exception)
                        self.logger.debug(
                            f"OCR for file '{file.name}' failed.")
                    self.logger.debug(f"OCR for file '{file.name}' finished.")

    async def run_file_ocr(
        self,
        file: File,
        provider: OcrProvider | None,
        force_ocr: bool = False
    ) -> None:
        """
        Run OCR for a file. Does commit.
        """
        query = sqlmodel.select(OcrResult).where(
            OcrResult.etag == file.etag and OcrResult.provider == provider)
        ocr_result = self.session.exec(query).first()

        if ocr_result and not force_ocr:
            self.logger.debug(
                f"OCR for file '{file.name}' already found. Skipping.")
            return

        self.logger.debug(
            f"OCR for file '{file.name}' not found. Running.")

        file_provider = FileProviderFactory.get_provider(
            provider=file.task.source.type)

        ocr_provider = OcrProviderFactory.get_provider(
            provider=provider
        )

        images = file_provider.file_to_image(uri=file.uri)

        ocr_result = OcrResult(
            etag=file.etag,
            provider=provider,
            created=datetime.datetime.now()
        )

        self.session.add(ocr_result)

        for index, image in enumerate(images):
            page = OcrPage(
                ocr_result=ocr_result,
                page=index,
                width=image.width,
                height=image.height
            )

            self.session.add(page)

            ocr = ocr_provider.run_ocr(image=image)

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

        self.session.commit()

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
