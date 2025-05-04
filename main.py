from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import easyocr
import pytesseract
from PIL import Image
import io
import requests
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv
import urllib.parse
from pdf2image import convert_from_bytes
import re
from pydantic import BaseModel
import uuid
load_dotenv()

app = FastAPI(title="Persian OCR API")

# تنظیمات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تنظیم مسیر Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# تنظیم زبان فارسی برای Tesseract
custom_config = r'--oem 3 --psm 6 -l fas'

# ایجاد خواننده EasyOCR برای فارسی
reader = easyocr.Reader(['fa'])

@app.post("/ocr")
async def process_image(image_url: str):
    try:
        if image_url.startswith('file://'):
            file_path = urllib.parse.unquote(image_url[7:])
            print(f"Processing local file: {file_path}")
            
            if not os.path.exists(file_path):
                raise HTTPException(status_code=400, detail=f"File not found at path: {file_path}")
            
            with open(file_path, 'rb') as file:
                content = file.read()
        else:
            response = requests.get(image_url)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to download image")
            content = response.content

        if image_url.lower().endswith('.pdf'):
            text = process_pdf_text(content)
        else:
            text = process_image_content_text(content)
            
        return {"text": text}
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        
        # تشخیص نوع فایل بر اساس نام
        if file.filename.lower().endswith('.pdf'):
            # پردازش PDF
            pdf_text = process_pdf_text(content)
            return {"text": pdf_text}
        else:
            # پردازش تصویر
            image_text = process_image_content_text(content)
            return {"text": image_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ocr-json")
async def process_image_json(image_url: str):
    try:
        if image_url.startswith('file://'):
            file_path = urllib.parse.unquote(image_url[7:])
            print(f"Processing local file: {file_path}")
            
            if not os.path.exists(file_path):
                raise HTTPException(status_code=400, detail=f"File not found at path: {file_path}")
            
            with open(file_path, 'rb') as file:
                content = file.read()
        else:
            response = requests.get(image_url)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to download image")
            content = response.content

        if image_url.lower().endswith('.pdf'):
            text = process_pdf_text(content)
        else:
            text = process_image_content_text(content)
            
        # تبدیل متن به JSON
        result = parse_multiple_choice(text)
        return result
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def clean_text(text):
    """پاکسازی و نرمال‌سازی متن"""
    # حذف فاصله‌های اضافی
    text = re.sub(r'\s+', ' ', text)
    # تبدیل اعداد فارسی به انگلیسی
    persian_numbers = '۰۱۲۳۴۵۶۷۸۹'
    english_numbers = '0123456789'
    translation_table = str.maketrans(persian_numbers, english_numbers)
    text = text.translate(translation_table)
    return text.strip()

def parse_multiple_choice(text):
    """تبدیل متن سوال چند گزینه‌ای به فرمت JSON"""
    questions = []
    current_question = None
    current_choices = {}
    question_number = None
    question_score = None
    
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = clean_text(lines[i])
        if not line:
            i += 1
            continue
            
        # تشخیص شروع سوال جدید با شماره
        if line[0].isdigit():
            # اگر سوال قبلی وجود دارد، آن را به لیست اضافه کن
            if current_question:
                questions.append({
                    "question_number": int(question_number) if question_number else None,
                    "score": question_score,
                    "question_text": current_question,
                    "choices": current_choices
                })
            
            # استخراج شماره سوال
            question_number = re.match(r'(\d+)', line).group(1)
            
            # جستجوی نمره در خط فعلی
            score_match = re.search(r'[(\-](\d+(?:[/.]\d+)?)\s*(?:نمره)?[)\-]', line)
            if score_match:
                score_text = score_match.group(1).replace('/', '.')
                try:
                    question_score = float(score_text)
                except ValueError:
                    question_score = None
            else:
                question_score = None
            
            # حذف شماره سوال و نمره از متن سوال و پاکسازی
            current_question = re.sub(r'^\d+[\-\.]?\s*(?:\(\d+(?:[/.]\d+)?\s*(?:نمره)?\))?\s*', '', line)
            current_choices = {}
            i += 1
            
            # خواندن ادامه متن سوال در خطوط بعدی
            while i < len(lines) and lines[i].strip() and not any(clean_text(lines[i]).startswith(prefix) for prefix in 
                ['الف', 'ب', 'پ', 'ت', 'ج', 'د', 'a', 'b', 'c', 'd', 'A', 'B', 'C', 'D',
                 '۱', '۲', '۳', '۴', '1', '2', '3', '4']):
                current_question += " " + clean_text(lines[i])
                i += 1
                
        # تشخیص گزینه‌ها
        elif any(line.startswith(prefix) for prefix in 
                ['الف', 'ب', 'پ', 'ت', 'ج', 'د', 'a', 'b', 'c', 'd', 'A', 'B', 'C', 'D',
                 '۱', '۲', '۳', '۴', '1', '2', '3', '4']):
            
            # تشخیص حرف گزینه
            choice_letter = None
            if line.startswith(('الف', 'a', 'A', '۱', '1')):
                choice_letter = 'الف'
            elif line.startswith(('ب', 'b', 'B', '۲', '2')):
                choice_letter = 'ب'
            elif line.startswith(('پ', 'c', 'C', '۳', '3')):
                choice_letter = 'پ'
            elif line.startswith(('ت', 'd', 'D', '۴', '4')):
                choice_letter = 'ت'
            elif line.startswith('ج'):
                choice_letter = 'ج'
            elif line.startswith('د'):
                choice_letter = 'د'
                
            if choice_letter:
                # حذف علامت‌های اضافی از ابتدای گزینه و پاکسازی متن
                choice_text = re.sub(r'^[(\-\.\s]*(الف|ب|پ|ت|ج|د|[abcdABCD]|[۱۲۳۴1234])[)\-\.\s]*', '', line)
                current_choices[choice_letter] = clean_text(choice_text)
            i += 1
        else:
            i += 1
    
    # اضافه کردن آخرین سوال
    if current_question:
        questions.append({
            "question_number": int(question_number) if question_number else None,
            "score": question_score,
            "question_text": current_question,
            "choices": current_choices
        })
    
    return {
        "type": "multiple_choice",
        "total_questions": len(questions),
        "total_score": sum(q["score"] for q in questions if q["score"] is not None),
        "questions": questions
    }

def process_image_content_text(image_content):
    image = Image.open(io.BytesIO(image_content))
    result = reader.readtext(image)
    text = ' '.join([item[1] for item in result])
    
    if not text.strip():
        text = pytesseract.image_to_string(image, config=custom_config)
    
    return text

def process_pdf_text(pdf_content):
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_content))
        text = ""
        
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text += page_text + "\n"
                continue
            
            try:
                images = convert_from_bytes(pdf_content)
                for image in images:
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    result = reader.readtext(image)
                    if result:
                        text += ' '.join([item[1] for item in result]) + "\n"
                    else:
                        tesseract_text = pytesseract.image_to_string(image, config=custom_config)
                        if tesseract_text.strip():
                            text += tesseract_text + "\n"
            except Exception as e:
                print(f"Error converting page to image: {str(e)}")
                continue
        
        return text if text.strip() else "No text could be extracted from the PDF"
    except Exception as e:
        print(f"Error in process_pdf: {str(e)}")
        raise Exception(f"Error processing PDF: {str(e)}")




# ورودی مشترک
class TTSInput(BaseModel):
    text: str

# --- روش 1: ESPnet
try:
    from espnet2.bin.tts_inference import Text2Speech
    import torch
    import soundfile as sf

    espnet_tts = Text2Speech.from_pretrained("m3hrdadfi/persian-tts")
except Exception as e:
    print("Error while loadiiining TTS model:", str(e))
    espnet_tts = None

@app.post("/tts/espnet")
def tts_espnet(input: TTSInput):
    if espnet_tts is None:
        raise HTTPException(status_code=500, detail="ESPnet TTS model not loaded.")
    try:
        wav = espnet_tts(input.text)["wav"]
        filename = f"{uuid.uuid4()}.wav"
        path = os.path.join("outputs", filename)
        os.makedirs("outputs", exist_ok=True)
        sf.write(path, wav.numpy(), 22050)
        return {"file_path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- روش 2: Coqui TTS
try:
    from TTS.api import TTS as CoquiTTS
    coqui_tts = CoquiTTS(model_name="tts_models/fa/mai/tacotron2-DDC", progress_bar=False, gpu=False)
except:
    coqui_tts = None

@app.post("/tts/coqui")
def tts_coqui(input: TTSInput):
    if coqui_tts is None:
        raise HTTPException(status_code=500, detail="Coqui TTS model not loaded.")
    try:
        filename = f"{uuid.uuid4()}.wav"
        path = os.path.join("outputs", filename)
        os.makedirs("outputs", exist_ok=True)
        coqui_tts.tts_to_file(text=input.text, file_path=path)
        return {"file_path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 