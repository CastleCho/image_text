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

def remove_unnecessary_spaces(text: str) -> str:
    text = text.replace(" ", "")
    # 필요한 띄어쓰기만 다시 추가
    text = re.sub(r"(유효기간)", "유효기간 ", text)
    text = re.sub(r"(교환처)", "교환처 ", text)
    text = re.sub(r"(선물정보)", "선물정보 ", text)
    text = re.sub(r"(사용여부)", "사용여부 ", text)
    text = re.sub(r"(쿠폰상태)", "쿠폰상태 ", text)
    # ... 나머지도 이런 식으로 처리
    return text


async def process_and_extract_text(file: UploadFile):
    contents = await read_file(file)
    pil_image = Image.open(io.BytesIO(contents))
    open_cv_image = np.array(pil_image)
    open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
    preprocessed_image = preprocess_image(open_cv_image)
    pil_image = Image.fromarray(cv2.cvtColor(preprocessed_image, cv2.COLOR_BGR2RGB))
    extracted_text = pytesseract.image_to_string(pil_image, lang='kor+eng', config='--oem 3 --psm 3')
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

    product_name_match = re.search(r"선물하기[^\n]*\n(.*?)(?=\d{6})", extracted_text, re.DOTALL)

    # '선물하기'가 없는 경우에는 제품명을 찾을 수 있는 다른 패턴을 사용합니다.
    if not product_name_match:
        product_name_match = re.search(r"([^\n]+)\n([^\n]+)\n(.*?)(?=\d{6})", extracted_text, re.DOTALL)
        if product_name_match:
            product_name = product_name_match.group(1).strip() + " " + product_name_match.group(2).strip()
        else:
            product_name = "null"
    else:
        product_name = product_name_match.group(1).strip()
        
    product_name = clean_product_name(product_name)
    info['product_name'] = product_name

    exchange_match = re.search(r"교환처\s*([^\n]+)", extracted_text)
    exchange_place = exchange_match.group(1).strip() if exchange_match else "null"
    if exchange_place == '64':
        exchange_place = 'CU'

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
    # "\n" 제거
    product_name = product_name.replace("\n", "")
    # 특정 패턴 제거
    remove_patterns = ["<", "선물하기", r"\d{2}:\d{2}", r"\d{3}\s\d{4}", ">", "©", "|", "Oipay", "all"]
    for pattern in remove_patterns:
        product_name = re.sub(pattern, "", product_name)
    # 알파벳, 숫자, 한글, 공백, 점을 제외한 나머지 문자를 제거
    product_name = re.sub(r"[^\w\s.]", "", product_name)
    # 공백을 하나로 합침
    product_name = re.sub(r"\s+", " ", product_name).strip()
    return product_name

@app.post("/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        try:
            extracted_text = await process_and_extract_text(file)
            extracted_text = remove_unnecessary_spaces(extracted_text)
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