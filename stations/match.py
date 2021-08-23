# Copyright 2021 Mycroft AI Inc.
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

from collections import namedtuple

from mycroft.util.parse import fuzzy_match

from . import stations


# Minimum confidence levels
CONF_EXACT_MATCH = 0.9
CONF_LIKELY_MATCH = 0.7
CONF_GENERIC_MATCH = 0.6

Match = namedtuple('Match', 'station confidence')


def match_station_name(phrase, station, news_keyword):
    """Determine confidence that a phrase requested a given station.

    Args:
        phrase (str): utterance from the user
        feed (str): the station feed to match against

    Returns:
        tuple: feed being matched, confidence level
    """
    phrase = phrase.lower().replace("play", "").strip()
    station_acronym = station.acronym.lower()
    short_name_confidence = fuzzy_match(phrase, station_acronym)
    long_name_confidence = fuzzy_match(phrase, station.full_name.lower())
    # Test with "News" added in case user only says acronym eg "ABC".
    # As it is short it may not provide a high match confidence.
    modified_short_name = "{} {}".format(station_acronym, news_keyword)
    variation_confidence = fuzzy_match(phrase, modified_short_name)
    key_confidence = CONF_GENERIC_MATCH if news_keyword in phrase and station_acronym in phrase else 0.0

    conf = max((short_name_confidence, long_name_confidence,
                variation_confidence, key_confidence))
    return Match(station, conf)


def match_station_from_utterance(skill, utterance):
    """Get the expected station from a user utterance.
    
    Returns:
        Station or None if news not requested.
    """
    match = Match(None, 0.0)
    if utterance is None:
        return match

    # Remove articles like "the" as it matches too well will "other"
    search_phrase = utterance.lower().replace('the', '').strip()

    if not skill.voc_match(search_phrase, 'News'):
        # User is not asking for the news - do not match.
        return match
    
    # Catch any short explicit phrases eg 'play the news'
    news_phrases = skill.translate_list("PlayTheNews") or []
    if utterance in news_phrases:
        station = skill.get_default_station()
        match = Match(station, 1.0)

    # Check primary feed list for matches eg 'ABC'
    news_keyword = skill.translate('OnlyNews').lower()
    for station in stations.values():
        station_match = match_station_name(utterance, station, news_keyword)
        if station_match.confidence > match.confidence:
            match = station_match

    # Check list of alternate names eg 'associated press' => 'AP'
    for name in skill.alt_feed_names:
        conf = fuzzy_match(utterance, name)
        if conf > match.confidence:
            station = stations[skill.alt_feed_names[name]]
            match = Match(station, conf)

    return match