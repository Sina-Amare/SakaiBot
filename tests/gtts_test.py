
from gtts import gTTS

text = "سلام، حال شما چطوره؟"
tts = gTTS(text=text, lang='fa')
tts.save("persian_test.mp3")
print("File saved as persian_test.mp3")
