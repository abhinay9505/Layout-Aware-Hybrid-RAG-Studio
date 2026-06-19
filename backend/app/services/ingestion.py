import os
from datetime import datetime
from langchain_core.documents import Document as LangDocument
from app.core.config import UPLOAD_DIR
from app.utils.file_processing import FileValidator, TextCleaner, TextNormalizer, RecursiveChunker
from app.utils.loaders import PDFLoader, DOCXLoader, ImageLoader, AudioLoader, VideoLoader
from app.services.database_mgr import DocumentManager
from app.services.vector_store import LocalVectorStore

class IngestionPipeline:
    def __init__(self):
        self.chunker = RecursiveChunker()

    async def process_document(self, text, file_name, file_type="document", user_id=None):
        cleaned = TextCleaner.clean(text)
        normalized = TextNormalizer.normalize(cleaned)
        chunks = self.chunker.split(normalized)

        document_id = await DocumentManager.save_document_metadata(
            file_name, len(chunks), file_type, user_id=user_id
        )

        docs = []
        for idx, chunk in enumerate(chunks):
            docs.append(LangDocument(
                page_content=chunk.page_content,
                metadata={
                    "document_id": document_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "chunk_id": idx,
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "user_id": user_id
                }
            ))

        await LocalVectorStore.add_documents(docs)
        return document_id, len(chunks)

class UploadService:
    def __init__(self):
        self.pipeline = IngestionPipeline()
        self.pdf_loader = PDFLoader()
        self.docx_loader = DOCXLoader()
        self.image_loader = ImageLoader()
        self.audio_loader = AudioLoader()
        self.video_loader = VideoLoader()

    async def upload(self, file, user_id=None):
        await FileValidator.validate(file)

        file_type = FileValidator.get_file_type(file.filename) or "document"
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Route to the correct loader based on file type
        ext = "." + file.filename.rsplit(".", 1)[-1].lower()

        if ext == ".pdf":
            text = await self.pdf_loader.load(file_path)
        elif ext == ".docx":
            text = await self.docx_loader.load(file_path)
        elif ext in ImageLoader.SUPPORTED:
            text = await self.image_loader.load(file_path)
        elif ext in AudioLoader.SUPPORTED:
            text = await self.audio_loader.load(file_path)
        elif ext in VideoLoader.SUPPORTED:
            text = await self.video_loader.load(file_path)
        else:
            text = ""

        if not text or not text.strip():
            return {
                "success": False,
                "detail": "Could not extract content from the file."
            }

        document_id, total_chunks = await self.pipeline.process_document(
            text, file.filename, file_type, user_id=user_id
        )


        # Type-specific success messages
        type_messages = {
            "document": "Document uploaded and indexed successfully",
            "image": "Image analyzed and indexed successfully",
            "audio": "Audio transcribed and indexed successfully",
            "video": "Video processed and indexed successfully",
        }

        return {
            "success": True,
            "message": type_messages.get(file_type, "File processed successfully"),
            "document_id": document_id,
            "file_name": file.filename,
            "file_type": file_type,
            "total_chunks": total_chunks
        }
