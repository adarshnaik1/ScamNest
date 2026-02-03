
from transformers import MarianTokenizer, MarianMTModel


tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-mul-en")
model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-mul-en")
class Translator:

    def __init__(self):
        self.tokenizer = tokenizer
        self.model = model

    def translate(self, text: str) -> str:
        try:
            batch = self.tokenizer([text], return_tensors="pt")
            generated_ids = self.model.generate(**batch)
            return self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        except Exception as e:
            raise e

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