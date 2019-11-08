# Vagrant

## 0. Prepare
1. Install VirtualBox
2. Install Vagrant

## 1. vagrant init
```
vagrant init
```

## 2. Vagrantfile
`vagrant init` 으로 Vagrantfile 파일을 작성
```
Vagrant.configure("2") do |config|
  config.vm.box = "generic/centos7"
end
```

## 3. Start!
```
vagrant up --provider virtualbox
```

## 4. ssh & set root password
```
vagrant ssh
sudo passwd root
```

## 5. disable firewall
```bash
sudo systemctl stop firewalld
sudo systemctl disable firewalld
```