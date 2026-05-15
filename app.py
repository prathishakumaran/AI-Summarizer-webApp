from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
import fitz  # PyMuPDF
from dotenv import load_dotenv
import os
import re
def extract_video_id(url):
    # Supports standard, shortened, and embed URLs
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

load_dotenv()
api = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = ""
    if request.method == "POST":
        mode = request.form.get("mode")

        try:
            if mode == "text":
                text = request.form.get("text_input", "").strip()
                if not text:
                    error = "Please enter some text."
                else:
                    summary = get_summary(f"Summarize the following text:\n{text}")

            elif mode == "pdf":
                if 'pdf_file' not in request.files or request.files['pdf_file'].filename == '':
                    error = "Please upload a PDF file."
                else:
                    file = request.files['pdf_file']
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                    file.save(file_path)

                    doc = fitz.open(file_path)
                    text = ""
                    for page in doc:
                        text += page.get_text()
                    summary = get_summary(f"Summarize the following PDF content:\n{text}")

            elif mode == "youtube":
                url = request.form.get("youtube_url", "").strip()
                if not url:
                    error = "Please enter a YouTube URL."
                else:
                    video_id = url.split("v=")[-1]  # Extract the actual video ID
                    transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                    try:
                        transcript = transcripts.find_manually_created()
                    except:
                        transcript = transcripts.find_generated()
        
                    transcript_data = transcript.fetch()
                    text = " ".join([t["text"] for t in transcript_data])
                    summary = get_summary(f"Summarize this YouTube video transcript:\n{text}")
        except Exception as e:
            error = "An error occurred: " + str(e)

    return render_template("index.html", summary=summary, error=error)

def get_summary(prompt):
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes content."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300
    )
    return response.choices[0].message.content.strip()

if __name__ == '__main__':
    # Use SSL only if cert.pem and key.pem exist
    cert_file = "cert.pem"
    key_file = "key.pem"
    if os.path.exists(cert_file) and os.path.exists(key_file):
        app.run(debug=True, ssl_context=(cert_file, key_file))
    else:
        app.run(debug=True)
