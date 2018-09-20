# Copyright 2018 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import feedparser
from os.path import dirname
import re

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.audio import wait_while_speaking
from mycroft.skills.audioservice import AudioService
from mycroft.messagebus.message import Message


class NewsSkill(MycroftSkill):
    def __init__(self):
        super(NewsSkill, self).__init__(name="NewsSkill")
        self.process = None
        self.audioservice = None

    def initialize(self):
        self.audioservice = AudioService(self.emitter)
        self.add_event('play:query', self.play__query)
        self.add_event('play:start', self.play__start)

    def play__query(self, message):
        phrase = message.data["phrase"]
        if self.voc_match(phrase, "News"):
            self.bus.emit(message.response({"phrase": phrase,
                                            "skill_id": self.skill_id,
                                            "conf": "1.0"}))  # TODO: change conf based on match %

    def play__start(self, message):
        if message.data["skill_id"] != self.skill_id:
            # Not for this skill!
            return

        phrase = message.data["phrase"]
        data = message.data["callback_data"]
        msg = Message(message.type, data={ 'utterance': phrase })
        self.handle_intent(msg)

    @property
    def url_rss(self):
        pre_select = self.settings.get("pre_select", "")
        url_rss = self.settings.get("url_rss")
        if "not_set" in pre_select:
            # Use a custom RSS URL
            url_rss = self.settings.get("url_rss")
        else:
            # Use the selected preset's URL
            url_rss = pre_select

        if not url_rss and 'url_rss' in self.config:
            url_rss = self.config['url_rss']

        return url_rss

    @intent_handler(IntentBuilder("").require("Play").require("News"))
    def handle_intent(self, message):
        try:
            data = feedparser.parse(self.url_rss)

            self.speak_dialog('news')
            wait_while_speaking()

            # After the intro, start the news stream
            url = re.sub('https', 'http',
                         data['entries'][0]['links'][0]['href'])

            # Inlcude the utterance, it might include controlls for the
            # playback system, e.g. "Play the news on the stereo"
            self.audioservice.play(url, message.data['utterance'])

        except Exception as e:
            self.log.error("Error: {0}".format(e))

    def stop(self):
        if self.audioservice.is_playing:
            self.audioservice.stop()
            return True
        else:
            return False


def create_skill():
    return NewsSkill()
