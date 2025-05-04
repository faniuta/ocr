# Persian OCR API

این پروژه یک API برای تبدیل تصاویر و PDF‌های فارسی به متن است. از کتابخانه‌های قدرتمند EasyOCR و Tesseract برای تشخیص متن فارسی استفاده می‌کند.

## ویژگی‌ها

- پشتیبانی از تصاویر دست‌نوشته و تایپ شده فارسی
- پشتیبانی از PDF‌های متنی و تصویری
- استفاده از دو موتور OCR (EasyOCR و Tesseract) برای دقت بیشتر
- API ساده و سریع با FastAPI

## پیش‌نیازها

- Python 3.8+
- Tesseract OCR
- زبان فارسی برای Tesseract

## نصب

1. نصب Tesseract OCR:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-fas
```

2. نصب کتابخانه‌های پایتون:
```bash
pip install -r requirements.txt
```

## اجرا

```bash
python main.py
```

API در آدرس `http://localhost:8000` در دسترس خواهد بود.

## استفاده از API

### تبدیل تصویر/PDF به متن

```bash
curl -X POST "http://localhost:8000/ocr" \
     -H "Content-Type: application/json" \
     -d '{"image_url": "URL_تصویر_یا_PDF"}'
```

### پاسخ

```json
{
    "text": "متن استخراج شده از تصویر یا PDF"
}
```

## نکات

- برای بهترین نتایج، از تصاویر با کیفیت بالا استفاده کنید
- API از هر دو موتور OCR استفاده می‌کند و بهترین نتیجه را برمی‌گرداند
- برای PDF‌های متنی، از استخراج مستقیم متن استفاده می‌شود
- برای PDF‌های تصویری، هر صفحه به صورت جداگانه پردازش می‌شود 

source .

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
