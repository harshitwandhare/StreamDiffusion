"""
prompt_morph.py — Prompt Interpolation for StreamDiffusion
===========================================================
Smoothly transitions between two text prompts by interpolating
their CLIP text embeddings in latent space.

This is useful for installation art where you want the visual
to drift slowly between two semantic states rather than cutting.

Concept:
  embed_A = CLIP("deep memory, roots of light, warm amber")
  embed_B = CLIP("present moment, third eye open, violet glow")
  embed_t = lerp(embed_A, embed_B, t)   # t in [0.0, 1.0]

  At t=0.0 the output carries the memory aesthetic.
  At t=0.5 both states are present simultaneously.
  At t=1.0 the output carries the present-moment aesthetic.

  This mirrors the idea that consciousness sees backward and forward
  at the same time — not as metaphor, but as the actual experience
  of watching two realities merge frame by frame.

Usage:
  from streamdiffusion.extensions.prompt_morph import PromptMorpher

  morpher = PromptMorpher(stream_pipeline)
  morpher.set_prompts(
      start="ancestral memory as neural light, roots, warm amber",
      end="third eye open, fractal iris, violet and indigo",
  )

  for frame_idx in range(num_frames):
      t = frame_idx / num_frames          # 0.0 → 1.0
      image = morpher.generate(input_image, t)

  # Oscillate back and forth (good for live loops):
  t = morpher.oscillate(speed=0.01)      # call every frame
  image = morpher.generate(input_image, t)
"""

import math
import torch
from typing import Optional
from PIL import Image


class PromptMorpher:
    """
    Handles smooth interpolation between two text prompts
    by operating directly on CLIP embeddings.

    Requires access to the internal StreamDiffusion pipeline
    (stream.stream, the StreamDiffusion object, not the wrapper).
    """

    def __init__(self, wrapper):
        """
        Parameters
        ----------
        wrapper : StreamDiffusionWrapper
            The initialized StreamDiffusionWrapper instance.
        """
        self.wrapper = wrapper
        self.pipe = wrapper.stream          # StreamDiffusion core

        self._embed_start = None
        self._embed_end = None
        self._neg_embed = None
        self._phase = 0.0                  # internal oscillator state [0, 2pi]
        self._t = 0.0                      # current interpolation position

        self._prompts_set = False

    def set_prompts(
        self,
        start: str,
        end: str,
        negative: str = "blurry, low quality",
    ) -> None:
        """
        Encode both prompts and cache their CLIP embeddings.
        Call this once before running the generation loop.

        Parameters
        ----------
        start : str
            The starting prompt (t=0.0).
        end : str
            The ending prompt (t=1.0).
        negative : str
            Negative prompt applied at both ends.
        """
        device = next(self.pipe.unet.parameters()).device
        dtype = next(self.pipe.unet.parameters()).dtype

        def encode(text: str) -> torch.Tensor:
            tokens = self.pipe.tokenizer(
                [text],
                padding="max_length",
                max_length=self.pipe.tokenizer.model_max_length,
                truncation=True,
                return_tensors="pt",
            )
            with torch.no_grad():
                embed = self.pipe.text_encoder(tokens.input_ids.to(device))[0]
            return embed.to(dtype)

        self._embed_start = encode(start)
        self._embed_end = encode(end)
        self._neg_embed = encode(negative)
        self._prompts_set = True

        print(f"[PromptMorpher] Ready: '{start[:40]}' → '{end[:40]}'")

    def get_embedding(self, t: float) -> torch.Tensor:
        """
        Linearly interpolate between start and end embeddings.

        Parameters
        ----------
        t : float
            Interpolation factor in [0.0, 1.0].
            0.0 = start prompt, 1.0 = end prompt.

        Returns
        -------
        torch.Tensor
            The interpolated CLIP embedding.
        """
        if not self._prompts_set:
            raise RuntimeError("Call set_prompts() first.")
        t = max(0.0, min(1.0, t))
        return self._embed_start * (1.0 - t) + self._embed_end * t

    def generate(self, input_image: Image.Image, t: float) -> Optional[Image.Image]:
        """
        Generate a frame using the interpolated embedding at position t.

        Parameters
        ----------
        input_image : PIL.Image.Image
            The input frame (from webcam / screen capture).
        t : float
            Interpolation position in [0.0, 1.0].

        Returns
        -------
        PIL.Image.Image or None
            The generated output frame.
        """
        if not self._prompts_set:
            raise RuntimeError("Call set_prompts() first.")

        embed_t = self.get_embedding(t)

        # Inject the interpolated embedding directly into the diffusion stream.
        # StreamDiffusion stores encoded prompts in stream.prompt_embeds.
        # Bypassing prepare() lets us change the embedding per-frame
        # without the overhead of re-tokenizing and re-encoding.
        original_embeds = self.pipe.prompt_embeds
        self.pipe.prompt_embeds = embed_t

        try:
            image_tensor = self.wrapper.preprocess_image(input_image)
            output = self.wrapper(image=image_tensor)
        finally:
            self.pipe.prompt_embeds = original_embeds

        return output

    def oscillate(self, speed: float = 0.005) -> float:
        """
        Advance the internal oscillator and return the current t value.
        Produces a smooth back-and-forth animation [0→1→0→1...].

        Call this every frame, then pass the returned t to generate().

        Parameters
        ----------
        speed : float
            How fast to oscillate. 0.005 = very slow drift (good for
            ambient installation). 0.05 = noticeable rhythm.

        Returns
        -------
        float
            Current t in [0.0, 1.0].
        """
        self._phase += speed
        self._t = (math.sin(self._phase) + 1.0) / 2.0
        return self._t

    def advance(self, step: float = 0.01) -> float:
        """
        Advance t linearly. Wraps around: 0→1→0→1...

        Useful for timed, event-driven transitions rather than
        smooth oscillation.

        Parameters
        ----------
        step : float
            Amount to advance per call. 0.01 = 100 frames per crossing.

        Returns
        -------
        float
            Current t in [0.0, 1.0].
        """
        self._t += step
        if self._t > 1.0:
            self._t = 0.0
        return self._t
