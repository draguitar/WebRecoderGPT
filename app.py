from flask import Flask, render_template, request, redirect, jsonify, send_from_directory
from flask import session
from flask_session import Session
import os
from markdown import markdown
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, AudioFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
import math
import re


load_dotenv(override=True)
app = Flask(__name__)
# 設定上傳的資料夾路徑
UPLOAD_FOLDER = 'uploads/'
TMP_FOLDER = os.path.join(UPLOAD_FOLDER, 'tmpchunk')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TMP_FOLDER'] = TMP_FOLDER
app.config['SECRET_KEY'] = "ASECL"
app.config['SESSION_TYPE'] = "filesystem"

openai_model = 'whisper-1'
gemini_model = 'gemini-1.5-pro-latest'

# 23MB 上限
max_chunk_size = 2 * 1024 * 1024  

Session(app)

# 檢查是否有資料夾，沒有則建立
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(TMP_FOLDER):
    os.makedirs(TMP_FOLDER)


def split_audio(video_path, start_time, end_time, chunk_filename_path):
    '''
    分割儲存音訊檔
    Args:
        原始檔案路徑
        開始時間
        結束時間
        切割後路徑檔名
    '''
    ffmpeg_extract_subclip(video_path, start_time, end_time, targetname=chunk_filename_path)


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
                {"role": "system", "content": "使用繁體中文回覆問題"},
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
    session_id = session.sid
    # session_id = session['session_id']
    print("SESSION ID >>" + session_id)
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

    return render_template('index2.html', transcript=transcription, summary=html_content, session_id=session_id)

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

    # 取得音訊長度（秒）
    with AudioFileClip(file_path) as audio:
        audio_duration = audio.duration  
    
    file_size = os.path.getsize(file_path)
    print(audio_duration)

    # 計算需要分割的片段數量
    num_chunks = math.ceil(file_size / max_chunk_size)

    # 每段的時間長度
    chunk_duration = audio_duration / num_chunks

    combined_text = ''
    formatted_text = ''

    for i in range(num_chunks):
        start_time = int(i * chunk_duration)
        end_time = int((i + 1) * chunk_duration)
        chunk_filename = f"{audio_file.filename[:-4]}_chunk{i}.mp3"
        chunk_file_path = os.path.join(app.config['TMP_FOLDER'], chunk_filename)

        split_audio(file_path, start_time, end_time, chunk_file_path)

        with open(chunk_file_path, "rb") as file:
            client = Groq(api_key=os.getenv('groq_api_key'))
            transcription = client.audio.transcriptions.create(
                file=(chunk_file_path, file.read()),
                model="whisper-large-v3",
                # language="zh",
                # response_format="verbose_json",
                response_format="json",
                prompt="這裡要轉成的是繁體中文。",
            )
            combined_text += transcription.text + "\n\n"
            
    formatted_text = re.sub(r'([。！？])', r'\1\n', combined_text)

    transcription_pth = os.path.join(app.config['TMP_FOLDER'], f'{audio_file.filename[:-4]}.txt')
    with open(transcription_pth, 'w', encoding='utf=8') as output_file:
        output_file.write(formatted_text)

    meeting_summary = summary(formatted_text)
    print(meeting_summary)

    return jsonify({'message': 'File uploaded successfully', 
                   'file_path': file_path,
                   'download_url':f'/download/{session.sid}',
                   'summary':markdown(meeting_summary)
                   }), 200

@app.route('/download/<sessiod_id>', methods=['GET'])
def downloadtranscription(sessiod_id):
    return send_from_directory(app.config['TMP_FOLDER'], path=f'{sessiod_id}.txt', as_attachment=True)



if __name__ == "__main__":
    app.run(debug=True, threaded=True)
