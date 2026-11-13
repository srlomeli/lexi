"""Deepgram speech for the web page.

Adds two routes to the Rasa server so the Deepgram key stays on the server:
  POST /webhooks/deepgram/listen  audio clip in, {"transcript": "..."} out
  GET  /webhooks/deepgram/speak?text=...  MP3 audio out, streamed as it is made
"""

import os
from typing import Any, Awaitable, Callable, Dict, Optional, Text

import httpx
from sanic import Blueprint, response
from sanic.request import Request

from rasa.core.channels.channel import InputChannel

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
except ImportError:
    pass

DEEPGRAM_URL = "https://api.deepgram.com/v1"


class DeepgramVoiceInput(InputChannel):
    @classmethod
    def name(cls) -> Text:
        return "deepgram"

    @classmethod
    def from_credentials(cls, credentials: Optional[Dict[Text, Any]]) -> InputChannel:
        credentials = credentials or {}
        return cls(
            stt_model=credentials.get("stt_model", "nova-3"),
            tts_voice=credentials.get("tts_voice", "aura-2-thalia-en"),
        )

    def __init__(self, stt_model: Text = "nova-3", tts_voice: Text = "aura-2-thalia-en") -> None:
        self.stt_model = stt_model
        self.tts_voice = tts_voice
        self._client: Optional[httpx.AsyncClient] = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    def _headers(self) -> Optional[Dict[Text, Text]]:
        key = os.environ.get("DEEPGRAM_API_KEY")
        return {"Authorization": f"Token {key}"} if key else None

    def blueprint(
        self, on_new_message: Callable[[Any], Awaitable[Any]]
    ) -> Blueprint:
        bp = Blueprint("deepgram_voice", __name__)

        @bp.route("/", methods=["GET"])
        async def health(_: Request) -> response.HTTPResponse:
            return response.json({"status": "ok", "key": bool(self._headers())})

        @bp.route("/listen", methods=["POST"])
        async def listen(request: Request) -> response.HTTPResponse:
            headers = self._headers()
            if not headers:
                return response.json({"error": "DEEPGRAM_API_KEY is not set"}, status=500)
            if not request.body:
                return response.json({"error": "no audio"}, status=400)
            headers["Content-Type"] = request.headers.get("content-type", "audio/webm")
            params = {"model": self.stt_model, "smart_format": "true", "language": "en"}
            try:
                r = await self._http().post(
                    f"{DEEPGRAM_URL}/listen", params=params, headers=headers, content=request.body
                )
                r.raise_for_status()
                alt = r.json()["results"]["channels"][0]["alternatives"][0]
                return response.json({"transcript": alt.get("transcript", "")})
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
                return response.json({"error": f"Deepgram listen failed: {e}"}, status=502)

        @bp.route("/speak", methods=["GET"])
        async def speak(request: Request) -> Optional[response.HTTPResponse]:
            headers = self._headers()
            if not headers:
                return response.json({"error": "DEEPGRAM_API_KEY is not set"}, status=500)
            text = (request.args.get("text") or "").strip()[:2000]
            if not text:
                return response.json({"error": "no text"}, status=400)
            client = self._http()
            upstream = None
            try:
                upstream = await client.send(
                    client.build_request(
                        "POST",
                        f"{DEEPGRAM_URL}/speak",
                        params={"model": self.tts_voice, "encoding": "mp3"},
                        headers=headers,
                        json={"text": text},
                    ),
                    stream=True,
                )
                if upstream.status_code != 200:
                    detail = (await upstream.aread()).decode(errors="replace")[:300]
                    return response.json({"error": f"Deepgram speak failed: {detail}"}, status=502)
                resp = await request.respond(content_type="audio/mpeg", headers={"Cache-Control": "no-store"})
                async for chunk in upstream.aiter_bytes():
                    await resp.send(chunk)
                await resp.eof()
                return None
            except httpx.HTTPError as e:
                return response.json({"error": f"Deepgram speak failed: {e}"}, status=502)
            finally:
                if upstream is not None:
                    await upstream.aclose()

        return bp
