from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
import pytesseract
import io
import uvicorn
import re

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "이미지 인식 api"}

@app.post("/text")
async def upload_image(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        extracted_text = pytesseract.image_to_string(image, lang='kor')

        return {"extracted_text": extracted_text}

    except pytesseract.TesseractError as te:
        raise HTTPException(status_code=400, detail=f"Tesseract OCR Error: {te}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"General Error: {e}")

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        extracted_text = pytesseract.image_to_string(image, lang='kor')

        expiration_match = re.search(r"유효기간\s+([\d년\s월일]+)", extracted_text)
        status_match = re.search(r"쿠폰상태\s+([\w]+)", extracted_text)
        product_name_match = re.search(r"<\s*.*\s*선물하기.*\s*\n\n(.*?)\n\n", extracted_text)
        exchange_place_match = re.search(r"교환처\s*([^\n]+)", extracted_text)

        if expiration_match:
            expiration_date = expiration_match.group(1).replace("\n", " ").strip()
        else:
            expiration_date = "null"

        if status_match:
            status = status_match.group(1).replace("\n", " ").strip()
        else:
            status = "null"

        if product_name_match:
            product_name = product_name_match.group(1).replace("\n\n", " ").strip()
            #product_name = " ".join([line for line in product_name.split() if not line.isdigit()])
        else:
            product_name = "null"

        if exchange_place_match:
            exchange_place = exchange_place_match.group(1).replace("\n", " ").strip()
        else:
            exchange_place = "null"

        return {
            "expiration_date": expiration_date,
            "coupon_status": status,
            "product_name": product_name,
            "exchange_place" : exchange_place
        }

    except pytesseract.TesseractError as te:
        raise HTTPException(status_code=400, detail=f"Tesseract OCR Error: {te}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"General Error: {e}")

