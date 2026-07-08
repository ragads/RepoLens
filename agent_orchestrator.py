import os
import json
import logging
from typing import List, Dict, Any, Tuple
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv
from services.database_service import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("agent_orchestrator")

# Load env variables
load_dotenv()

# Configure Gemini — will be initialized per-call using current API key
_gemini_client = None

def _get_gemini_client():
    global _gemini_client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key is not configured. Please add it to your .env file or input it in System Configuration.")
    # Always recreate client to pick up runtime key changes
    return genai.Client(api_key=api_key)

class AgentOrchestrator:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.model_name = "gemini-2.5-flash"

    def _call_llm(self, system_instruction: str, prompt: str) -> str:
        """Helper to invoke Gemini API with system instructions."""
        client = _get_gemini_client()
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        return response.text

    def run_workflow(self, question: str, on_step_callback=None) -> Dict[str, Any]:
        """
        Executes the agentic workflow:
        User Question -> Planner Agent -> Code Search Agent -> Documentation Agent -> Answer Generator
        
        on_step_callback: function that accepts (step_name, data_dict) for UI updates.
        """
        logger.info(f"Starting workflow for question: '{question}'")
        logs = []
        
        def log_step(step_name: str, status: str, message: str, data: Any = None):
            log_entry = {
                "step": step_name,
                "status": status,
                "message": message,
                "data": data,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            logs.append(log_entry)
            if on_step_callback:
                on_step_callback(step_name, log_entry)

        from datetime import datetime
        
        # ----------------------------------------------------
        # 1. Fetch available files in index
        # ----------------------------------------------------
        available_files = self.db.get_all_files()
        file_summary = [
            {"filename": f["filename"], "file_type": f["file_type"], "language": f["language"]}
            for f in available_files
        ]
        
        log_step(
            "System Index", 
            "success", 
            f"Retrieved active file index. Found {len(file_summary)} files in database.",
            {"files": file_summary}
        )

        # ----------------------------------------------------
        # 2. Planner Agent
        # ----------------------------------------------------
        log_step("Planner Agent", "running", "Planner is analyzing the question and database file index...")
        
        planner_system = """You are the Lead Planner Agent of an AI Software Engineer Assistant.
Your task is to analyze the user's question, inspect the catalog of available files, and generate a precise search plan.
You must output a JSON object with the following fields:
{
  "explanation": "Brief explanation of what the user wants and what needs to be looked at.",
  "code_search_keywords": ["keyword1", "keyword2"],
  "doc_search_keywords": ["keyword1", "keyword2"],
  "target_files": ["optional_specific_filename_from_catalog.py"],
  "analysis_strategy": "A brief sentence explaining how we will synthesize the answer (e.g. explain flow, check bug, write tests)."
}
Make sure you match user terms against the file catalog. If they mention a file name, put it in target_files.
Ensure you return ONLY valid JSON.
"""
        
        planner_prompt = f"""
User Question: {question}

Catalog of Available Files:
{json.dumps(file_summary, indent=2)}
"""
        
        try:
            planner_res = self._call_llm(planner_system, planner_prompt)
            # Clean JSON markdown blocks if any
            clean_res = planner_res.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            clean_res = clean_res.strip()
            
            plan = json.loads(clean_res)
            log_step("Planner Agent", "success", "Planner Agent successfully generated the retrieval plan.", plan)
        except Exception as e:
            logger.error(f"Planner Agent failed: {e}")
            plan = {
                "explanation": "Default plan due to parser fallback.",
                "code_search_keywords": [question.split()[0]] if question.split() else ["code"],
                "doc_search_keywords": [question.split()[0]] if question.split() else ["doc"],
                "target_files": [],
                "analysis_strategy": "Direct synthesis search fallback."
            }
            log_step("Planner Agent", "warning", f"Planner Agent encountered error: {e}. Executing fallback plan.", plan)

        # ----------------------------------------------------
        # 3. Code Search Agent
        # ----------------------------------------------------
        log_step("Code Search Agent", "running", "Code Search Agent is querying the database for relevant source code using Hybrid Vector Search...")
        
        retrieved_code_files = []
        retrieved_code_chunks = []
        code_keywords = plan.get("code_search_keywords", [])
        target_files = plan.get("target_files", [])
        
        # 1. Search target files first (catalog keyword match)
        searched_ids = set()
        for filename in target_files:
            matches = self.db.search_files(filename, file_types=["source_code"])
            for m in matches:
                if m["id"] not in searched_ids:
                    retrieved_code_files.append(m)
                    searched_ids.add(m["id"])

        # 2. Query keywords (catalog keyword match)
        for kw in code_keywords:
            matches = self.db.search_files(kw, file_types=["source_code"])
            for m in matches:
                if m["id"] not in searched_ids:
                    retrieved_code_files.append(m)
                    searched_ids.add(m["id"])
                    
        # Limit to top 5 files to avoid context blowout
        retrieved_code_files = retrieved_code_files[:5]
        
        # 3. Query Vector similarities for chunks
        try:
            vector_matches = self.db.search_chunks_vector(question, limit=5, file_types=["source_code"])
            retrieved_code_chunks.extend(vector_matches)
        except Exception as e:
            logger.warning(f"Vector chunk search failed for code: {e}")
        
        code_summary = [
            {"filename": f["filename"], "language": f.get("language"), "size_bytes": f.get("size_bytes")}
            for f in retrieved_code_files
        ]
        if retrieved_code_chunks:
            code_summary.append({"vector_chunks_found": len(retrieved_code_chunks)})
            
        log_step(
            "Code Search Agent", 
            "success", 
            f"Code Search Agent retrieved {len(retrieved_code_files)} code files and {len(retrieved_code_chunks)} vector matching chunks.",
            {"retrieved_files": code_summary}
        )

        # ----------------------------------------------------
        # 4. Documentation Agent
        # ----------------------------------------------------
        log_step("Documentation Agent", "running", "Documentation Agent is querying the database for API and design documents using Hybrid Vector Search...")
        
        retrieved_doc_files = []
        retrieved_doc_chunks = []
        doc_keywords = plan.get("doc_search_keywords", [])
        
        # 1. Search target files first in docs
        for filename in target_files:
            matches = self.db.search_files(filename, file_types=["api_doc", "design_doc"])
            for m in matches:
                if m["id"] not in searched_ids:
                    retrieved_doc_files.append(m)
                    searched_ids.add(m["id"])

        # 2. Query keywords
        for kw in doc_keywords:
            matches = self.db.search_files(kw, file_types=["api_doc", "design_doc"])
            for m in matches:
                if m["id"] not in searched_ids:
                    retrieved_doc_files.append(m)
                    searched_ids.add(m["id"])
                    
        retrieved_doc_files = retrieved_doc_files[:5]
        
        # 3. Query Vector similarities for doc chunks
        try:
            vector_matches = self.db.search_chunks_vector(question, limit=5, file_types=["api_doc", "design_doc"])
            retrieved_doc_chunks.extend(vector_matches)
        except Exception as e:
            logger.warning(f"Vector chunk search failed for docs: {e}")
        
        doc_summary = [
            {"filename": f["filename"], "file_type": f["file_type"], "size_bytes": f.get("size_bytes")}
            for f in retrieved_doc_files
        ]
        if retrieved_doc_chunks:
            doc_summary.append({"vector_chunks_found": len(retrieved_doc_chunks)})
            
        log_step(
            "Documentation Agent", 
            "success", 
            f"Documentation Agent retrieved {len(retrieved_doc_files)} docs and {len(retrieved_doc_chunks)} vector matching chunks.",
            {"retrieved_files": doc_summary}
        )

        # ----------------------------------------------------
        # 5. Answer Generator Agent
        # ----------------------------------------------------
        log_step("Answer Generator Agent", "running", "Synthesizing final response based on retrieved resources...")
        
        generator_system = """You are the Senior Answer Generator Agent of an AI Software Engineer Assistant.
Your task is to synthesize the final answer to the user's question.
You are provided with:
1. The user question.
2. The agentic retrieval plan.
3. Contents of relevant source code files found.
4. Contents of relevant API/design documentation files found.

You must answer the user's question accurately, citing the relevant files and explaining details clearly. 
For specific requests:
- "Explain code": Describe how it works, its components, flow, and integration points.
- "Find bugs": Point out syntax, logical, or architectural errors, explain why they occur, and write corrected code blocks as diffs or full code.
- "Generate tests": Write comprehensive unit tests in the appropriate framework (e.g. pytest, jest) with mock setups.
- "Generate API docs": Write Markdown-formatted API specifications, endpoint descriptions, schemas, and usage examples.

Make the output extremely professional, using Markdown tables, lists, and code syntax highlighting. Highlight warnings or notes with GitHub alert blockquote syntax, like:
> [!NOTE]
> ...
"""

        # Build context
        code_context = ""
        for f in retrieved_code_files:
            code_context += f"\n\n--- FILE: {f['filename']} (Type: Source Code, Language: {f.get('language')}) ---\n"
            code_context += f["content"]
            
        if retrieved_code_chunks:
            code_context += "\n\n--- RELEVANT CODE CHUNKS (VECTOR SEARCH MATCHES) ---"
            for idx, c in enumerate(retrieved_code_chunks):
                code_context += f"\n[Chunk #{idx+1} from {c['filename']} (Similarity Score: {round(c['score'], 3)})]\n"
                code_context += c["content"] + "\n"

        doc_context = ""
        for f in retrieved_doc_files:
            doc_context += f"\n\n--- FILE: {f['filename']} (Type: {f['file_type']}) ---\n"
            doc_context += f["content"]
            
        if retrieved_doc_chunks:
            doc_context += "\n\n--- RELEVANT DOCUMENTATION CHUNKS (VECTOR SEARCH MATCHES) ---"
            for idx, c in enumerate(retrieved_doc_chunks):
                doc_context += f"\n[Chunk #{idx+1} from {c['filename']} (Similarity Score: {round(c['score'], 3)})]\n"
                doc_context += c["content"] + "\n"

        generator_prompt = f"""
User Question: {question}

Planner Strategy:
{json.dumps(plan, indent=2)}

--- RETRIEVED SOURCE CODE ---
{code_context if code_context else "No relevant source code files were found."}

--- RETRIEVED DOCUMENTATION ---
{doc_context if doc_context else "No relevant API or design docs were found."}
"""

        try:
            answer = self._call_llm(generator_system, generator_prompt)
            log_step("Answer Generator Agent", "success", "Answer Generator successfully compiled the response.")
        except Exception as e:
            logger.error(f"Answer Generator failed: {e}")
            answer = f"Error generating answer: {e}. Please check your API configuration or verify that your query matches files in the index."
            log_step("Answer Generator Agent", "failed", f"Answer Generator failed: {e}")

        # Save query log to database
        all_retrieved_filenames = [f["filename"] for f in (retrieved_code_files + retrieved_doc_files)]
        # Dedup filenames and append vector matching file names
        for c in (retrieved_code_chunks + retrieved_doc_chunks):
            if c["filename"] not in all_retrieved_filenames:
                all_retrieved_filenames.append(c["filename"])
                
        self.db.save_query(
            question=question,
            plan=json.dumps(plan),
            retrieved_files=all_retrieved_filenames,
            answer=answer,
            agent_trace=logs
        )
        
        return {
            "answer": answer,
            "plan": plan,
            "logs": logs,
            "retrieved_files": all_retrieved_filenames
        }
