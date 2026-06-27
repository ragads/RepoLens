# services/supabase_service.py
import os
import json
import logging
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
import services.sqlite_service as sqlite_service
from services.embedding_service import get_embedding

logger = logging.getLogger("supabase_service")

def get_client() -> Optional[Client]:
    """Validates env credentials and checks connection. Returns Client or None."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not (url and key):
        return None
    try:
        c = create_client(url, key)
        # Verify table check
        c.table('assistant_files').select('id').limit(1).execute()
        return c
    except Exception as e:
        logger.warning(f"Supabase connection verified check failed: {e}. Falling back to SQLite.")
        return None

# ── COUNTS ──────────────────────────────────────────────────────────
def get_file_count(c: Optional[Client]) -> int:
    if not c: 
        return sqlite_service.get_file_count()
    try:
        r = c.table('assistant_files').select('id', count='exact').limit(1).execute()
        return r.count or 0
    except Exception as e:
        logger.error(f"Failed to get file count from Supabase: {e}")
        return sqlite_service.get_file_count()

def get_chunk_count(c: Optional[Client]) -> int:
    if not c: 
        return sqlite_service.get_chunk_count()
    try:
        r = c.table('assistant_file_chunks').select('id', count='exact').limit(1).execute()
        return r.count or 0
    except Exception as e:
        logger.error(f"Failed to get chunk count from Supabase: {e}")
        return sqlite_service.get_chunk_count()

def get_query_count(c: Optional[Client]) -> int:
    if not c: 
        return sqlite_service.get_query_count()
    try:
        r = c.table('assistant_queries').select('id', count='exact').limit(1).execute()
        return r.count or 0
    except Exception as e:
        logger.error(f"Failed to get query count from Supabase: {e}")
        return sqlite_service.get_query_count()

def get_storage_bytes(c: Optional[Client]) -> int:
    if not c: 
        return sqlite_service.get_storage_bytes()
    try:
        r = c.table('assistant_files').select('size_bytes').execute()
        return sum(row['size_bytes'] for row in (r.data or []) if row.get('size_bytes'))
    except Exception as e:
        logger.error(f"Failed to get storage bytes from Supabase: {e}")
        return sqlite_service.get_storage_bytes()

def get_storage_label(c: Optional[Client]) -> str:
    b = get_storage_bytes(c)
    return f'{b/1024/1024:.1f} MB' if b > 1024*1024 else f'{b/1024:.0f} KB'

# ── FILES ───────────────────────────────────────────────────────────
def get_all_files(c: Optional[Client]) -> List[Dict[str, Any]]:
    if not c: 
        return sqlite_service.get_all_files()
    try:
        r = c.table('assistant_files')\
             .select('id,filename,file_type,language,size_bytes,created_at')\
             .order('created_at', desc=True).execute()
        return r.data or []
    except Exception as e:
        logger.error(f"Failed to get all files from Supabase: {e}")
        return sqlite_service.get_all_files()

def get_file_type_breakdown(c: Optional[Client]) -> Dict[str, int]:
    files = get_all_files(c)
    counts = {}
    for f in files:
        ft = f['file_type']
        counts[ft] = counts.get(ft, 0) + 1
    return counts

def get_language_breakdown(c: Optional[Client]) -> Dict[str, int]:
    files = get_all_files(c)
    counts = {}
    for f in files:
        lang = f['language'] or 'Unknown'
        counts[lang] = counts.get(lang, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1])[:10])

def delete_file(c: Optional[Client], file_id: int):
    if not c: 
        return sqlite_service.delete_file(file_id)
    try:
        c.table('assistant_file_chunks').delete().eq('file_id', file_id).execute()
        c.table('assistant_files').delete().eq('id', file_id).execute()
    except Exception as e:
        logger.error(f"Failed to delete file from Supabase: {e}")
        sqlite_service.delete_file(file_id)

def wipe_all(c: Optional[Client]):
    if not c: 
        return sqlite_service.wipe_all()
    try:
        c.table('assistant_file_chunks').delete().neq('id', 0).execute()
        c.table('assistant_files').delete().neq('id', 0).execute()
        c.table('assistant_queries').delete().neq('id', 0).execute()
    except Exception as e:
        logger.error(f"Failed to wipe Supabase: {e}")
        sqlite_service.wipe_all()

# ── QUERIES ─────────────────────────────────────────────────────────
def get_query_history(c: Optional[Client], limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    if not c: 
        return sqlite_service.get_query_history(limit, offset)
    try:
        r = c.table('assistant_queries').select('*')\
             .order('created_at', desc=True)\
             .range(offset, offset+limit-1).execute()
        
        result = []
        for row in (r.data or []):
            rd = dict(row)
            try:
                if isinstance(rd.get('retrieved_files'), str):
                    rd['retrieved_files'] = json.loads(rd['retrieved_files'])
            except Exception:
                pass
            try:
                if isinstance(rd.get('agent_trace'), str):
                    rd['agent_trace'] = json.loads(rd['agent_trace'])
            except Exception:
                pass
            result.append(rd)
        return result
    except Exception as e:
        logger.error(f"Failed to get query history from Supabase: {e}")
        return sqlite_service.get_query_history(limit, offset)

def get_recent_queries(c: Optional[Client], n: int = 5) -> List[Dict[str, Any]]:
    if not c: 
        return sqlite_service.get_recent_queries(n)
    try:
        r = c.table('assistant_queries')\
             .select('id,question,created_at,plan,retrieved_files,answer,agent_trace')\
             .order('created_at', desc=True).limit(n).execute()
        
        result = []
        for row in (r.data or []):
            rd = dict(row)
            try:
                if isinstance(rd.get('retrieved_files'), str):
                    rd['retrieved_files'] = json.loads(rd['retrieved_files'])
            except Exception:
                pass
            try:
                if isinstance(rd.get('agent_trace'), str):
                    rd['agent_trace'] = json.loads(rd['agent_trace'])
            except Exception:
                pass
            result.append(rd)
        return result
    except Exception as e:
        logger.error(f"Failed to get recent queries from Supabase: {e}")
        return sqlite_service.get_recent_queries(n)

def get_queries_today(c: Optional[Client]) -> int:
    if not c: 
        return sqlite_service.get_queries_today()
    try:
        from datetime import date
        today = str(date.today())
        r = c.table('assistant_queries').select('id', count='exact')\
             .gte('created_at', today).execute()
        return r.count or 0
    except Exception as e:
        logger.error(f"Failed to get queries today from Supabase: {e}")
        return sqlite_service.get_queries_today()

def insert_query_log(c: Optional[Client], question: str, plan: str, retrieved_files: List[str], answer: str, trace: Optional[List[Dict[str, Any]]] = None):
    payload = {
        'question': question, 
        'plan': plan,
        'retrieved_files': json.dumps(retrieved_files),
        'answer': answer,
    }
    if trace:
        payload['agent_trace'] = json.dumps(trace)
    
    if not c:
        return sqlite_service.insert_query_log(payload)
        
    try:
        c.table('assistant_queries').insert(payload).execute()
    except Exception as e:
        logger.error(f"Failed to insert query log into Supabase: {e}")
        sqlite_service.insert_query_log(payload)

def get_avg_files_per_query(c: Optional[Client]) -> float:
    if not c:
        return sqlite_service.get_avg_files_per_query()
    try:
        r = c.table('assistant_queries').select('retrieved_files').execute()
        lengths = []
        for row in (r.data or []):
            try:
                files = json.loads(row['retrieved_files']) if isinstance(row['retrieved_files'], str) else row['retrieved_files']
                lengths.append(len(files))
            except Exception:
                pass
        return round(sum(lengths) / len(lengths), 1) if lengths else 0.0
    except Exception as e:
        logger.error(f"Failed to get avg files from Supabase: {e}")
        return sqlite_service.get_avg_files_per_query()

# ── SEMANTIC SEARCH ─────────────────────────────────────────────────
def semantic_search(c: Optional[Client], embedding: List[float], top_k: int = 8, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
    if not c: 
        return sqlite_service.semantic_search(embedding, top_k, file_type)
    try:
        params = {'query_embedding': embedding, 'match_count': top_k}
        if file_type:
            params['file_type_filter'] = file_type
        r = c.rpc('match_chunks', params).execute()
        return r.data or []
    except Exception as e:
        logger.warning(f"Failed RPC match_chunks on Supabase: {e}. Falling back to SQLite.")
        return sqlite_service.semantic_search(embedding, top_k, file_type)

def search_chunks_vector(c: Optional[Client], query: str, limit: int = 5, file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Thin wrapper interface matching search_chunks_vector."""
    query_vector = get_embedding(query)
    if not query_vector:
        return []
        
    ft_filter = None
    if file_types and len(file_types) == 1:
        ft_filter = file_types[0]
        
    raw_results = semantic_search(c, query_vector, top_k=limit, file_type=ft_filter)
    
    # Map key properties for console.py and search.py compatibility
    mapped = []
    for r in raw_results:
        mapped.append({
            "content": r.get("content", ""),
            "filename": r.get("filename", ""),
            "file_type": r.get("file_type", "source_code"),
            "score": r.get("similarity", 0.0)
        })
    return mapped

# ── INGESTION OPERATIONS ─────────────────────────────────────────────
def get_file_content(c: Optional[Client], file_id: int) -> Dict[str, Any]:
    if not c:
        return sqlite_service.get_file_content(file_id)
    try:
        r = c.table('assistant_files').select('*').eq('id', file_id).execute()
        return r.data[0] if r.data else {}
    except Exception as e:
        logger.error(f"Failed to get file content from Supabase: {e}")
        return sqlite_service.get_file_content(file_id)

def chunk_text_by_lines(text: str, max_lines: int = 40, overlap_lines: int = 5) -> List[str]:
    lines = text.splitlines()
    chunks = []
    if not lines:
        return chunks
    i = 0
    while i < len(lines):
        chunk_lines = lines[i:i + max_lines]
        chunks.append("\n".join(chunk_lines))
        i += max_lines - overlap_lines
        if i >= len(lines):
            break
    return chunks

def save_file(c: Optional[Client], filename: str, file_type: str, content: str, language: str, size_bytes: int) -> bool:
    """Saves file to Supabase or SQLite and embeds chunks."""
    file_id = None
    if c:
        try:
            payload = {
                "filename": filename,
                "file_type": file_type,
                "content": content,
                "language": language,
                "size_bytes": size_bytes
            }
            # Check for existing
            res = c.table("assistant_files").select("id").eq("filename", filename).eq("file_type", file_type).execute()
            if res.data:
                file_id = res.data[0]["id"]
                c.table("assistant_files").update(payload).eq("id", file_id).execute()
            else:
                insert_res = c.table("assistant_files").insert(payload).execute()
                file_id = insert_res.data[0]["id"]
        except Exception as e:
            logger.error(f"Failed to save file to Supabase: {e}")
            c = None # force fallback
            
    if not c:
        file_id = sqlite_service.save_file(filename, file_type, content, language, size_bytes)
        
    if file_id is None:
        return False
        
    # Rebuild chunks
    if c:
        try:
            c.table("assistant_file_chunks").delete().eq("file_id", file_id).execute()
        except Exception:
            pass
    else:
        sqlite_service.clear_chunks(file_id)
        
    chunks = chunk_text_by_lines(content)
    for idx, chunk in enumerate(chunks):
        embedding_val = get_embedding(chunk)
        embedding_json = json.dumps(embedding_val) if embedding_val else None
        
        if c:
            try:
                chunk_data = {
                    "file_id": file_id,
                    "chunk_index": idx,
                    "content": chunk,
                    "embedding": embedding_json
                }
                if embedding_val:
                    chunk_data["embedding_vec"] = embedding_val
                c.table("assistant_file_chunks").insert(chunk_data).execute()
            except Exception as e:
                logger.error(f"Failed to insert chunk to Supabase: {e}")
        else:
            sqlite_service.insert_chunk(file_id, idx, chunk, embedding_json)
            
    return True

def insert_file_with_chunks(c: Optional[Client], file_info: Dict[str, Any]) -> bool:
    """Helper used by GitHub Repo ingestion clone_and_index."""
    path = file_info.get("path", "")
    content = file_info.get("content", "")
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="ignore")
        
    ext = path.split(".")[-1].lower() if "." in path else ""
    from pages.data import LANGUAGE_MAPPING
    lang = LANGUAGE_MAPPING.get(ext, "text")
    
    if ext in ["md", "txt"]:
        db_type = "design_doc" if "design" in path.lower() or "architecture" in path.lower() else "api_doc"
    else:
        db_type = "source_code"
        
    return save_file(c, path, db_type, content, lang, len(content))

# ── NEW RPC / TIMELINE HELPERS ─────────────────────────────────────
def get_queries_per_day(c: Optional[Client], days: int = 30) -> List[Dict[str, Any]]:
    if c:
        try:
            r = c.rpc('queries_per_day', {'day_count': days}).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"Failed queries_per_day RPC: {e}")
            
    # SQLite fallback
    try:
        import sqlite3
        conn = sqlite3.connect(sqlite_service.SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DATE(created_at) AS day, COUNT(*) AS count
            FROM assistant_queries
            WHERE created_at >= datetime('now', ?)
            GROUP BY day ORDER BY day
        """, (f"-{days} days",))
        rows = cursor.fetchall()
        conn.close()
        return [{"day": r[0], "count": r[1]} for r in rows]
    except Exception as e:
        logger.error(f"Failed queries_per_day SQLite query: {e}")
        return []

def get_top_retrieved_files(c: Optional[Client], limit: int = 10) -> List[Dict[str, Any]]:
    if c:
        try:
            r = c.rpc('top_retrieved_files', {'top_n': limit}).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"Failed top_retrieved_files RPC: {e}")
            
    # SQLite fallback
    try:
        import sqlite3
        conn = sqlite3.connect(sqlite_service.SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT retrieved_files FROM assistant_queries")
        rows = cursor.fetchall()
        conn.close()
        
        counts = {}
        for r in rows:
            if r[0]:
                try:
                    files = json.loads(r[0])
                    for f in files:
                        counts[f] = counts.get(f, 0) + 1
                except Exception:
                    pass
        sorted_files = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [{"filename": f[0], "count": f[1]} for f in sorted_files[:limit]]
    except Exception as e:
        logger.error(f"Failed top_retrieved_files SQLite query: {e}")
        return []

def get_files_per_day(c: Optional[Client], days: int = 30) -> List[Dict[str, Any]]:
    """RPC function for files_per_day."""
    if c:
        try:
            r = c.rpc('files_per_day', {'day_count': days}).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"Failed files_per_day RPC: {e}")
            
    # SQLite fallback
    try:
        import sqlite3
        conn = sqlite3.connect(sqlite_service.SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DATE(created_at) AS day, COUNT(*) AS count
            FROM assistant_files
            WHERE created_at >= datetime('now', ?)
            GROUP BY day ORDER BY day
        """, (f"-{days} days",))
        rows = cursor.fetchall()
        conn.close()
        return [{"day": r[0], "count": r[1]} for r in rows]
    except Exception as e:
        logger.error(f"Failed files_per_day SQLite query: {e}")
        return []


# ── COMPATIBILITY CLASS WRAPPER ─────────────────────────────────────
class DatabaseManager:
    """Compatibility class delegate for agent_orchestrator.py."""
    def __init__(self):
        self.supabase_client = get_client()
        self.use_supabase = self.supabase_client is not None

    def get_all_files(self) -> List[Dict[str, Any]]:
        return get_all_files(self.supabase_client)

    def search_files(self, keyword: str, file_types: List[str] = None) -> List[Dict[str, Any]]:
        # Map back to old signature or use search_files logic from SQLite/Supabase
        # Let's write a simple implementation matching search_files
        files = self.get_all_files()
        results = []
        for f in files:
            if file_types and f["file_type"] not in file_types:
                continue
            if keyword.lower() in f["filename"].lower():
                # We need content too
                content_file = get_file_content(self.supabase_client, f["id"])
                results.append({
                    "id": f["id"],
                    "filename": f["filename"],
                    "file_type": f["file_type"],
                    "language": f["language"],
                    "size_bytes": f["size_bytes"],
                    "content": content_file.get("content", "")
                })
        return results

    def search_chunks_vector(self, query: str, limit: int = 5, file_types: List[str] = None) -> List[Dict[str, Any]]:
        return search_chunks_vector(self.supabase_client, query, limit, file_types)

    def save_query(self, question: str, plan: str, retrieved_files: List[str], answer: str, agent_trace: Optional[List[Dict[str, Any]]] = None) -> bool:
        try:
            insert_query_log(self.supabase_client, question, plan, retrieved_files, answer, agent_trace)
            return True
        except Exception:
            return False

    def delete_file(self, file_id: Any) -> bool:
        delete_file(self.supabase_client, file_id)
        return True

    def get_file_content(self, file_id: Any) -> Dict[str, Any]:
        return get_file_content(self.supabase_client, file_id)

    def save_file(self, filename: str, file_type: str, content: str, language: str, size_bytes: int) -> bool:
        return save_file(self.supabase_client, filename, file_type, content, language, size_bytes)
