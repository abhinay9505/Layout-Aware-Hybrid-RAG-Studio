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
_reranker_instance = None
_reranker_lock = asyncio.Lock()

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

def _get_reranker():
    global _reranker_instance
    if _reranker_instance is not None:
        return _reranker_instance
    
    from sentence_transformers import CrossEncoder
    try:
        # Load lightweight reranker model directly to prevent system memory/paging file crashes
        logging.info("Loading lightweight reranker model (cross-encoder/ms-marco-MiniLM-L-6-v2)...")
        _reranker_instance = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        logging.info("Successfully loaded cross-encoder/ms-marco-MiniLM-L-6-v2.")
    except Exception as e:
        logging.error(f"Failed to load lightweight reranker model: {e}. Reranking disabled.")
        _reranker_instance = None
    return _reranker_instance

def _calculate_boost(doc, query):
    boost = 0.0
    query_lower = query.lower()
    doc_content_lower = doc.page_content.lower()

    # 1. Table chunks boost
    if doc.metadata.get("content_type") == "table":
        boost += 0.5
        
    # 2. Figure/diagram chunks boost
    if doc.metadata.get("content_type") == "figure":
        boost += 0.3
        
    # 3. Exact keyword match boost (non-stopwords)
    punctuation = '.,;:!?()[]{}*-_/\\'
    def get_clean_words(text):
        return [w.strip(punctuation) for w in text.split() if w.strip(punctuation)]

    query_words = set(get_clean_words(query_lower))
    chunk_words = set(get_clean_words(doc_content_lower))
    common_words = query_words.intersection(chunk_words)
    stopwords = {"vs", "and", "or", "the", "a", "of", "in", "to", "for", "with", "on", "at", "by", "from", "is"}
    important_common_words = common_words - stopwords
    if important_common_words:
        boost += 0.1 * len(important_common_words)
        
    # 4. Same section matches boost
    doc_section = doc.metadata.get("section_name", "").lower()
    if doc_section and any(word in doc_section for word in query_words if word not in stopwords):
        boost += 0.2
        
    # 5. Query-specific boosts (e.g. BERTBASE vs BERTLARGE)
    if "bertbase" in query_lower or "bertlarge" in query_lower or "bert" in query_lower:
        boost_terms = ["bertbase", "bertlarge", "l=", "h=", "a=", "parameters", "total parameters", "l =", "h =", "a ="]
        match_count = sum(1 for term in boost_terms if term in doc_content_lower)
        if match_count > 0:
            boost += 0.15 * match_count

    return boost

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
            # Detect table intent keywords
            intent_keywords = ["compare", "difference", "score", "accuracy", "parameters", "architecture", "result", "benchmark", "glue", "squad", "mnli"]
            query_lower = query.lower()
            has_table_intent = any(kw in query_lower for kw in intent_keywords)

            # 1. Fetch all documents for this user
            all_docs = []
            for doc_id, doc in db.docstore._dict.items():
                if user_id and doc.metadata.get("user_id") != user_id:
                    continue
                all_docs.append(doc)
            
            if not all_docs:
                return []
                
            # Helper to get unique document key
            def get_doc_key(doc):
                doc_id = doc.metadata.get("document_id", "default")
                chunk_id = doc.metadata.get("chunk_id", 0)
                return f"{doc_id}_{chunk_id}"
                
            # 2. Get vector similarity scores for all candidate docs
            semantic_raw = db.similarity_search_with_score(
                query,
                k=len(all_docs),
                filter=filter_dict if filter_dict else None
            )
            
            vector_scores = {}
            for doc, distance_score in semantic_raw:
                doc_key = get_doc_key(doc)
                similarity = 1.0 - float(distance_score)
                vector_scores[doc_key] = max(0.0, min(1.0, similarity))

            # 3. Calculate BM25 scores
            def tokenize(text):
                punctuation = '.,;:!?()[]{}*-_/\\'
                return [w.strip(punctuation) for w in text.lower().split() if w.strip(punctuation)]
                
            from rank_bm25 import BM25Okapi
            tokenized_corpus = [tokenize(doc.page_content) for doc in all_docs]
            bm25 = BM25Okapi(tokenized_corpus)
            tokenized_query = tokenize(query)
            bm25_raw_scores = bm25.get_scores(tokenized_query)
            
            max_bm25 = max(bm25_raw_scores) if len(bm25_raw_scores) > 0 else 0.0
            bm25_scores = {}
            for doc, raw_score in zip(all_docs, bm25_raw_scores):
                doc_key = get_doc_key(doc)
                bm25_scores[doc_key] = (float(raw_score) / max_bm25) if max_bm25 > 0 else 0.0

            # 4. Calculate Exact keyword match scores
            keyword_variations = {
                "NSP": ["nsp", "next sentence prediction"],
                "MLM": ["mlm", "masked lm", "masked language model"],
                "Figure 1": ["figure 1", "fig 1", "fig. 1"],
                "Figure 2": ["figure 2", "fig 2", "fig. 2"],
                "BERTBASE": ["bertbase", "bert-base", "bert base"],
                "BERTLARGE": ["bertlarge", "bert-large", "bert large"],
                "GLUE": ["glue"],
                "SQuAD": ["squad"]
            }
            
            query_tokens = set(tokenize(query_lower))
            
            exact_match_scores = {}
            for doc in all_docs:
                doc_key = get_doc_key(doc)
                doc_lower = doc.page_content.lower()
                doc_tokens = set(tokenize(doc_lower))
                
                score = 0.0
                # Check for important keywords match
                for kw, patterns in keyword_variations.items():
                    query_has_kw = False
                    for pattern in patterns:
                        if " " in pattern:
                            if pattern in query_lower:
                                query_has_kw = True
                                break
                        else:
                            if pattern in query_tokens:
                                query_has_kw = True
                                break
                    
                    if query_has_kw:
                        doc_has_kw = False
                        for pattern in patterns:
                            if " " in pattern:
                                if pattern in doc_lower:
                                    doc_has_kw = True
                                    break
                            else:
                                if pattern in doc_tokens:
                                    doc_has_kw = True
                                    break
                        if doc_has_kw:
                            score += 1.0
                
                # General exact phrase match for entire query
                if len(query_lower.strip()) > 3 and query_lower.strip() in doc_lower:
                    score += 1.5
                    
                exact_match_scores[doc_key] = score

            # 5. Combine scores: 0.3 * Vector Similarity + 0.3 * BM25 + 0.4 * Exact Match
            scored_candidates_dict = {}
            for doc in all_docs:
                doc_key = get_doc_key(doc)
                v_score = vector_scores.get(doc_key, 0.0)
                b_score = bm25_scores.get(doc_key, 0.0)
                e_score = exact_match_scores.get(doc_key, 0.0)
                
                combined_score = 0.3 * v_score + 0.3 * b_score + 0.4 * e_score
                scored_candidates_dict[doc_key] = {
                    "doc": doc,
                    "score": combined_score
                }
                
            # If table intent detected, prioritize table chunks first, then text chunks
            if has_table_intent:
                table_docs = [doc for doc in all_docs if doc.metadata.get("content_type") == "table"]
                text_docs = [doc for doc in all_docs if doc.metadata.get("content_type") != "table"]
                
                scored_table_docs = [scored_candidates_dict[get_doc_key(doc)] for doc in table_docs]
                scored_table_docs.sort(key=lambda x: x["score"], reverse=True)
                
                scored_text_docs = [scored_candidates_dict[get_doc_key(doc)] for doc in text_docs]
                scored_text_docs.sort(key=lambda x: x["score"], reverse=True)
                
                # Retrieve up to 10 table chunks and up to 20 text chunks, and slice to 20
                top_candidates = (scored_table_docs[:10] + scored_text_docs)[:20]
            else:
                scored_candidates = list(scored_candidates_dict.values())
                scored_candidates.sort(key=lambda x: x["score"], reverse=True)
                top_candidates = scored_candidates[:20]
            
            # 6. Rerank top candidates using CrossEncoder (if loaded)
            reranker = _get_reranker()
            if reranker is not None and top_candidates:
                try:
                    candidate_docs = [item["doc"] for item in top_candidates]
                    pairs = [[query, doc.page_content] for doc in candidate_docs]
                    
                    import numpy as np
                    raw_scores = reranker.predict(pairs)
                    
                    def sigmoid(x):
                        return 1.0 / (1.0 + np.exp(-x))
                        
                    reranked_results = []
                    for doc, raw_score in zip(candidate_docs, raw_scores):
                        norm_score = float(sigmoid(raw_score))
                        doc_key = get_doc_key(doc)
                        e_score = exact_match_scores.get(doc_key, 0.0)
                        b_score = bm25_scores.get(doc_key, 0.0)
                        
                        base_score = 0.5 * norm_score + 0.3 * e_score + 0.2 * b_score
                        boost = _calculate_boost(doc, query)
                        final_score = base_score + boost
                        
                        reranked_results.append({
                            "document": doc,
                            "score": final_score
                        })
                    reranked_results.sort(key=lambda x: x["score"], reverse=True)
                    return reranked_results[:k]
                except Exception as e:
                    logging.error(f"Error during CrossEncoder reranking: {e}. Falling back to combined scores.")
                    
            results = []
            for item in top_candidates:
                doc = item["doc"]
                boost = _calculate_boost(doc, query)
                results.append({
                    "document": doc,
                    "score": item["score"] + boost
                })
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:k]
        except Exception as e:
            logging.error(f"Failed to perform priority search: {e}")
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
