import asyncio
import websockets
import json
import time
import threading
import zlib
from typing import Optional, Dict, Any, Callable
from core.client.platform import build_identify_payload
from discord_api_types import DEFAULT_GATEWAY_INTENTS

class AsyncDiscordGateway:
    """Async Discord Gateway client with zlib-stream compression support"""

    def __init__(self, token: str, client_type: str = "web", compress: bool = True):
        self.token = token
        self.client_type = client_type
        self.compress = compress
        self.ws: Optional[websockets.WebSocketServerProtocol] = None
        self.sequence: Optional[int] = None
        self.session_id: Optional[str] = None
        self.heartbeat_interval: Optional[float] = None
        self.last_heartbeat: float = time.time()
        self.connected = False
        self.identified = False

        # Compression support
        self.decompressor: Optional[zlib.decompressobj] = None
        self.buffer = bytearray()

        # Callbacks
        self.on_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_ready: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_close: Optional[Callable[[int, str], None]] = None
        self.on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self.on_payload: Optional[Callable[[Dict[str, Any]], None]] = None

    async def connect(self):
        """Connect to Discord Gateway with optional compression"""
        base_url = "wss://gateway.discord.gg/?v=10&encoding=json"
        url = base_url + ("&compress=zlib-stream" if self.compress else "")

        # Initialize compression if enabled
        if self.compress:
            self.decompressor = zlib.decompressobj()
            self.buffer = bytearray()

        try:
            async with websockets.connect(url) as websocket:
                self.ws = websocket
                self.connected = True
                print(f"🔌 Connected to Discord Gateway {'(compressed)' if self.compress else '(uncompressed)'}")

                # Start heartbeat task
                heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                try:
                    async for message in websocket:
                        if self.compress:
                            await self._handle_compressed_message(message)
                        else:
                            await self._handle_message(message)
                except websockets.exceptions.ConnectionClosed as e:
                    print("🔌 Gateway connection closed")
                    if self.connected and self.on_close:
                        try:
                            self.on_close(int(getattr(e, "code", 1000) or 1000), str(getattr(e, "reason", "")))
                        except Exception:
                            pass
                finally:
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
                    self.connected = False
                    self.identified = False
                    self.ws = None

        except Exception as e:
            print(f"❌ Gateway connection error: {e}")
            if self.on_error:
                self.on_error(e)

    async def close(self):
        """Close the active websocket so the owning bridge can be restarted."""
        self.connected = False
        websocket = self.ws
        if websocket is not None:
            try:
                await websocket.close()
            except Exception:
                pass

    async def _handle_compressed_message(self, message: bytes):
        """Handle zlib-stream compressed messages"""
        try:
            # Add new data to buffer
            self.buffer.extend(message)

            # Check if this is the end of a data packet (ends with 0x00 0x00 0xff 0xff)
            if len(message) >= 4 and message[-4:] == b'\x00\x00\xff\xff':
                # Decompress the buffer
                decompressed = self.decompressor.decompress(self.buffer)

                # Handle multiple messages in one packet (split by newlines)
                messages = decompressed.decode('utf-8').strip().split('\n')

                for msg in messages:
                    if msg.strip():
                        await self._handle_message(msg)

                # Clear buffer for next packet
                self.buffer = bytearray()

        except Exception as e:
            print(f"❌ Error decompressing message: {e}")
            # Fallback to treating as uncompressed
            try:
                await self._handle_message(message.decode('utf-8'))
            except:
                print("❌ Failed to handle message as uncompressed too")

    async def _handle_message(self, message: str):
        """Handle incoming gateway messages"""
        try:
            data = json.loads(message)
            op = data.get('op')
            event_type = data.get('t')
            event_data = data.get('d')

            if self.on_payload:
                try:
                    self.on_payload(data)
                except Exception:
                    pass

            # Update sequence
            if 's' in data and data['s'] is not None:
                self.sequence = data['s']

            # Handle different opcodes
            if op == 10:  # Hello
                self.heartbeat_interval = event_data['heartbeat_interval'] / 1000
                await self._identify()
                print(f"📡 Heartbeat interval: {self.heartbeat_interval}s")

            elif op == 11:  # Heartbeat ACK
                self.last_heartbeat = time.time()
                print("💓 Heartbeat acknowledged")

            elif op == 0:  # Dispatch (events)
                await self._handle_event(event_type, event_data)

            elif op == 9:  # Invalid Session
                print("❌ Invalid session, reconnecting...")
                self.identified = False
                await asyncio.sleep(5)
                await self._identify()

            elif op == 7:  # Reconnect
                print("🔄 Gateway requested reconnect")
                self.connected = False
                websocket = self.ws
                if websocket is not None:
                    await websocket.close()
                if self.on_close:
                    self.on_close(4000, "Gateway requested reconnect")
                return

        except json.JSONDecodeError:
            print(f"❌ Failed to parse message: {message}")
        except Exception as e:
            print(f"❌ Error handling message: {e}")

    async def _handle_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle Discord events"""
        if event_type == 'READY':
            self.session_id = event_data.get('session_id')
            user = event_data.get('user', {})
            username = user.get('username', 'Unknown')
            user_id = user.get('id', 'Unknown')
            self.identified = True
            print(f"✅ READY! Logged in as {username} ({user_id})")

            if self.on_ready:
                self.on_ready(event_data)

        elif event_type == 'MESSAGE_CREATE':
            if self.on_message:
                self.on_message(event_data)

        if self.on_event:
            try:
                self.on_event(event_type, event_data)
            except Exception:
                pass

        # Add more event handlers as needed

    async def _identify(self):
        """Identify using the same supported client profile as the legacy gateway."""
        if self.identified:
            print("Already identified, skipping duplicate IDENTIFY")
            return

        identify_payload = build_identify_payload(
            token=self.token,
            client_type=self.client_type,
            status="online",
            intents=DEFAULT_GATEWAY_INTENTS,
            compress=False,
        )
        await self.ws.send(json.dumps(identify_payload))
        print(f"Sent gateway IDENTIFY for client profile '{self.client_type}'")

    async def _heartbeat_loop(self):
        """Maintain heartbeat to keep connection alive"""
        await asyncio.sleep(self.heartbeat_interval * 0.1)  # Small delay before first heartbeat

        while self.connected:
            if self.heartbeat_interval:
                heartbeat_payload = {
                    "op": 1,  # Heartbeat
                    "d": self.sequence
                }

                try:
                    await self.ws.send(json.dumps(heartbeat_payload))
                    print(f"💓 Sent heartbeat (seq: {self.sequence})")
                    await asyncio.sleep(self.heartbeat_interval)
                except Exception as e:
                    print(f"❌ Heartbeat error: {e}")
                    break
            else:
                await asyncio.sleep(1)

    async def send_message(self, channel_id: str, content: str):
        """Send a message (requires MESSAGE_CREATE permission)"""
        if not self.identified:
            print("❌ Not identified, cannot send message")
            return

        message_payload = {
            "type": 0,
            "content": content,
            "tts": False,
            "flags": 0
        }

        # This would need to be sent via HTTP API, not gateway
        # Gateway is for receiving events, HTTP API for sending
        print(f"📤 Would send message to {channel_id}: {content}")
        print("💡 Note: Messages should be sent via Discord HTTP API, not gateway")

    async def send_json(self, payload: Dict[str, Any]) -> bool:
        """Send a JSON payload over the gateway connection."""
        if not self.ws or not self.connected:
            return False
        try:
            await self.ws.send(json.dumps(payload))
            return True
        except Exception:
            return False

    def run(self):
        """Run the gateway client"""
        asyncio.run(self.connect())

# Example usage
async def main():
    # Replace with your actual token
    token = "YOUR_DISCORD_TOKEN_HERE"

    gateway = AsyncDiscordGateway(token)

    # Set up event handlers
    def on_ready(data):
        print("🎉 Bot is ready!")

    def on_message(data):
        content = data.get('content', '')
        author = data.get('author', {}).get('username', 'Unknown')
        print(f"📨 {author}: {content}")

    gateway.on_ready = on_ready
    gateway.on_message = on_message

    await gateway.connect()

if __name__ == "__main__":
    # Run with: python async_gateway.py
    client = AsyncDiscordGateway("YOUR_TOKEN_HERE")
    client.run()