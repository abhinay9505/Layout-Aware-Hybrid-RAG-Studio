import os
import logging
import asyncio
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document as LangDocument
from app.core.config import FAISS_INDEX_DIR
from app.core.dependencies import embedding_model

# In-memory singleton FAISS instance and async lock for thread-safety
_db_instance = None
_lock = asyncio.Lock()

def _get_db():
    global _db_instance
    if _db_instance is not None:
        return _db_instance
    
    # Try to load from disk
    if os.path.exists(os.path.join(FAISS_INDEX_DIR, "index.faiss")):
        try:
            _db_instance = FAISS.load_local(
                FAISS_INDEX_DIR, 
                embedding_model, 
                allow_dangerous_deserialization=True
            )
            logging.info("Successfully loaded existing FAISS index from disk.")
            return _db_instance
        except Exception as e:
            logging.error(f"Error loading FAISS index: {e}")
            
    # If it doesn't exist or failed to load, initialize an empty one:
    import faiss
    from langchain_community.docstore.in_memory import InMemoryDocstore
    # MiniLM-L6-v2 dimension is 384
    dimension = 384
    index = faiss.IndexFlatIP(dimension)
    _db_instance = FAISS(
        embedding_function=embedding_model,
        index=index,
        docstore=InMemoryDocstore({}),
        index_to_docstore_id={},
        distance_strategy=DistanceStrategy.COSINE
    )
    logging.info("Initialized new empty FAISS index.")
    return _db_instance

class LocalVectorStore:
    @staticmethod
    async def add_documents(docs):
        async with _lock:
            db = _get_db()
            try:
                # Add documents to FAISS index
                db.add_documents(docs)
                # Persist updated index to disk
                db.save_local(FAISS_INDEX_DIR)
                logging.info(f"Successfully indexed and persisted {len(docs)} documents.")
            except Exception as e:
                logging.error(f"Failed to add documents to FAISS index: {e}")

    @staticmethod
    async def similarity_search(query, k=5, user_id=None):
        async with _lock:
            db = _get_db()
        
        filter_dict = {}
        if user_id:
            filter_dict["user_id"] = user_id

        try:
            # FAISS similarity_search_with_score returns list of (Document, score)
            # Under DistanceStrategy.COSINE / IndexFlatIP, score is cosine similarity (higher is better)
            raw_results = db.similarity_search_with_score(
                query,
                k=k,
                filter=filter_dict if filter_dict else None
            )
            
            scores = []
            for doc, score in raw_results:
                scores.append({
                    "score": float(score),
                    "document": doc
                })
            return scores
        except Exception as e:
            logging.error(f"Failed to perform FAISS similarity search: {e}")
            return []

    @staticmethod
    async def delete_documents(document_id):
        async with _lock:
            db = _get_db()
            try:
                # Find all docstore IDs matching the document_id
                ids_to_delete = []
                for doc_id, doc in db.docstore._dict.items():
                    if doc.metadata.get("document_id") == document_id:
                        ids_to_delete.append(doc_id)
                
                if ids_to_delete:
                    db.delete(ids_to_delete)
                    db.save_local(FAISS_INDEX_DIR)
                    logging.info(f"Deleted {len(ids_to_delete)} vectors matching document_id: {document_id}")
                else:
                    logging.info(f"No vectors found matching document_id: {document_id}")
            except Exception as e:
                logging.error(f"Failed to delete vectors from FAISS: {e}")
