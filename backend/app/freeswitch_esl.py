import asyncio
import logging
from typing import Optional

log = logging.getLogger("dishhome.esl")

class ESLClient:
    """
    A lightweight, asyncio-based FreeSWITCH ESL (Event Socket Library) client.
    Connects to FreeSWITCH to monitor call events and bridge them to the frontend.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 8021, password: str = "ClueCon"):
        self.host = host
        self.port = port
        self.password = password
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._running = False

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self._running = True
            log.info(f"Connected to FreeSWITCH ESL on {self.host}:{self.port}")
            
            # Authenticate
            await self._send_command(f"auth {self.password}")
            
            # Subscribe to events
            await self._send_command("event plain CHANNEL_ANSWER CHANNEL_HANGUP")
            
            # Start listener loop
            asyncio.create_task(self._listen())
        except ConnectionRefusedError:
            log.warning(f"Could not connect to FreeSWITCH ESL on {self.host}:{self.port}. Is FreeSWITCH running?")
            self._running = False
        except Exception as e:
            log.error(f"FreeSWITCH ESL Connection error: {e}")
            self._running = False

    async def _send_command(self, cmd: str):
        if self.writer:
            self.writer.write(f"{cmd}\n\n".encode("utf-8"))
            await self.writer.drain()

    async def _listen(self):
        buffer = ""
        while self._running and self.reader:
            try:
                line = await self.reader.readline()
                if not line:
                    break
                decoded = line.decode("utf-8")
                
                # Simple parsing for demo purposes
                if "Event-Name: CHANNEL_ANSWER" in decoded:
                    log.info("ESL: Channel Answered")
                    # Here we would parse headers and push to WebSocket
                    
                if "Event-Name: CHANNEL_HANGUP" in decoded:
                    log.info("ESL: Channel Hung Up")
                    
            except Exception as e:
                log.error(f"ESL listen error: {e}")
                break
        
        self.disconnect()

    def disconnect(self):
        self._running = False
        if self.writer:
            self.writer.close()

# Global singleton
esl_client = ESLClient()

async def start_esl():
    await esl_client.connect()
