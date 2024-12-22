from flask import Flask, request, render_template
from transformers import pipeline
import os

app = Flask(__name__)
UPLOAD_FOLDER = './knowledge_base'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
            return "File uploaded successfully"
        return "Invalid file type. Upload a .txt or .docx file."
    return '''
    <!DOCTYPE html>
    <html>
    <body>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file">
        <button type="submit">Upload</button>
    </form>
    </body>
    </html>
    '''

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

    # Remove section headers (e.g., ### General Knowledge ###)
    import re
    context = re.sub(r'###.*?###', '', context).strip()

    # Use LLM for answering
    try:
        # Limit the context size if too large
        if len(context) > 3000:
            context = context[:3000]
        
        result = qa_pipeline(question=question, context=context)
        print(result)
        if result['score'] < 0.1:  # If confidence is low
            return "I'm not confident about the answer. Try rephrasing your question."
        return result['answer']
    except Exception as e:
        return "Sorry, I couldn't find an answer. Error: " + str(e)

# Web interface
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
