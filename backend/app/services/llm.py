"""
The Agent — LLM Router (4-Model Architecture)

[M1] Worker    : gpt-4o-mini       — 입력 파싱, 구조화. 생각하지 않는 처리기.
[M2] Stabilizer: Claude 3.5 Sonnet — 언어 정리, 안정적 해석. 과확장 방지.
[M3] Judge     : Flagship          — 판단, 개입, 설득, 차단. 희소 호출.
[M4] Distiller : Sonnet급          — 장기 기억 정제. 노이즈 제거 요약.
"""

from enum import Enum
from typing import Optional

from app.config import get_settings


class ModelRole(str, Enum):
    """4개 모델 역할."""
    WORKER = "worker"         # M1: 파싱, 구조화
    STABILIZER = "stabilizer" # M2: 정리, 분해, 노트
    JUDGE = "judge"           # M3: 판단, 개입
    DISTILLER = "distiller"   # M4: 기억 정제


class LLMRouter:
    """
    역할 기반 모델 라우터.
    각 역할에 맞는 모델과 클라이언트를 선택.
    """

    def __init__(self):
        self.settings = get_settings()
        self._openai_client = None
        self._anthropic_client = None

    @property
    def openai_client(self):
        if self._openai_client is None:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._openai_client

    @property
    def anthropic_client(self):
        if self._anthropic_client is None:
            from anthropic import AsyncAnthropic
            self._anthropic_client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        return self._anthropic_client

    def _get_model_name(self, role: ModelRole) -> str:
        """역할에 맞는 모델명 반환."""
        mapping = {
            ModelRole.WORKER: self.settings.llm_worker_model,
            ModelRole.STABILIZER: self.settings.llm_stabilizer_model,
            ModelRole.JUDGE: self.settings.llm_judge_model,
            ModelRole.DISTILLER: self.settings.llm_distiller_model,
        }
        return mapping[role]

    def _is_openai_model(self, model_name: str) -> bool:
        return model_name.startswith("gpt-")

    async def call(
        self,
        role: ModelRole,
        system_prompt: str,
        user_message: str,
        response_format: Optional[dict] = None,
        max_tokens: int = 1000,
    ) -> str:
        """
        역할에 맞는 모델 호출.
        OpenAI 모델이면 OpenAI API, 아니면 Anthropic API 사용.
        """
        model_name = self._get_model_name(role)

        if self._is_openai_model(model_name):
            return await self._call_openai(
                model_name, system_prompt, user_message, response_format, max_tokens
            )
        else:
            return await self._call_anthropic(
                model_name, system_prompt, user_message, max_tokens
            )

    async def _call_openai(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        response_format: Optional[dict],
        max_tokens: int,
    ) -> str:
        """OpenAI API 호출."""
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = await self.openai_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def _call_anthropic(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
    ) -> str:
        """Anthropic API 호출."""
        response = await self.anthropic_client.messages.create(
            model=model,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return response.content[0].text


# 싱글턴
_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
