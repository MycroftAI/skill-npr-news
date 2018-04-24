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
from mycroft.util.log import LOG
try:
    from mycroft.skills.audioservice import AudioService
except:
    from mycroft.util import play_mp3
    AudioService = None


class NewsSkill(MycroftSkill):
    def __init__(self):
        super(NewsSkill, self).__init__(name="NewsSkill")
        self.process = None
        self.audioservice = None

    def initialize(self):
        if AudioService:
            self.audioservice = AudioService(self.emitter)

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
            # Stop anything already playing
            self.stop()

            self.speak_dialog('news')
            wait_while_speaking()

            # After the intro, start the news stream
            url = re.sub('https', 'http',
                         data['entries'][0]['links'][0]['href'])
            # if audio service module is available use it
            if self.audioservice:
                self.audioservice.play(url, message.data['utterance'])
            else:  # othervice use normal mp3 playback
                self.process = play_mp3(url)

        except Exception as e:
            LOG.error("Error: {0}".format(e))

    def stop(self):
        if self.audioservice:
            self.audioservice.stop()
        else:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait()


def create_skill():
    return NewsSkill()
