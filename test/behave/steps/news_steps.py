# Copyright 2017 Mycroft AI Inc.
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
#
import time

from behave import given, then

from mycroft.messagebus import Message
from test.integrationtests.voight_kampff import emit_utterance


def wait_playback_start(context, timeout=10):
    cnt = 0
    while context.bus.get_messages('mycroft.audio.service.play') == []:
        if cnt > (timeout * (1.0 / 0.5)):
            return False
        time.sleep(0.5)
    return True


@given('news is playing')
def given_news_playing(context):
    emit_utterance(context.bus, 'what is the news')
    wait_playback_start(context)
    time.sleep(1)
    context.bus.clear_messages()


@given('nothing is playing')
def given_nothing_playing(context):
    context.bus.emit(Message('mycroft.stop'))
    time.sleep(5)
    context.bus.clear_messages()


@then('playback should start')
def then_playback_start(context):
    assert wait_playback_start is True, 'Playback didn\'t start'


@then('"mycroft-news" should stop playing')
def then_playback_stop(context):
    cnt = 0
    while context.bus.get_messages('mycroft.audio.service.stop') == []:
        if cnt > 20:
            assert False, "No stop message received"
            break
        else:
            cnt += 1
        time.sleep(0.5)


@then('"mycroft-news" should pause playing')
def then_playback_pause(context):
    cnt = 0
    while context.bus.get_messages('mycroft.audio.service.pause') == []:
        if cnt > 20:
            assert False, "No stop message received"
            break
        else:
            cnt += 1
        time.sleep(0.5)
