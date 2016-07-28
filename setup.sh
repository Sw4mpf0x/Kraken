#apt-get update
#touch /var/www/ghostdriver.log
#chmod 755 /var/www/ghostdriver.log
#chown www-data /var/www/ghostdriver.log

#Setup Postgresql
/etc/init.d/postgresql start
su postgres << 'EOF'
createdb kraken_db
psql -c "CREATE USER kraken WITH PASSWORD 'kraken' CREATEDB;"
psql -c 'GRANT ALL PRIVILEGES ON DATABASE "kraken_db" TO kraken;'
EOF

mv celeryd.conf /etc/default/celeryd
mv celeryd /etc/init.d/celeryd
mv Kraken.sh /usr/bin/Kraken
mv Kraken/ /opt/
#Install PhantomJS
apt-get -y install python-requests python-m2crypto build-essential chrpath libssl-dev libxft-dev libfreetype6 libfreetype6-dev libfontconfig1 libfontconfig1-dev

# Install RabbitMQ
apt-get -y install rabbitmq-server

pip install celery

cd ~
MACHINE_TYPE=`uname -m`
if [ ${MACHINE_TYPE} == 'x86_64' ]; then
	PHANTOM_JS="phantomjs-1.9.8-linux-x86_64"
	export PHANTOM_JS="phantomjs-1.9.8-linux-x86_64"
else
	PHANTOM_JS="phantomjs-1.9.8-linux-i686"
	export PHANTOM_JS="phantomjs-1.9.8-linux-i686"
fi

wget https://bitbucket.org/ariya/phantomjs/downloads/$PHANTOM_JS.tar.bz2
tar xvjf $PHANTOM_JS.tar.bz2

mv $PHANTOM_JS /usr/local/share
ln -sf /usr/local/share/$PHANTOM_JS/bin/phantomjs /usr/local/bin
rm $PHANTOM_JS.tar.bz2


chmod 755 /usr/bin/Kraken
chmod 755 /etc/init.d/celeryd

useradd -r -s /bin/sh celery

chown celery /opt/Kraken/Web_Scout/static/Web_Scout/
chgrp celery /opt/Kraken/Web_Scout/static/Web_Scout/
chmod 755 /opt/Kraken/Web_Scout/static/Web_Scout/

chown celery /opt/Kraken/ghostdriver.log
chgrp celery /opt/Kraken/ghostdriver.log
chmod 755 /opt/Kraken/ghostdriver.log
#Make Kraken Directory
#start postgresql service at boot
#Install Python Virtual Environment
apt-get -y install python-pip python-dev build-essential libpq-dev swig
pip install --upgrade pip
pip install Django
pip install psycopg2
pip install virtualenvwrapper
pip install selenium
echo "export WORKON_HOME=$HOME/.virtualenvs" >> ~/.bash_profile
echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bash_profile
source ~/.bash_profile
cd /opt/Kraken
mkvirtualenv Kraken --no-site-packages
workon Kraken
pip install psycopg2
pip install M2Crypto
pip install celery
#Install Django
pip install selenium
pip install Django

pip install Pillow==2.6.1 requests
./manage.py migrate
./manage.py makemigrations
./manage.py migrate
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@kraken.com', '2wsxXSW@')" | python ./manage.py shell
#Setup Python Virtual Environment

deactivate

#Setup Apache
apt-get -y install apache2 libapache2-mod-wsgi

echo "<VirtualHost *:8000>" >> /etc/apache2/sites-available/000-default.conf
echo "" >> /etc/apache2/sites-available/000-default.conf
echo "    Alias /static /opt/Kraken/Web_Scout/static/" >> /etc/apache2/sites-available/000-default.conf
echo "    <Directory /opt/Kraken/Web_Scout/static/Web_Scout/>" >> /etc/apache2/sites-available/000-default.conf
echo "        Require all granted" >> /etc/apache2/sites-available/000-default.conf
echo "    </Directory>" >> /etc/apache2/sites-available/000-default.conf
echo "" >> /etc/apache2/sites-available/000-default.conf
echo "    <Directory /opt/Kraken/>" >> /etc/apache2/sites-available/000-default.conf
echo "        <Files wsgi.py>" >> /etc/apache2/sites-available/000-default.conf
echo "            Require all granted" >> /etc/apache2/sites-available/000-default.conf
echo "        </Files>" >> /etc/apache2/sites-available/000-default.conf
echo "    </Directory>" >> /etc/apache2/sites-available/000-default.conf
echo "    WSGIDaemonProcess Kraken python-path=/opt/Kraken:/root/.virtualenvs/Kraken/lib/python2.7/site-packages" >> /etc/apache2/sites-available/000-default.conf
echo "    WSGIProcessGroup Kraken" >> /etc/apache2/sites-available/000-default.conf
echo "    WSGIScriptAlias / /opt/Kraken/Kraken/wsgi.py" >> /etc/apache2/sites-available/000-default.conf
echo "" >> /etc/apache2/sites-available/000-default.conf
echo "</VirtualHost>" >> /etc/apache2/sites-available/000-default.conf
echo "listen 8000" >> /etc/apache2/ports.conf
/etc/init.d/apache2 restart


echo ""
echo ""
echo "Setup complete!"
echo "Open your browser and visit http://localhost:8000/"
echo ""


# Install Celery (above) and RabbitMQ



# Daemonize Celery




