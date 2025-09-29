# modules/openai_handler.py
import os
import json
from openai import OpenAI

# This is the specification for the "tool" that OpenAI will use.
# It matches the TOOL_SPEC from the VBA code.
NPPES_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "build_nppes_query",
        "description": "Translate a provider search request into NPPES API parameters.",
        "parameters": {
            "type": "object",
            "properties": {
                "number": {
                    "type": "string",
                    "description": "The 10-digit National Provider Identifier (NPI)",
                },
                 "limit": {"type": "integer", "description": "Number of results to return, 1-200"},
            },
            "required": ["number"],
        },
    },
}

def get_nppes_params_from_ai(npi: str, client: OpenAI) -> dict | None:
    """
    Asks OpenAI to generate parameters for the NPPES API using tool-calling.
    This replicates the VBA 'GPT_GetNppesParams' function.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that uses tools to answer questions about healthcare providers."},
                {"role": "user", "content": f"Please retrieve the details for the provider with NPI {npi}."}
            ],
            tools=[NPPES_TOOL_SPEC],
            tool_choice="auto",
            temperature=0,
        )
        
        message = response.choices[0].message
        if message.tool_calls:
            # Extract the arguments from the tool call
            tool_call = message.tool_calls[0]
            if tool_call.function.name == "build_nppes_query":
                arguments = json.loads(tool_call.function.arguments)
                return arguments
        
        print(f"OpenAI did not return the expected tool call for NPI {npi}")
        return None

    except Exception as e:
        print(f"OpenAI parameter generation failed for NPI {npi}: {e}")
        return None


def get_specialty_and_contact_type(taxonomy: str, client: OpenAI) -> dict | None:
    """
    Uses OpenAI's JSON Mode to map a taxonomy to a primary specialty and contact type.
    This replaces the VBA 'GPT_SummariseNppes' function.
    """
    if not taxonomy:
        return None

    try:
        prompt = (
            f"Given the healthcare provider taxonomy description \"{taxonomy}\", "
            "determine the primary specialty and contact type. The contact type must be one "
            "of these options: Physician, Physician Assistant, Nurse Practitioner, Pharmacist, "
            "Physical Therapist, Dietitian, or Other."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns data in JSON format."},
                {"role": "user", "content": f"{prompt} Please return a JSON object with two keys: 'primary_specialty' and 'contact_type'."}
            ],
            temperature=0.2,
        )
        
        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as e:
        print(f"OpenAI API call failed for taxonomy '{taxonomy}': {e}")
        return None