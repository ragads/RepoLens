# pages/settings.py
import os
import streamlit as st
from theme import inject_theme
from services.supabase_service import (
    get_file_count,
    get_chunk_count,
    get_query_count,
    get_storage_bytes,
    wipe_all,
    get_all_files,
    save_file,
    delete_file
)

def seed_sample_codebase(client):
    auth_code = """import os
import jwt
import hashlib

# TODO: Fix security vulnerability in hashing
def hash_password(password, salt="static_salt"):
    # WARNING: Using static salt and MD5 is structurally insecure!
    return hashlib.md5((password + salt).encode()).hexdigest()

def generate_token(user_id):
    # WARNING: Hardcoded secret key should be loaded from environment variables
    SECRET_KEY = "SUPER_SECRET_KEY_123"
    payload = {
        "user_id": user_id,
        "exp": 3600
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def authenticate_user(username, password, db_connection):
    cursor = db_connection.cursor()
    # WARNING: SQL Injection vulnerability in query
    query = f"SELECT id, password_hash FROM users WHERE username = '{username}'"
    cursor.execute(query)
    user = cursor.fetchone()
    
    if user:
        user_id, pwd_hash = user
        input_hash = hash_password(password)
        if input_hash == pwd_hash:
            return generate_token(user_id)
    return None
"""
    save_file(client, "auth_manager.py", "source_code", auth_code, "python", len(auth_code))

    api_doc = """# Authentication & User Management API

## POST /api/v1/auth/login
Authenticates a user and issues a bearer JSON Web Token (JWT).

### Request Headers
- `Content-Type: application/json`

### Request Body
```json
{
  "username": "johndoe",
  "password": "SecretPassword123"
}
```

### Success Response
- **Code:** 200 OK
- **Content:**
```json
{
  "status": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

### Error Responses
- **Code:** 401 Unauthorized (Invalid username or password)
- **Code:** 400 Bad Request (Missing fields)
"""
    save_file(client, "auth_api_docs.md", "api_doc", api_doc, "markdown", len(api_doc))

    design_doc = """# Authentication System Architecture Design

## 1. Overview
The security core governs credentials, tokens, and authorization. It utilizes a stateless JSON Web Token (JWT) workflow to authorize clients for access to resource endpoints.

## 2. Authentication Flow
1. **Client Submission**: Client sends username and password to `/api/v1/auth/login`.
2. **Hash Check**: The system hashes the incoming password and matches it against the stored hash in the Database.
3. **Token Generation**: On matching credentials, a signed JWT payload is constructed containing the user's primary key and expiry time.
4. **Token Verification**: Downstream middleware verifies the token signature on each request.

## 3. Cryptographic Requirements
- Hashing must utilize strong adaptive hashing functions (e.g. bcrypt, Argon2).
- Unique, cryptographically secure salts must be generated for each password.
- JWT secret keys must be retrieved from vault storage at runtime.
"""
    save_file(client, "architecture_design.md", "design_doc", design_doc, "markdown", len(design_doc))

def _test_supabase(url, key):
    try:
        from supabase import create_client
        c = create_client(url, key)
        c.table('assistant_files').select('id').limit(1).execute()
        st.success('✓  Supabase connection verified')
    except Exception as e:
        st.error(f'✗  Supabase failed: {e}')
 
def _test_gemini(key):
    try:
        from google import genai
        # Test client build and simple model list
        c = genai.Client(api_key=key)
        c.models.list(config=None)
        st.success('✓  Gemini API key valid')
    except Exception as e:
        st.error(f'✗  Gemini failed: {e}')

def render_api_keys():
    st.markdown('#### 🔑  API Keys')
    with st.form('api_keys_form'):
        gemini_key   = st.text_input('Gemini API Key', value=os.getenv("GEMINI_API_KEY", ""), type='password',
            help='Required for embeddings and answer generation')
        supabase_url = st.text_input('Supabase Project URL', value=os.getenv("SUPABASE_URL", ""),
            placeholder='https://xxxx.supabase.co')
        supabase_key = st.text_input('Supabase Service Key', value=os.getenv("SUPABASE_KEY", ""), type='password',
            help='Use the service_role key from your Supabase project')
        save = st.form_submit_button('💾  Save & Test Connections')
        
    if save:
        # Save credentials to env
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key
        if supabase_url:
            os.environ["SUPABASE_URL"] = supabase_url
        if supabase_key:
            os.environ["SUPABASE_KEY"] = supabase_key
            
        st.toast("Settings saved.", icon="💾")
        _test_supabase(supabase_url, supabase_key)
        _test_gemini(gemini_key)
        st.rerun()

def render_db_status(client):
    st.markdown('#### 🗄️  Database Status')
    c1,c2,c3,c4 = st.columns(4)
    c1.metric('Mode',    'Supabase' if client else 'SQLite')
    c2.metric('Files',   get_file_count(client))
    c3.metric('Chunks',  get_chunk_count(client))
    c4.metric('Queries', get_query_count(client))
    storage = get_storage_bytes(client)
    st.caption(f'Total storage (content): {storage/1024/1024:.2f} MB')

def render_danger_zone(client):
    st.markdown('#### ⚠️  Danger Zone')
    st.markdown('''
    <div style="border:1px solid #9B1C1C;
        border-radius:10px; padding:16px; margin-top:8px; background:rgba(155,28,28,0.05);">
        <p style="color:#f87171; font-size:0.82rem; margin:0;">Wiping the database will permanently delete all indexed files, chunk vector embeddings, and past query logs.</p>
    </div>''', unsafe_allow_html=True)
    
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    confirm = st.text_input('Type DELETE to confirm wipe')
    if st.button('🗑️  Wipe All Data', type='secondary'):
        if confirm == 'DELETE':
            wipe_all(client)
            st.success('All data wiped. Re-index to continue.')
            st.rerun()
        else:
            st.error('Type DELETE in the confirmation box first.')

def render(client):
    inject_theme()
    
    col_l, col_r = st.columns(2, gap='large')
    with col_l:
        render_api_keys()
        
    with col_r:
        render_db_status(client)
        st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin:20px 0;'>", unsafe_allow_html=True)
        
        # Demo Workspace Manager Seeding
        st.markdown("#### ⚡  Demo Codebase presets")
        files_indexed = get_all_files(client)
        if not files_indexed:
            st.info("No codebase contexts indexed. Load the sample codebase to test bugs & unit test presets.")
            if st.button("🚀  Load Sample Codebase", use_container_width=True):
                with st.spinner("Seeding database index..."):
                    seed_sample_codebase(client)
                st.success("Loaded sample auth codebase!")
                st.rerun()
        else:
            st.success("✅ Demo Codebase Loaded!")
            
        st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin:20px 0;'>", unsafe_allow_html=True)
        render_danger_zone(client)
