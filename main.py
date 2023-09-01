from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
import pytesseract
import cv2
import numpy as np
import io
from typing import List
import re


app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "이미지 인식 api"}

async def process_and_extract_text(file: UploadFile):
    contents = await read_file(file)
    pil_image = Image.open(io.BytesIO(contents))
    open_cv_image = np.array(pil_image)
    open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
    preprocessed_image = preprocess_image(open_cv_image)
    pil_image = Image.fromarray(cv2.cvtColor(preprocessed_image, cv2.COLOR_BGR2RGB))
    extracted_text = pytesseract.image_to_string(pil_image, lang='kor+eng', config='--oem 1 --psm 6')
    return extracted_text

def preprocess_image(image: np.array) -> np.array:
    # 이미지를 흑백으로 변환
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 이미지에 적응형 이진화 적용
    threshold_img = cv2.adaptiveThreshold(gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY, 11, 2)
    return threshold_img

async def read_file(file: UploadFile):
    contents = await file.read()
    if file.filename.endswith('.png'):
        contents = convert_to_jpeg(contents)
    return contents

def convert_to_jpeg(png_bytes):
    png_image = Image.open(io.BytesIO(png_bytes))
    rgb_im = png_image.convert('RGB')
    byte_io = io.BytesIO()
    rgb_im.save(byte_io, format='JPEG')
    return byte_io.getvalue()


def extract_info_from_text(extracted_text: str) -> dict:
    info = {}

    product_name_match = re.search(r"선물하기[^\n]*\n(.*?)(?=\d{3})", extracted_text,re.DOTALL)
    product_name = product_name_match.group(1).strip() if product_name_match else "null"
    product_name = clean_product_name(product_name)
    info['product_name'] = product_name

    exchange_match = re.search(r"교환처\s*([^\n]+)", extracted_text)
    exchange_place = exchange_match.group(1).strip() if exchange_match else "null"
    info['exchange_place'] = exchange_place

    expiration_match = re.search(r"유효기간\s*([^\n]+)", extracted_text)
    if not expiration_match:
        expiration_match = re.search(r"(\d{4}[.년]\s*\d{1,2}[.월]*\s*\d{1,2}[일]*)", extracted_text)
    expiration_date = expiration_match.group(1).strip() if expiration_match else "null"
    info['expiration_date'] = expiration_date

    if "쿠폰상태" in extracted_text:
        status_match = re.search(r"쿠폰상태\s+([\w]+)", extracted_text)
        info['coupon_status'] = status_match.group(1).strip() if status_match else "null"

    return info

def clean_product_name(product_name: str) -> str:
    remove_patterns = ["<", "선물하기",r"\d{2}:\d{2}", r"\d{3}\s\d{4}", r"[^\w\s]", ">", "©", "|", "Oipay", "all"]
    for pattern in remove_patterns:
        product_name = re.sub(pattern, "", product_name)
    product_name = re.sub(r"\s+", " ", product_name).strip()
    return product_name

@app.post("/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        try:
            extracted_text = await process_and_extract_text(file)
            info = extract_info_from_text(extracted_text)
            results.append(info)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"General Error: {e}")
    return {"results": results}

@app.post("/text")
async def upload_images(files: List[UploadFile] = File(...)):
    extracted_texts = []
    for file in files:
        try:
            extracted_text = await process_and_extract_text(file)
            extracted_texts.append(extracted_text)
        except pytesseract.TesseractError as te:
            raise HTTPException(status_code=400, detail=f"Tesseract OCR Error: {te}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"General Error: {e}")

    return {"extracted_texts": extracted_texts}