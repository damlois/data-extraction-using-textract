import streamlit as st
import boto3
import io
from pdf2image import convert_from_bytes
import pandas as pd
from PIL import Image
import pytesseract
import time

# Set page layout to wide
# st.set_page_config(layout="wide")

# Initialize boto3 client for Textract
textract = boto3.client('textract')

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows example

def extract_text_from_image(image_bytes, queries):
    try:
        response = textract.analyze_document(
            Document={'Bytes': image_bytes},
            FeatureTypes=['QUERIES'],
            QueriesConfig={'Queries': queries}
        )

        form_data = []

        if 'Blocks' in response:
            for block in response['Blocks']:
                if block['BlockType'] == 'QUERY':
                    query_alias = block.get('Query', {}).get('Alias')
                    for item in block.get('Relationships', []):
                        for id in item.get('Ids', []):
                            block_item = next((b for b in response['Blocks'] if b['Id'] == id), None)
                            if block_item:
                                form_data.append((query_alias, block_item.get('Text', '') + ' --> ' + str(block_item.get('Confidence'))))

        return form_data
    except Exception as e:
        st.warning(f"Textract failed: {e}. Falling back to Tesseract.")
        return extract_text_with_tesseract(image_bytes, queries)

def extract_text_with_tesseract(image_bytes, queries):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        # Process text to match query format if needed
        # For simplicity, returning dummy data for queries
        form_data = [(query['Alias'], text) for query in queries]
        return form_data
    except Exception as e:
        st.error(f"Error in Tesseract: {e}")
        return []

def extract_text_from_pdf(pdf_bytes, queries):
    try:
        images = convert_from_bytes(pdf_bytes)
        form_data = []

        for image in images:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            response = textract.analyze_document(
                Document={'Bytes': img_byte_arr},
                FeatureTypes=['QUERIES'],
                QueriesConfig={'Queries': queries}
            )

            if 'Blocks' in response:
                for block in response['Blocks']:
                    if block['BlockType'] == 'QUERY':
                        query_alias = block.get('Query', {}).get('Alias')
                        for item in block.get('Relationships', []):
                            for id in item.get('Ids', []):
                                block_item = next((b for b in response['Blocks'] if b['Id'] == id), None)
                                if block_item:
                                    form_data.append((query_alias, block_item.get('Text', '') + ' -->  ' + str(block_item.get('Confidence'))))

        return form_data
    except Exception as e:
        st.warning(f"Textract failed: {e}. Falling back to Tesseract.")
        images = convert_from_bytes(pdf_bytes)
        form_data = []
        for image in images:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            form_data.extend(extract_text_with_tesseract(img_byte_arr, queries))
        return form_data

def extract_fields_from_form_data(form_data, query_aliases):
    fields = {alias: "Not Found" for alias in query_aliases}

    for alias, value in form_data:
        if alias in fields:
            fields[alias] = value.strip()

    return fields


st.title("Data Extraction using Amazon Textract")

# Bold section headers using Markdown
st.markdown("**Upload Files**", unsafe_allow_html=True)
uploaded_files = st.file_uploader("Upload files (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)

st.markdown("**Enter Your Queries**", unsafe_allow_html=True)
num_queries = st.number_input("Number of queries", min_value=1, step=1, value=1)

query_data = []
query_aliases = []
for i in range(num_queries):
    with st.expander(f"Query {i+1}", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            query_text = st.text_input(f"Query Text {i+1}", key=f"query_text_{i}")
        with col2:
            query_alias = st.text_input(f"Query Alias {i+1}", key=f"query_alias_{i}")
        if query_text and query_alias:
            query_data.append({"Text": query_text, "Alias": query_alias})
            query_aliases.append(query_alias)

if query_data and uploaded_files:
    if st.button("Submit"):
        all_extracted_fields = []

        # Record the start time
        start_time = time.time()

        with st.spinner('Extracting text from documents...'):
            for uploaded_file in uploaded_files:
                file_type = uploaded_file.type
                form_data = []

                if file_type in ["image/png", "image/jpeg", "image/jpg"]:
                    image_bytes = uploaded_file.read()
                    form_data = extract_text_from_image(image_bytes, query_data)
                elif file_type == "application/pdf":
                    pdf_bytes = uploaded_file.read()
                    form_data = extract_text_from_pdf(pdf_bytes, query_data)

                if form_data:
                    extracted_fields = extract_fields_from_form_data(form_data, query_aliases)
                    extracted_fields["Filename"] = uploaded_file.name
                    all_extracted_fields.append(extracted_fields)

        # Record the end time
        end_time = time.time()
        elapsed_time = end_time - start_time

        st.success('Text extracted successfully!')
        st.write(f"Time taken to extract data from the resumes: {elapsed_time:.2f} seconds")

        df = pd.DataFrame(all_extracted_fields, index=range(1, len(all_extracted_fields) + 1))
        df = df[["Filename"] + [col for col in df.columns if col != "Filename"]]
        st.dataframe(df, use_container_width=True)
