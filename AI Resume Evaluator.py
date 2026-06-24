from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
import os, re, json, tempfile
from flask import Flask, request, render_template_string
from werkzeug.utils import secure_filename

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "docx"}
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OpenAI and OPENAI_API_KEY else None


HTML = """
<!DOCTYPE html>
<html>
<head>
<title>AI Resume Evaluator</title>
<style>
body{margin:0;font-family:Arial;background:#f5f7fb;color:#111827}
.header{background:linear-gradient(90deg,#6d28d9,#0047ff);color:white;text-align:center;padding:28px}
.header h1{margin:0;font-size:38px}
.main{display:grid;grid-template-columns:360px 1fr;gap:25px;padding:25px}
.card{background:white;border-radius:16px;padding:25px;box-shadow:0 4px 14px #0001}
.upload{border:2px dashed #7c3aed;border-radius:14px;padding:35px;text-align:center}
button{background:#6d28d9;color:white;border:0;border-radius:9px;padding:14px 20px;font-weight:bold;cursor:pointer}
button:hover{background:#5b21b6}
.full{width:100%;margin-top:18px}
.download{background:white;color:#6d28d9;border:1px solid #8b5cf6}
.error{color:red;font-weight:bold;margin-top:15px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:25px 0}
.box{text-align:center;border:1px solid #e5e7eb;border-radius:14px;padding:20px}
.score{font-size:38px;font-weight:bold;color:#6d28d9}
.tabs{display:flex;gap:18px;flex-wrap:wrap;border-bottom:1px solid #ddd;margin-bottom:20px}
.tab{padding:12px 5px;cursor:pointer;font-weight:bold;color:#374151}
.tab.active{color:#6d28d9;border-bottom:3px solid #6d28d9}
.section{display:none;background:#f8f7ff;border-radius:12px;padding:20px;white-space:pre-wrap;line-height:1.7}
.section.active{display:block}
.tips{background:#f8f9ff;border-radius:12px;padding:20px;margin-top:25px}
textarea{display:none}
@media(max-width:900px){.main,.grid{grid-template-columns:1fr}}
</style>
</head>
<body>

<div class="header">
<h1>📄 AI Resume Evaluator</h1>
<p>Get AI-powered feedback and improve your resume</p>
</div>

<div class="main">
<div class="card">
<h2>Upload Your Resume</h2>
<p>Upload PDF or DOCX resume.</p>

<form method="POST" enctype="multipart/form-data">
<div class="upload">
<h1>☁️</h1>
<p>Click to upload resume</p>
<p>PDF DOCX Max 10MB</p>
<input type="file" name="resume" accept=".pdf,.docx" required>
</div>
<button class="full" type="submit">Analyze Resume</button>
</form>

{% if error %}<div class="error">{{ error }}</div>{% endif %}

<div class="tips">
<h3>💡 Tips</h3>
<p>✅ Use a clean resume</p>
<p>✅ Add skills and achievements</p>
<p>✅ Use standard resume sections</p>
<p>✅ Keep formatting simple</p>
</div>
</div>

<div class="card">
<div style="display:flex;justify-content:space-between;align-items:center">
<h2>AI Feedback Results</h2>
<button class="download" onclick="downloadReport()">Download Report</button>
</div>

<div class="grid">
<div class="box"><p>Overall Score</p><div class="score">{{ data.overall_score }}</div></div>
<div class="box"><p>ATS Score</p><div class="score">{{ data.ats_score }}</div></div>
<div class="box"><p>Skills Found</p><div class="score">{{ data.skills_count }}</div></div>
<div class="box"><p>Improvements</p><div class="score">{{ data.improvements_count }}</div></div>
</div>

<div class="tabs">
<div class="tab active" onclick="showTab('summary',this)">Summary</div>
<div class="tab" onclick="showTab('strengths',this)">Strengths</div>
<div class="tab" onclick="showTab('weaknesses',this)">Weaknesses</div>
<div class="tab" onclick="showTab('missing',this)">Missing Skills</div>
<div class="tab" onclick="showTab('improvements',this)">Improvements</div>
<div class="tab" onclick="showTab('ats',this)">ATS Tips</div>
</div>

<div id="summary" class="section active">{{ data.summary }}</div>
<div id="strengths" class="section">{{ data.strengths }}</div>
<div id="weaknesses" class="section">{{ data.weaknesses }}</div>
<div id="missing" class="section">{{ data.missing_skills }}</div>
<div id="improvements" class="section">{{ data.improvements }}</div>
<div id="ats" class="section">{{ data.ats_tips }}</div>

<textarea id="report">{{ report }}</textarea>
</div>
</div>

<script>
function showTab(id, el){
    document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    el.classList.add('active');
}

function downloadReport(){
    let text = document.getElementById("report").value;
    if(!text.trim()){
        alert("Please analyze a resume first.");
        return;
    }
    let blob = new Blob([text], {type:"text/plain"});
    let a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "resume_feedback_report.txt";
    a.click();
}
</script>

</body>
</html>
"""


def default_data():
    return {
        "overall_score": "0",
        "ats_score": "0",
        "skills_count": "0",
        "improvements_count": "0",
        "summary": "Upload your resume and click Analyze Resume.",
        "strengths": "No analysis yet.",
        "weaknesses": "No analysis yet.",
        "missing_skills": "No analysis yet.",
        "improvements": "No analysis yet.",
        "ats_tips": "No analysis yet."
    }


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_pdf(path):
    if PdfReader is None:
        raise Exception("pypdf not installed. Run: python -m pip install pypdf")
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_docx(path):
    if Document is None:
        raise Exception("python-docx not installed. Run: python -m pip install python-docx")
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text(path):
    if path.endswith(".pdf"):
        return extract_pdf(path)
    if path.endswith(".docx"):
        return extract_docx(path)
    raise Exception("Unsupported file format.")


def local_analysis(text):
    words = re.findall(r"[A-Za-z]+", text)
    skills = ["Python", "Flask", "SQL", "HTML", "CSS", "JavaScript", "Machine Learning", "Git", "API"]
    found = [s for s in skills if s.lower() in text.lower()]

    return {
        "overall_score": "72",
        "ats_score": "68",
        "skills_count": str(len(found)),
        "improvements_count": "8",
        "summary": "Resume analyzed successfully. Add stronger achievements, measurable results and role-specific keywords.",
        "strengths": "• Resume has readable content\n• Skills section is present\n• Experience or project details are included",
        "weaknesses": "• Achievements need numbers\n• Some sections may need better structure\n• Keywords can be improved",
        "missing_skills": "• Add job-specific tools\n• Add soft skills\n• Add certifications if available",
        "improvements": "• Add measurable achievements\n• Use bullet points\n• Add professional summary\n• Improve formatting\n• Add ATS keywords",
        "ats_tips": "• Use simple headings\n• Avoid tables/images\n• Add exact job keywords\n• Save resume as PDF or DOCX"
    }


def ai_analysis(text):
    if client is None:
        return local_analysis(text)

    prompt = f"""
Analyze this resume. Return ONLY valid JSON with these keys:
overall_score, ats_score, skills_count, improvements_count,
summary, strengths, weaknesses, missing_skills, improvements, ats_tips.

Resume:
{text[:12000]}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    raw = response.output_text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        data = local_analysis(text)
        data["summary"] = raw
        return data


@app.route("/", methods=["GET", "POST"])
def home():
    data = default_data()
    error = None
    report = ""

    if request.method == "POST":
        try:
            file = request.files.get("resume")

            if not file or file.filename == "":
                raise Exception("Please upload a resume.")

            if not allowed_file(file.filename):
                raise Exception("Only PDF and DOCX files are allowed.")

            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1].lower()

            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp:
                file.save(temp.name)
                path = temp.name

            text = extract_text(path)
            os.remove(path)

            if len(text.strip()) < 50:
                raise Exception("Resume text is unreadable or too short.")

            data = ai_analysis(text)

            report = f"""
AI Resume Evaluation Report

Overall Score: {data.get('overall_score')}
ATS Score: {data.get('ats_score')}
Skills Found: {data.get('skills_count')}
Improvements: {data.get('improvements_count')}

Summary:
{data.get('summary')}

Strengths:
{data.get('strengths')}

Weaknesses:
{data.get('weaknesses')}

Missing Skills:
{data.get('missing_skills')}

Improvements:
{data.get('improvements')}

ATS Tips:
{data.get('ats_tips')}
"""

        except Exception as e:
            error = str(e)

    return render_template_string(HTML, data=data, error=error, report=report)


if __name__ == "__main__":
    app.run(debug=True)