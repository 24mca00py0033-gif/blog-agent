"""Image generation through Hugging Face Inference Providers."""
import io

from huggingface_hub import InferenceClient

from ..config import get_settings

_SIZES = {"1024x1024": (1024, 1024), "1024x1536": (1024, 1536), "1536x1024": (1536, 1024)}


def generate_image_bytes(prompt: str, size: str = "1024x1024") -> bytes:
    s = get_settings()
    if not s.hf_token:
        raise RuntimeError("HF_TOKEN is not set.")
    client = InferenceClient(provider=s.hf_image_provider, api_key=s.hf_token)
    width, height = _SIZES.get(size, (1024, 1024))
    image = client.text_to_image(prompt, model=s.hf_image_model, width=width, height=height)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
