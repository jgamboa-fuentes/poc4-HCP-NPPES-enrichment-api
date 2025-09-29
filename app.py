# app.py
import os
from flask import Flask, request
from flask_restx import Api, Resource, fields
from dotenv import load_dotenv
from openai import OpenAI

# Import our new handler functions
from modules import db_handler, nppes_handler, openai_handler

# Load environment variables from .env file
load_dotenv()

# Initialize Flask App and Flask-RESTX API
app = Flask(__name__)
api = Api(app, version='1.0', title='HCP Enrichment API',
          description='An API to enrich HCP data using NPI numbers.',
          doc='/docs')

ns = api.namespace('enrich', description='Enrichment Operations')

enrich_model = api.model('EnrichmentPayload', {
    'source_table': fields.String(required=True, description='Source table name (e.g., AIPOC.POC4_HCP_Targeting_Test)'),
    'destination_table': fields.String(required=True, description='Destination table name')
})

@ns.route('/by_npi')
class EnrichByNPI(Resource):
    @ns.expect(enrich_model, validate=True)
    def post(self):
        """
        Triggers the HCP data enrichment process for a specified table.
        """
        data = request.json
        source_table = data['source_table']
        destination_table = data['destination_table']
        
        processed_count = 0
        failed_count = 0
        
        try:
            # Initialize the OpenAI client once
            openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            conn = db_handler.get_db_connection()
            cursor = conn.cursor()
            
            npi_list = db_handler.get_npis_to_enrich(cursor, source_table)
            if not npi_list:
                return {'message': 'No records needed enrichment.'}, 200

            for npi in npi_list:
                print(f"Processing NPI: {npi}...")
                
                # 1. Ask AI for NPPES query parameters
                nppes_params = openai_handler.get_nppes_params_from_ai(npi, openai_client)
                if not nppes_params:
                    print(f"  -> Failed to get NPPES parameters from AI for {npi}.")
                    failed_count += 1
                    continue
                
                # 2. Get data from NPPES using the parameters from the AI
                nppes_data = nppes_handler.get_nppes_data(nppes_params)
                if not nppes_data:
                    print(f"  -> Failed to get NPPES data for {npi}.")
                    failed_count += 1
                    continue
                
                # 3. Get specialty/contact type from OpenAI
                taxonomy = nppes_data.get("taxonomy")
                ai_summary = openai_handler.get_specialty_and_contact_type(taxonomy, openai_client)

                # 4. Combine data and apply fallback logic
                enriched_data = nppes_data.copy()
                if ai_summary:
                    enriched_data["primary_specialty"] = ai_summary.get("primary_specialty")
                    enriched_data["contact_type"] = ai_summary.get("contact_type")
                else:
                    enriched_data["primary_specialty"] = taxonomy
                    if taxonomy and "assistant" in taxonomy.lower():
                        enriched_data["contact_type"] = "Physician Assistant"
                    else:
                        enriched_data["contact_type"] = "Physician"
                
                # 5. Update the database record
                db_handler.update_hcp_record(cursor, destination_table, npi, enriched_data)
                processed_count += 1
            
            conn.commit()
            cursor.close()
            conn.close()

            summary = f"Enrichment complete. Processed: {processed_count}, Failed: {failed_count}."
            return {'message': summary}, 200

        except Exception as e:
            api.abort(500, f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)