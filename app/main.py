import os
import json
import uuid
import asyncio
import tempfile
from pathlib import Path
from dotenv import load_dotenv

from google.genai.types import Part, Content
from google.adk.runners import Runner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from google.cloud import texttospeech

from Agents.agent import root_agent  # update this import path as needed

# Load environment
load_dotenv()

APP_NAME = "Modern Virtual Sales Assistant"
session_service = InMemorySessionService()
STATIC_DIR = Path("static")

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    await websocket.accept()
    session_id = str(session_id)
    live_events, live_request_queue = start_agent_session(session_id)
    agent_task = asyncio.create_task(agent_to_client_messaging(websocket, live_events))
    client_task = asyncio.create_task(client_to_agent_messaging(websocket, live_request_queue))
    await asyncio.gather(agent_task, client_task)

def start_agent_session(session_id: str):
    session = session_service.create_session(app_name=APP_NAME, user_id=session_id, session_id=session_id)
    runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)
    run_config = RunConfig(response_modalities=["TEXT"])
    live_request_queue = LiveRequestQueue()
    live_events = runner.run_live(session=session, live_request_queue=live_request_queue, run_config=run_config)
    return live_events, live_request_queue

async def agent_to_client_messaging(websocket, live_events):
    async for event in live_events:
        if event.turn_complete:
            await websocket.send_text(json.dumps({"turn_complete": True}))
        if event.interrupted:
            await websocket.send_text(json.dumps({"interrupted": True}))

        part: Part = event.content and event.content.parts and event.content.parts[0]
        if not part or not event.partial:
            continue

        text = part.text
        if text:
            await websocket.send_text(json.dumps({"message": text}))
            await asyncio.sleep(0)

async def client_to_agent_messaging(websocket, live_request_queue):
    while True:
        text = await websocket.receive_text()
        content = Content(role="user", parts=[Part.from_text(text=text)])
        live_request_queue.send_content(content=content)
        await asyncio.sleep(0)

@app.post("/tts")
async def synthesize_speech(request: Request):
    data = await request.json()
    text = data.get("text", "")

    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text.replace("x", " by "))

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Wavenet-D"
    )

    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio.write(response.audio_content)
        temp_audio_path = temp_audio.name

    return FileResponse(temp_audio_path, media_type="audio/mpeg")