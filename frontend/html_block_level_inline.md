# HTML - 블록 레빌(Block level) 요소와 인라인(inline) 요소

1. 블록 요소
    - DIV, H1, P
    - 사용 가능한 최대 가로 너비를 사용한다.
    - 크기를 지정할 수 있다.
    - (width: 100%; height: 0; 시작)
    - 수직으로 쌓인다.
    - margin, padding 위, 아래, 좌, 우 사용 가능하다.
    - 레이아웃(layout)을 잡는 용도로 사용
    - `display: inline;` 을 통해서 강제로 인라인 요소로 변경할 수가 있다.

2. 인라인 요소
    - SPAN, IMG
    - 필요한 만큼의 너비만 사용한다.
    - 크기를 지정할 수 없다.
    - (width: 0; height: 0; 시작)
    - 수평으로 쌓인다. (띄어쓰기가 포함되는)
        - 줄바꿈이 없으면, 띄어쓰기는 없어진다.
    - margin, padding 위, 아래에 대해서 온전히 사용할 수 없다.
        - 사실상 위, 아래는 안된다고 보면 될 듯...
    - 텍스트(text)를 다루는 용도
    - `display: block;` 을 통해서 강제로 블록 요소로 변경할 수가 있다.

3. display 속성 (property)
    - block, inline에 따라 블록/인라인으로 강제 조정 가능하다.
    - 개별 태그는 이미 block 또는 inline의 값이 지정되어 있다.

4. charset EUC-KR vs UTF-8
    - EUC-KR: 완성형, 박 영 웅
    - UTF-8: 조합형, ㅂ ㅏ ㄱ ㅇ ㅕ ㅇ ㅇ ㅜ ㅇ