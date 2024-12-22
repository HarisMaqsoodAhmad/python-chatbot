from flask import Flask, request, render_template
from transformers import pipeline
import os
import re

app = Flask(__name__)
UPLOAD_FOLDER = './knowledge_base'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Load QA model
qa_pipeline = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")

# Admin: Upload knowledge base
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith(('.txt', '.docx')):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            return "File uploaded successfully."
        return "Invalid file type. Please upload a .txt or .docx file."
    return render_template('upload.html')

# User: Ask questions
@app.route('/ask', methods=['POST'])
def ask_question():
    question = request.form.get('question')
    kb_files = os.listdir(app.config['UPLOAD_FOLDER'])
    if not kb_files:
        return "Knowledge base is empty. Please upload a file first."

    # Load and clean knowledge base content
    kb_path = os.path.join(app.config['UPLOAD_FOLDER'], kb_files[0])
    if kb_path.endswith('.docx'):
        from docx import Document
        doc = Document(kb_path)
        context = " ".join([p.text for p in doc.paragraphs])
    else:
        with open(kb_path, 'r') as kb_file:
            context = kb_file.read()

    # Clean context by removing section headers (e.g., ### General Knowledge ###)
    context = re.sub(r'###.*?###', '', context).strip()

    # Clean context by removing URLs
    try:
        # Limit the context size if too large
        if len(context) > 3000:
            context = context[:3000]  # Adjust as needed
            
        # Generate the answer using the pipeline
        result = qa_pipeline(question=question, context=context)

        if result['score'] < 0.1:  # Low-confidence answer
            return "Sorry, I couldn't find a confident answer to your question. Please try rephrasing it."
        return result['answer']
    except Exception as e:
        # Handle errors gracefully
        return "An error occurred while processing your request. Please try again."

# Web interface
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
