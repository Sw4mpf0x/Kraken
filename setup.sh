#apt-get update
#touch /var/www/ghostdriver.log
#chmod 755 /var/www/ghostdriver.log
#chown www-data /var/www/ghostdriver.log

printf "\033[1;31mInstalling Dependencies\033[0m\n"
# Install RabbitMQ
sudo apt-get update
apt-get -y install rabbitmq-server postgresql python-requests python-m2crypto build-essential openssl chrpath libssl-dev libxft-dev libfreetype6 libfreetype6-dev libfontconfig1 libfontconfig1-dev python-pip python-dev build-essential libpq-dev swig apache2 libapache2-mod-wsgi
pip install --upgrade pip
pip install Django psycopg2 virtualenvwrapper selenium celery

sudo /etc/init.d/postgresql start
su postgres << 'EOF'
createdb kraken_db
psql -c "CREATE USER kraken WITH PASSWORD 'kraken' CREATEDB;"
psql -c 'GRANT ALL PRIVILEGES ON DATABASE "kraken_db" TO kraken;'
EOF

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
useradd -r -s /bin/sh celery

chown celery /opt/Kraken/Web_Scout/static/Web_Scout/
chgrp celery /opt/Kraken/Web_Scout/static/Web_Scout/
chmod 755 /opt/Kraken/Web_Scout/static/Web_Scout/

chown celery /opt/Kraken/ghostdriver.log
chgrp celery /opt/Kraken/ghostdriver.log
chmod 755 /opt/Kraken/ghostdriver.log

printf "\033[1;31mInstalling PhantomJS\033[0m\n"
# Install PhantomJS
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


printf "\033[1;31mSetting up Python Virtual Environment\033[0m\n"
#Install Python Virtual Environment
echo "export WORKON_HOME=$HOME/.virtualenvs" >> ~/.bash_profile
echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bash_profile
source ~/.bash_profile
cd /opt/Kraken
printf "\033[1;31mCreating new Django private key\033[0m\n"
secretkey=$(echo 'import random;print "".join([random.SystemRandom().choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50)])' | python)
echo SECRET_KEY = \'$secretkey\' >> /opt/Kraken/Kraken/settings.py
mkvirtualenv Kraken --no-site-packages
workon Kraken
pip install psycopg2 M2Crypto celery selenium Django
#pip install M2Crypto
#pip install celery
#Install Django
#pip install selenium
#pip install Django

pip install Pillow==2.6.1 requests
./manage.py migrate
./manage.py makemigrations
./manage.py migrate

printf "\033[1;31mCreating Django Superuser\033[0m\n"
# Create django super user. Default creds = admin:2wsxXSW@
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@kraken.com', '2wsxXSW@')" | python ./manage.py shell
deactivate

printf "\033[1;31mSetting up Apache config\033[0m\n"
#Setup Apache
openssl req -x509 -nodes -days 1825 -newkey rsa:4096 -keyout kraken.key -out kraken.crt -subj '/C=US/ST=Oregon/L=Portland/CN=www.kraken.oc'
mkdir /etc/apache2/ssl
mv kraken.crt /etc/apache2/ssl/
mv kraken.key /etc/apache2/ssl/


# Setup Apache 
echo "listen 8000" >> /etc/apache2/ports.conf
cat <<'EOF' >> /etc/apache2/sites-available/000-default.conf

<VirtualHost *:8000>

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

    ServerName kraken.com
    SSLEngine on
    SSLCertificateFile /etc/apache2/ssl/kraken.crt
    SSLCertificateKeyFile /etc/apache2/ssl/kraken.key
    
</VirtualHost>

EOF
sudo a2enmod ssl

printf "\033[1;31mStarting Kraken\033[0m\n"
sudo /etc/init.d/rabbitmq-server start
sudo /etc/init.d/apache2 start
sudo /etc/init.d/celeryd start



echo ""
echo ""
echo "Setup complete!"
echo "Run 'Kraken start' and open your browser and visit http://localhost:8000/"
echo "Login with admin:2wsxXSW@"
echo ""

