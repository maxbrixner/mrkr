
   async def scan_source(
        self,
        source: Source
    ) -> None:
        """
        Scan a source by refreshing all file associations. Does commit.
        """
        self.logger.debug(f"Scanning source {source.id}.")
        await self.update_source_status(
            source=source,
            status=SourceStatus.scanning
        )

        try:
            connector = FileProviderFactory.get_provider(
                provider=source.provider)
            origin = connector.list_files(uri=source.uri)

            for file in source.files:
                self.session.delete(file)

            for file in origin:
                new_file = File(
                    source=source,
                    name=file.name,
                    uri=file.uri,
                    etag=file.etag
                )
                self.session.add(new_file)
                self.logger.debug(f"File '{file.name}' added.")

            await self.update_source_status(
                source=source,
                status=SourceStatus.ready
            )

            self.logger.debug(f"Scan of source {source.id} successful.")
        except Exception as exception:
            self.logger.exception(exception)
            self.logger.debug(f"Scan of source {source.id} failed.")

            await self.update_source_status(
                source=source,
                status=SourceStatus.error
            )

    async def auto_generate_tasks(self, project: Project) -> None:
        """
        Automatically generate tasks for a project.
        """
        tasks = project.tasks

        for source in project.sources:
            for file in source.files:

                matching_task: Task | None = None
                for task in project.tasks:
                    print("a", task.pattern, file.name)
                    if re.fullmatch(task.pattern, file.name):
                        matching_task = task
                        break

                if not matching_task:
                    self.logger.debug(
                        f"No task for file '{file.name}' found. "
                        f"Generating new task.")
                    task = await self._generate_task_from_file(
                        project=project,
                        file=file
                    )
                    self.session.add(task)
                    tasks.append(task)
                else:
                    self.logger.debug(
                        f"Existing task for file '{file.name}' found. "
                        f"Skipping.")

        self.session.commit()

    async def _generate_task_from_file(
        self,
        project: Project,
        file: File
    ) -> Task:
        """
        Generate a task infering a pattern from a filename.
        """
        match = re.fullmatch(r'(.*)(page[0-9]*)(.*)', file.name)
        if match:
            name = match.group(1) + 'page*' + match.group(3)
            pattern = match.group(1) + 'page[0-9]*' + match.group(3)
        else:
            name = file.name
            pattern = file.name

        task = Task(
            project=project,
            name=name,
            created=datetime.datetime.now(),
            modified=None,
            status=TaskStatus.open,
            pattern=pattern
        )

        return task

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
            for file in source.files:
                self.logger.debug(
                    f"OCR for file {file.id} from source {source.id} started.")
                try:
                    await self.run_file_ocr(
                        file=file,
                        provider=provider,
                        force_ocr=force_ocr
                    )
                    self.logger.debug(
                        f"OCR for file {file.id} from source {source.id} "
                        f"successful.")
                except Exception as exception:
                    self.logger.exception(exception)
                    self.logger.debug(
                        f"OCR for file {file.id} from source {source.id} "
                        f"failed.")

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
                f"OCR for file {file.id} already found. Skipping.")
            return

        self.logger.debug(
            f"OCR for file {file.id} not found. Running.")

        file_provider = FileProviderFactory.get_provider(
            provider=file.source.provider)

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

# ---------------------------------------------------------------------------- #
