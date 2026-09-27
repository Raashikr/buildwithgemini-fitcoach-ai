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
import pathlib

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore
from google.genai import types

try:
    from .a2ui_utils import a2ui_callback
except ImportError:
    from app.a2ui_utils import a2ui_callback

# IMPORTANT: Hardcoded Project ID and Bucket Name strings as required for Agent Platform deployment
GCP_PROJECT_ID = "qwiklabs-gcp-03-1aaca47776f8"
GCS_BUCKET_NAME = "fitcoach-ai-public-qwiklabs-gcp-03-1aaca47776f8"


def get_db():
    """Returns a Firestore client instance connected to the hardcoded GCP project."""
    return firestore.Client(project=GCP_PROJECT_ID)


def list_exercises(category: str = None) -> str:
    """Retrieves all exercises from the Firestore database, optionally filtered by category.

    Args:
        category: Optional category filter (e.g. 'Chest', 'Legs', 'Back', 'Core').

    Returns:
        A formatted string listing matching exercises with their details.
    """
    db = get_db()
    docs = db.collection("exercises").stream()

    exercises = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        if category:
            doc_category = data.get("category", "")
            if category.lower() not in doc_category.lower():
                continue
        exercises.append(data)

    if not exercises:
        filter_msg = f" in category '{category}'" if category else ""
        return f"No exercises found in the database{filter_msg}."

    result_lines = [f"Found {len(exercises)} exercise(s):"]
    for ex in exercises:
        result_lines.append(
            f"- [{ex.get('id')}] {ex.get('name')} | Category: {ex.get('category')} | "
            f"Muscle: {ex.get('muscle_group')} | Difficulty: {ex.get('difficulty')} | Equipment: {ex.get('equipment')}"
        )
    return "\n".join(result_lines)


def get_exercise_details(exercise_id: str) -> str:
    """Retrieves detailed information and instructions for a specific exercise by ID.

    Args:
        exercise_id: The unique ID of the exercise (e.g., 'barbell_bench_press', 'barbell_back_squat').

    Returns:
        A formatted string with full details and execution instructions for the exercise.
    """
    db = get_db()
    doc_ref = db.collection("exercises").document(exercise_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Exercise with ID '{exercise_id}' was not found in the database."

    data = doc.to_dict()
    return (
        f"Exercise Details for '{data.get('name')}' (ID: {doc.id}):\n"
        f"- Category: {data.get('category')}\n"
        f"- Target Muscle Group: {data.get('muscle_group')}\n"
        f"- Difficulty Level: {data.get('difficulty')}\n"
        f"- Equipment Needed: {data.get('equipment')}\n"
        f"- Instructions: {data.get('instructions')}"
    )


def add_exercise(
    exercise_id: str,
    name: str,
    category: str,
    muscle_group: str,
    difficulty: str,
    equipment: str,
    instructions: str,
) -> str:
    """Adds or updates an exercise document in the Firestore database.

    Args:
        exercise_id: Unique identifier for the exercise (e.g., 'dumbell_bicep_curl').
        name: Display name of the exercise (e.g., 'Dumbbell Bicep Curl').
        category: Category of workout (e.g., 'Arms', 'Chest', 'Legs').
        muscle_group: Targeted muscle groups (e.g., 'Biceps Brachii').
        difficulty: Skill level needed (e.g., 'Beginner', 'Intermediate', 'Advanced').
        equipment: Equipment required (e.g., 'Dumbbells').
        instructions: Step-by-step technique instructions.

    Returns:
        A confirmation message string.
    """
    db = get_db()
    exercise_data = {
        "id": exercise_id,
        "name": name,
        "category": category,
        "muscle_group": muscle_group,
        "difficulty": difficulty,
        "equipment": equipment,
        "instructions": instructions,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    db.collection("exercises").document(exercise_id).set(exercise_data)
    return f"Successfully added exercise '{name}' (ID: {exercise_id}) to Firestore."


def calculate_one_rep_max(weight_lifted: float, reps: int) -> str:
    """Calculates estimated One-Rep Max (1RM) using the Epley formula and computes working set weight targets for Strength, Hypertrophy, and Endurance.

    Args:
        weight_lifted: Weight lifted in lbs or kg.
        reps: Number of repetitions completed (must be between 1 and 30).

    Returns:
        A formatted string with estimated 1RM and target working set weights.
    """
    if reps <= 0:
        return "Error: Repetitions must be greater than 0."
    if weight_lifted <= 0:
        return "Error: Weight lifted must be greater than 0."

    if reps == 1:
        one_rep_max = weight_lifted
    else:
        # Epley Formula: 1RM = weight * (1 + reps / 30)
        one_rep_max = weight_lifted * (1.0 + (reps / 30.0))

    one_rep_max_rounded = round(one_rep_max, 1)

    # Calculate target working set weights
    strength_85 = round(one_rep_max * 0.85, 1)      # Heavy strength: 85% 1RM (~3-5 reps)
    hypertrophy_75 = round(one_rep_max * 0.75, 1)   # Muscle building: 75% 1RM (~8-12 reps)
    endurance_65 = round(one_rep_max * 0.65, 1)     # Muscular endurance: 65% 1RM (~15+ reps)

    return (
        f"1RM Calculation Results:\n"
        f"- Performance: {weight_lifted} for {reps} rep(s)\n"
        f"- Estimated 1RM: {one_rep_max_rounded}\n"
        f"- Target Working Set Weights:\n"
        f"  * Heavy Strength (85% 1RM, ~3-5 reps): {strength_85}\n"
        f"  * Hypertrophy / Muscle Building (75% 1RM, ~8-12 reps): {hypertrophy_75}\n"
        f"  * Muscular Endurance (65% 1RM, ~15+ reps): {endurance_65}"
    )


def log_workout_session(
    exercise_id: str,
    sets: int,
    reps: int,
    weight_lifted: float,
    notes: str = "",
) -> str:
    """Logs a completed workout session/set to the Firestore 'workout_logs' collection.

    Args:
        exercise_id: ID of exercise performed (e.g. 'barbell_bench_press').
        sets: Number of sets completed.
        reps: Number of reps per set.
        weight_lifted: Weight used in lbs or kg.
        notes: Optional notes or observations about the session.

    Returns:
        A confirmation message string.
    """
    db = get_db()
    log_data = {
        "exercise_id": exercise_id,
        "sets": sets,
        "reps": reps,
        "weight_lifted": weight_lifted,
        "notes": notes,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    doc_ref = db.collection("workout_logs").document()
    doc_ref.set(log_data)
    return f"Successfully logged workout session for '{exercise_id}' ({sets}x{reps} @ {weight_lifted}) to Firestore."


def fetch_public_exercise_info(query: str = "") -> str:
    """Fetches public exercise definitions and muscle targeted guides from the free wger Workout Manager public API.

    Args:
        query: Optional search keyword to filter exercises (e.g. 'Abs', 'Arms', 'Kettlebell', 'Bench').

    Returns:
        A formatted string listing exercises with categories, equipment, and targeted muscle groups from the wger public database.
    """
    import os
    import requests

    # Read optional API key from environment variable if configured
    api_key = os.getenv("WGER_API_KEY")
    headers = {"User-Agent": "FitCoachAI/1.0"}
    if api_key:
        headers["Authorization"] = f"Token {api_key}"

    url = "https://wger.de/api/v2/exerciseinfo/"
    params = {"limit": 15}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        formatted_exercises = []

        for item in results:
            cat_name = item.get("category", {}).get("name", "General")
            translations = item.get("translations", [])
            ex_name = translations[0].get("name", "Exercise") if translations else "Exercise"

            if query and query.lower() not in cat_name.lower() and query.lower() not in ex_name.lower():
                continue

            muscles = [
                m.get("name_en") or m.get("name")
                for m in item.get("muscles", [])
                if m.get("name_en") or m.get("name")
            ]
            muscle_str = ", ".join(muscles) if muscles else "Full Body"
            equip = [e.get("name") for e in item.get("equipment", []) if e.get("name")]
            equip_str = ", ".join(equip) if equip else "None"

            formatted_exercises.append(
                f"- {ex_name} | Category: {cat_name} | Target Muscles: {muscle_str} | Equipment: {equip_str}"
            )

        if not formatted_exercises:
            return f"No public exercise guides found matching '{query}' from wger API."

        return "wger Public Exercise Database Results:\n" + "\n".join(formatted_exercises[:5])
    except Exception as e:
        return f"Failed to fetch public exercise data from wger API: {e}"


def geocode_address(address: str) -> str:
    """Converts a street address or location name into geographic latitude and longitude coordinates using the Google Maps Geocoding API.

    Args:
        address: Street address, landmark, or location query (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'Times Square, NYC').

    Returns:
        A formatted string containing latitude, longitude, and formatted address.
    """
    import os
    import requests
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            return f"Geocoding failed for address '{address}': {data.get('status', 'No results')}"

        result = data["results"][0]
        formatted_address = result.get("formatted_address", address)
        location = result.get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")

        return f"Geocoding Result for '{address}':\n- Formatted Address: {formatted_address}\n- Latitude: {lat}\n- Longitude: {lng}"
    except Exception as e:
        return f"Failed to geocode address '{address}': {e}"


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "gym",
    radius_meters: float = 3000.0,
) -> str:
    """Finds nearby places of a specific type (e.g. 'gym', 'fitness_center', 'park') near a given location using the Google Places API (New).

    Args:
        latitude: Latitude coordinate of search center.
        longitude: Longitude coordinate of search center.
        place_type: Type of place to search for (e.g. 'gym', 'fitness_center', 'park', 'sports_complex').
        radius_meters: Radius in meters around location (default: 3000.0 meters).

    Returns:
        A formatted string listing nearby places with name, formatted address, and location coordinates.
    """
    import os
    import requests
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }

    body = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius_meters),
            }
        },
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=5)
        response.raise_for_status()
        data = response.json()

        places = data.get("places", [])
        if not places:
            return f"No nearby places of type '{place_type}' found within {radius_meters}m of ({latitude}, {longitude})."

        result_lines = [f"Found {len(places)} nearby place(s) of type '{place_type}':"]
        for p in places:
            display_name = p.get("displayName", {}).get("text", "Unknown Place")
            addr = p.get("formattedAddress", "No address provided")
            loc = p.get("location", {})
            lat = loc.get("latitude")
            lng = loc.get("longitude")
            result_lines.append(f"- Name: {display_name} | Address: {addr} | Location: ({lat}, {lng})")

        return "\n".join(result_lines)
    except Exception as e:
        return f"Failed to find nearby places: {e}"


async def generate_workout_visual(
    prompt: str, tool_context: ToolContext = None
) -> str:
    """Generates an image/visual for a fitness workout or exercise item using the gemini-3.1-flash-lite-image model in the global region.
    Saves the generated image artifact for the Playground UI and uploads the image bytes directly to a public Cloud Storage bucket.

    Args:
        prompt: Description of the workout image or motivational fitness poster to generate (e.g., 'Motivational bench press poster with cinematic lighting').
        tool_context: ADK ToolContext injected automatically.

    Returns:
        The public HTTPS URL of the generated image in Cloud Storage.
    """
    import uuid
    from google import genai
    from google.cloud import storage
    from google.genai import types

    filename = f"workout_visual_{uuid.uuid4().hex[:8]}.jpg"

    try:
        # Generate image using gemini-3.1-flash-lite-image in global region
        client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location="global")
        res = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        part = res.candidates[0].content.parts[0]
        image_bytes = part.inline_data.data
        mime_type = part.inline_data.mime_type or "image/jpeg"

        # (1) Save artifact if tool_context is provided (for Playground Artifacts panel)
        if tool_context and hasattr(tool_context, "save_artifact"):
            await tool_context.save_artifact(
                filename=filename,
                artifact=types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            )

        # (2) Upload image bytes directly to public Cloud Storage bucket and return public HTTPS URL
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_path = f"visuals/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_path}"
        return public_url
    except Exception as e:
        return f"Failed to generate workout visual: {e}"


async def generate_workout_video(
    prompt: str, tool_context: ToolContext = None
) -> str:
    """Generates a short fitness exercise or workout demonstration video using Google's Omni model (gemini-omni-flash-preview) in the global region.
    Saves the generated video artifact for the Playground UI and uploads the video bytes directly to a public Cloud Storage bucket.

    Args:
        prompt: Description of the fitness exercise or workout demonstration video to generate (e.g., 'A short video showing proper squat technique').
        tool_context: ADK ToolContext injected automatically.

    Returns:
        The public HTTPS URL of the generated video in Cloud Storage.
    """
    import base64
    import uuid
    from google import genai
    from google.cloud import storage
    from google.genai import types

    filename = f"workout_video_{uuid.uuid4().hex[:8]}.mp4"
    bucket_name = "fitcoach-ai-public-qwiklabs-gcp-03-1aaca47776f8"

    try:
        # Generate video using gemini-omni-flash-preview model in global region
        client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location="global")

        video_bytes = None

        # Primary method: client.interactions.create (Omni interaction model API)
        try:
            interaction = client.interactions.create(
                model="gemini-omni-flash-preview",
                input=prompt,
            )
            if hasattr(interaction, "output_video") and getattr(interaction.output_video, "data", None):
                raw = interaction.output_video.data
                video_bytes = base64.b64decode(raw) if isinstance(raw, str) else raw
            elif hasattr(interaction, "outputs") and interaction.outputs:
                for out in interaction.outputs:
                    if getattr(out, "type", None) == "video" and getattr(out, "data", None):
                        raw = out.data
                        video_bytes = base64.b64decode(raw) if isinstance(raw, str) else raw
                        break
        except Exception:
            pass

        # Fallback method: client.models.generate_videos
        if not video_bytes:
            try:
                import time
                operation = client.models.generate_videos(
                    model="gemini-omni-flash-preview",
                    prompt=prompt,
                )
                while not getattr(operation, "done", True):
                    time.sleep(4)
                    operation = client.operations.get(operation)
                if hasattr(operation, "response") and getattr(operation.response, "generated_videos", None):
                    gv = operation.response.generated_videos[0]
                    video_bytes = client.files.download(file=gv.video)
            except Exception:
                pass

        if not video_bytes:
            return "Failed to generate workout video: No video bytes returned from model."

        mime_type = "video/mp4"

        # (1) Save video artifact if tool_context is provided (for Playground Artifacts panel)
        if tool_context and hasattr(tool_context, "save_artifact"):
            await tool_context.save_artifact(
                filename=filename,
                artifact=types.Part.from_bytes(data=video_bytes, mime_type=mime_type),
            )

        # (2) Upload video bytes directly to public Cloud Storage bucket and return public HTTPS URL
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blob_path = f"videos/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
        return public_url
    except Exception as e:
        return f"Failed to generate workout video: {e}"


# Load Agent Engine resource name from deployment_metadata.json if available
agent_engine_id = None
deploy_meta_file = pathlib.Path(__file__).parent.parent / "deployment_metadata.json"
if deploy_meta_file.exists():
    try:
        with open(deploy_meta_file) as f:
            meta = json.load(f)
            agent_engine_id = meta.get("remote_agent_runtime_id")
    except Exception:
        pass

sandbox_code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_id
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends completed session events to Vertex AI Memory Bank for long-term facts & preferences extraction."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


def memory_service_builder():
    """Builds a VertexAiMemoryBankService connected to the deployed Agent Engine Memory Bank instance for production deployments."""
    mb_id = (agent_engine_id.split("/")[-1]) if agent_engine_id else "7593480189095444480"
    return VertexAiMemoryBankService(
        project=GCP_PROJECT_ID,
        location="us-east1",
        agent_engine_id=mb_id,
    )


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="You are FitCoach AI, an intelligent fitness, workout, and nutrition assistant.",
    workflow_description=(
        "Analyze the request and return structured UI when appropriate. "
        "You have access to a Firestore exercise database, logging tools, calculation tools, the wger public exercise API, Google Maps location tools, image and video generation tools, Python code execution, and long-term Memory Bank recall. "
        "Use your tools to list exercises, get detailed instructions, add new exercises, log workout sessions, calculate One-Rep Max (1RM) targets, "
        "fetch public exercise guides, geocode addresses to coordinates, search for nearby gyms and fitness places, generate workout visuals and videos, and recall user fitness goals, dietary restrictions, and allergies across sessions. "
        "IMPORTANT: Always remember and strictly observe all stated user allergies (e.g. food, supplement, or environmental allergies), dietary restrictions, and health conditions across all sessions, and ensure no recommended meals, supplements, or workout advice conflict with the user's recorded allergies."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
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


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=sandbox_code_executor,
    tools=[
        PreloadMemoryTool(),
        list_exercises,
        get_exercise_details,
        add_exercise,
        calculate_one_rep_max,
        log_workout_session,
        fetch_public_exercise_info,
        geocode_address,
        find_nearby_places,
        generate_workout_visual,
        generate_workout_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
