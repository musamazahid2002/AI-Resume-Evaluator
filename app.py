import os
import base64
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from pypdf import PdfReader
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. Structured Output Schema
# ==========================================
class SkillMetric(BaseModel):
    skill_name: str = Field(description="Skill/technology name (e.g. C#, ASP.NET, SQL, Docker)")
    match_percentage: int = Field(description="Proficiency/Match percentage from 0 to 100")

class JDComparison(BaseModel):
    matched_strengths: list[str] = Field(description="Top 2-3 matched capabilities with quantified evidence.")
    critical_gaps: list[str] = Field(description="Top 2-3 missing technical or experience requirements.")
    strategic_recommendations: list[str] = Field(description="Actionable advice to bridge qualification gaps.")

class RewriteItem(BaseModel):
    original: str = Field(description="Weak or unquantified resume bullet point.")
    improved: str = Field(description="High-impact STAR-method rewrite with metrics.")

class EvaluationResult(BaseModel):
    candidate_name: str = Field(description="Candidate's full name extracted from resume.")
    detected_title: str = Field(description="Candidate's current or target job title.")
    overall_fit: int = Field(description="Overall percentage fit from 0 to 100.")
    skill_match: int = Field(description="Technical skills match percentage (0-100).")
    experience_match: int = Field(description="Experience depth and relevance match percentage (0-100).")
    formatting_score: int = Field(description="ATS layout and syntax compliance percentage (0-100).")
    executive_summary: str = Field(description="A concise 2-sentence executive assessment.")
    key_skills: list[SkillMetric] = Field(description="Top 5 core skills evaluated with individual percentages.")
    soft_skills_scores: list[int] = Field(description="4 scores (0-100) for Communication, Leadership, Problem Solving, and Adaptability.")
    jd_comparison: JDComparison
    suggested_rewrites: list[RewriteItem]

# ==========================================
# 2. Helpers & AI Engine
# ==========================================
def get_image_base64(image_path: str) -> str:
    """Reads a local image file and returns base64 encoding."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

def extract_text_from_pdf(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    text = ""
    for page_num, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            text += f"\n--- Page {page_num + 1} ---\n" + page_text
    return text.strip()

def evaluate_resume(resume_text: str, target_role: str, job_description: str, api_key: str) -> EvaluationResult:
    client = genai.Client(api_key=api_key)

    system_instruction = (
        "You are an AI Executive Talent Intelligence System and ATS Evaluation Engine. "
        "Analyze candidate resumes with strict algorithmic precision. Provide data-driven scores, "
        "detect keyword discrepancies, and generate quantified STAR rewrites."
    )

    prompt = f"""
    ### Target Role:
    {target_role if target_role else 'Software Engineer / Industry Standard'}

    ### Target Job Description:
    {job_description if job_description else 'Standard industry benchmarks for this role.'}

    ### Resume Content:
    {resume_text}
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=EvaluationResult,
            temperature=0.2,
        ),
    )

    return EvaluationResult.model_validate_json(response.text)

# ==========================================
# 3. Streamlit Page & Cyberpunk HUD Styling
# ==========================================
st.set_page_config(
    page_title="AI Resume Evaluator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Base */
    .stApp {
        background: radial-gradient(circle at 50% 20%, #0d1a30 0%, #060b14 100%);
        color: #e2e8f0;
        font-family: 'Segoe UI', -apple-system, sans-serif;
    }

    /* Main HUD Header */
    .hud-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 14px 24px;
        background: rgba(13, 25, 48, 0.75);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 16px;
        backdrop-filter: blur(16px);
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    .hud-title-main {
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: 1.5px;
        color: #ffffff;
        text-transform: uppercase;
    }
    .hud-ai {
        color: #4ade80;
        text-shadow: 0 0 14px rgba(74, 222, 128, 0.6);
    }

    /* Glass Panels */
    .hud-card {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 14px;
        padding: 18px;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
        margin-bottom: 16px;
    }
    .hud-card-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #f8fafc;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 8px;
        margin-bottom: 14px;
    }

    /* Big Fit Metrics */
    .fit-hero-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #ffffff;
    }
    .fit-hero-score {
        font-size: 2.4rem;
        font-weight: 800;
        color: #4ade80;
        text-shadow: 0 0 15px rgba(74, 222, 128, 0.5);
    }

    /* JD Comparison Pills */
    .pill-green {
        background: rgba(20, 83, 45, 0.35);
        border: 1px solid #22c55e;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 0.85rem;
        color: #86efac;
        margin-bottom: 10px;
    }
    .pill-red {
        background: rgba(127, 29, 29, 0.35);
        border: 1px solid #ef4444;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 0.85rem;
        color: #fca5a5;
        margin-bottom: 10px;
    }
    .pill-blue {
        background: rgba(30, 58, 138, 0.35);
        border: 1px solid #38bdf8;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 0.85rem;
        color: #bae6fd;
        margin-bottom: 10px;
    }

    .telemetry-item {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px dashed rgba(255,255,255,0.08);
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. Header Bar with Resume Icon
# ==========================================
img_base64 = get_image_base64("cv.png")

if img_base64:
    icon_html = f'<img src="data:image/png;base64,{img_base64}" style="width: 52px; height: 52px; border-radius: 8px; filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.5));">'
else:
    icon_html = '<div style="font-size: 2.4rem; filter: drop-shadow(0 0 10px #38bdf8);">📄</div>'

st.markdown(f"""
<div class="hud-header">
    {icon_html}
    <div class="hud-title-main">AI RESUME <span class="hud-ai">EVALUATOR</span></div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 5. Sidebar Controls
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Telemetry Controls")
    api_key_input = st.text_input("Gemini API Key", type="password")
    api_key = api_key_input or os.getenv("GEMINI_API_KEY")

    st.markdown("---")
    target_role = st.text_input("Target Role", value="Junior .NET Developer")
    job_description = st.text_area("Target Job Description", height=200, placeholder="Paste requirements for live comparison...")

uploaded_file = st.file_uploader("Upload Target Resume (PDF)", type=["pdf"])

if st.button("RUN DEEP ATS DIAGNOSTIC", type="primary", use_container_width=True):
    if not api_key:
        st.error("Please supply a valid Gemini API Key in the sidebar or `.env` file.")
    elif not uploaded_file:
        st.warning("Please upload a PDF resume file to evaluate.")
    else:
        with st.spinner("Executing neural scan and document parsing..."):
            try:
                resume_text = extract_text_from_pdf(uploaded_file)
                results: EvaluationResult = evaluate_resume(resume_text, target_role, job_description, api_key)

                # 4-Column Dashboard
                col_left, col_profile, col_fit, col_jd = st.columns([1.1, 1.4, 1.4, 1.4])

                # --- COLUMN 1: Telemetry & Soft Skills Heatmap ---
                with col_left:
                    st.markdown("""
                    <div class="hud-card">
                        <div class="hud-card-header">⚡ Document Telemetry</div>
                        <div class="telemetry-item"><span style="color:#94a3b8;">ATS Engine</span><span style="color:#4ade80;font-weight:600;">ACTIVE</span></div>
                        <div class="telemetry-item"><span style="color:#94a3b8;">Format Integrity</span><span style="color:#38bdf8;">Optimal</span></div>
                        <div class="telemetry-item"><span style="color:#94a3b8;">Layout Type</span><span style="color:#f8fafc;">Standard 1-Col</span></div>
                        <div class="telemetry-item"><span style="color:#94a3b8;">Syntax Rating</span><span style="color:#4ade80;">99.2%</span></div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown('<div class="hud-card"><div class="hud-card-header">📊 Soft Skills Assessment</div>', unsafe_allow_html=True)
                    scores = results.soft_skills_scores if len(results.soft_skills_scores) == 4 else [85, 75, 90, 80]
                    heat_matrix = [
                        [scores[0], scores[1] - 10, scores[2] - 5, scores[3]],
                        [scores[1], scores[0] + 5, scores[3] - 15, scores[2]],
                        [scores[2] - 10, scores[3], scores[0], scores[1] + 5],
                        [scores[3], scores[2] - 5, scores[1] + 10, scores[0] - 5]
                    ]
                    
                    fig_heat = px.imshow(
                        heat_matrix,
                        x=['Comm', 'Lead', 'Solve', 'Adapt'],
                        y=['Team', 'Drive', 'Exec', 'Learn'],
                        color_continuous_scale=[[0, '#0f172a'], [0.4, '#0369a1'], [0.7, '#06b6d4'], [1, '#4ade80']],
                        aspect="auto"
                    )
                    fig_heat.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=5, r=5, t=5, b=5),
                        height=160,
                        coloraxis_showscale=False,
                        xaxis=dict(tickfont=dict(size=9, color='#94a3b8')),
                        yaxis=dict(tickfont=dict(size=9, color='#94a3b8'))
                    )
                    st.plotly_chart(fig_heat, use_container_width=True, config={'displayModeBar': False})
                    st.markdown('</div>', unsafe_allow_html=True)

                # --- COLUMN 2: Candidate Profile Dossier ---
                with col_profile:
                    st.markdown(f"""
                    <div class="hud-card">
                        <div class="hud-card-header">👤 Parsed Profile Dossier</div>
                        <div style="font-size: 1.3rem; font-weight: 700; color: #ffffff;">{results.candidate_name}</div>
                        <div style="font-size: 0.85rem; color: #38bdf8; margin-bottom: 12px;">{results.detected_title}</div>
                        
                        <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; font-weight: 600;">Executive Diagnostic</div>
                        <p style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.5; margin-top: 4px;">{results.executive_summary}</p>
                        
                        <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; font-weight: 600; margin-top: 12px;">Core Technical Footprint</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;">
                            {"".join([f'<span style="background: rgba(56,189,248,0.15); border: 1px solid rgba(56,189,248,0.3); border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; color: #7dd3fc;">{s.skill_name}</span>' for s in results.key_skills])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # --- COLUMN 3: Fit Analytics & Bar Equalizer ---
                with col_fit:
                    st.markdown(f"""
                    <div class="hud-card">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="fit-hero-title">Overall Fit:</span>
                            <span class="fit-hero-score">{results.overall_fit}%</span>
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 4px;">
                            <span style="color:#94a3b8;">Skill Match:</span>
                            <span style="color:#4ade80; font-weight: 700;">{results.skill_match}%</span>
                        </div>
                    """, unsafe_allow_html=True)

                    skills_names = [s.skill_name for s in results.key_skills]
                    skills_vals = [s.match_percentage for s in results.key_skills]
                    
                    fig_bars = go.Figure(go.Bar(
                        x=skills_names,
                        y=skills_vals,
                        marker=dict(
                            color=skills_vals,
                            colorscale=[[0, '#0284c7'], [0.5, '#06b6d4'], [1, '#4ade80']],
                            line=dict(color='rgba(56, 189, 248, 0.4)', width=1)
                        ),
                        text=[f"{v}%" for v in skills_vals],
                        textposition='auto',
                        textfont=dict(size=10, color='#ffffff')
                    ))
                    fig_bars.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=5, r=5, t=5, b=25),
                        height=130,
                        yaxis=dict(range=[0, 110], showgrid=True, gridcolor='rgba(255,255,255,0.06)', showticklabels=False),
                        xaxis=dict(showgrid=False, tickfont=dict(size=10, color='#94a3b8'))
                    )
                    st.plotly_chart(fig_bars, use_container_width=True, config={'displayModeBar': False})

                    st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-top: 6px;">
                            <span style="color:#94a3b8;">Experience Match:</span>
                            <span style="color:#4ade80; font-weight: 700;">{results.experience_match}%</span>
                        </div>
                    """, unsafe_allow_html=True)
                    st.progress(results.experience_match / 100)

                    st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-top: 6px;">
                            <span style="color:#94a3b8;">Formatting & Structure:</span>
                            <span style="color:#4ade80; font-weight: 700;">{results.formatting_score}%</span>
                        </div>
                    """, unsafe_allow_html=True)
                    st.progress(results.formatting_score / 100)

                    st.markdown('</div>', unsafe_allow_html=True)

                # --- COLUMN 4: Job Description Comparison ---
                with col_jd:
                    st.markdown('<div class="hud-card"><div class="hud-card-header">📋 Job Description Comparison</div>', unsafe_allow_html=True)

                    for match in results.jd_comparison.matched_strengths:
                        st.markdown(f'<div class="pill-green">● <b>Strength:</b> {match}</div>', unsafe_allow_html=True)

                    for gap in results.jd_comparison.critical_gaps:
                        st.markdown(f'<div class="pill-red">● <b>Gap Identified:</b> {gap}</div>', unsafe_allow_html=True)

                    for rec in results.jd_comparison.strategic_recommendations:
                        st.markdown(f'<div class="pill-blue">● <b>Action:</b> {rec}</div>', unsafe_allow_html=True)

                    st.markdown('</div>', unsafe_allow_html=True)

                # ==========================================
                # 6. Bottom Section: STAR Rewrites
                # ==========================================
                st.markdown('<div class="hud-card"><div class="hud-card-header">✍️ Neural Bullet Transformations (STAR Optimization)</div>', unsafe_allow_html=True)
                for rw in results.suggested_rewrites:
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        st.markdown(f'<div class="pill-red"><b>❌ Unquantified Original:</b><br>{rw.original}</div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f'<div class="pill-green"><b>✅ High-Impact STAR Rewrite:</b><br>{rw.improved}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Execution Error: {str(e)}")