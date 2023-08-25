from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
import pytesseract
import io
import uvicorn
import re
from typing import List
from pyzbar.pyzbar import decode

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "이미지 인식 api"}

def clean_product_name(product_name: str) -> str:
    # 제품명에서 "교환처", "유효기간", "주문번호"와 같은 불필요한 문자열 제거
    remove_patterns = ["교환처", "유효기간", "주문번호", r"\d{4,8}\s*\d{4,8}", r"\d{4}\.\d{1,2}\.\d{1,2}"]
    for pattern in remove_patterns:
        product_name = re.sub(pattern, "", product_name)
    # 여러 공백 및 줄바꿈을 한 공백으로 치환
    product_name = re.sub(r"\s+", " ", product_name).strip()
    return product_name

def extract_barcode_number(image) -> str:
    decoded_objects = decode(image)
    for obj in decoded_objects:
        barcode_number = obj.data.decode('utf-8')
        return barcode_number
    return "null"

async def extract_text_from_image(file: UploadFile):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    extracted_text = pytesseract.image_to_string(image, lang='kor')
    return extracted_text

def extract_info_from_text(extracted_text: str) -> dict:
    if "쿠폰상태" in extracted_text:
        status_match = re.search(r"쿠폰상태\s+([\w]+)", extracted_text)
        status = status_match.group(1).strip() if status_match else "null"
        return {"coupon_status": status}
    else:
        # 제품명 추출
        product_name_match = re.search(r"(.*?)(?=\n\n\d{4,8}\s*\d{4,8}|\n\n\d{4,8})", extracted_text, re.DOTALL)
        product_name = product_name_match.group(1).strip() if product_name_match else "null"
        product_name = clean_product_name(product_name)
    
        # 교환처 추출
        exchange_match = re.search(r"교환처\s*([^\n]+)", extracted_text)
        exchange_place = exchange_match.group(1).strip() if exchange_match else "null"

        # 유효기간 추출
        expiration_match = re.search(r"유효기간\s*([^\n]+)", extracted_text)
        if not expiration_match:
            expiration_match = re.search(r"(\d{4}[.년]\s*\d{1,2}[.월]*\s*\d{1,2}[일]*)", extracted_text)
        expiration_date = expiration_match.group(1).strip() if expiration_match else "null"


    return {
        "product_name": product_name,
        "exchange_place": exchange_place,
        "expiration_date": expiration_date
    }

@app.post("/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    results = []
    barcode_numbers = []

    for file in files:
        try:
            contents = await file.read()
            image = Image.open(io.BytesIO(contents))
            # 바코드 번호 추출
            barcode_number = extract_barcode_number(image)
            barcode_numbers.append(barcode_number)

            # 텍스트 추출
            extracted_text = pytesseract.image_to_string(image, lang='kor')
            info = extract_info_from_text(extracted_text)
            info['barcode_number'] = barcode_number  # 바코드 번호 추가
            results.append(info)

        except pytesseract.TesseractError as te:
            raise HTTPException(status_code=400, detail=f"Tesseract OCR Error: {te}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"General Error: {e}")

    is_matching = all(x == barcode_numbers[0] for x in barcode_numbers[1:]) if barcode_numbers else False
    return {"results": results, "is_matching_barcodes": is_matching}

@app.post("/text")
async def upload_image(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        try:
            contents = await file.read()
            image = Image.open(io.BytesIO(contents))
            extracted_text = pytesseract.image_to_string(image, lang='kor')

            return {"extracted_text": extracted_text}

        except pytesseract.TesseractError as te:
            raise HTTPException(status_code=400, detail=f"Tesseract OCR Error: {te}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"General Error: {e}")
            