"""
Model ensemble for LLMs
"""

import asyncio
import logging
import random
from typing import List, Optional

from providers.base import BaseProvider

logger = logging.getLogger(__name__)


class EnsembleProvider(BaseProvider):
    """Ensemble of AI providers for weighted sampling and parallel generation."""

    _logged_initialization: bool = False

    def __init__(
        self,
        providers: List[BaseProvider],
        weights: Optional[List[float]] = None,
        random_seed: Optional[int] = None,
    ):
        """Initialize the ensemble with a list of already instantiated providers.

        Args:
            providers: List of BaseProvider instances (e.g., OpenAIProvider, ClaudeProvider)
            weights: Optional list of floats representing the selection probability for each provider.
                     If neither provided nor configured, defaults to uniform distribution.
            random_seed: Seed for deterministic model selection.
        """
        if not providers:
            raise ValueError("EnsembleProvider requires at least one provider.")

        self.providers = providers

        # Extract and normalize model weights
        if weights:
            if len(weights) != len(providers):
                raise ValueError("Length of weights must match length of providers.")
            self.weights = weights
        else:
            self.weights = [1.0 for _ in providers]

        total = sum(self.weights)
        self.weights = [w / total for w in self.weights]

        # Set up random state for deterministic model selection
        self.random_state = random.Random()
        if random_seed is not None:
            self.random_state.seed(random_seed)
            logger.debug(
                f"EnsembleProvider: Set random seed to {random_seed} for deterministic model selection"
            )

        # Only log if we have multiple models or this is the first ensemble
        if len(providers) > 1 or not EnsembleProvider._logged_initialization:
            logger.info(
                f"Initialized EnsembleProvider with {len(providers)} providers."
            )
            EnsembleProvider._logged_initialization = True

    def _sample_provider(self) -> BaseProvider:
        """Sample a provider from the ensemble based on weights"""
        index = self.random_state.choices(
            range(len(self.providers)), weights=self.weights, k=1
        )[0]
        sampled_provider = self.providers[index]
        return sampled_provider

    async def generate_text(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> str:
        """Generate text using a randomly selected provider based on weights"""
        provider = self._sample_provider()
        return await provider.generate_text(system_prompt, user_prompt, **kwargs)

    async def generate_multiple(
        self, system_prompt: str, user_prompt: str, n: int, **kwargs
    ) -> List[str]:
        """Generate multiple texts in parallel (each sampled independently from the ensemble)"""
        tasks = [
            self.generate_text(system_prompt, user_prompt, **kwargs) for _ in range(n)
        ]
        return await asyncio.gather(*tasks)

    async def parallel_generate(
        self, system_prompt: str, user_prompts: List[str], **kwargs
    ) -> List[str]:
        """Generate responses for multiple prompts in parallel (each sampled independently)"""
        tasks = [
            self.generate_text(system_prompt, prompt, **kwargs)
            for prompt in user_prompts
        ]
        return await asyncio.gather(*tasks)

    async def generate_all(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> List[str]:
        """Generate text using ALL available models in the ensemble simultaneously."""
        tasks = [
            provider.generate_text(system_prompt, user_prompt, **kwargs)
            for provider in self.providers
        ]
        return await asyncio.gather(*tasks)
