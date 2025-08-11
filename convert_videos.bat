@echo off
FOR /L %%G IN (1,1,10) DO (
    echo Processing Video %%G...
    python "h:\My Drive\Consulting\Udemy Course\Fraud Fundamentals Course\Scripts\gemini-tts-converter.py" "h:\My Drive\Consulting\Udemy Course\Fraud Fundamentals Course\Module 2\Video %%G"
)
echo All videos processed.
