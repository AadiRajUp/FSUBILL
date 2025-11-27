#
# Written and maintained by FSU
#

import base64
import json
from typing import List, Dict
import requests
import fitz
from flask import Flask, request, render_template
from werkzeug.datastructures import ImmutableMultiDict, FileStorage

# ----------------------------------
ENDPOINT = "https://api.pdfendpoint.com/v1/convert"
app = Flask(__name__)
app.secret_key = "##$$"
# ----------------------------------


def parse_table(table_json: str) -> List[List[str]]:
    '''
    returns parsed table row from table_json, empty if invalid
    '''
    try:
        return json.loads(table_json)
    except json.JSONDecodeError:
        return list()


def calculate_total(table_values: List[List[str]]) -> float:
    '''
    total price calculation at index 6
    '''
    return sum(float(row[5]) for row in table_values if len(row) > 5)


def encode_files_to_base64(files: ImmutableMultiDict[str, FileStorage]) -> List[Dict[str, str]]:
    '''
    convert uploaded files to base64 with `metadata`
    '''
    encoded_files = list()
    for file_key in files:
        file = files[file_key]
        file_bytes = file.read()
        encoded_files.append({
            "filename": file.filename,
            "mime_type": file.mimetype,
            "data": base64.b64encode(file_bytes).decode("utf-8")
        })
    return encoded_files


def generate_pdf(html_content: str) -> str:
    '''
    using ENDPOINT generate pdf from html
    '''
    payload = {
        "html": html_content,
        "margin_top": "0cm",
        "margin_bottom": "0cm",
        "margin_right": "0cm",
        "margin_left": "0cm",
        "no_backgrounds": False,
        "no_images": False,
        "printBackground": True,
        "sandbox": True
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer pdfe_live_e2386b010bda9ea889d9a1dc16cb9cd41076"
    }
    response = requests.post(ENDPOINT, json=payload, headers=headers)
    response_data = response.json()
    return response_data.get('data', {}).get('url', '')


def pdf_first_page_to_base64(pdf_url: str) -> Dict[str, str]:
    '''
    convert from first page of pdf to base64-enc png image
    '''
    pdf_bytes = requests.get(pdf_url).content
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    pix = page.get_pixmap(dpi=300)
    img_bytes = pix.tobytes("png")
    return {
        "filename": "firstpage.png",
        "mime_type": "image/png",
        "data": base64.b64encode(img_bytes).decode("utf-8")
    }


def render_bill_template(
    title: str,
    date: str,
    table_values: List[List[str]],
    total: float,
    pdf_url: str,
    images_base64: List[Dict[str, str]]
) -> str:
    '''
    render_template bill-new.html with necessary data
    '''
    return render_template(
        'bill-new.html',
        title=title,
        date=date,
        tableData=table_values,
        total=total,
        downloadLink=pdf_url,
        images=images_base64
    )


@app.route('/')
def index() -> str:
    return render_template("Index.html")


@app.route('/generate-bill', methods=['POST'])
def generate_bill() -> str:
    title = request.form.get('title', '')
    date = request.form.get('date', '')
    table_json = request.form.get('table', '[]')

    table_values = parse_table(table_json)
    total = calculate_total(table_values)
    images_base64 = encode_files_to_base64(request.files)

    html_content = render_template(
        'bill-new.html',
        title=title,
        date=date,
        tableData=table_values,
        total=total,
        downloadLink="",
        downloadName="",
        images=images_base64
    )

    pdf_url = generate_pdf(html_content)

    if pdf_url:
        images_base64.append(pdf_first_page_to_base64(pdf_url))

    return render_bill_template(title, date, table_values, total, pdf_url, images_base64)


if __name__ == "__main__":
    app.run(debug=True)
