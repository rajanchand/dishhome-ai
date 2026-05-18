import asyncio
import logging
import secrets
import struct
import numpy as np
from typing import Dict
from faster_whisper import WhisperModel
import os

from app.config import settings
from app.agent import run_conversation_agent

# AudioSocket protocol constants (per Asterisk res_audiosocket):
#   type 0x00 = HANGUP, 0x01 = ID (UUID), 0x02 = SILENCE, 0x03 = ERROR,
#   type 0x10 = SLIN audio payload (8kHz/16-bit/mono).
MSG_TYPE_HANGUP = 0x00
MSG_TYPE_ID = 0x01
MSG_TYPE_ERROR = 0x03
MSG_TYPE_AUDIO = 0x10

# Defensive caps — the wire format permits a 16-bit length so an attacker
# could ask us to allocate up to 65 KB per frame. SLIN frames at 20 ms / 8 kHz
# are 320 bytes; UUID identifiers are 16 bytes. Anything wildly larger is a
# protocol violation, not a legitimate caller.
MAX_AUDIO_PAYLOAD = 4096
MAX_ID_PAYLOAD = 64

try:
    from piper import PiperVoice
    HAS_PIPER = True
except ImportError:
    HAS_PIPER = False

log = logging.getLogger("dishhome.audio")

class AudioSession:
    def __init__(self, call_id: str, asr_model: WhisperModel, tts_voice=None):
        self.call_id = call_id
        self.asr_model = asr_model
        self.tts_voice = tts_voice
        self.audio_buffer = bytearray()
        self.silence_frames = 0
        self.is_speaking = False

    async def process_frame(self, frame: bytes, writer: asyncio.StreamWriter):
        self.audio_buffer.extend(frame)
        
        # Simple energy-based VAD (Replace with Silero in production)
        audio_array = np.frombuffer(frame, dtype=np.int16)
        energy = np.abs(audio_array).mean()
        
        if energy > 500:
            self.silence_frames = 0
            self.is_speaking = True
        else:
            self.silence_frames += 1
            
        # Utterance complete if silent for > 1s
        if self.is_speaking and self.silence_frames > 50:
            audio_np = np.frombuffer(self.audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
            # Faster-Whisper expects 16kHz
            audio_16k = np.repeat(audio_np, 2)
            
            log.info(f"[{self.call_id}] Running ASR...")
            # We must run this in an executor to avoid blocking the asyncio loop!
            loop = asyncio.get_running_loop()
            segments, info = await loop.run_in_executor(None, lambda: self.asr_model.transcribe(audio_16k, beam_size=1, language="en"))
            text = "".join([s.text for s in segments]).strip()
            
            self.audio_buffer.clear()
            self.is_speaking = False
            self.silence_frames = 0
            
            if text:
                log.info(f"[{self.call_id}] Customer: {text}")
                # Dispatch the agent and TTS (pass self.tts_voice if we have one)
                # Note: To pass tts_voice, we need it on the session
                await self.run_agent_and_tts(text, writer, self.tts_voice)
                
        # Guard against buffer bloat
        if not self.is_speaking and len(self.audio_buffer) > 16000 * 5:
            self.audio_buffer.clear()

    async def run_agent_and_tts(self, text: str, writer: asyncio.StreamWriter, tts_voice=None):
        # 1. LLM / LangGraph Agent
        response_text = await run_conversation_agent(self.call_id, text)
        log.info(f"[{self.call_id}] Agent: {response_text}")
        
        # 2. Piper TTS Stream
        if tts_voice:
            # Piper outputs 16kHz raw PCM by default, we need 8kHz for AudioSocket
            # We will use simple decimation (drop every other sample) for 16k -> 8k
            # This is a naive downsample for performance.
            audio_stream = tts_voice.synthesize_stream_raw(response_text)
            for raw_chunk in audio_stream:
                # raw_chunk is 16-bit 16kHz PCM bytes
                # Convert to numpy, downsample to 8kHz, convert back to bytes
                np_chunk = np.frombuffer(raw_chunk, dtype=np.int16)
                np_8k = np_chunk[::2]
                chunk_8k = np_8k.tobytes()
                
                # Send to AudioSocket in chunks of 320 bytes (20ms)
                for i in range(0, len(chunk_8k), 320):
                    sub_chunk = chunk_8k[i:i+320]
                    if len(sub_chunk) == 320:
                        out_header = bytes([16]) + len(sub_chunk).to_bytes(2, byteorder='big')
                        writer.write(out_header + sub_chunk)
                        await writer.drain()
        else:
            # Fallback Dummy PCM
            dummy_pcm = b"\x00\x00" * 8000 # 1 second of silence
            chunk_size = 320 # 20ms at 8000Hz 16-bit
            for i in range(0, len(dummy_pcm), chunk_size):
                chunk = dummy_pcm[i:i+chunk_size]
                out_header = bytes([16]) + len(chunk).to_bytes(2, byteorder='big')
                writer.write(out_header + chunk)
                await writer.drain()

class AudioSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 4000):
        self.host = host
        self.port = port
        self.sessions: Dict[str, AudioSession] = {}
        log.info("Loading ASR model...")
        self.asr_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        
        self.tts_voice = None
        model_path = os.path.join(os.path.dirname(__file__), "en_US-lessac-medium.onnx")
        if HAS_PIPER and os.path.exists(model_path):
            log.info("Loading TTS model...")
            self.tts_voice = PiperVoice.load(model_path)
        else:
            log.warning("Piper TTS model not found or piper not installed. Using dummy audio fallback.")

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        log.info(f"New AudioSocket connection from {addr}")

        # Generate the session key *server-side*. Earlier code used the raw
        # UUID payload sent by the peer as the dict key, which lets a malicious
        # caller pick the key (and therefore collide with / hijack another
        # active session). The peer's UUID is still logged for cross-referencing
        # with the SIP/FreeSWITCH side.
        call_id = secrets.token_hex(16)
        peer_id: str | None = None
        session: AudioSession | None = None

        try:
            header = await reader.readexactly(3)
            msg_type = header[0]
            payload_len = int.from_bytes(header[1:3], byteorder='big')
            if msg_type != MSG_TYPE_ID or payload_len > MAX_ID_PAYLOAD:
                log.warning(
                    "Rejecting AudioSocket %s: first frame type=0x%02x len=%d",
                    addr, msg_type, payload_len,
                )
                return
            peer_id = (await reader.readexactly(payload_len)).hex() if payload_len else ""

            session = AudioSession(call_id, self.asr_model, self.tts_voice)
            self.sessions[call_id] = session
            log.info("[%s] AudioSocket session opened (peer_id=%s)", call_id, peer_id or "<none>")

            while True:
                header = await reader.readexactly(3)
                msg_type = header[0]
                payload_len = int.from_bytes(header[1:3], byteorder='big')

                if msg_type == MSG_TYPE_AUDIO:
                    if payload_len == 0 or payload_len > MAX_AUDIO_PAYLOAD:
                        log.warning("[%s] Dropping oversized audio frame: %d bytes", call_id, payload_len)
                        # Still consume the bytes to stay framed; cap allocation.
                        remaining = payload_len
                        while remaining:
                            chunk = await reader.read(min(remaining, MAX_AUDIO_PAYLOAD))
                            if not chunk:
                                raise asyncio.IncompleteReadError(b"", remaining)
                            remaining -= len(chunk)
                        continue
                    payload = await reader.readexactly(payload_len)
                    await session.process_frame(payload, writer)
                elif msg_type in (MSG_TYPE_HANGUP, MSG_TYPE_ERROR):
                    log.info(f"[{call_id}] Connection ended (type=0x{msg_type:02x})")
                    break
                else:
                    # Unknown frame: skip its payload but keep the stream framed.
                    if payload_len:
                        if payload_len > MAX_AUDIO_PAYLOAD:
                            log.warning("[%s] Unknown frame with oversized len=%d, closing", call_id, payload_len)
                            break
                        await reader.readexactly(payload_len)

        except asyncio.IncompleteReadError:
            log.info(f"AudioSocket connection closed by peer {addr}")
        except Exception as e:
            log.error(f"Error in AudioSocket session [{call_id}]: {e}", exc_info=True)
        finally:
            log.info(f"Cleaning up AudioSocket connection from {addr} [{call_id}]")
            self.sessions.pop(call_id, None)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        server = await asyncio.start_server(self.handle_connection, self.host, self.port)
        addr = server.sockets[0].getsockname()
        log.info(f"AudioSocket server listening on {addr}")
        async with server:
            await server.serve_forever()

async def start_audio_server():
    if not settings.enable_audio_server:
        log.info("Audio server disabled via config.")
        return
        
    server = AudioSocketServer(
        host=settings.freeswitch_audiosocket_host,
        port=settings.freeswitch_audiosocket_port
    )
    await server.start()
