import speech_recognition as sr

r = sr.Recognizer()
with sr.Microphone() as source:
    print("HABLA AHORA...")
    r.adjust_for_ambient_noise(source, duration=0.5)
    audio = r.listen(source, timeout=10, phrase_time_limit=8)

print("bytes:", len(audio.get_raw_data()))
print("TEXTO:", r.recognize_google(audio, language="es-ES"))