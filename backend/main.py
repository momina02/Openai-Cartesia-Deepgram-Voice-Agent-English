import asyncio
import json
import aiohttp
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
import uuid
from pathlib import Path
import wave
from system_prompt import system_prompt
from openai import OpenAI

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Deepgram Realtime endpoint
DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen?"
    "model=nova-2&encoding=linear16&sample_rate=16000&channels=1"
)

# -------------------------------
# FastAPI setup
# -------------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Helper Functions
# -------------------------------
def create_session_folder(session_id):
    """Create a folder structure for the session"""
    base_path = Path("call_data") / session_id
    base_path.mkdir(parents=True, exist_ok=True)
    
    # Create subfolders
    (base_path / "audio_messages").mkdir(exist_ok=True)
    
    return base_path

def save_audio_message(session_path, audio_data, speaker, message_index):
    """Save individual audio message"""
    audio_path = session_path / "audio_messages" / f"{message_index:03d}_{speaker}.wav"
    with open(audio_path, "wb") as f:
        f.write(audio_data)
    return str(audio_path)

def append_to_transcription(session_path, speaker, text, timestamp):
    """Append a message to the transcription file"""
    transcription_file = session_path / f"transcription_{session_path.name}.txt"
    
    with open(transcription_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {speaker}: {text}\n\n")

# -------------------------------
# WebSocket Route
# -------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    # call_start = datetime.utcnow()
    call_start = datetime.now(timezone.utc)
    
    print(f"✅ Client connected!")
    print(f"📝 Session ID: {session_id}")
    print(f"⏰ Call started at: {call_start}")
    
    # Create session folder
    session_path = create_session_folder(session_id)
    
    # Initialize session data
    conversation_history = [{"role": "system", "content": system_prompt}]
    message_counter = 0
    complete_call_audio = []  # Store all audio chunks for complete recording
    call_ended_normally = False  # Track if call ended through normal flow
    
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(
            DEEPGRAM_URL,
            headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}
        ) as deepgram_ws:

            print("🎧 Connected to Deepgram WebSocket")

            initial_message = "Hello! This is Raqmi's complaint assistant speaking. How are you today?"

            async def send_tts_and_text(text, is_initial=False):
                """Send both text and audio to frontend, and save recordings"""
                nonlocal message_counter
                
                tts_url = "https://api.cartesia.ai/tts/bytes"
                headers = {
                    "Cartesia-Version": "2024-06-10",
                    "X-API-Key": CARTESIA_API_KEY,
                    "Content-Type": "application/json"
                }
                tts_payload = {
                    "model_id": "sonic-2",
                    "transcript": text,
                    "voice": {
                        "mode": "id",
                        "id": "f786b574-daa5-4673-aa0c-cbe3e8534c02"
                    },
                    "output_format": {
                        "container": "wav",
                        "encoding": "pcm_f32le",
                        "sample_rate": 44100
                    },
                    "language": "en",
                    "speed": "normal"
                }

                async with session.post(tts_url, headers=headers, json=tts_payload) as tts_response:
                    if tts_response.status == 200:
                        audio_data = await tts_response.read()
                        
                        # Save individual message audio
                        message_counter += 1
                        save_audio_message(session_path, audio_data, "bot", message_counter)
                        
                        # Add to complete call audio
                        complete_call_audio.append(audio_data)
                        
                        # Log to transcription
                        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %I:%M:%S %p")
                        
                        append_to_transcription(session_path, "Bot", text, timestamp)
                        
                        # Send to frontend
                        await websocket.send_text(f"Bot: {text}")
                        await websocket.send_bytes(audio_data)
                        
                        print(f"🔊 Sent audio [{message_counter}]: {text[:50]}...")
                    else:
                        error_text = await tts_response.text()
                        print(f"⚠️ Cartesia TTS error ({tts_response.status}): {error_text}")

            # Send initial greeting
            await send_tts_and_text(initial_message, is_initial=True)

            async def receive_from_deepgram():
                """Handle incoming transcriptions from Deepgram"""
                nonlocal message_counter, call_ended_normally
                
                async for msg in deepgram_ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)

                        if "channel" in data and "alternatives" in data["channel"]:
                            transcript = data["channel"]["alternatives"][0].get("transcript", "")
                            if transcript:
                                print("🗣️ Transcribed:", transcript)
                                
                                # Log user message to transcription
                                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %I:%M:%S %p")
                                
                                append_to_transcription(session_path, "User", transcript, timestamp)
                                
                                # Add user message to conversation history
                                conversation_history.append({"role": "user", "content": transcript})

                                # Get response from OpenAI
                                response = client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=conversation_history,
                                )

                                bot_reply = response.choices[0].message.content
                                conversation_history.append({"role": "assistant", "content": bot_reply})
                                
                                print("🤖 Bot:", bot_reply)

                                # Check if response contains JSON (end of call scenario)
                                text_part = ""
                                json_part = None
                                
                                # Try to find JSON in the response
                                if "{" in bot_reply and "}" in bot_reply:
                                    json_start = bot_reply.find("{")
                                    json_end = bot_reply.rfind("}") + 1
                                    
                                    if json_start >= 0 and json_end > json_start:
                                        text_part = bot_reply[:json_start].strip()
                                        json_str = bot_reply[json_start:json_end].strip()
                                        
                                        try:
                                            json_part = json.loads(json_str)
                                        except json.JSONDecodeError:
                                            text_part = bot_reply
                                            json_part = None
                                
                                # If we found valid JSON with end_call flag
                                if json_part and json_part.get("end_call"):
                                    # Mark that call ended normally
                                    call_ended_normally = True
                                    
                                    # First, send the goodbye message if there is one
                                    if text_part:
                                        await websocket.send_text(f"User: {transcript}")
                                        await send_tts_and_text(text_part)
                                        await asyncio.sleep(1)
                                    
                                    # Add call metadata
                                    call_end = datetime.now(timezone.utc)
                                    duration = (call_end - call_start).total_seconds()
                                    json_part["session_id"] = session_id
                                    json_part["call_start_time"] = call_start.isoformat()
                                    json_part["call_end_time"] = call_end.isoformat()
                                    json_part["call_duration_seconds"] = duration

                                    print("\n📊 FINAL CALL SUMMARY:")
                                    print(json.dumps(json_part, indent=4))

                                    # Save JSON summary to session folder
                                    with open(session_path / "call_summary.json", "w") as f:
                                        json.dump(json_part, f, indent=4)
                                    
                                    # Also append to main log file
                                    with open("call_log.json", "a") as f:
                                        json.dump(json_part, f)
                                        f.write("\n")
                                    
                                    # Save complete call audio
                                    if complete_call_audio:
                                        complete_audio_path = session_path / f"complete_call_{session_id}.wav"
                                        with open(complete_audio_path, "wb") as f:
                                            # Write the first audio file as-is (it has WAV header)
                                            if complete_call_audio:
                                                f.write(complete_call_audio[0])
                                                # For subsequent audio chunks, skip WAV header (first 44 bytes)
                                                for audio_chunk in complete_call_audio[1:]:
                                                    f.write(audio_chunk[44:])
                                        print(f"🎵 Saved complete call audio: {complete_audio_path}")

                                    # Close the connection
                                    await websocket.send_text("Bot: Call ended.")
                                    await websocket.close()
                                    return
                                
                                # Normal conversation - send text and audio to user
                                await websocket.send_text(f"User: {transcript}")
                                await send_tts_and_text(bot_reply)

            # Start listening to Deepgram in background
            asyncio.create_task(receive_from_deepgram())

            try:
                # Forward audio from client to Deepgram
                while True:
                    message = await websocket.receive()

                    if "bytes" in message and message["bytes"]:
                        await deepgram_ws.send_bytes(message["bytes"])

                    elif "text" in message:
                        data = message["text"]
                        print("Received text:", data)

            except Exception as e:
                print("❌ Client disconnected:", e)
                
                # Only save incomplete call data if the call didn't end normally
                if not call_ended_normally:
                    call_end = datetime.utcnow()
                    duration = (call_end - call_start).total_seconds()
                    
                    incomplete_summary = {
                        "session_id": session_id,
                        "call_start_time": call_start.isoformat(),
                        "call_end_time": call_end.isoformat(),
                        "call_duration_seconds": duration,
                        "status": "incomplete",
                        "reason": str(e)
                    }
                    
                    with open(session_path / "call_summary.json", "w") as f:
                        json.dump(incomplete_summary, f, indent=4)
                else:
                    print("✅ Call ended normally, skipping incomplete summary")

# -------------------------------
# Serve frontend AFTER WebSocket
# -------------------------------
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
