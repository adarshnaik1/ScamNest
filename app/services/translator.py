
# from transformers import MarianTokenizer, MarianMTModel
#
#
# tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-mul-en")
# model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-mul-en")
import os
from huggingface_hub import InferenceClient
from ..config import get_settings

settings = get_settings()

class Translator:

    def __init__(self):
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=settings.hf_token
        )
        # print(settings.hf_token)

    def translate(self, text: str) :
        try:
            result = self.client.translation(
                text,
                model="Helsinki-NLP/opus-mt-mul-en",
            )
            return result.translation_text.strip()
        except Exception as e:
            raise e

translator = Translator()
# print(translator.translate("some text"))
print(translator.translate("""
तुमच्या बँक खात्यात संशयास्पद हालचाल आढळून आली आहे.
कृपया तात्काळ खालील लिंकवर क्लिक करून तुमची माहिती पडताळून पहा.

# """))
# # print("end")
# print("end")
# import sys
# sys.exit(0)