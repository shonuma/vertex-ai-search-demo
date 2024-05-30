grep "deb http://archive.ubuntu.com/ubuntu focal-updates main" /etc/apt/sources.list
if [ x$0 = "x1" ];
then
    echo "deb http://archive.ubuntu.com/ubuntu focal-updates main" >> /etc/apt/sources.list
fi
apt -y update
apt -y install libgtk-3-dev
apt -y install libgstreamer-plugins-base1.0-0
apt -y install libmpv-dev mpv