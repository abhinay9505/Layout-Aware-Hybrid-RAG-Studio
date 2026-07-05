import os
from datetime import datetime
from langchain_core.documents import Document as LangDocument
from app.core.config import UPLOAD_DIR
from app.utils.file_processing import FileValidator, TextCleaner, TextNormalizer, RecursiveChunker
from app.utils.loaders import PDFLoader, DOCXLoader
from app.services.database_mgr import DocumentManager
from app.services.vector_store import LocalVectorStore

class IngestionPipeline:
    def __init__(self):
        self.chunker = RecursiveChunker()

    async def process_document(self, pages, file_name, file_type="document", user_id=None, extracted_figures=None):
        all_chunks = []
        for page in pages:
            cleaned = TextCleaner.clean(page["text"])
            normalized = TextNormalizer.normalize(cleaned)
            if not normalized.strip():
                continue
            page_chunks = self.chunker.split(normalized, page_num=page["page_num"])
            all_chunks.extend(page_chunks)

        total_chunks = len(all_chunks)
        document_id = await DocumentManager.save_document_metadata(
            file_name, total_chunks, file_type, user_id=user_id
        )

        docs = []
        for idx, chunk in enumerate(all_chunks):
            docs.append(LangDocument(
                page_content=chunk.page_content,
                metadata={
                    "document_id": document_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "chunk_id": idx,
                    "page_num": chunk.metadata.get("page_num", 1),
                    "section_name": chunk.metadata.get("section_name", "Header/Title"),
                    "content_type": chunk.metadata.get("content_type", "text"),
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "user_id": user_id
                }
            ))

        if docs:
            await LocalVectorStore.add_documents(docs)

        # Save extracted figures if any
        if extracted_figures:
            from app.services.database_mgr import FigureManager
            for fig in extracted_figures:
                await FigureManager.save_figure(
                    document_id=document_id,
                    figure_number=fig["figure_number"],
                    caption=fig["caption"],
                    page_number=fig["page_number"],
                    image_path=fig["image_path"],
                    nearby_text=fig["nearby_text"],
                    user_id=user_id
                )

        return document_id, total_chunks


class UploadService:
    def __init__(self):
        self.pipeline = IngestionPipeline()
        self.pdf_loader = PDFLoader()
        self.docx_loader = DOCXLoader()

    async def upload(self, file, user_id=None):
        await FileValidator.validate(file)

        ext = "." + file.filename.rsplit(".", 1)[-1].lower()
        if ext not in [".pdf", ".docx"]:
            return {
                "success": False,
                "detail": "Unsupported file format. Only PDF and DOCX are allowed."
            }

        file_type = "document"
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        pages = []
        extracted_figures = []
        if ext == ".pdf":
            pages = await self.pdf_loader.load(file_path)
            extracted_figures = getattr(self.pdf_loader, "extracted_figures", [])
        elif ext == ".docx":
            text = await self.docx_loader.load(file_path)
            if text and text.strip():
                pages = [{"text": text, "page_num": 1}]

        if not pages:
            return {
                "success": False,
                "detail": "Could not extract content from the file."
            }

        document_id, total_chunks = await self.pipeline.process_document(
            pages, file.filename, file_type, user_id=user_id, extracted_figures=extracted_figures
        )

        return {
            "success": True,
            "message": "Document uploaded and indexed successfully",
            "document_id": document_id,
            "file_name": file.filename,
            "file_type": file_type,
            "total_chunks": total_chunks
        }
