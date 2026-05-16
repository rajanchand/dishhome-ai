import asyncio
import logging
import struct
from typing import Dict

from app.config import settings

log = logging.getLogger("dishhome.audio")

class AudioSession:
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.buffer = bytearray()
        self.is_active = True

    async def process_frame(self, frame: bytes):
        # Here we would feed the frame into Silero VAD and then Faster-Whisper
        # For now, we just log the received frame size
        # log.debug(f"Received {len(frame)} bytes for {self.call_id}")
        pass

class AudioSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 4000):
        self.host = host
        self.port = port
        self.sessions: Dict[str, AudioSession] = {}

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        log.info(f"New AudioSocket connection from {addr}")

        try:
            # FreeSWITCH AudioSocket sends a UUID/CallID in the first few bytes or as a header
            # For simplicity, we'll assume a fixed header for now or generate one
            call_id = f"call_{addr[1]}"
            session = AudioSession(call_id)
            self.sessions[call_id] = session

            while True:
                data = await reader.read(320)  # 20ms of 8kHz mono PCM is 160 samples * 2 bytes = 320 bytes
                if not data:
                    break
                
                await session.process_frame(data)

        except Exception as e:
            log.error(f"Error in AudioSocket session: {e}")
        finally:
            log.info(f"Closing AudioSocket connection from {addr}")
            writer.close()
            await writer.wait_closed()

    async def start(self):
        server = await asyncio.start_server(self.handle_connection, self.host, self.port)
        addr = server.sockets[0].getsockname()
        log.info(f"AudioSocket server listening on {addr}")
        async with server:
            await server.serve_forever()

async def start_audio_server():
    server = AudioSocketServer(
        host=settings.freeswitch_audiosocket_host,
        port=settings.freeswitch_audiosocket_port
    )
    await server.start()
