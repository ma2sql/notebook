# pyenv install

>pyenv lets you easily switch between multiple versions of Python.
>It’s simple, unobtrusive, and follows the UNIX tradition of
>single-purpose tools that do one thing well.

https://github.com/yyuu/pyenv


## pyenv installer
ref: https://github.com/yyuu/pyenv-installer

```bash
# 필요한 라이브러리를 먼저 설치
yum install zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel

# Install
# https://github.com/pyenv/pyenv-installer
curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash

# update
pyenv update

# Uninstall
rm -fr ~/.pyenv

# remove these lines from .bashrc or .bash_profile
export PATH="/root/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

## Usage
ref: https://github.com/pyenv/pyenv/blob/master/COMMANDS.md

```bash
# checking installable python versions
pyenv install --list

# installing python
pyenv install [version]

# checking installed python verions
pyenv versions

# checking the current python version
pyenv version

# pyenv-virtualenv 는 pyenv-installer 사용 시 자동을 설치됨.
pyenv-virtualenv

# create
pyenv virtualenv [version] [virtualenv's name]

# create virtualenv by local version
pyenv virtualenv [virtualenv's name]

# check virtualenvs
pyenv virtualenvs

# activate virtualenv
pyenv shell [virtualenv's name]

# uninstall virtualenv
pyenv uninstall [virtualenv's name]
```
