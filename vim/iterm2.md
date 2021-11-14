# Iterm2 관련 설정

## tab 이동 관련 단축키 처리
Iterm2 사용시, 탭 이동을 위한 `Ctrl+PageUp/Down` 단축키가 먹히지 않을 때에는 아래와 같이 조치한다.

참고: https://superuser.com/questions/322983/how-to-let-ctrl-page-down-switch-tabs-inside-vim-in-terminal-app

_Based on ramn's answer and just as a reference, this is how to solve this problem in iTerm2:_

1. Go to iTerm / Preferences... / Profiles / Keys
2. Press the + button to add a profile shortcut
3. Use shortcut: ^Page Up, action: "Send Escape sequence", value [5;5~
4. Use shortcut: ^Page Down, action: "Send Escape sequence", value [6;5~
