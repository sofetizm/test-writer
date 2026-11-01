"""Chat backends: any OpenAI-compatible API, a local Hugging Face model, or a script (tests)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class Reply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class Backend:
    name = "base"

    def chat(self, messages: list[dict]) -> Reply:
        raise NotImplementedError

    def describe(self) -> dict:
        return {"backend": self.name}


class OpenAICompatible(Backend):
    """OpenAI, Groq, OpenRouter, DeepSeek, a local vLLM/Ollama server...

    Key and URL come from OPENAI_API_KEY and OPENAI_BASE_URL. Prices are USD per 1M tokens.
    """

    name = "openai"

    def __init__(self, model: str, price_in: float = 0.0, price_out: float = 0.0,
                 max_tokens: int = 4096, temperature: float = 0.0, rpm: float = 0.0,
                 reasoning_effort: str | None = None, client=None):
        self.model, self.price_in, self.price_out = model, price_in, price_out
        self.max_tokens, self.temperature = max_tokens, temperature
        self.reasoning_effort = reasoning_effort
        self.min_interval = 60.0 / rpm if rpm > 0 else 0.0
        self._last = 0.0
        if client is None:
            from openai import OpenAI

            client = OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"), max_retries=8)
        self.client = client

    def chat(self, messages: list[dict]) -> Reply:
        delay = self._last + self.min_interval - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()
        kwargs = {"model": self.model, "messages": messages, "max_tokens": self.max_tokens,
                  "temperature": self.temperature}
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
        resp = self.client.chat.completions.create(**kwargs)
        usage = resp.usage
        n_in = getattr(usage, "prompt_tokens", 0) or 0
        n_out = getattr(usage, "completion_tokens", 0) or 0
        return Reply(resp.choices[0].message.content or "", n_in, n_out,
                     (n_in * self.price_in + n_out * self.price_out) / 1e6)

    def describe(self) -> dict:
        return {"backend": self.name, "model": self.model, "temperature": self.temperature,
                "reasoning_effort": self.reasoning_effort,
                "price_in_per_1m": self.price_in, "price_out_per_1m": self.price_out}


class HFLocal(Backend):
    """A local model through transformers (e.g. on a free Colab T4)."""

    name = "hf"

    def __init__(self, model: str, load_in_4bit: bool = True, max_new_tokens: int = 3072):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self.torch, self.model_name, self.max_new_tokens = torch, model, max_new_tokens
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        cuda = torch.cuda.is_available()
        dtype = (torch.bfloat16 if cuda and torch.cuda.is_bf16_supported()
                 else torch.float16 if cuda else torch.float32)
        kwargs: dict = {"dtype": dtype}
        if cuda:
            kwargs["device_map"] = {"": 0}
        self.quantized = load_in_4bit and cuda
        if self.quantized:
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=dtype)
        self.model = AutoModelForCausalLM.from_pretrained(model, **kwargs).eval()

    def chat(self, messages: list[dict]) -> Reply:
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False,
                                                    add_generation_prompt=True)
        enc = self.tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
        enc = enc.to(self.model.device)
        with self.torch.inference_mode():
            out = self.model.generate(**enc, max_new_tokens=self.max_new_tokens, do_sample=False,
                                      pad_token_id=self.tokenizer.eos_token_id)
        new = out[0, enc["input_ids"].shape[1]:]
        return Reply(self.tokenizer.decode(new, skip_special_tokens=True),
                     int(enc["input_ids"].shape[1]), int(new.shape[0]))

    def describe(self) -> dict:
        return {"backend": self.name, "model": self.model_name, "quantized_4bit": self.quantized}


class Scripted(Backend):
    """Replays fixed replies. Used in tests and to evaluate hand-written test suites."""

    name = "scripted"

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.seen: list[list[dict]] = []

    def chat(self, messages: list[dict]) -> Reply:
        self.seen.append(messages)
        text = self.replies.pop(0) if self.replies else "ACTION: finish"
        return Reply(text, input_tokens=sum(len(m["content"]) for m in messages) // 4,
                     output_tokens=len(text) // 4)
