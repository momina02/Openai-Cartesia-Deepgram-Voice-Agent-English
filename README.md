# English Voice Agent (OpenAI + Cartesia + Deepgram)

<p align="left">
  <img src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/WebSockets-333333?style=for-the-badge&logo=websocket&logoColor=white"/>
  <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white"/>
  <img src="https://img.shields.io/badge/Deepgram-1A73E8?style=for-the-badge&logo=deepgram&logoColor=white"/>
  <img src="https://img.shields.io/badge/Cartesia-EE4C2C?style=for-the-badge&logoColor=white"/>
</p>

A real-time **English voice agent** built with **OpenAI Realtime API**, **Cartesia TTS**, and **Deepgram STT**. This agent listens, transcribes, thinks, and speaks back instantly using streaming audio.

---

## 🚀 Features

* Real-time speech-to-text (Deepgram)
* Natural conversation reasoning (OpenAI Realtime API)
* High‑quality text‑to‑speech (Cartesia)
* Works fully on WebSockets for low latency
* Plug‑and‑play Python implementation

---

## 📂 Project Structure

```
├── app.py                # Main FastAPI server
├── agent.py              # Voice agent processing logic
├── websocket_manager.py  # WebSocket streaming utilities
├── requirements.txt      # Dependencies
└── README.md
```

---

## ▶️ Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/momina02/Openai-Cartesia-Deepgram-Voice-Agent-English.git
cd Openai-Cartesia-Deepgram-Voice-Agent-English
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your API keys to `.env`

```
OPENAI_API_KEY=your_key
DEEPGRAM_API_KEY=your_key
CARTESIA_API_KEY=your_key
```

### 4. Run the server

```bash
python app.py
```

---

## 🎤 How It Works

1. Client streams microphone audio → server.
2. Deepgram converts audio to text in real time.
3. OpenAI Realtime API generates a response.
4. Cartesia converts response text to speech.
5. Speech is streamed back to the client.

---

## 🤝 Contributing

Pull requests are welcome! If you'd like a new feature (like Urdu support or UI), feel free to open an issue.

---

## 📄 License

MIT License.

