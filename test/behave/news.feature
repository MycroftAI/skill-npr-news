Feature: mycroft-news

  Scenario Outline: what's the news
    Given an english speaking user
    And nothing is playing
      When the user says "<what's the news>"
      Then "mycroft-news" should reply with dialog from "news.dialog"

   Examples: what's the news
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
     | play the latest news |
     | play today's news |
     | play today's headlines |
     | play today's news briefing |

  Scenario Outline: play the news
    Given an english speaking user
    And nothing is playing
      When the user says "<play the news>"
      Then "mycroft-playback-control" should reply with dialog from "just.one.moment.dialog"

   Examples: play the news
     | play the news |
     | play the news |
     | play news briefing |
     | play news |
     | play news briefing |
     | play headlines |

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
