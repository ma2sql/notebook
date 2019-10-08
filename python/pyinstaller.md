---
tags: [python]
---

# pyinstaller를 사용한 단일 바이너리 파일 만들기

- [pyinstaller](#pyinstaller)
- [Install](#install)
- [Usage](#usage)
- [pyenv 환경에서의 빌드](#pyenv-환경에서의-빌드)
    - [OSError: Python library not found: libpython3.7.so.1.0, libpython3.7m.so.1.0, libpython3.7mu.so.1.0](#oserror-python-library-not-found-libpython37so10-libpython37mso10-libpython37muso10)
    - [ERROR: The Python ssl extension was not compiled. Missing the OpenSSL lib?](#error-the-python-ssl-extension-was-not-compiled-missing-the-openssl-lib)

## 배경
개발된 파이썬 버전, OS 환경, 의존성 라이브러리 설치 등등 DBA로서 사용하는 파이썬 스크립트의 규모에 비해 필요한 환경을 준비하는 것은 매우 번거롭다. 파이썬으로 작성된 스크립트를 실행이 가능한 단일 바이너리 파일로 만들어 배포하는 형태로 사용하면, 이러한 것들이 매우 간편해질 것이다. 바로 이 부분에 도움을 줄 수 있는 것이 `PyInstaller` 이다.
- https://github.com/pyinstaller/pyinstaller

## pyinstaller
`PyInstaller`는 파이썬 어플리케이션과 의존성이 있는 라이브러리들을 하나의 패키지로 만들어주는 툴이다. 사용자는 파이썬 인터프리터나 기타 모듈이 없이도 자신의 파이썬 스크립트를 실행시킬 수 있게 된다.

## Install
설치는 보통을 파이썬 모듈처럼 pip로 설치하는 것이 가능하다.
```bash
pip install pyinstaller
```

## Usage
사용 또한 간편하다. 단순히 아래와 같은 명령으로 한 줄로 빌드하는 것이 가능하다. 다만, 이렇게 만들어진 바이너리 파일은 파일을 생성한 시점의 GCC 버전 등에 의존성이 있으므로 참고하도록 하자.
```bash
# -F: Create a one-file bundled executable.
#  --clean: Clean PyInstaller cache and remove temporary files
pyinstaller -F --clean aof_parser.py 
ls dist/
-rwxr-xr-x 1 root root 8364144 Oct  8 17:11 aof_parser
```

## pyenv 환경에서의 빌드
파이썬 개발환경에서는 virtualenv 등의 가상 환경이 많이 쓰이고, 또 이러한 것들을 편하게 만들어주는 pyenv 또한 많이 쓰인다. 다만, 이러한 경우에는 몇 가지 문제가 발생할 수 있는데, 이에 대한 해결책은 다음과 같다.

### OSError: Python library not found: libpython3.7.so.1.0, libpython3.7m.so.1.0, libpython3.7mu.so.1.0
- https://github.com/pyinstaller/pyinstaller/wiki/FAQ#gnulinux
```bash
PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install
3.6.6 already exists
continue with installation? (y/N) y
```
### ERROR: The Python ssl extension was not compiled. Missing the OpenSSL lib?
- https://github.com/pyenv/pyenv/wiki/Common-build-problems#error-the-python-ssl-extension-was-not-compiled-missing-the-openssl-lib
```bash
export LD_LIBRARY_PATH=$HOME/.pyenv/versions/3.6.6/lib
```

## Reference
- https://7me.oji.0j0.jp/2018/09/13/pyinstaller-pyenv-oserror-typeerror-library-not-found/