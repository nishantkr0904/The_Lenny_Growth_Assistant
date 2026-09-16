"""Python Client for the Production Pi Coding Agent Bridge Daemon.

Manages child process lifecycle, JSON-RPC 2.0 communication over stdio,
turn execution, real-time streaming, and clean process termination.
"""

import asyncio
import atexit
import json
import logging
import os
import time
from typing import Any, AsyncGenerator, Optional
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger("lenny_assistant.agent.pi_bridge")
settings = get_settings()

DAEMON_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "bridge_daemon.mjs")


class PiTurnResult(BaseModel):
    """Result of a completed conversational turn executed by Pi."""

    content: str
    tier: str
    top_score: float
    can_synthesize: bool
    model_used: str
    selected_evidence: list[dict[str, Any]] = []
    duration_ms: int = 0
    generation_failed: bool = False
    error_detail: Optional[str] = None


class PiBridgeClient:
    """Async client managing the long-running Pi Coding Agent bridge subprocess."""

    _instance: Optional["PiBridgeClient"] = None

    def __init__(self, script_path: Optional[str] = None) -> None:
        self.script_path = script_path or DAEMON_SCRIPT_PATH
        self._process: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()
        self._request_counter = 0
        self._is_started = False

    @classmethod
    def get_instance(cls) -> "PiBridgeClient":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the Pi bridge daemon child process."""
        if self._process is not None and self._process.returncode is None:
            return  # Already running

        cmd = ["node", self.script_path]
        logger.info("Starting Pi bridge daemon subprocess: %s", " ".join(cmd))

        env = os.environ.copy()
        env["OLLAMA_BASE_URL"] = settings.OLLAMA_BASE_URL
        env["OLLAMA_MODEL"] = settings.OLLAMA_MODEL
        env["LLM_PROVIDER"] = settings.LLM_PROVIDER
        if settings.ANTHROPIC_API_KEY:
            env["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
        if settings.ANTHROPIC_MODEL:
            env["ANTHROPIC_MODEL"] = settings.ANTHROPIC_MODEL
        if settings.GEMINI_API_KEY:
            env["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        if settings.GEMINI_MODEL:
            env["GEMINI_MODEL"] = settings.GEMINI_MODEL
        if settings.OPENAI_API_KEY:
            env["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        if settings.OPENAI_MODEL:
            env["OPENAI_MODEL"] = settings.OPENAI_MODEL
        if settings.GROQ_API_KEY:
            env["GROQ_API_KEY"] = settings.GROQ_API_KEY
        if settings.GROQ_MODEL:
            env["GROQ_MODEL"] = settings.GROQ_MODEL

        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,  # Stderr flows directly to container logs
            env=env,
        )

        # Register sync termination on Python interpreter exit
        atexit.register(self._sync_terminate)

        # Wait for ready signal or ping
        try:
            line = await asyncio.wait_for(self._process.stdout.readline(), timeout=10.0)
            if line:
                data = json.loads(line.decode("utf-8").strip())
                logger.info("Pi bridge daemon ready signal received: %s", data)
            self._is_started = True
        except Exception as exc:
            logger.warning("Did not receive immediate ready signal from Pi daemon: %s", exc)
            # Verify via ping
            await self.ping()

    def _sync_terminate(self) -> None:
        """Synchronous process cleanup on exit."""
        if self._process is not None and self._process.returncode is None:
            try:
                self._process.terminate()
            except Exception:
                pass

    async def close(self) -> None:
        """Cleanly shutdown the Pi bridge daemon."""
        if self._process is None or self._process.returncode is not None:
            return

        logger.info("Shutting down Pi bridge daemon...")
        try:
            # Send shutdown message
            req = {"jsonrpc": "2.0", "id": "shutdown", "method": "shutdown"}
            if self._process.stdin:
                self._process.stdin.write((json.dumps(req) + "\n").encode("utf-8"))
                await self._process.stdin.drain()
            await asyncio.wait_for(self._process.wait(), timeout=3.0)
        except Exception as exc:
            logger.warning("Error during graceful Pi shutdown: %s, killing process", exc)
            try:
                self._process.kill()
            except Exception:
                pass
        finally:
            self._process = None
            self._is_started = False

    async def ping(self) -> dict[str, Any]:
        """Ping the Pi daemon to verify health."""
        async with self._lock:
            if self._process is None or self._process.returncode is not None:
                await self.start()

            self._request_counter += 1
            req_id = f"ping-{self._request_counter}"
            req = {"jsonrpc": "2.0", "id": req_id, "method": "ping"}

            self._process.stdin.write((json.dumps(req) + "\n").encode("utf-8"))
            await self._process.stdin.drain()

            while True:
                line = await asyncio.wait_for(self._process.stdout.readline(), timeout=5.0)
                if not line:
                    raise RuntimeError("Pi bridge daemon closed stdout unexpectedly")
                msg = json.loads(line.decode("utf-8").strip())
                if msg.get("id") == req_id:
                    return msg.get("result", {})

    async def execute_turn(
        self,
        user_prompt: str,
        rewritten_query: Optional[str] = None,
        history: Optional[list[dict[str, Any]]] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> PiTurnResult:
        """Execute a complete conversational turn through Pi Coding Agent."""
        async with self._lock:
            if self._process is None or self._process.returncode is not None:
                await self.start()

            start_t = time.perf_counter()
            self._request_counter += 1
            req_id = f"turn-{self._request_counter}"

            chosen_provider = provider or settings.LLM_PROVIDER
            if not model_name:
                if chosen_provider == "anthropic":
                    chosen_model = settings.ANTHROPIC_MODEL
                elif chosen_provider in ("gemini", "google"):
                    chosen_model = settings.GEMINI_MODEL
                elif chosen_provider == "openai":
                    chosen_model = settings.OPENAI_MODEL
                elif chosen_provider == "groq":
                    chosen_model = settings.GROQ_MODEL
                else:
                    chosen_model = settings.OLLAMA_MODEL
            else:
                chosen_model = model_name

            params = {
                "user_prompt": user_prompt,
                "rewritten_query": rewritten_query or user_prompt,
                "history": history or [],
                "provider": chosen_provider,
                "model_name": chosen_model,
            }
            if api_key:
                params["api_key"] = api_key

            req = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "execute_turn",
                "params": params,
            }

            self._process.stdin.write((json.dumps(req) + "\n").encode("utf-8"))
            await self._process.stdin.drain()

            # Read stream until response with matching ID is returned
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    raise RuntimeError("Pi bridge daemon closed connection during execute_turn")

                msg = json.loads(line.decode("utf-8").strip())

                if msg.get("id") == req_id:
                    if "error" in msg:
                        err = msg["error"]
                        raise RuntimeError(f"Pi Error ({err.get('code')}): {err.get('message')}")

                    result = msg.get("result", {})
                    elapsed = int((time.perf_counter() - start_t) * 1000)

                    return PiTurnResult(
                        content=result.get("response", ""),
                        tier=result.get("tier", "Insufficient"),
                        top_score=float(result.get("top_score", 0.0)),
                        can_synthesize=bool(result.get("can_synthesize", False)),
                        model_used=result.get("model", "ollama/llama3.1:8b"),
                        selected_evidence=result.get("selected_evidence", []),
                        duration_ms=elapsed,
                        generation_failed=bool(result.get("generation_failed", False)),
                        error_detail=result.get("error_detail"),
                    )

    async def stream_turn(
        self,
        user_prompt: str,
        rewritten_query: Optional[str] = None,
        history: Optional[list[dict[str, Any]]] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream a conversational turn emitting events from Pi Coding Agent."""
        async with self._lock:
            if self._process is None or self._process.returncode is not None:
                await self.start()

            start_t = time.perf_counter()
            self._request_counter += 1
            req_id = f"stream-{self._request_counter}"

            chosen_provider = provider or settings.LLM_PROVIDER
            if not model_name:
                if chosen_provider == "anthropic":
                    chosen_model = settings.ANTHROPIC_MODEL
                elif chosen_provider in ("gemini", "google"):
                    chosen_model = settings.GEMINI_MODEL
                elif chosen_provider == "openai":
                    chosen_model = settings.OPENAI_MODEL
                elif chosen_provider == "groq":
                    chosen_model = settings.GROQ_MODEL
                else:
                    chosen_model = settings.OLLAMA_MODEL
            else:
                chosen_model = model_name

            params = {
                "user_prompt": user_prompt,
                "rewritten_query": rewritten_query or user_prompt,
                "history": history or [],
                "provider": chosen_provider,
                "model_name": chosen_model,
            }
            if api_key:
                params["api_key"] = api_key

            req = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "execute_turn",
                "params": params,
            }

            self._process.stdin.write((json.dumps(req) + "\n").encode("utf-8"))
            await self._process.stdin.drain()

            while True:
                line = await self._process.stdout.readline()
                if not line:
                    raise RuntimeError("Pi bridge daemon closed connection during stream_turn")

                msg = json.loads(line.decode("utf-8").strip())

                # Check notifications
                if "method" in msg and "id" not in msg:
                    method = msg["method"]
                    notif_params = msg.get("params", {})

                    if method == "tool_call":
                        yield {"event": "tool_call", "data": notif_params}
                    elif method == "tool_result":
                        yield {"event": "evidence", "data": notif_params}
                    elif method == "token_delta":
                        yield {"event": "delta", "data": notif_params}

                elif msg.get("id") == req_id:
                    if "error" in msg:
                        err = msg["error"]
                        raise RuntimeError(f"Pi Error ({err.get('code')}): {err.get('message')}")

                    result = msg.get("result", {})
                    elapsed = int((time.perf_counter() - start_t) * 1000)

                    final_res = PiTurnResult(
                        content=result.get("response", ""),
                        tier=result.get("tier", "Insufficient"),
                        top_score=float(result.get("top_score", 0.0)),
                        can_synthesize=bool(result.get("can_synthesize", False)),
                        model_used=result.get("model", "ollama/llama3.1:8b"),
                        selected_evidence=result.get("selected_evidence", []),
                        duration_ms=elapsed,
                        generation_failed=bool(result.get("generation_failed", False)),
                        error_detail=result.get("error_detail"),
                    )
                    yield {"event": "result", "data": final_res}
                    break
