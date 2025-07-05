import os
from enum import Enum
from aiohttp import ClientSession, ClientTimeout


class Provider(str, Enum):
    ELEVEN = "ELEVENLABS"


class TTSClient:
    def __init__(self):
        self.provider = Provider(os.getenv("TTS_PROVIDER", "ELEVENLABS"))
        if self.provider is Provider.ELEVEN:
            self._api_key = os.environ["ELEVENLABS_API_KEY"]
            self._url = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        self._timeout = ClientTimeout(total=int(os.getenv("TTS_TIMEOUT", 15)))

    async def synth(self, *, text: str, voice_id: str, fmt: str = "mp3") -> bytes:
        if self.provider is Provider.ELEVEN:
            url = self._url.format(voice_id=voice_id)
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.4, "similarity_boost": 0.8},
            }
            headers = {
                "xi-api-key": self._api_key,
                "accept": f"audio/{fmt}",
                "content-type": "application/json",
            }
            async with ClientSession(timeout=self._timeout) as s:
                async with s.post(url, json=payload, headers=headers) as r:
                    r.raise_for_status()
                    return await r.read()
        raise NotImplementedError
