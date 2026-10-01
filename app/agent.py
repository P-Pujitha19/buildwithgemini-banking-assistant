# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
from typing import Optional, Dict, Any, List
import urllib.request
from zoneinfo import ZoneInfo

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

from .a2ui_utils import a2ui_callback

PROJECT_ID = "qwiklabs-gcp-02-40df00ca0376"
MEMORY_BANK_ID = "7886434067200081920"

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are NovaSmart Bank's AI Customer Assistant. You help customers explore home loans, "
        "personal loans, credit cards, high-yield savings products, perform EMI calculations, "
        "check live currency exchange rates, and generate promotional images. You remember user "
        "preferences across conversations, specifically preferred banking products, loan interests, "
        "and customer preferences."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


def _get_firestore_client():
    return firestore.Client(project=PROJECT_ID)


def get_customer_profile(customer_id: str) -> Dict[str, Any]:
    """Retrieves customer profile and preferences from the 'customers' collection in Firestore.

    Args:
        customer_id: The unique ID of the customer (e.g. 'cust_001').

    Returns:
        Dictionary containing customer details including preferences, credit score, and existing accounts.
    """
    db = _get_firestore_client()
    doc_ref = db.collection("customers").document(customer_id)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return {"error": f"Customer '{customer_id}' not found."}


def update_customer_preferences(customer_id: str, preference_key: str, preference_value: str) -> str:
    """Updates or adds a preference key-value pair in a customer's profile in Firestore.

    Args:
        customer_id: Unique ID of the customer (e.g. 'cust_001').
        preference_key: The preference field name (e.g. 'preferred_contact_method', 'interested_in').
        preference_value: The value to set for the preference.

    Returns:
        A success or error status message.
    """
    db = _get_firestore_client()
    doc_ref = db.collection("customers").document(customer_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Error: Customer '{customer_id}' does not exist."

    doc_ref.set({"preferences": {preference_key: preference_value}}, merge=True)
    return f"Successfully updated preference '{preference_key}' = '{preference_value}' for customer '{customer_id}'."


def read_loan_products(category: str = "") -> List[Dict[str, Any]]:
    """Reads available loan products (e.g. Home Loans, Personal Loans) from the 'loans' Firestore collection.

    Args:
        category: Optional category filter (e.g. 'home', 'personal'). Leave empty to fetch all.

    Returns:
        List of matching loan product records.
    """
    db = _get_firestore_client()
    coll = db.collection("loans")
    docs = coll.stream()
    results = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        if not category or category.lower() in d.get("category", "").lower() or category.lower() in d.get("name", "").lower():
            results.append(d)
    return results


def read_credit_cards(category: str = "") -> List[Dict[str, Any]]:
    """Reads available credit card products from the 'credit_cards' Firestore collection.

    Args:
        category: Optional filter for card category (e.g., 'cashback', 'travel', 'rewards').

    Returns:
        List of credit card records.
    """
    db = _get_firestore_client()
    coll = db.collection("credit_cards")
    docs = coll.stream()
    results = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        if not category or category.lower() in d.get("category", "").lower() or category.lower() in d.get("name", "").lower():
            results.append(d)
    return results


def read_banking_products(category: str = "") -> List[Dict[str, Any]]:
    """Reads general banking products (savings, CDs, checking) from the 'banking_products' Firestore collection.

    Args:
        category: Optional category filter (e.g., 'savings', 'cd', 'checking').

    Returns:
        List of banking products matching criteria.
    """
    db = _get_firestore_client()
    coll = db.collection("banking_products")
    docs = coll.stream()
    results = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        if not category or category.lower() in d.get("category", "").lower() or category.lower() in d.get("name", "").lower():
            results.append(d)
    return results


def write_banking_product(product_id: str, name: str, category: str, interest_rate: float, description: str) -> str:
    """Adds or updates a banking product record in the 'banking_products' Firestore collection.

    Args:
        product_id: Unique identifier for the product (e.g. 'prod_money_market').
        name: Display name of the product.
        category: Product category (e.g. 'savings', 'checking', 'investment').
        interest_rate: Annual interest rate percentage (e.g. 4.5).
        description: Feature details and summary.

    Returns:
        Status message confirming the write operation.
    """
    db = _get_firestore_client()
    doc_ref = db.collection("banking_products").document(product_id)
    doc_ref.set({
        "name": name,
        "category": category,
        "interest_rate": interest_rate,
        "description": description,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }, merge=True)
    return f"Successfully saved product '{product_id}' to 'banking_products' collection."


def calculate_emi(loan_amount: float, interest_rate: float, tenure_years: int) -> Dict[str, Any]:
    """Calculates Equated Monthly Installment (EMI) for loan planning.

    Args:
        loan_amount: The loan principal amount (e.g. 250000.0).
        interest_rate: Annual interest rate in percentage (e.g. 6.5).
        tenure_years: Loan tenure in years (e.g. 30).

    Returns:
        Dictionary containing emi_amount, total_payment, and total_interest.
    """
    r = (interest_rate / 12) / 100
    n = tenure_years * 12
    if r == 0:
        emi = loan_amount / n
    else:
        emi = loan_amount * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)

    total_payment = emi * n
    total_interest = total_payment - loan_amount

    return {
        "emi_amount": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
    }


def get_exchange_rates() -> Dict[str, Any]:
    """Retrieves live currency exchange rates for USD to INR and EUR to INR from a free public API.

    Returns:
        Dictionary containing USD to INR and EUR to INR live exchange rates.
    """
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rates = data.get("rates", {})
            usd_inr = rates.get("INR")
            eur = rates.get("EUR")
            eur_inr = round(usd_inr / eur, 4) if (usd_inr and eur) else None
            return {
                "USD_to_INR": usd_inr,
                "EUR_to_INR": eur_inr,
                "base": "USD",
                "status": "success",
            }
    except Exception as e:
        return {"error": f"Failed to fetch exchange rates: {str(e)}"}


def generate_promo_image(product_type: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Generates promotional banking images for Home Loans, Personal Loans, or Credit Cards using gemini-3.1-flash-lite-image.

    Saves the image as an artifact in ToolContext for the Playground Artifacts panel and uploads it to Cloud Storage to return a public HTTPS URL.

    Args:
        product_type: Banking product type ('Home Loans', 'Personal Loans', or 'Credit Cards').

    Returns:
        Dictionary containing product_type, filename, public_url, and status.
    """
    prompts = {
        "home loans": "A modern, warm, high-quality promotional banner for Home Loans showing a beautiful suburban family home with keys",
        "personal loans": "A vibrant, modern promotional banner for Personal Loans showing happy individuals achieving lifestyle goals",
        "credit cards": "A sleek, premium promotional banner for Credit Cards showing a luxury rewards credit card with cashback features"
    }

    key = product_type.lower().strip()
    prompt = prompts.get(key, f"A professional banking promotional banner for {product_type}")

    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
    )

    image_bytes = None
    mime_type = "image/jpeg"
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            image_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type
            break

    if not image_bytes:
        return {"error": "Failed to generate promotional image."}

    clean_type = product_type.lower().replace(" ", "_")
    filename = f"promo_{clean_type}.jpg"

    # 1. Save artifact for Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload to Cloud Storage bucket and return public HTTPS URL
    bucket_name = f"banking-promo-images-{PROJECT_ID}"
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"

    return {
        "product_type": product_type,
        "filename": filename,
        "public_url": public_url,
        "status": "success"
    }


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback triggered after each turn to persist session memories in Memory Bank."""
    await callback_context.add_session_to_memory()
    return None


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        get_customer_profile,
        update_customer_preferences,
        read_loan_products,
        read_credit_cards,
        read_banking_products,
        write_banking_product,
        calculate_emi,
        get_exchange_rates,
        generate_promo_image,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)


app = App(
    root_agent=root_agent,
    name="app",
)

