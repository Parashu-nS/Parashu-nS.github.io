import os
from flask import Flask, render_template, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
import pytesseract
from pdf2image import convert_from_path
from openai import OpenAI

app = Flask(__name__)

# Set up the uploads folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

# Configure OpenAI API
OPENAI_API_KEY = ""

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    try:
        # Convert PDF to images
        pages = convert_from_path(pdf_path)

        extracted_text = ''
        for page in pages:
            # Perform OCR on each page image
            text = pytesseract.image_to_string(page)
            extracted_text += text + '\n'
        return extracted_text
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Home route for uploading files and providing API key
@app.route('/', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        # Collect API key from the user
        api_key = request.form['api_key']
        if not api_key:
            return render_template('index.html', error="API Key is required")
        
        # Check if the post request has the file parts
        if 'requirement_file' not in request.files or 'std_file' not in request.files or 'result_format_file' not in request.files:
            return render_template('index.html', error="Please upload all files")
        
        requirement_file = request.files['requirement_file']
        std_file = request.files['std_file']
        result_format_file = request.files['result_format_file']
        
        # If the files are not allowed, return an error
        if not allowed_file(requirement_file.filename) or not allowed_file(std_file.filename) or not allowed_file(result_format_file.filename):
            return render_template('index.html', error="Only PDF and text files are allowed")
        
        # Save the uploaded files to the uploads folder
        requirement_filename = secure_filename(requirement_file.filename)
        std_filename = secure_filename(std_file.filename)
        result_format_filename = secure_filename(result_format_file.filename)
        requirement_file.save(os.path.join(UPLOAD_FOLDER, requirement_filename))
        std_file.save(os.path.join(UPLOAD_FOLDER, std_filename))
        result_format_file.save(os.path.join(UPLOAD_FOLDER, result_format_filename))
        
        # Prompt for OpenAI API input
        requirement_text = extract_text_from_pdf(os.path.join(UPLOAD_FOLDER, requirement_filename))
        std_text = extract_text_from_pdf(os.path.join(UPLOAD_FOLDER, std_filename))
        with open(os.path.join(UPLOAD_FOLDER, result_format_filename), 'r') as f:
            result_format = f.read().strip()
        prompt = f"I want output exactly in the reference format:{result_format}.Task is about the Gate Valve specifications comparison between customers reuest and STD availabality in company. For this task compare the TWO Data Sets, Requirements_dataSet and Standards_dataSet. Requirements_dataSet is:{requirement_text}. Standards_dataSet is:{std_text}."
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        # Generate Spec Deviation report
        completion = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Specification Deviation Report"},
                {"role": "user", "content": prompt}
            ]
        )
        api_output = completion.choices[0].message.content
        
        # Save the API output to a text file
        output_filepath = os.path.join(UPLOAD_FOLDER, 'output.txt')
        with open(output_filepath, 'w',encoding='utf-8') as f:
            f.write(api_output)
        
        return render_template('result.html', api_output=api_output)
    
    return render_template('index.html')

# Route to download the output file
@app.route('/download')
def download_output():
    return send_file(os.path.join(UPLOAD_FOLDER, 'output.txt'), as_attachment=True)

if __name__ == '__main__':
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.run(debug=True)
