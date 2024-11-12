from groq import Groq
from openai import OpenAI
import os

gemini_model = 'gemini-1.5-pro-latest'


def test_groq_whisper():
    client = Groq(api_key=os.getenv('groq_api_key'))
    path = r'.\uploads\tmpchunk\6bd6bd5d-0234-459e-ac62-d095f88e6c96_chunk0.mp3'

    with open(path, "rb") as file:
        client = Groq(api_key=os.getenv('groq_api_key'))
        transcription = client.audio.transcriptions.create(
            file=(path, file.read()),
            model="whisper-large-v3",
            language="zh",
            response_format="verbose_json",
            # response_format="json",
            prompt="這裡要轉成的是繁體中文。",
        )

    # print(transcription)

    segments = transcription.segments

    print(segments)

def test_gemini_whisper():
    path = r'.\uploads\sample.mp3'
    client = OpenAI(
            api_key=os.getenv('gemini_api_key'),
            base_url=os.getenv('gemini_api_url')
        )


    with open(path, "rb") as file:
        client = Groq(api_key=os.getenv('groq_api_key'))
        transcription = client.audio.transcriptions.create(
            file=(path, file.read()),
            model="whisper-large-v3",
            language="zh",
            response_format="verbose_json",
            # response_format="json",
            prompt="這裡要轉成的是繁體中文。",
        )

    print(transcription.text)

def test_gemini():
    transcription = '幫我介紹深度學習，五十個字以內'
    try:
        client = OpenAI(
            api_key=os.getenv('gemini_api_key'),
            base_url=os.getenv('gemini_api_url')
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
        
        print(completion.choices[0].message)
        print(10*'-')
        print(completion.choices[0].message.content)
    except:
        print('Failed to connect to the Whisper API')
 

if __name__=='__main__':
    # test_gemini()
    # test_gemini()
    test_gemini_whisper()
    