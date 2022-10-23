#!/usr/bin/env python3
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Activates the Google Assistant with either a hotword or a button press, using the
Google Assistant Library.

The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio.

.. note:

    Hotword detection (such as "Okay Google") is supported only with Raspberry Pi 2/3.
    If you're using a Pi Zero, this code works but you must press the button to activate
    the Google Assistant.
"""

import logging
import platform
import sys
import threading
import argparse
import locale


from google.assistant.library.event import EventType

from aiy.assistant import auth_helpers
from aiy.assistant.library import Assistant
from aiy.board import Board, Led
from aiy.cloudspeech import CloudSpeechClient

from google.cloud import translate

from google.cloud import texttospeech

import os
import threading


class MyAssistant:
    
    
    
    """An assistant that runs in the background.

    The Google Assistant Library event loop blocks the running thread entirely.
    To support the button trigger, we need to run the event loop in a separate
    thread. Otherwise, the on_button_pressed() method will never get a chance to
    be invoked.
    """

    def __init__(self):
        self._task = threading.Thread(target=self._run_task)
        self._can_start_conversation = False
        self._assistant = None
        self._board = Board()
        self._board.button.when_pressed = self._on_button_pressed
        self._board.button.when_longpressed = self._on_button_longpressed
        self._recog_client_on = False
        self._foreign_lang = "en"
        self._who_is_speaking = 0
        self._is_streaming = 0
        self._speech_client = None

    def start(self):
        """
        Starts the assistant event loop and begins processing events.
        """
        self._task.start()

    def _run_task(self):
        credentials = auth_helpers.get_assistant_credentials()
        with Assistant(credentials) as assistant:
            self._assistant = assistant
            for event in assistant.start():
                self._process_event(event)

    def _process_event(self, event):
        logging.info(event)
        if event.type == EventType.ON_START_FINISHED:
            self._board.led.status = Led.BEACON_DARK  # Ready.
            self._can_start_conversation = True
            # Start the voicehat button trigger.
            logging.info('Say "OK, Google" or press the button, then speak. '
                         'Press Ctrl+C to quit...')

        elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
            self._can_start_conversation = False
            self._board.led.state = Led.ON  # Listening.

        elif event.type == EventType.ON_END_OF_UTTERANCE:
            self._board.led.state = Led.PULSE_QUICK  # Thinking.

        elif (event.type == EventType.ON_CONVERSATION_TURN_FINISHED
              or event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT
              or event.type == EventType.ON_NO_RESPONSE):
            self._board.led.state = Led.BEACON_DARK  # Ready.
            self._can_start_conversation = True

        elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
            sys.exit(1)

    def _on_button_pressed(self):
        if self._is_streaming == 0:
            x = threading.Thread(target=self.start_recognize)
            x.start()
            self._is_streaming=1
        else:
            logging.info('try stopping')
            self._is_streaming=0
            self._speech_client.stop_recognize()
        
    def start_recognize(self):
        
        try:
            logging.info('Start cloudspeech')
                
            if self._recog_client_on == False:
                client = CloudSpeechClient(None, self._board)
                self._speech_client = client
                with Board() as board:
                    #self._board.led.state = Led.ON
                    #while True:
                        logging.info('Say something.')
                        if self._who_is_speaking == 0:
                            text = client.recognize(language_code='fr')
                        else:
                            text = client.recognize(language_code=self._foreign_lang)
                            
                        if text is None:
                            logging.info('You said nothing.')
                     #       continue

                        logging.info('You said: "%s"' % text)
                        text = text.lower()
                        
                        #translate
                        ttext = translate_text(self, text)
                        logging.info('I translate in: "%s"' % ttext)
                        
                        
                        #play
                        play(self, ttext)
                        
                        if self._who_is_speaking == 0:
                            self._who_is_speaking = 1
                        else:
                            self._who_is_speaking = 0
                            
                        client.stop_listening()
                        self._is_streaming=0
            
                      #  break
                            
            else:
                client.stop_listening()
                self._is_streaming=0
            
        except:
            print("Oops!", sys.exc_info()[0], "occurred.")
            if self._who_is_speaking == 0:
                self._who_is_speaking = 1
            else:
                self._who_is_speaking = 0
            self._is_streaming=0
            play(self, 'Je ne comprends pas la commande', True)     

    

    def _on_button_longpressed(self):
        
        try:
            self._is_streaming=0
            logging.info('Start cloudspeech')
                
            if self._recog_client_on == False:
                client = CloudSpeechClient(None, self._board)
                with Board() as board:
                    #self._board.led.state = Led.ON
                    while True:
                        logging.info('Say something.')
                        text = client.recognize(language_code='fr')
                        if text is None:
                            logging.info('You said nothing.')
                            continue

                        logging.info('You said: "%s"' % text)
                        text = text.lower()
                        if 'choix de la langue' in text:
                            #board.led.state = Led.ON
                            lang_full = text[18:]
                            lang_full = lang_full.strip()
                            self._foreign_lang = corresp_lang(lang_full)
                            self._who_is_speaking = 0
                            logging.info('Selected language '+self._foreign_lang)
                            client.stop_listening()
                            break
            else:
                client.stop_listening()
        except:
            print("Oops!", sys.exc_info()[0], "occurred.")
            self._who_is_speaking = 1
            play(self, 'Je ne comprends pas la commande', True)            

def corresp_lang(lang):
    return{
        "anglais":"en",
        "espagnol":"es",
        "espagnole":"es",
        "arabe":"ar",
        "biélorusse":"be",
        "bulgare":"bg",
        "bosnien":"bs",
        "tchèque":"cs",
        "danois":"da",
        "allemand":"de",
        "maldivien":"dv",
        "grec":"el",
        "estonien":"et",
        "persan":"fa",
        "finnois":"fi",
        "fidjien":"fj",
        "croate":"hr",
        "hongrois":"hu",
        "arménien":"hy",
        "indonésien":"id",
        "islandais":"is",
        "italien":"it",
        "javanais":"jv",
        "géorgien":"ka",
        "coréen":"ko",
        "kurde":"ku",
        "malgache":"mg",
        "moldave":"mo",
        "néerlandais":"nl",
        "norvégien":"no",
        "polonais":"pl",
        "portugais":"pt",
        "roumain":"ro",
        "russe":"ru",
        "slovène":"sl",
        "suédois":"sv",
        "turc":"tr",
        "ukrainien":"uk",
        "ukrainienne":"uk",
        "vietnamien":"vi",
        "chinois":"zh",
        "japonais":"ja",
        "zoulou":"zu",
    }.get(lang, "en")
        

def translate_text(self, text="YOUR_TEXT_TO_TRANSLATE", project_id="voice-assistant-284119"):
    """Translating Text."""

    client = translate.TranslationServiceClient()

    #parent = client.location_path(project_id, "global")

    # Detail on supported types can be found here:
    # https://cloud.google.com/translate/docs/supported-formats
    if self._who_is_speaking == 0:
        response = client.translate_text(
            parent='projects/{}'.format(project_id),
            contents=[text],
            mime_type="text/plain",  # mime types: text/plain, text/html
            source_language_code="fr",
            target_language_code=self._foreign_lang,
        )
    else:
        response = client.translate_text(
            parent='projects/{}'.format(project_id),
            contents=[text],
            mime_type="text/plain",  # mime types: text/plain, text/html
            source_language_code=self._foreign_lang,
            target_language_code="fr",
        )
    
    # Display the translation for each input text provided
    for translation in response.translations:
        print(u"Translated text: {}".format(translation.translated_text))
        return translation.translated_text
        
    
def play(self, text="YOUR_TEXT_TO_PLAY", force=False):
    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)
    logging.info(force)
    # Build the voice request, select the language code ("en-US") and the ssml
    # voice gender ("neutral")
    if force:
        voice = texttospeech.VoiceSelectionParams(
            language_code="fr", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
    else:
        if self._who_is_speaking == 0:
            voice = texttospeech.VoiceSelectionParams(
                language_code=self._foreign_lang, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
        else:
            voice = texttospeech.VoiceSelectionParams(
                language_code="fr", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # The response's audio_content is binary.
    with open("/home/pi/output/output.mp3", "wb") as out:
        # Write the response to the output file.
        out.write(response.audio_content)
        print('Audio content written to file "output.mp3"')
    
    os.system('mpg123 /home/pi/output/output.mp3')


def main():
    logging.basicConfig(level=logging.INFO)
    MyAssistant().start()


if __name__ == '__main__':
    main()
