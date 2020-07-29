Feature: mycroft-news

  Scenario Outline: what's the news
    Given an english speaking user
    And nothing is playing
      When the user says "<what's the news>"
      Then "mycroft-news" should reply with dialog from "news.dialog"

   Examples: What's the news - standard intent
     | what's the news |
     | what's the news |
     | what's new |
     | what's the news |
     | what's the latest news |
     | let's hear the news |
     | what's this hour's news |
     | give me the news |
     | news |
     | news briefing |
     | brief me |
     | brief me on the headlines |
     | give me the headlines |
     | give me the breaking news |
     | what's the breaking news |
     | breaking news |
     | give me the news updates |
     | what's today's news |
     | what's today's briefing |
     | what are today's headlines |
     | what's today's headlines |
     | tell me the news |
     | tell me today's headlines |
     | tell me the headlines |
     | tell me what's happening |
     | what's happening |

  Scenario Outline: Play the news using Common Play Framework
    Given an english speaking user
    And nothing is playing
      When the user says "<play the news>"
      Then "mycroft-playback-control" should reply with dialog from "news.dialog"

   Examples: play the news
     | play the news |
     | play the news |
     | play news briefing |
     | play news |
     | play news briefing |
     | play headlines |
     | play the latest news |
     | play today's news |
     | play today's headlines |
     | play today's news briefing |

  Scenario Outline: stop news playback
    Given an english speaking user
      And news is playing
      When the user says "<stop the news>"
      Then "mycroft-news" should stop playing

   Examples: stop news playback
     | stop the news |
     | stop |
     | stop playing |

  @xfail
  # Jira MS-108 https://mycroft.atlassian.net/browse/MS-108
  Scenario Outline: Failing stop news playback
    Given an english speaking user
      And news is playing
      When the user says "<stop the news>"
      Then "mycroft-news" should stop playing

   Examples: stop news playback
     | stop the news |
     | quit |
     | end |
     | turn it off |
     | turn off news |
     | turn off music |
     | shut it off |
     | shut up |
     | be quiet |
     | end playback |
     | silence |

  Scenario Outline: pause news playback
    Given an english speaking user
      When the user says "<pause the news>"
      Then "mycroft-news" should pause playing

   Examples: pause news playback
     | pause the news |
     | pause |

  Scenario Outline: play a specific news channel
    Given an english speaking user
      When the user says "<play a specific news channel>"
      Then "mycroft-playback-control" should reply with dialog from "just.one.moment.dialog"
      Then mycroft reply should contain "<specified channel>"

   Examples: play specific news channel
     | play a specific news channel | specified channel |
     | play the BBC news | BBC News |
     | Play the NPR news | NPR News |
     | Play AP hourly news | AP Hourly Radio News |
     | Play the news from Associated Press | AP Hourly Radio News |
     | Play CBC news | CBC News |
     | Play Fox News | Fox News |
     | Play PBS news | PBS Newshour |
     | Play YLE news | YLE |
     | Play  ABC news | ABC |
     | Play  DLF news | DLF |
     | Play  TSF news | TSF |
     | Play WDR news | WDR |
     | play news from bbc | BBC News |
     | Play news from ekot | Ekot |

  @xfail
  Scenario Outline: give me the news from channel
    Given an english speaking user
      When the user says "<give me news from a specific channel>"
      Then mycroft reply should contain "<specified channel>"

   Examples:
     | give me news from a specific channel | specified channel |
     | give me the news from bbc | BBC News |
     | give me the news from ekot | Ekot |
     | tell me the latest NPR news | NPR |
     | what are the latest headlines from Fox | Fox |
     | what are the headlines from WDR | WDR |

  Scenario Outline: play music with names similar to news channels
    Given an english speaking user
     When the user says "<play some music>"
     Then "NewsSkill" should not respond

    Examples:
      | play some music |
      | what time is it |
      | what's the weather |
      | cancel timer |
      | play metallica |
      | play 1live on tunein |
      | play sunshine on tunein |
      | play bigfm on tunein |
      | Play klassik lounge easy radio |
      | play the song monkey brains |
      | play the song skinamarinky dinky dink |
      | play the song python programming |
      | play the song covid-19 |