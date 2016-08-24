printf "\033[1;31mInstalling Dependencies\033[0m\n"
# Install RabbitMQ
sudo apt-get update
sudo apt-get -y install apache2 libapache2-mod-wsgi sqlite3 rabbitmq-server python-requests python-m2crypto build-essential openssl chrpath libssl-dev libxft-dev libfreetype6 libfreetype6-dev libfontconfig1 libfontconfig1-dev python-pip python-dev build-essential libpq-dev swig apache2 libapache2-mod-wsgi
pip install --upgrade pip
pip install Django virtualenvwrapper selenium celery

printf "\033[1;31mMoving files around and changing permissions\033[0m\n"
mv celeryd.conf /etc/default/celeryd
mv celeryd /etc/init.d/celeryd
mv Kraken.sh /usr/bin/Kraken
mv Kraken/ /opt/

chown root /etc/default/celeryd
chmod 640 /etc/default/celeryd
chmod 755 /usr/bin/Kraken
chmod 755 /etc/init.d/celeryd

printf "\033[1;31mAdding celery user\033[0m\n"
usercheck=$(id -u celery)
if [ -z $usercheck ]
    then
        useradd -r -s /bin/sh celery
fi
usermod -a -G www-data celery

chown -R www-data /opt/Kraken
chgrp -R www-data /opt/Kraken
chmod 775 /opt/Kraken/Web_Scout/static/Web_Scout/
chmod 775 /opt/Kraken/ghostdriver.log
chmod 775 /opt/Kraken/tmp/

printf "\033[1;31mInstalling PhantomJS\033[0m\n"
# Install PhantomJS
phantomjscheck=$(which phantomjs)
if [ -z $phantomjscheck ]
    then
        MACHINE_TYPE=`uname -m`
        if [ ${MACHINE_TYPE} == 'x86_64' ]; then
        	PHANTOM_JS="phantomjs-1.9.8-linux-x86_64"
        	export PHANTOM_JS="phantomjs-1.9.8-linux-x86_64"
        else
        	PHANTOM_JS="phantomjs-1.9.8-linux-i686"
        	export PHANTOM_JS="phantomjs-1.9.8-linux-i686"
        fi
        
        tar xvjf $PHANTOM_JS.tar.bz2
        
        sudo mv $PHANTOM_JS /usr/local/share
        sudo ln -sf /usr/local/share/$PHANTOM_JS/bin/phantomjs /usr/local/bin
fi

printf "\033[1;31mSetting up Python Virtual Environment\033[0m\n"
#Install Python Virtual Environment
echo "export WORKON_HOME=$HOME/.virtualenvs" >> ~/.bash_profile
echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bash_profile
source ~/.bash_profile
cd /opt/Kraken

secretkeycheck=$(grep "SECRET_KEY" /opt/Kraken/Kraken/settings.py)
if [ -z $secretkeycheck ]
    then
        printf "\033[1;31mCreating new Django private key\033[0m\n"
        secretkey=$(echo 'import random;print "".join([random.SystemRandom().choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50)])' | python)
        echo SECRET_KEY = \'$secretkey\' >> /opt/Kraken/Kraken/settings.py
fi
mkvirtualenv Kraken --no-site-packages
workon Kraken
pip install M2Crypto celery selenium Django

pip install Pillow==2.6.1 requests
./manage.py migrate
./manage.py makemigrations
./manage.py migrate

printf "\033[1;31mCreating Django Superuser\033[0m\n"

# Create django super user. Default creds = admin:2wsxXSW@
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@kraken.com', '2wsxXSW@')" | python ./manage.py shell
deactivate

chmod 774 /opt/Kraken/Kraken/
chmod 774 /opt/Kraken/Kraken/kraken.db
chown www-data /opt/Kraken/Kraken/kraken.db
chgrp www-data /opt/Kraken/Kraken/kraken.db

printf "\033[1;31mSetting up Apache config\033[0m\n"

# Setup Apache 
krakencheck=$(grep "Kraken Entry" /etc/apache2/sites-available/000-default.conf)
if [ "$krakencheck" ]
    then
        printf "\033[1;31mKraken has already been installed.\033[0m\n"
        read -p "If you like to overwrite Kraken's current Apache config, press [ENTER]. Otherwise press Ctrl+c to exit."
        sed -i '/\#Kraken\ Entry/,/\<\/VirtualHost\>/d' /etc/apache2/sites-available/000-default.conf
        sed -i '/\#Kraken\ Entry/ { N; d; }' /etc/apache2/ports.conf
fi

echo "Select a TCP port to host Kraken on: [8000]"
read port
if [ -z $port ]
    then
        port="8000"
fi

portcheck=$(grep "listen $port" /etc/apache2/ports.conf)


while [ "$portcheck" ]
        do
        printf "\033[1;31mPort $port is currently is use.\033[0m\n"
        echo "Enter a new port to use: "
        read port
        portcheck=$(grep "listen $port" /etc/apache2/ports.conf)
done

echo "#Kraken Entry" >> /etc/apache2/ports.conf
echo "listen $port" >> /etc/apache2/ports.conf
cat <<'EOF' >> /etc/apache2/sites-available/000-default.conf

#Kraken Entry
<VirtualHost *:$port>

	Alias /js /opt/Kraken/common/js/
	Alias /css /opt/Kraken/common/css/
	Alias /fonts /opt/Kraken/common/fonts/
    Alias /static /opt/Kraken/Web_Scout/static/
    <Directory /opt/Kraken/Web_Scout/static/Web_Scout/>
        Require all granted
    </Directory>
    <Directory /opt/Kraken/common/>
        Require all granted
    </Directory>

    <Directory /opt/Kraken/>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>
    WSGIDaemonProcess Kraken python-path=/opt/Kraken:/root/.virtualenvs/Kraken/lib/python2.7/site-packages
    WSGIProcessGroup Kraken
    WSGIScriptAlias / /opt/Kraken/Kraken/wsgi.py
    
</VirtualHost>

EOF

printf "\033[1;31mStarting Kraken\033[0m\n"

Kraken reset
echo ""
echo ""
echo "Setup complete!"
echo "Open your browser and visit http://localhost:$port/"
echo "Login with admin:2wsxXSW@"
echo ""

