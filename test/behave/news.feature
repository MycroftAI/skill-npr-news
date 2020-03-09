Feature: mycroft-news

  Scenario Outline: play the news
    Given an english speaking user
    And nothing is playing
      When the user says "<play the news>"
      Then "mycroft-news" should reply with "Here is the latest news from NPR News Now."

   Examples: play the news
     | play the news |
     | play the news |
     | what's new |
     | what's the news |
     | what's the latest news |
     | let's hear the news |
     | play the latest news |
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
     | play news briefing |
     | play news |
     | play today's news |
     | play news briefing |
     | play headlines |
     | play today's headlines |
     | play today's news briefing |
     | tell me the news |
     | tell me today's headlines |
     | tell me the headlines |
     | tell me what's happening |
     | what's happening |

  Scenario Outline: stop news playback
    Given an english speaking user
      And news is playing
      When the user says "<stop the news>"
      Then "mycroft-news" should stop playing

   Examples: stop news playback
     | stop the news |
     | stop |
     | silence |
     | stop playing |

  @xfail
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
      Then "mycroft-common play" should reply with "just a second"
      And "mycroft-news" should reply with the dialog "news.dialog"

   Examples: play specific news channel
     | play a specific news channel |
     | play the BBC news |
     | Play the NPR news |
     | Play AP hourly news |
     | Play the news from Associated Press |
     | Play CBC news |
     | Play Fox News |
     | Play PBS news |
     | Play YLE news |
     | Play  DLF news |
     | Play WDR news |
