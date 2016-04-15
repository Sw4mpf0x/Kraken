apt-get update
#cwd=$(pwd)
touch /var/www/ghostdriver.log
chmod 755 /var/www/ghostdriver.log
chown www-data /var/www/ghostdriver.log

#Setup Postgresql
service postgresql start
su postgres << 'EOF'
createdb kraken_db
psql -c "CREATE USER kraken WITH PASSWORD 'kraken' CREATEDB;"
psql -c 'GRANT ALL PRIVILEGES ON DATABASE "kraken_db" TO kraken;'
EOF

mv Kraken/ /opt/
#Install PhantomJS
apt-get -y install python-requests python-m2crypto build-essential chrpath libssl-dev libxft-dev libfreetype6 libfreetype6-dev libfontconfig1 libfontconfig1-dev


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

#Make Kraken Directory
#start postgresql service at boot
#http://thecodeship.com/deployment/deploy-django-apache-virtualenv-and-mod_wsgi/
#https://www.digitalocean.com/community/tutorials/how-to-serve-django-applications-with-apache-and-mod_wsgi-on-ubuntu-14-04
#Install Python Virtual Environment
apt-get -y install python-pip python-dev build-essential libpq-dev swig
pip install --upgrade pip
pip install Django
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
#Install Django
pip install selenium
pip install Django
pip install Pillow==2.6.1 requests
./manage.py migrate
./manage.py makemigrations
./manage.py migrate
chmod 777 /opt/Kraken/Web_Scout/static/Web_Scout/
#Setup Python Virtual Environment
#echo "export WORKON_HOME=$HOME/.virtualenvs" >> ~/.bash_profile
#echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bash_profile
#source ~/.bash_profile
#cd /opt/Kraken
#mkvirtualenv Kraken --no-site-packages
#pip freeze > requirements.txt
#workon Kraken
#for i in $(cat requirements.txt);do pip install $i;done
#pip install psycopg2

deactivate
#rm requirements.txt



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
service apache2 restart


echo ""
echo ""
echo "Setup complete!"
echo "Open your browser and visit http://localhost:8000/"
echo ""