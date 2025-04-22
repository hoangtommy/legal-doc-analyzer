from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
from PyPDF2 import PdfReader
import docx2txt
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

openai_api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=openai_api_key)

SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt'}

from pdf_utils import generate_pdf_from_json
from dropbox_sign import Configuration, ApiClient, SignatureRequestApi, SignatureRequestSendRequest, SubSignatureRequestSigner

@app.before_request
def log_request():
    print(f"Received {request.method} request at {request.path}")

def extract_text(file):
    filename = file.filename.lower()
    if filename.endswith('.pdf'):
        reader = PdfReader(file)
        text = " ".join(page.extract_text() or "" for page in reader.pages)
        return text
    elif filename.endswith('.docx'):
        return docx2txt.process(file)
    elif filename.endswith('.txt'):
        return file.read().decode('utf-8')
    else:
        return None

@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload():
    if request.method == 'OPTIONS':
        print("OPTIONS preflight request received")
        return '', 204
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files uploaded'}), 400
    all_text = ""
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return jsonify({'error': 'Unsupported file type'}), 400
        text = extract_text(file)
        if text and len(text.strip()) > 0:
            all_text += text + "\n"
    if not all_text.strip():
        return jsonify({'error': 'Could not extract text from any file'}), 400
    # Call OpenAI API
    try:
        json_structure = '''{
  "issuer_information": {
    "name": "Not Specified",
    "previous_names": "Not Specified",
    "state_of_incorporation": "Not Specified",
    "date_of_incorporation": "Not Specified",
    "entity_type": "Not Specified",
    "primary_business_address": "Not Specified",
    "phone_number": "Not Specified"
  },
  "related_persons": {
    "officers_directors_promoters_info": "Not Specified",
    "gross_proceeds_used_for_related_persons": "Not Specified"
  },
  "industry_group": "Not Specified",
  "offering_details": {
    "federal_exemption_relied_upon": "Not Specified",
    "generally_solicited_or_advertised": "Not Specified",
    "new_or_amended_filing": "Not Specified",
    "first_sale_date": "Not Specified",
    "offering_closed_and_duration": "Not Specified",
    "type_of_securities_offered": "Not Specified",
    "business_combination_transaction": "Not Specified",
    "minimum_investment_from_outside_investor": "Not Specified",
    "lowest_waivable_investment_amount": "Not Specified"
  },
  "sales_compensation": {
    "persons_receiving_compensation": {
      "name": "Not Specified",
      "address": "Not Specified",
      "broker_status": "Not Specified",
      "crd_number": "Not Specified"
    },
    "states_solicited": "Not Specified",
    "sales_commissions": "Not Specified",
    "finders_fee": "Not Specified"
  },
  "offering_sales_amounts": {
    "total_offering_amount": "Not Specified",
    "amount_sold": "Not Specified"
  },
  "investors": {
    "sold_to_non_accredited_investors": "Not Specified",
    "number_of_non_accredited_investors": "Not Specified"
  }
}'''
        system_prompt = f"You are a legal document analyzer. Extract the following fields from the provided legal document and return them as a valid JSON object. If a field is not found, set the value to 'Not Specified'. The JSON structure should be exactly as follows: {json_structure}"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": all_text[:12000]}
            ]
        )
        # Try to parse the result as JSON
        import json
        try:
            result_json = json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Failed to parse OpenAI response as JSON: {e}")
            result_json = {"error": "Failed to extract structured data. Please check the document and try again."}

        # Generate PDF from extracted data
        pdf_path = "/tmp/extracted_data.pdf"
        generate_pdf_from_json(result_json, pdf_path)

        # Send PDF for signature via Dropbox Sign
        api_key = os.getenv("DROPBOX_SIGN_API_KEY")
        configuration = Configuration(username=api_key)
        with ApiClient(configuration) as api_client:
            signature_api = SignatureRequestApi(api_client)
            signer = SubSignatureRequestSigner(
                email_address=os.getenv("SIGNER_EMAIL", "signer@example.com"),
                name=os.getenv("SIGNER_NAME", "Signer Name")
            )
            signature_request = SignatureRequestSendRequest(
                title="Legal Doc Signature",
                subject="Please sign this document",
                message="Kindly review and sign.",
                signers=[signer],
                files=[pdf_path],
                test_mode=True
            )
            signature_response = signature_api.signature_request_send(signature_request)
        resp = jsonify({'result': result_json, 'signature_request': signature_response.to_dict()})
        print(f"Response headers: {dict(resp.headers)}")
        return resp
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
