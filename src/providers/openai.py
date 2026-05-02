import asyncio
import json
import time
import uuid
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from providers.base import BaseProvider
from helpers.exceptions import AIProviderError
from config import Settings, setup_logger, ensure_dir

logger = setup_logger(Settings.LOG_DIR / "openai_provider.log", name="linkedin-mcp.openai")


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _build_display_prompt(messages: List[Dict[str, str]]) -> str:
    """
    Render messages into a single plain-text prompt for the manual UI.
    """
    chunks: List[str] = []
    for m in messages:
        role = str(m.get("role", "user")).upper()
        content = m.get("content", "")
        chunks.append(f"### {role}\n{content}\n")
    return "\n".join(chunks).rstrip() + "\n"


def _atomic_write_json(path: Any, payload: Dict[str, Any]) -> None:
    ensure_dir(str(path.parent))
    tmp = path.parent / f".{path.name}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, str(path))


class OpenAIProvider(BaseProvider):
    """LLM interface using OpenAI-compatible APIs"""

    _initialized_models: set[str] = set()

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        api_base: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 4096,
        timeout: int = 120,
        retries: int = 2,
        retry_delay: int = 5,
        random_seed: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        manual_mode: bool = False,
        manual_queue_dir: Optional[Any] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.random_seed = random_seed
        self.reasoning_effort = reasoning_effort

        self.manual_mode = manual_mode
        self.manual_queue_dir = None

        if self.manual_mode:
            if not manual_queue_dir:
                raise ValueError(
                    "manual_queue_dir is required when manual_mode is True."
                )
            # manual_queue_dir expected to be a Path-like object from config or passed in
            self.manual_queue_dir = manual_queue_dir
            ensure_dir(str(self.manual_queue_dir))
            self.client = None
        else:
            try:
                import openai
            except ImportError:
                raise AIProviderError(
                    "openai package is required. Install with: pip install openai"
                )

            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=self.timeout,
                max_retries=self.retries,
            )

        if self.model not in OpenAIProvider._initialized_models:
            logger.info(f"Initialized OpenAI LLM with model: {self.model}")
            OpenAIProvider._initialized_models.add(self.model)

    async def generate_text(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> str:
        """Generate text using a system message and conversational context"""
        formatted_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        OPENAI_REASONING_MODEL_PREFIXES = (
            "o1-",
            "o1",
            "o3-",
            "o3",
            "o4-",
            "gpt-5-",
            "gpt-5",
            "gpt-oss-120b",
            "gpt-oss-20b",
        )
        model_lower = str(self.model).lower()
        is_openai_reasoning_model = model_lower.startswith(
            OPENAI_REASONING_MODEL_PREFIXES
        )

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
        }

        if is_openai_reasoning_model:
            params["max_completion_tokens"] = kwargs.get("max_tokens", self.max_tokens)
            reasoning_effort = kwargs.get("reasoning_effort", self.reasoning_effort)
            if reasoning_effort is not None:
                params["reasoning_effort"] = reasoning_effort
            if "verbosity" in kwargs:
                params["verbosity"] = kwargs["verbosity"]
        else:
            params["temperature"] = kwargs.get("temperature", self.temperature)
            params["top_p"] = kwargs.get("top_p", self.top_p)
            params["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)

            if kwargs.get("response_format") == "json_object":
                params["response_format"] = {"type": "json_object"}

            reasoning_effort = kwargs.get("reasoning_effort", self.reasoning_effort)
            if reasoning_effort is not None:
                params["reasoning_effort"] = reasoning_effort

        seed = kwargs.get("seed", self.random_seed)
        if seed is not None and not self.manual_mode:
            if (
                self.api_base
                == "https://generativelanguage.googleapis.com/v1beta/openai/"
            ):
                logger.warning(
                    "Skipping seed parameter as Google AI Studio doesn't support it."
                )
            else:
                params["seed"] = seed

        if self.manual_mode:
            timeout_arg = kwargs.get("timeout", None)
            return await self._manual_wait_for_answer(params, timeout=timeout_arg)

        timeout_arg = kwargs.get("timeout", self.timeout)
        retries = kwargs.get("retries", self.retries)
        retry_delay = kwargs.get("retry_delay", self.retry_delay)

        for attempt in range(retries + 1):
            try:
                response = await asyncio.wait_for(
                    self._call_api(params), timeout=timeout_arg
                )
                return response
            except asyncio.TimeoutError:
                if attempt < retries:
                    logger.warning(
                        f"Timeout on attempt {attempt + 1}/{retries + 1}. Retrying..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"All {retries + 1} attempts failed with timeout")
                    raise
            except Exception as e:
                if attempt < retries:
                    logger.warning(
                        f"Error on attempt {attempt + 1}/{retries + 1}: {str(e)}. Retrying..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(
                        f"All {retries + 1} attempts failed with error: {str(e)}"
                    )
                    raise

        raise AIProviderError("Unexpected fallback out of retry loop.")

    async def _call_api(self, params: Dict[str, Any]) -> str:
        """Make the actual API call"""
        loop = asyncio.get_running_loop()

        def _sync_call():
            if self.client is None:
                raise AIProviderError("OpenAI client is not initialized.")
            return self.client.chat.completions.create(**params)

        response = await loop.run_in_executor(None, _sync_call)
        logger.debug(f"API parameters: {params}")
        # logger.debug(f"API response: {response.choices[0].message.content}")
        return str(response.choices[0].message.content)

    async def _manual_wait_for_answer(
        self, params: Dict[str, Any], timeout: Optional[Union[int, float]]
    ) -> str:
        """
        Manual mode: write a task JSON file and poll for *.answer.json
        """
        if self.manual_queue_dir is None:
            raise RuntimeError("manual_queue_dir is not initialized")

        task_id = str(uuid.uuid4())
        messages = params.get("messages", [])
        display_prompt = _build_display_prompt(messages)

        task_payload: Dict[str, Any] = {
            "id": task_id,
            "created_at": _iso_now(),
            "model": params.get("model"),
            "display_prompt": display_prompt,
            "messages": messages,
            "meta": {
                "max_tokens": params.get("max_tokens"),
                "max_completion_tokens": params.get("max_completion_tokens"),
                "temperature": params.get("temperature"),
                "top_p": params.get("top_p"),
                "reasoning_effort": params.get("reasoning_effort"),
                "verbosity": params.get("verbosity"),
            },
        }

        task_path = self.manual_queue_dir / f"{task_id}.json"
        answer_path = self.manual_queue_dir / f"{task_id}.answer.json"

        _atomic_write_json(task_path, task_payload)
        logger.info(f"[manual_mode] Task enqueued: {task_path}")

        start = time.time()
        poll_interval = 0.5

        while True:
            if answer_path.exists():
                try:
                    with open(answer_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    logger.warning(
                        f"[manual_mode] Failed to parse answer JSON for {task_id}: {e}"
                    )
                    await asyncio.sleep(poll_interval)
                    continue

                answer = str(data.get("answer") or "")
                logger.info(f"[manual_mode] Answer received for {task_id}")
                return answer

            if timeout is not None and (time.time() - start) > float(timeout):
                raise asyncio.TimeoutError(
                    f"Manual mode timed out after {timeout} seconds waiting for answer of task {task_id}"
                )

            await asyncio.sleep(poll_interval)
