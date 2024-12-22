from flask import Flask, request, render_template, redirect, url_for, session
from transformers import pipeline
import os
import re

app = Flask(__name__)
app.secret_key = 'secret_key'  # For managing sessions
UPLOAD_FOLDER = './knowledge_base'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Load QA model
qa_pipeline = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")

# Simple login system
users = {
    "admin": "admin123",  # Admin credentials
    "user": "user123"     # User credentials
}

# Login Page
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None  # Initialize an error variable
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate credentials
        if username in users and users[username] == password:
            session['username'] = username
            if username == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            error = "Invalid credentials. Please try again."  # Set the error message

    return render_template('login.html', error=error)  # Pass the error to the template

# Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Admin Dashboard
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))

    message = None  # Initialize a variable for success or error messages

    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith(('.txt', '.docx')):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            message = "File uploaded successfully!"  # Success message
        else:
            message = "Invalid file type. Please upload a .txt or .docx file."

    # Get the list of existing files
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('admin.html', files=files, message=message)

# Delete File (Admin)
@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        message = f"File '{filename}' deleted successfully!"
    else:
        message = f"File '{filename}' not found."

    # Refresh the admin page with updated file list and message
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('admin.html', files=files, message=message)


# User Dashboard
@app.route('/user')
def user_dashboard():
    if 'username' not in session or session['username'] != 'user':
        return redirect(url_for('login'))

    return render_template('user.html')

# Ask Questions (User)
@app.route('/ask', methods=['POST'])
def ask_question():
    question = request.form.get('question')
    kb_files = os.listdir(app.config['UPLOAD_FOLDER'])
    if not kb_files:
        return "Knowledge base is empty. Please ask the admin to upload a file first."

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

    try:
        # Limit the context size if too large
        if len(context) > 3000:
            context = context[:3000]

        # Generate the answer using the pipeline
        result = qa_pipeline(question=question, context=context)

        if result['score'] < 0.1:  # Low-confidence answer
            return "Sorry, I couldn't find a confident answer to your question. Please try rephrasing it."
        return result['answer']
    except Exception as e:
        return "An error occurred while processing your request. Please try again."

if __name__ == '__main__':
    app.run(debug=True)
