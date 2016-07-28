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
	/etc/init.d/postgresql start
	/etc/init.d/rabbitmq-server start
	/etc/init.d/celeryd start
	/etc/init.d/apache2 start
}

stop(){
	/etc/init.d/postgresql stop
	/etc/init.d/rabbitmq-server stop
	/etc/init.d/celeryd stop
	/etc/init.d/apache2 stop
}

reset(){
	/etc/init.d/postgresql stop
	/etc/init.d/rabbitmq-server stop
	/etc/init.d/celeryd stop
	/etc/init.d/apache2 stop
	/etc/init.d/postgresql start
	/etc/init.d/rabbitmq-server start
	/etc/init.d/celeryd start
	/etc/init.d/apache2 start
}

update(){
	stop
	rm -rf /tmp/Kraken
	git clone https://github.com/Sw4mpf0x/Kraken.git /tmp/
	rm -rf /opt/Kraken
	mv /tmp/Kraken/Kraken /opt/
	/opt/Kraken/manage.py makemigrations
	/opt/Kraken/manage.py migrate
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