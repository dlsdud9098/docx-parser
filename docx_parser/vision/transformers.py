"""
Hugging Face Transformers Vision Provider.

Supports various multimodal models:
- LLaVA (llava-hf/llava-v1.6-mistral-7b-hf)
- Qwen-VL (Qwen/Qwen2-VL-7B-Instruct)
- InternVL (OpenGVLab/InternVL2-8B)
- Phi-3-Vision (microsoft/Phi-3-vision-128k-instruct)
- and more...

Features:
- Single image processing
- Batch processing for multiple images (GPU memory efficient)
"""

from pathlib import Path
from typing import Optional, Union, Any, List, Dict, TYPE_CHECKING
import io

from .base import VisionProvider
from .exceptions import ProviderNotInstalledError, ImageProcessingError

if TYPE_CHECKING:
    from ..parser import ImageInfo


class TransformersVisionProvider(VisionProvider):
    """Hugging Face Transformers Vision Provider

    Example:
        # LLaVA
        provider = TransformersVisionProvider(
            model_id="llava-hf/llava-v1.6-mistral-7b-hf"
        )

        # Qwen-VL
        provider = TransformersVisionProvider(
            model_id="Qwen/Qwen2-VL-7B-Instruct"
        )

        # With quantization
        provider = TransformersVisionProvider(
            model_id="llava-hf/llava-v1.6-mistral-7b-hf",
            load_in_4bit=True
        )
    """

    # Known model types for automatic processor selection
    MODEL_TYPES = {
        "llava": ["llava-hf", "liuhaotian"],
        "qwen": ["Qwen/Qwen2-VL", "Qwen/Qwen-VL"],
        "internvl": ["OpenGVLab/InternVL"],
        "phi3": ["microsoft/Phi-3-vision"],
        "idefics": ["HuggingFaceM4/idefics"],
    }

    def __init__(
        self,
        model_id: str,
        prompt: Optional[str] = None,
        max_tokens: int = 150,
        language: str = "ko",
        device: Optional[str] = None,
        torch_dtype: Optional[str] = "auto",
        load_in_4bit: bool = False,
        load_in_8bit: bool = False,
        trust_remote_code: bool = True,
        batch_size: int = 4,
    ):
        """
        Args:
            model_id: Hugging Face 모델 ID (예: "llava-hf/llava-v1.6-mistral-7b-hf")
            prompt: 커스텀 프롬프트
            max_tokens: 최대 토큰 수
            language: 응답 언어
            device: 디바이스 (None=auto, "cuda", "cpu", "mps")
            torch_dtype: Torch dtype ("auto", "float16", "bfloat16", "float32")
            load_in_4bit: 4bit 양자화 (bitsandbytes 필요)
            load_in_8bit: 8bit 양자화 (bitsandbytes 필요)
            trust_remote_code: 원격 코드 신뢰 여부
            batch_size: 배치 처리 크기 (기본: 4, GPU 메모리에 따라 조절)
        """
        try:
            import torch
            from transformers import AutoProcessor, AutoModelForVision2Seq
            from PIL import Image
            self._torch = torch
            self._AutoProcessor = AutoProcessor
            self._AutoModelForVision2Seq = AutoModelForVision2Seq
            self._Image = Image
        except ImportError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else "transformers"
            raise ProviderNotInstalledError("Transformers", f"{missing} (pip install transformers torch pillow)")

        self.model_id = model_id
        self.device = device
        self.torch_dtype = torch_dtype
        self.load_in_4bit = load_in_4bit
        self.load_in_8bit = load_in_8bit
        self.trust_remote_code = trust_remote_code
        self.batch_size = batch_size

        # Determine device
        if device is None:
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
        else:
            self._device = device

        # Determine dtype
        if torch_dtype == "auto":
            if self._device == "cuda":
                self._dtype = torch.float16
            else:
                self._dtype = torch.float32
        elif torch_dtype == "float16":
            self._dtype = torch.float16
        elif torch_dtype == "bfloat16":
            self._dtype = torch.bfloat16
        else:
            self._dtype = torch.float32

        # Load model and processor
        self._load_model()

        super().__init__(model=model_id, prompt=prompt, max_tokens=max_tokens, language=language)

    def _load_model(self):
        """모델과 프로세서 로드"""
        # Quantization config
        quantization_config = None
        if self.load_in_4bit or self.load_in_8bit:
            try:
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=self.load_in_4bit,
                    load_in_8bit=self.load_in_8bit,
                    bnb_4bit_compute_dtype=self._dtype if self.load_in_4bit else None,
                )
            except ImportError:
                raise ProviderNotInstalledError("Transformers (quantization)", "bitsandbytes")

        # Load processor
        self._processor = self._AutoProcessor.from_pretrained(
            self.model_id,
            trust_remote_code=self.trust_remote_code,
        )

        # Decoder-only 모델 배치 처리를 위해 padding_side를 left로 설정
        if hasattr(self._processor, 'tokenizer') and self._processor.tokenizer is not None:
            self._processor.tokenizer.padding_side = "left"

        # Load model
        model_kwargs = {
            "trust_remote_code": self.trust_remote_code,
            "torch_dtype": self._dtype,
            "device_map": "auto" if self._device == "cuda" else None,
        }

        if quantization_config:
            model_kwargs["quantization_config"] = quantization_config

        # Try different model classes based on model type
        model_loaded = False
        model_classes = [
            "AutoModelForVision2Seq",
            "LlavaForConditionalGeneration",
            "Qwen2VLForConditionalGeneration",
            "AutoModelForCausalLM",
        ]

        for class_name in model_classes:
            try:
                if class_name == "AutoModelForVision2Seq":
                    ModelClass = self._AutoModelForVision2Seq
                else:
                    from transformers import AutoModelForCausalLM
                    ModelClass = AutoModelForCausalLM

                self._model = ModelClass.from_pretrained(
                    self.model_id,
                    **model_kwargs
                )
                model_loaded = True
                break
            except Exception:
                continue

        if not model_loaded:
            raise ImageProcessingError(self.model_id, "Failed to load model with any supported class")

        # Move to device if not using device_map
        if self._device != "cuda" and not (self.load_in_4bit or self.load_in_8bit):
            self._model = self._model.to(self._device)

    @property
    def default_model(self) -> str:
        return "llava-hf/llava-v1.6-mistral-7b-hf"

    @property
    def provider_name(self) -> str:
        return "transformers"

    def describe_image(
        self,
        image: Union[Path, bytes, io.BytesIO],
        prompt: Optional[str] = None,
    ) -> str:
        """이미지 설명 생성

        Args:
            image: 이미지 파일 경로, bytes, 또는 BytesIO 객체
            prompt: 커스텀 프롬프트 (None이면 self.prompt 사용)
        """
        use_prompt = prompt if prompt is not None else self.prompt

        try:
            # Load image from path or bytes
            if isinstance(image, (bytes, io.BytesIO)):
                if isinstance(image, bytes):
                    image = io.BytesIO(image)
                pil_image = self._Image.open(image).convert("RGB")
            else:
                pil_image = self._Image.open(image).convert("RGB")
            image = pil_image  # for processing

            # Prepare conversation format
            conversation = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": use_prompt},
                    ],
                },
            ]

            # Apply chat template
            try:
                text_prompt = self._processor.apply_chat_template(
                    conversation, tokenize=False, add_generation_prompt=True
                )
            except Exception:
                # Fallback for models without chat template
                text_prompt = f"USER: <image>\n{use_prompt}\nASSISTANT:"

            # Process inputs (리스트로 전달 - A.X-4.0-VL 등 일부 모델 호환성)
            inputs = self._processor(
                images=[image],
                text=[text_prompt],
                padding=True,
                return_tensors="pt"
            )

            # Move to device
            inputs = {k: v.to(self._device) if hasattr(v, 'to') else v for k, v in inputs.items()}

            # Generate
            with self._torch.inference_mode():
                output_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=self.max_tokens,
                    do_sample=False,
                )

            # Decode - 전체 출력을 디코딩한 후 프롬프트 제거
            full_output = self._processor.batch_decode(
                output_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )[0]

            # 프롬프트 제거 (다양한 모델 형식 지원)
            response = full_output
            # assistant 응답 부분만 추출
            for separator in ["ASSISTANT:", "assistant:", "<|assistant|>", "Assistant:"]:
                if separator in response:
                    response = response.split(separator)[-1]
                    break

            # 프롬프트 텍스트가 남아있으면 제거
            if use_prompt in response:
                response = response.split(use_prompt)[-1]

            return response.strip()

        except Exception as e:
            raise ImageProcessingError(str(image), str(e)) from e

    def _encode_image(self, image_path: Path) -> str:
        from .utils import encode_image_base64
        return encode_image_base64(image_path)

    def unload(self):
        """모델 언로드 (메모리 해제)"""
        if hasattr(self, '_model'):
            del self._model
        if hasattr(self, '_processor'):
            del self._processor
        if self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()

    def _load_pil_image(self, image: Union[Path, bytes, io.BytesIO]) -> Any:
        """이미지를 PIL Image로 로드"""
        if isinstance(image, bytes):
            image = io.BytesIO(image)
        if isinstance(image, io.BytesIO):
            return self._Image.open(image).convert("RGB")
        return self._Image.open(image).convert("RGB")

    def _get_text_prompt(self, prompt: Optional[str] = None) -> str:
        """텍스트 프롬프트 생성 (chat template 적용)

        Args:
            prompt: 사용할 프롬프트 (None이면 self.prompt 사용)
        """
        use_prompt = prompt if prompt is not None else self.prompt
        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": use_prompt},
                ],
            },
        ]
        try:
            return self._processor.apply_chat_template(
                conversation, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            return f"USER: <image>\n{use_prompt}\nASSISTANT:"

    def describe_images(
        self,
        images: List["ImageInfo"],
        image_prompts: Optional[Dict[int, str]] = None,
    ) -> Dict[int, str]:
        """여러 이미지 배치 처리

        Args:
            images: ImageInfo 리스트 (path 또는 data 필드 사용)
            image_prompts: {이미지_인덱스: 프롬프트} 매핑 (선택)
                - 특정 이미지에 커스텀 프롬프트 적용
                - 지정되지 않은 이미지는 기본 프롬프트(self.prompt) 사용

        Returns:
            {이미지_인덱스: 설명} 딕셔너리

        Note:
            batch_size에 따라 이미지를 배치로 나누어 처리합니다.
            GPU 메모리가 부족하면 batch_size를 줄이세요.
            image_prompts가 지정된 경우 개별 처리로 진행합니다.
        """
        if not images:
            return {}

        # image_prompts가 있으면 개별 처리 (프롬프트가 다를 수 있으므로)
        if image_prompts:
            result = {}
            for img in images:
                try:
                    prompt = image_prompts.get(img.index)
                    if img.path:
                        description = self.describe_image(Path(img.path), prompt=prompt)
                    elif img.data:
                        description = self.describe_image(img.data, prompt=prompt)
                    else:
                        continue
                    result[img.index] = description
                except Exception as e:
                    result[img.index] = f"[이미지 처리 실패: {str(e)}]"
            return result

        # 이미지가 1개면 단일 처리
        if len(images) == 1:
            img = images[0]
            try:
                if img.path:
                    description = self.describe_image(Path(img.path))
                elif img.data:
                    description = self.describe_image(img.data)
                else:
                    return {}
                return {img.index: description}
            except Exception as e:
                return {img.index: f"[이미지 처리 실패: {str(e)}]"}

        result = {}
        text_prompt = self._get_text_prompt()

        # 배치 단위로 처리
        for batch_start in range(0, len(images), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(images))
            batch_images = images[batch_start:batch_end]

            # PIL 이미지로 로드
            pil_images = []
            batch_indices = []
            for img in batch_images:
                try:
                    if img.path:
                        pil_img = self._load_pil_image(Path(img.path))
                    elif img.data:
                        pil_img = self._load_pil_image(img.data)
                    else:
                        continue
                    pil_images.append(pil_img)
                    batch_indices.append(img.index)
                except Exception as e:
                    result[img.index] = f"[이미지 로드 실패: {str(e)}]"

            if not pil_images:
                continue

            try:
                # 배치 처리
                batch_descriptions = self._process_batch(pil_images, text_prompt)

                # 결과 매핑
                for idx, desc in zip(batch_indices, batch_descriptions):
                    result[idx] = desc

            except Exception as e:
                # 배치 실패 시 개별 처리로 폴백
                for img in batch_images:
                    if img.index in result:
                        continue  # 이미 에러 메시지가 있음
                    try:
                        if img.path:
                            description = self.describe_image(Path(img.path))
                        elif img.data:
                            description = self.describe_image(img.data)
                        else:
                            continue
                        result[img.index] = description
                    except Exception as e2:
                        result[img.index] = f"[이미지 처리 실패: {str(e2)}]"

        return result

    def _process_batch(
        self,
        pil_images: List[Any],
        text_prompt: str
    ) -> List[str]:
        """배치 이미지 처리

        Args:
            pil_images: PIL Image 리스트
            text_prompt: 텍스트 프롬프트

        Returns:
            설명 리스트 (이미지 순서대로)
        """
        batch_size = len(pil_images)

        # 각 이미지에 동일한 프롬프트 적용
        text_prompts = [text_prompt] * batch_size

        # Processor로 배치 입력 생성
        inputs = self._processor(
            images=pil_images,
            text=text_prompts,
            return_tensors="pt",
            padding=True,
        )

        # 디바이스로 이동
        inputs = {k: v.to(self._device) if hasattr(v, 'to') else v for k, v in inputs.items()}

        # 배치 생성
        with self._torch.inference_mode():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=self.max_tokens,
                do_sample=False,
                pad_token_id=self._processor.tokenizer.pad_token_id if hasattr(self._processor, 'tokenizer') else None,
            )

        # 전체 출력을 디코딩한 후 프롬프트 제거
        full_outputs = self._processor.batch_decode(
            output_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )

        # 프롬프트에서 사용자 입력 추출 (제거용)
        use_prompt = self.prompt

        descriptions = []
        for full_output in full_outputs:
            response = full_output
            # assistant 응답 부분만 추출
            for separator in ["ASSISTANT:", "assistant:", "<|assistant|>", "Assistant:"]:
                if separator in response:
                    response = response.split(separator)[-1]
                    break

            # 프롬프트 텍스트가 남아있으면 제거
            if use_prompt and use_prompt in response:
                response = response.split(use_prompt)[-1]

            descriptions.append(response.strip())

        return descriptions
