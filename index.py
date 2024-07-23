import streamlit as st
import boto3
import io
from PIL import Image
from pdf2image import convert_from_bytes

# Initialize boto3 client for Textract
textract = boto3.client('textract')


def extract_text_from_pdf(pdf_bytes):
    # Convert PDF to images
    images = convert_from_bytes(pdf_bytes)

    # Extract text from each image
    extracted_text = ""
    for image in images:
        # Convert PIL image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        # Call Textract
        response = textract.detect_document_text(Document={'Bytes': img_byte_arr})

        # Extract text
        for item in response["Blocks"]:
            if item["BlockType"] == "LINE":
                extracted_text += item["Text"] + "\n"

    return extracted_text


st.title("PDF Text Extraction using Amazon Textract")

# File uploader
uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    # Extract text from PDF
    pdf_bytes = uploaded_file.read()
    with st.spinner('Extracting text...'):
        extracted_text = extract_text_from_pdf(pdf_bytes)

    st.success('Text extracted successfully!')
    st.text_area("Extracted Text", extracted_text, height=400)
