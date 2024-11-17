import nltk
from nltk.tokenize import sent_tokenize
from typing import Tuple
from burr.core import ApplicationBuilder, State, action, when, expr
from servant.tts.tts_pyttsx import TextToSpeechPyTtsx
from servant.llm.llm_ollama_remote import LmmOllamaRemote
from servant.stt.stt_whisper_remote import SpeechToTextWhisperRemote
from servant.voice_activation.voice_activation import VoiceActivatedRecorder

nltk.download('punkt_tab')

# the components we need for the service
record_request = VoiceActivatedRecorder(
    wake_word="hey computer",
    threshold=200,
    device_index=None,
    silence_lead_time=2
)
tts_service = TextToSpeechPyTtsx()
stt_service = SpeechToTextWhisperRemote(
    url='http://127.0.0.1:8000/v1/audio/transcriptions'
)
llm_service = LmmOllamaRemote(
    model='llama3.2:1b',
    host="http://127.0.0.1:11434",
)

def title(msg):
    print("###########################################################################################################")
    print(f"# {msg}")
    print("###########################################################################################################")

@action(reads=[], writes=["voice_buffer"])
def get_user_speak_input(state: State) -> Tuple[dict, State]:
    # block until wake word has been said
    audio_buffer = record_request.listen_for_wake_word()
    title(f"get_user_speak_input")
    return {"voice_buffer": audio_buffer}, state.update(voice_buffer=audio_buffer)

@action(reads=["voice_buffer"], writes=["prompt","prompt_len"])
def transcribe_voice_recording(state: State) -> Tuple[dict, State]:
    audio_buffer = state.get("voice_buffer")
    transcription = stt_service.transcribe(audio_buffer)
    title(f"transcribe_voice_recording: {transcription}")
    return {"prompt": transcription, "prompt_len": len(str(transcription).strip())}, state.update(prompt=transcription).update(prompt_len=len(str(transcription).strip()))

@action(reads=[], writes=["voice_buffer"])
def we_did_not_understand(state: State) -> Tuple[dict, State]:
    message = "Ich habe dich leider nicht verstanden. Sag es noch mal."
    title(message)
    voice_buffer = record_request.start_recording()
    return {"voice_buffer": voice_buffer}, state.update(voice_buffer=voice_buffer)

@action(reads=["chat_history"], writes=["prompt", "chat_history"])
def human_input(state: State) -> Tuple[dict, State]:
    # add the prompt to history
    prompt = state.get("prompt")
    print(f"User: {prompt}")
    chat_item = {"content": prompt, "role": "user"}
    title(f"human_input: {prompt}")
    return {"prompt": prompt}, state.update(prompt=prompt).append(chat_history=chat_item)

@action(reads=["prompt"], writes=["exit_chat"])
def exit_chat_check(state: State) -> Tuple[dict, State]:
    prompt = state.get("prompt")
    is_ending = llm_service.is_conversation_ending(prompt)
    title(f"exit_chat_check: {is_ending}")
    return {"exit_chat": is_ending}, state.update(exit_chat=is_ending)

@action(reads=[], writes=["chat_history"])
def exit_chat(state: State) -> Tuple[dict, State]:
    title("exit_chat")
    title("exit_chat")
    return {"chat_history": []}, state.update(chat_history=[])

@action(reads=["chat_history"], writes=["response", "chat_history"])
def ai_response(state: State) -> Tuple[dict, State]:
    # give the history including the last user input to the LLM to get its response
    response_stream = llm_service.chat_stream(state["chat_history"])
    response = ''
    print("KI: ", end='', flush=True)
    # consume the stream and collect response while printing to console
    buffer = ""
    response = ""
    sentences_all = []
    for chunk in response_stream:
        response += chunk
        buffer += chunk
        print(chunk, end='', flush=True)
        # Tokenize to sentences
        sentences = sent_tokenize(buffer)
        # process all full sentences (except incomplete)
        for sentence in sentences[:-1]:
            tts_service.speak(sentence)
            sentences_all.append(sentence)
        # store last (maybe incomplete) sentence in the buffer
        buffer = sentences[-1]
    if len(buffer) > 2:
        # add last fragment of response
        tts_service.speak(buffer)
        sentences_all.append(buffer)
    # add response to the history to show to the use
    chat_item = {"content": response, "role": "assistant"}
    print()
    title(f"ai_response finished")
    for s in sentences_all:
        print(f"Sentence: {s}")
    return {"response": response}, state.update(response=response).append(chat_history=chat_item)

def application():
    return (
        ApplicationBuilder()
        .with_actions(
            get_user_speak_input=get_user_speak_input,
            transcribe_voice_recording=transcribe_voice_recording,
            we_did_not_understand=we_did_not_understand,
            human_input=human_input,
            ai_response=ai_response,
            exit_chat_check=exit_chat_check,
            exit_chat=exit_chat
        )
        .with_transitions(
            # get first user input with wakeup word "hey computer" and send to transcription
            ("get_user_speak_input", "transcribe_voice_recording"),
            # check if we have enough chars from the transcription, if not go to we_did_not_understand
            ("transcribe_voice_recording", "we_did_not_understand", expr("prompt_len < 10")),
            # if we_did_not_understand directly record again and transcribe again
            ("we_did_not_understand", "transcribe_voice_recording"),
            # if prompt_len is ok then send to human_input
            ("transcribe_voice_recording", "exit_chat_check", expr("prompt_len >= 10")),
            # if user wants to end the conversation we do so
            ("exit_chat_check", "exit_chat", when(exit_chat=True)),
            # else pass on to use this as human input
            ("exit_chat_check", "human_input", when(exit_chat=False)),
            # the human input is given to the LLM to get a response
            ("human_input", "ai_response"),
            # after AI has answered go back to wait for wakeup word to record again
            ("ai_response", "get_user_speak_input"),
        )
        .with_state(chat_history=[], exit_chat=False)
        .with_entrypoint("get_user_speak_input")
        .with_tracker("local", project="servant-llm")
        .build()
    )

if __name__ == "__main__":
    app = application()
    #app.visualize(include_conditions=True, output_file_path="graph.png", include_state=True)
    action_we_ran, result, state = app.run(halt_after=["exit_chat"])
    title("Application finished")
    for item in state['chat_history']:
        print(item['role'] + ':' + item['content'] + '\n')