#/bin/bash

display_usage(){
	clear
	echo "============================================================"
	echo "This Kraken utility is used to start and stop services"
	echo "required to run Kraken, as well as update Kraken with the"
	echo "latest version."
	echo ""
	echo "Usage: $0 [start|stop|reset|update]"
	echo "============================================================"
}

if [ $# -le 0 ]
	then
		display_usage
		exit 0
fi

start(){
	sudo /etc/init.d/rabbitmq-server start
	sudo /etc/init.d/celeryd start
	sudo /etc/init.d/apache2 start
	echo ""
	printf "\033[1;31mOpen browser and navigate to http://localhost:8000\033[0m\n"
	echo ""
}

stop(){
	sudo /etc/init.d/rabbitmq-server stop
	sudo /etc/init.d/celeryd stop
	sudo /etc/init.d/apache2 stop
}

reset(){
	sudo/etc/init.d/rabbitmq-server stop
	sudo/etc/init.d/celeryd stop
	sudo/etc/init.d/apache2 stop
	sudo/etc/init.d/rabbitmq-server start
	sudo/etc/init.d/celeryd start
	sudo/etc/init.d/apache2 start
	echo ""
	printf "\033[1;31mOpen browser and navigate to http://localhost:8000\033[0m\n"
	echo ""
}

update(){
	printf "\033[1;31mWARNING! This will delete your Kraken database!\033[0m\n"
	read -p "Press [enter] to continue or Ctrl+C to cancel."
	printf "\033[1;31mStopping Kraken\033[0m\n"
	stop
	rm -rf /tmp/Kraken
	printf "\033[1;31mDownloading latest version of Kraken\033[0m\n"
	git clone https://github.com/Sw4mpf0x/Kraken.git /tmp/
	rm -rf /opt/Kraken
	mv /tmp/Kraken/Kraken /opt/
	/opt/Kraken/manage.py makemigrations
	/opt/Kraken/manage.py migrate
	chown -R www-data /opt/Kraken
	chgrp -R www-data /opt/Kraken
	chmod 775 /opt/Kraken/Kraken/
	chmod 775 /opt/Kraken/Kraken/kraken.db
	chmod 775 /opt/Kraken/Web_Scout/static/Web_Scout/
	chmod 775 /opt/Kraken/ghostdriver.log
	echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@kraken.com', '2wsxXSW@')" | python ./manage.py shell
	printf "\033[1;31mStarting Kraken\033[0m\n"
	start
	rm -rf /tmp/Kraken
}

case "$1" in
  	start)
        start
        ;;
  	stop)
        stop
        ;;
  	reset|reload)
        stop
        start
        ;;
    update)
        update
        ;;
  	*)
        display_usage
        exit 1
esac

exit 0