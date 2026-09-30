#!/usr/bin/env python3
"""
Gateway Bridge - Async Gateway Compatibility Layer
Allows async_gateway.py to work with existing synchronous bot.py
"""

import asyncio
import threading
import time
import json
from typing import Dict, Any, Callable, Optional
from async_gateway import AsyncDiscordGateway

class GatewayBridge:
    """
    Bridges async gateway events to synchronous bot callbacks.
    Runs async gateway in background thread while maintaining sync compatibility.
    """

    def __init__(self, token: str, compress: bool = True, client_type: str = "web"):
        self.token = token
        self.compress = compress
        self.client_type = client_type

        # Async gateway instance
        self.gateway = AsyncDiscordGateway(token, client_type, compress)

        # Sync callback storage
        self._sync_callbacks = {
            'on_ready': None,
            'on_message': None,
            'on_payload': None,
            'on_guild_create': None,
            'on_guild_update': None,
            'on_guild_delete': None,
            'on_channel_create': None,
            'on_channel_update': None,
            'on_channel_delete': None,
            'on_guild_member_add': None,
            'on_guild_member_remove': None,
            'on_guild_member_update': None,
            'on_presence_update': None,
            'on_typing_start': None,
            'on_message_delete': None,
            'on_message_update': None,
            'on_reaction_add': None,
            'on_reaction_remove': None,
            'on_error': None,
            'on_close': None,
        }

        # Bridge state
        self.running = False
        self.thread = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._shutdown_event = threading.Event()

        # Connection state (for compatibility with bot.py)
        self.connection_active = False
        self.gateway_latency_ms = None
        self.session_id = None
        self.resume_gateway_url = None
        self.can_resume = False

    def set_callback(self, event_type: str, callback: Callable):
        """Set synchronous callback for gateway events"""
        if event_type in self._sync_callbacks:
            self._sync_callbacks[event_type] = callback

    def on_ready(self, callback: Callable):
        """Set ready event callback"""
        self.set_callback('on_ready', callback)

    def on_message(self, callback: Callable):
        """Set message event callback"""
        self.set_callback('on_message', callback)

    def on_payload(self, callback: Callable):
        """Set raw payload callback"""
        self.set_callback('on_payload', callback)

    def on_error(self, callback: Callable):
        """Set error event callback"""
        self.set_callback('on_error', callback)

    def on_close(self, callback: Callable):
        """Set close event callback"""
        self.set_callback('on_close', callback)

    def start(self):
        """Start the gateway bridge in background thread"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_async_loop, name="AsyncGatewayBridge")
        self.thread.start()

        # Wait for connection
        timeout = 30
        start_time = time.time()
        while self.running and not self.connection_active and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if not self.connection_active:
            self.stop()
            raise Exception("Gateway bridge failed to connect within 30 seconds")

    def stop(self):
        """Stop the gateway bridge"""
        self.running = False
        self._shutdown_event.set()
        loop = self._loop
        if loop and loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(self.gateway.close(), loop)
                future.result(timeout=3)
            except Exception:
                pass

        if self.thread and self.thread.is_alive() and self.thread is not threading.current_thread():
            self.thread.join(timeout=5)
        self.connection_active = False

    def close(self):
        """Keep the WebSocketApp-compatible close entrypoint used by DiscordBot."""
        self.stop()

    def _run_async_loop(self):
        """Run the async gateway in a separate thread"""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._async_main())
        except Exception as e:
            print(f"❌ Gateway bridge error: {e}")
            if self._sync_callbacks['on_error']:
                try:
                    self._sync_callbacks['on_error'](e)
                except Exception:
                    pass
        finally:
            self.running = False
            self.connection_active = False
            if self._loop and not self._loop.is_closed():
                self._loop.close()
            self._loop = None

    async def _async_main(self):
        """Main async gateway loop"""
        # Set up event handlers to bridge to sync callbacks
        self.gateway.on_ready = self._bridge_ready
        self.gateway.on_message = self._bridge_message
        self.gateway.on_error = self._bridge_error
        self.gateway.on_close = self._bridge_close
        self.gateway.on_payload = self._bridge_payload

        # Add custom event handlers for other Discord events
        original_on_event = self.gateway.on_event

        def bridged_on_event(event_type, data):
            # Call original handler
            if original_on_event:
                original_on_event(event_type, data)

            # Bridge to sync callbacks
            self._bridge_event(event_type, data)

        self.gateway.on_event = bridged_on_event

        try:
            await self.gateway.connect()
        except Exception as e:
            print(f"❌ Gateway bridge connection failed: {e}")
            if self._sync_callbacks['on_error']:
                try:
                    self._sync_callbacks['on_error'](e)
                except Exception:
                    pass

    def _bridge_ready(self, data: Dict[str, Any]):
        """Bridge READY event to sync callback"""
        self.connection_active = True
        self.session_id = data.get('session_id')
        self.resume_gateway_url = data.get('resume_gateway_url')
        self.can_resume = True

        # Update latency if available
        if hasattr(self.gateway, 'latency'):
            self.gateway_latency_ms = self.gateway.latency * 1000

        if self._sync_callbacks['on_ready']:
            try:
                self._sync_callbacks['on_ready'](data)
            except Exception as e:
                print(f"❌ Error in on_ready callback: {e}")

    def _bridge_message(self, data: Dict[str, Any]):
        """Bridge MESSAGE_CREATE event to sync callback"""
        if self._sync_callbacks['on_message']:
            try:
                self._sync_callbacks['on_message'](data)
            except Exception as e:
                print(f"❌ Error in on_message callback: {e}")

    def _bridge_error(self, error):
        """Bridge error event to sync callback"""
        if self._sync_callbacks['on_error']:
            try:
                self._sync_callbacks['on_error'](error)
            except Exception as e:
                print(f"❌ Error in on_error callback: {e}")

    def _bridge_close(self, code: int, reason: str):
        """Bridge close event to sync callback"""
        self.connection_active = False
        if self._sync_callbacks['on_close']:
            try:
                self._sync_callbacks['on_close'](code, reason)
            except Exception as e:
                print(f"❌ Error in on_close callback: {e}")

    def _bridge_event(self, event_type: str, data: Dict[str, Any]):
        """Bridge other Discord events to sync callbacks"""
        callback_name = f'on_{event_type.lower()}'
        if callback_name in self._sync_callbacks and self._sync_callbacks[callback_name]:
            try:
                self._sync_callbacks[callback_name](data)
            except Exception as e:
                print(f"❌ Error in {callback_name} callback: {e}")

    def _bridge_payload(self, payload: Dict[str, Any]):
        """Bridge raw payloads to sync callback"""
        callback = self._sync_callbacks.get('on_payload')
        if callback:
            try:
                callback(payload)
            except Exception as e:
                print(f"❌ Error in on_payload callback: {e}")

    # Compatibility methods for bot.py
    def get_gateway_latency_metrics(self) -> Dict[str, Any]:
        """Return gateway latency metrics (for compatibility)"""
        return {
            'latency_ms': self.gateway_latency_ms,
            'connected': self.connection_active,
            'compressed': self.compress,
            'client_type': self.client_type,
        }

    def send_message(self, channel_id: str, content: str, **kwargs):
        """Send message through async gateway"""
        if not self.connection_active:
            raise Exception("Gateway not connected")

        # This would need to be implemented in async_gateway.py
        # For now, return None to indicate not implemented
        return None

    def send(self, message: str):
        """WebSocket-compatible send method used by legacy bot code."""
        try:
            payload = json.loads(message)
        except Exception:
            return
        self.send_json(payload)

    def send_json(self, payload: Dict[str, Any]) -> bool:
        """Thread-safe JSON send over async gateway."""
        if not self._loop or not self.running:
            return False
        try:
            fut = asyncio.run_coroutine_threadsafe(self.gateway.send_json(payload), self._loop)
            return bool(fut.result(timeout=3))
        except Exception:
            return False

    def __del__(self):
        """Cleanup on destruction"""
        self.stop()