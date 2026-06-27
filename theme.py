# theme.py
import streamlit as st

COLORS = {
    "bg_base":         "#050b18",
    "bg_panel":        "rgba(10, 20, 45, 0.75)",
    "border_cyan":     "#00f0ff",
    "border_magenta":  "#d946ef",
    "text_primary":    "#e8f4ff",
    "text_secondary":  "#7ea8c9",
    "accent_cyan":     "#00f0ff",
    "accent_magenta":  "#d946ef",
    "sidebar_bg":      "rgba(5, 12, 30, 0.92)",
}

def inject_theme():
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600;700&family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

    /* Global viewport frame with Space-Blue Glassmorphic design */
    .stApp {
        background: radial-gradient(ellipse at 20% 50%, #0a1628 0%, #050b18 60%, #020810 100%) padding-box,
                    linear-gradient(135deg, #00f0ff, #d946ef) border-box !important;
        background-attachment: fixed;
        color: #e8f4ff;
        font-family: 'Inter', 'Plus Jakarta Sans', sans-serif;
        border: 2px solid transparent !important;
        box-shadow: 0 0 35px rgba(0, 240, 255, 0.22), inset 0 0 20px rgba(0, 240, 255, 0.08);
        border-radius: 20px;
        margin: 12px !important;
        padding: 5px;
        overflow: hidden !important;
    }
    
    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 98% !important;
    }
    
    /* Headers and titles */
    h1 {
        font-family: 'Orbitron', 'Space Grotesk', sans-serif !important;
        color: #e8f4ff !important;
        letter-spacing: 0.05em;
        font-size: 1.75rem;
    }
    h2, h3 {
        color: #00f0ff !important;
        font-family: 'Space Grotesk', 'Inter', sans-serif !important;
    }
    h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #f8fafc;
    }
    p, li, label, .stMarkdown {
        color: #b0cce0 !important;
    }
    
    /* Background Floating Glow Circles */
    .glow-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: -1;
        overflow: hidden;
        pointer-events: none;
    }
    .glow-circle {
        position: absolute;
        border-radius: 50%;
        filter: blur(140px);
        opacity: 0.1;
        animation: float 25s infinite alternate ease-in-out;
    }
    .gc1 {
        width: 500px;
        height: 500px;
        background: radial-gradient(circle, #00f0ff 0%, #bd93f9 100%);
        top: -150px;
        right: -100px;
        animation-delay: 0s;
    }
    .gc2 {
        width: 450px;
        height: 450px;
        background: radial-gradient(circle, #d946ef 0%, #bd93f9 100%);
        bottom: -100px;
        left: 5%;
        animation-delay: -7s;
    }
    @keyframes float {
        0% { transform: translate(0, 0) scale(1) rotate(0deg); }
        50% { transform: translate(50px, 80px) scale(1.1) rotate(180deg); }
        100% { transform: translate(-30px, 40px) scale(0.95) rotate(360deg); }
    }

    /* Sidebar customization */
    [data-testid="stSidebar"] {
        background: rgba(5, 12, 30, 0.95) !important;
        border-right: 1px solid rgba(0, 240, 255, 0.2) !important;
        backdrop-filter: blur(16px) !important;
    }
    
    /* Centered sidebar menu layout */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 10px !important;
        padding: 10px 14px !important;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.015) !important;
        border: 1px solid rgba(255, 255, 255, 0.03) !important;
        border-radius: 10px !important;
        padding: 12px 18px !important;
        margin: 0 !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex !important;
        align-items: center !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
    }
    
    /* Hide the default radio circle inputs */
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    
    /* Sidebar label typography */
    [data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: #7ea8c9 !important;
        font-family: 'Space Grotesk', 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.03em !important;
        margin: 0 !important;
        font-weight: 500 !important;
        transition: color 0.25s ease !important;
    }
    
    /* Menu item hover effects */
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: rgba(0, 240, 255, 0.05) !important;
        border-color: rgba(0, 240, 255, 0.2) !important;
        transform: translateY(-1px) !important;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover p {
        color: #00f0ff !important;
    }
    
    /* Active menu item highlighting */
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked),
    [data-testid="stSidebar"] div[role="radiogroup"] [aria-checked="true"] {
        background: linear-gradient(135deg, rgba(0, 240, 255, 0.12) 0%, rgba(217, 70, 239, 0.12) 100%) !important;
        border: 1px solid rgba(0, 240, 255, 0.35) !important;
        box-shadow: 0 0 14px rgba(0, 240, 255, 0.18), inset 0 0 8px rgba(0, 240, 255, 0.08) !important;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p,
    [data-testid="stSidebar"] div[role="radiogroup"] [aria-checked="true"] p {
        color: #00f0ff !important;
        font-weight: 700 !important;
        text-shadow: 0 0 8px rgba(0, 240, 255, 0.3) !important;
    }

    /* Sidebar Active / Inactive Buttons */
    div[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%) !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0, 240, 255, 0.3) !important;
        color: #ffffff !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        text-align: left !important;
        padding: 8px 16px !important;
    }
    div[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
        background: transparent !important;
        border: 1px solid transparent !important;
        color: #cbd5e1 !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        text-align: left !important;
        padding: 8px 16px !important;
    }
    div[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {
        background: rgba(255, 255, 255, 0.04) !important;
        color: #ffffff !important;
    }

    /* Main Area Buttons styling */
    div[data-testid="stMain"] button[data-testid="stBaseButton-secondary"] {
        background: rgba(13, 20, 36, 0.7) !important;
        border: 1px solid #bd93f9 !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stMain"] button[data-testid="stBaseButton-secondary"]:hover {
        background: rgba(0, 240, 255, 0.4) !important;
        border-color: #00f0ff !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 240, 255, 0.15) !important;
    }
    div[data-testid="stMain"] button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #00b4d8 0%, #3b82f6 50%, #d946ef 100%) !important;
        border: none !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 15px rgba(0, 240, 255, 0.2) !important;
    }
    div[data-testid="stMain"] button[data-testid="stBaseButton-primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(0, 240, 255, 0.3) !important;
    }

    /* Expander Container Styling */
    div[data-testid="stExpander"] {
        background: rgba(13, 20, 36, 0.55) !important;
        border: 1.5px solid rgba(0, 240, 255, 0.3) !important;
        box-shadow: 0 0 15px rgba(0, 240, 255, 0.1) !important;
        border-radius: 20px !important;
        padding: 0.5rem !important;
        backdrop-filter: blur(12px) !important;
        margin-bottom: 1.25rem !important;
    }
    div[data-testid="stExpander"] details {
        border: none !important;
        background: transparent !important;
    }

    /* Text inputs & Area styling */
    textarea[data-testid="stTextArea-TextArea"], 
    input[type="text"], 
    input[type="password"] {
        background-color: rgba(10, 20, 45, 0.8) !important;
        color: #e8f4ff !important;
        border: 1px solid rgba(0, 240, 255, 0.3) !important;
        border-radius: 8px !important;
    }
    textarea[data-testid="stTextArea-TextArea"]:focus, 
    input:focus {
        border-color: #00f0ff !important;
        box-shadow: 0 0 12px rgba(0, 240, 255, 0.2) !important;
    }

    /* Streamlit Tabs overrides */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(6, 10, 18, 0.5);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.04);
        margin-bottom: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        color: #94a3b8;
        font-weight: 600;
        font-family: 'Space Grotesk', sans-serif;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 240, 255, 0.15) 0%, rgba(217, 70, 239, 0.15) 100%) !important;
        color: #00f0ff !important;
        border: 1px solid rgba(0, 240, 255, 0.3) !important;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tabpanel"] {
        background: rgba(13, 20, 36, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 14px !important;
        padding: 1.25rem !important;
    }

    /* Table overrides */
    table {
        width: 100% !important;
        border-collapse: collapse !important;
    }
    th {
        background-color: rgba(0, 240, 255, 0.06) !important;
        color: #00f0ff !important;
        padding: 8px 12px !important;
        border-bottom: 2px solid #bd93f9 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.8rem;
    }
    td {
        padding: 8px 12px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.03) !important;
        color: #cbd5e1 !important;
        font-size: 0.8rem;
    }

    /* Code and JSON styling */
    code {
        background: rgba(0, 240, 255, 0.1) !important;
        color: #00f0ff !important;
        padding: 2px 6px !important;
        border-radius: 6px !important;
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
        font-size: 0.9em !important;
    }
    pre {
        background: #020c1b !important;
        border: 1px solid rgba(0, 240, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #050b18; }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(#00f0ff, #d946ef);
        border-radius: 3px;
    }

    /* File uploader custom style */
    div[data-testid="stFileUploader"] {
        background: rgba(6, 10, 18, 0.4) !important;
        border: 1px dashed rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }

    /* Agent status badges */
    .agent-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-right: 0.4rem;
    }
    .badge-running { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.25); }
    .badge-success { background: rgba(34, 197, 94, 0.15); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.25); }
    .badge-info { background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.25); }

    /* Console panel for agent steps */
    .console-panel {
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.8rem;
        background: #020c1b !important;
        border-left: 3px solid #00f0ff !important;
        border-radius: 8px;
        border: 1px solid rgba(0, 240, 255, 0.2);
        padding: 1rem;
        max-height: 400px;
        overflow-y: auto;
        box-shadow: inset 0 2px 10px rgba(0,0,0,0.8);
    }
    
    .console-item {
        margin-bottom: 0.6rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.02);
    }

    .pulsing-dot {
        width: 10px;
        height: 10px;
        background-color: #22c55e;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
        animation: pulse 1.6s infinite;
        vertical-align: middle;
        margin-right: 8px;
    }

    .pulsing-dot-amber {
        width: 10px;
        height: 10px;
        background-color: #f59e0b;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7);
        animation: pulse-amber 1.6s infinite;
        vertical-align: middle;
        margin-right: 8px;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(34, 197, 94, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }

    @keyframes pulse-amber {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(245, 158, 11, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
    }

    /* Live Agent Network Pipeline Diagram styling */
    .agent-flow-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        margin-top: 10px;
        flex-wrap: wrap;
    }
    
    .agent-flow-node {
        flex: 1;
        min-width: 120px;
        background: rgba(15, 23, 42, 0.6);
        border: 1.5px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 8px 12px;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .agent-flow-connector {
        color: #475569;
        font-weight: bold;
        font-size: 1.1rem;
    }
    
    .node-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.8rem;
        font-weight: 700;
        color: #ffffff;
    }
    
    .node-desc {
        font-size: 0.65rem;
        color: #64748b;
        margin-top: 2px;
    }
    
    /* Pulsing glow highlights for active agents */
    .pulsing-glow-purple {
        border-color: #c084fc !important;
        box-shadow: 0 0 15px rgba(192, 132, 252, 0.4) !important;
    }
    .pulsing-glow-cyan {
        border-color: #22d3ee !important;
        box-shadow: 0 0 15px rgba(34, 211, 238, 0.4) !important;
    }
    .pulsing-glow-magenta {
        border-color: #f472b6 !important;
        box-shadow: 0 0 15px rgba(244, 114, 182, 0.4) !important;
    }
    .pulsing-glow-green {
        border-color: #4ade80 !important;
        box-shadow: 0 0 15px rgba(74, 222, 128, 0.4) !important;
    }
    
    .flow-idle {
        opacity: 0.5;
    }
    
    .flow-completed {
        border-color: #10b981 !important;
        background-color: rgba(16, 185, 129, 0.08) !important;
        opacity: 1.0;
    }

    /* Reset styles for columns inside columns (nested columns) */
    div[data-testid="column"] div[data-testid="column"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        backdrop-filter: none !important;
    }
</style>
""", unsafe_allow_html=True)
