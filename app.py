from flask import Flask, render_template, request, redirect, jsonify
import speech_recognition as sr
import os
from markdown import markdown
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
app = Flask(__name__)
# 設定上傳的資料夾路徑
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
openai_model = 'whisper-1'
gemini_model = 'gemini-1.5-pro-latest'

# 檢查是否有資料夾，沒有則建立
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def speech_to_text(audio_file):
    '''
    Args:
        audio_file (BufferedReader)

    Returns:
        Transcription (str)
    '''
    try:
        openai_client = OpenAI(api_key=os.getenv('openai_api_key'))
        transcription = openai_client.audio.transcriptions.create(
            model=openai_model,
            file=audio_file,
            response_format = 'text'
        )
    except:
        return 'Failed to connect to the API　server'

    return transcription

def summary(transcription:str)->str:
    client = None
    api_base_url = os.getenv('gemini_api_url')
    api_key = os.getenv('gemini_api_key')

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=api_base_url,
        )
        completion = client.chat.completions.create(
            model = gemini_model,
            messages=[
                {"role": "user", "content": f"{transcription}"}
            ],
            temperature=0.2,
            n=1
        )
    except:
        return 'Failed to connect to the Whisper API'

    return completion.choices[0].message.content


@app.route("/", methods=["GET", "POST"])
def index():
    transcription = ""
    # summary = ""
    html_content = ""
    if request.method == "POST":
        print("FORM DATA RECEIVED")

        if "file" not in request.files:
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        if file:
            audio_file= open(file_path, "rb")
            transcription = speech_to_text(audio_file)

            if transcription:
                msg = summary(transcription)
                html_content = markdown(msg)

    return render_template('index.html', transcript=transcription, summary=html_content)

@app.route('/autoUpload', methods=['POST'])
def upload_audio():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    audio_file = request.files['audio_file']
    
    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # 設定儲存路徑
    upload_folder = 'uploads'
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    # 儲存檔案
    file_path = os.path.join(upload_folder, audio_file.filename)
    audio_file.save(file_path)
    
    return jsonify({'message': 'File uploaded successfully', 
                   'file_path': file_path}), 200


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
