// let socket;

// document.getElementById("callBtn").addEventListener("click", () => {
//   socket = new WebSocket("ws://localhost:8000/ws");

//   socket.onopen = () => {
//     console.log("✅ Connected to backend");
//     socket.send("Hello backend!");
//   };

//   socket.onmessage = (event) => {
//     console.log("Message from backend:", event.data);
//   };

//   socket.onclose = () => {
//     console.log("❌ Disconnected from backend");
//   };
// });

// ===== STEP 3

let socket;

document.getElementById("callBtn").addEventListener("click", async () => {
  // Connect to WebSocket
  // socket = new WebSocket("ws://localhost:8000/ws");

  // Dynamically detect the correct WebSocket URL
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socketUrl = `${protocol}//${window.location.host}/ws`;
  socket = new WebSocket(socketUrl);
  console.log(`🌐 Connecting to WebSocket at: ${socketUrl}`);

  socket.onopen = async () => {
    console.log("✅ Connected to backend");

    // Request microphone access
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    console.log("🎤 Microphone access granted");

    // Create AudioContext with 16kHz sample rate
    const audioContext = new AudioContext({ sampleRate: 16000 });
    const source = audioContext.createMediaStreamSource(stream);

    // Create a ScriptProcessorNode to capture raw PCM data
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    source.connect(processor);
    processor.connect(audioContext.destination);

    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      const buffer = new ArrayBuffer(input.length * 2);
      const view = new DataView(buffer);
      let offset = 0;

      for (let i = 0; i < input.length; i++, offset += 2) {
        let s = Math.max(-1, Math.min(1, input[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      }

      // Send PCM bytes to backend WebSocket
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(buffer);
      }
    };

    console.log("🎧 Streaming microphone audio...");
  };

  // socket.onmessage = (event) => {
  //   console.log("📩 Message from backend:", event.data);
  // };

  socket.onmessage = async (event) => {
    if (typeof event.data === "string") {
      console.log("📩 Message from backend:", event.data);
      // This handles text (User and Bot messages)
    } else if (event.data instanceof Blob) {
      console.log("🎵 Received audio blob:", event.data);

      // Convert Blob to playable audio
      const arrayBuffer = await event.data.arrayBuffer();
      const audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.start(0);

      console.log("🔊 Playing bot audio response...");
    }
  };

  socket.onclose = () => {
    console.log("❌ Disconnected from backend");
  };

  socket.onerror = (error) => {
    console.error("⚠️ WebSocket error:", error);
  };
});
