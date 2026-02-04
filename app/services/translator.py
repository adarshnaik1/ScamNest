
# TRANSLATION DISABLED TO REDUCE DEPLOYMENT SIZE
# Removing transformers, torch, and sentencepiece saves ~1.5-2 GB

# from transformers import MarianTokenizer, MarianMTModel
# tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-mul-en")
# model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-mul-en")

class Translator:
    """Dummy translator that returns text as-is (translation disabled)."""

    def __init__(self):
        pass

    def translate(self, text: str) -> str:
        """Return text unchanged (translation disabled for deployment size optimization)."""
        return text

#
# print(translate("""Here is the **Marathi translation** of the given Kannada text:
#
# **मराठी:**
#
# तुमच्या बँक खात्यात संशयास्पद हालचाल आढळून आली आहे.
# कृपया तात्काळ खालील लिंकवर क्लिक करून तुमची माहिती पडताळून पहा.
#
# """))
# print("end")
# print("end")
# import sys
# sys.exit(0)