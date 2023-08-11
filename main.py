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
        product_name_match = re.search(r"선물하기\s+0 ×\n\n([\s\S]+?)\n\n\d", extracted_text)
        exchange_place_match = re.search(r"교환처\s*([^\n]+)", extracted_text)

        if expiration_match:
            expiration_date = expiration_match.group(1).replace("\n", " ").strip()
        else:
            expiration_date = "유효기간 정보를 찾을 수 없습니다."

        if status_match:
            status = status_match.group(1).replace("\n", " ").strip()
        else:
            status = "쿠폰상태 정보를 찾을 수 없습니다."

        if product_name_match:
            product_name = product_name_match.group(1).replace("\n", " ").strip()
            product_name = " ".join([line for line in product_name.split() if not line.isdigit()])
        else:
            product_name = "상품명 정보를 찾을 수 없습니다."

        if exchange_place_match:
            exchange_place = exchange_place_match.group(1).replace("\n", " ").strip()
        else:
            exchange_place = "교환처 정보를 찾을 수 없습니다."

        return {
            "유효기간": expiration_date,
            "쿠폰상태": status,
            "상품명": product_name,
            "교환처" : exchange_place
        }

    except pytesseract.TesseractError as te:
        raise HTTPException(status_code=400, detail=f"Tesseract OCR Error: {te}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"General Error: {e}")


