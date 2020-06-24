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
from test.integrationtests.voight_kampff import emit_utterance, mycroft_responses, then_wait


def wait_for_service_message(context, message_type):
    """Common method for detecting audio play, stop, or pause messages"""
    msg_type = 'mycroft.audio.service.{}'.format(message_type)
    def check_for_msg(message):
        return (message.msg_type == msg_type, '')

    passed, debug = then_wait(msg_type, check_for_msg, context)

    if not passed:
        debug += mycroft_responses(context)
    if not debug:
        if message_type == 'play':
            message_type = 'start'
        debug = "Mycroft didn't {} playback".format(message_type)

    assert passed, debug


@given('news is playing')
def given_news_playing(context):
    emit_utterance(context.bus, 'what is the news')
    wait_for_service_message(context, 'play')
    time.sleep(1)
    context.bus.clear_messages()


@given('nothing is playing')
def given_nothing_playing(context):
    context.bus.emit(Message('mycroft.stop'))
    time.sleep(5)
    context.bus.clear_messages()


@then('playback should start')
def then_playback_start(context):
    wait_for_service_message(context, 'start')


@then('"mycroft-news" should stop playing')
def then_playback_stop(context):
    wait_for_service_message(context, 'stop')


@then('"mycroft-news" should pause playing')
def then_playback_pause(context):
    wait_for_service_message(context, 'pause')

# TODO remove from Skill once included in Mycroft-core
def then_wait_fail(msg_type, criteria_func, context, timeout=10):
    """Wait for a specified time, failing if criteria is fulfilled.

    Arguments:
        msg_type: message type to watch
        criteria_func: Function to determine if a message fulfilling the
                       test case has been found.
        context: behave context
        timeout: Time allowance for a message fulfilling the criteria

    Returns:
        tuple (bool, str) test status and debug output
    """
    status, debug = then_wait(msg_type, criteria_func, context, timeout)
    return (not status, debug)

@then('"{skill}" should not reply')
def then_do_not_reply(context, skill):

    def check_all_dialog(message):
        msg_skill = message.data.get('meta').get('skill')
        utt = message.data['utterance'].lower()
        skill_responded = skill == msg_skill
        debug_msg = ("{} responded with '{}'. \n".format(skill, utt)
                     if skill_responded else '')
        return (skill_responded, debug_msg)

    passed, debug = then_wait_fail('speak', check_all_dialog, context)
    if not passed:
        assert_msg = debug
        assert_msg += mycroft_responses(context)
    assert passed, assert_msg or '{} responded'.format(skill)
