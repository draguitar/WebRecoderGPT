from openai import OpenAI
import os

openai_model = 'whisper-1'
gemini_model = 'gemini-1.5-pro-latest'

def speech_to_text(audio_file)->str:
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