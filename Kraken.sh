#/bin/bash

display_usage(){
    echo "====================================================================="
    echo "This Kraken utility is used to start and stop Kraken,"
    echo "update Kraken, backup, restore, and add new users."
    echo ""
    echo "Usage: $0 [start|stop|restart|update|backup|"
    echo "           restore|adduser <username> <password>]"
    echo "====================================================================="
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
    printf "\033[1;31mKraken started.\033[0m\n"
    port=$(awk 'c&&!--c{print $2};/\#Kraken\ Entry/{c=1}' /etc/apache2/ports.conf)
    printf "\033[1;31mOpen a browser and navigate to http://localhost:$port\033[0m\n"
    echo ""
}

stop(){
    sudo /etc/init.d/rabbitmq-server stop
    sudo /etc/init.d/celeryd stop
    sudo /etc/init.d/apache2 stop
    printf "\033[1;31mKraken stopped.\033[0m\n"
}

update(){
    printf "\033[1;31mWARNING! Are you sure you want to update?\033[0m\n"
    read -p "Press [enter] to continue or Ctrl+c to cancel."
    printf "\033[1;31mStopping Kraken...\033[0m\n"
    stop
    backup

    rm -rf /tmp/Kraken
    printf "\033[1;31mDownloading latest version of Kraken...\033[0m\n"
    git clone https://github.com/Sw4mpf0x/Kraken.git /tmp/Kraken

    rm -rf /opt/Kraken
    mv /tmp/Kraken/Kraken /opt/
    secretkey=$(echo 'import random;print "".join([random.SystemRandom().choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50)])' | python)
    echo SECRET_KEY = \'$secretkey\' >> /opt/Kraken/Kraken/settings.py
    #/opt/Kraken/manage.py makemigrations
    #/opt/Kraken/manage.py migrate
    
    printf "\033[1;31mRestoring Kraken data...\033[0m\n"
    cwd=$(pwd)
    echo $cwd/KrakenBackup.zip | restore


    chown -R www-data /opt/Kraken
    chgrp -R www-data /opt/Kraken
    chmod 775 /opt/Kraken/Kraken/
    chmod 775 /opt/Kraken/Kraken/kraken.db
    chmod 775 /opt/Kraken/static/Web_Scout/
    chmod 775 /opt/Kraken/ghostdriver.log
    chmod 775 /opt/Kraken/tmp/
    #echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@kraken.com', '2wsxXSW@')" | python /opt/Kraken/manage.py shell
    printf "\033[1;31mStarting Kraken\033[0m\n"
    if [ -e "/tmp/Kraken/update.sh" ]
        then
            chmod 755 /tmp/Kraken/update.sh
            /tmp/Kraken/update.sh
    fi
    start


    rm -rf /tmp/Kraken
    rm $cwd/KrakenBackup.zip
    printf "\033[1;31mUpdate complete!\033[0m\n"
}

backup(){
    printf "\033[1;31mBacking up Kraken to current directory...\033[0m\n"
    zip -j KrakenBackup.zip /opt/Kraken/Kraken/kraken.db /opt/Kraken/static/Web_Scout/*
    printf "\033[1;31mBackup saved to KrakenBackup.zip in current working directory.\033[0m\n"
}

restore(){
    while [ -z "$backuppath" ]
    do
        echo "Specify absolute path to KrakenBackup.zip: "
        read backuppath
        if [ ! -e "$backuppath" ]; then
            echo "Invalid path entered."
            backuppath=""
        fi
    done

    if [ ! -d "/tmp/krakenbackup" ]
        then
            mkdir /tmp/krakenbackup
    fi
    printf "\033[1;31mRestoring Kraken data...\033[0m\n"
    unzip $backuppath -d /tmp/krakenbackup/
    cp /tmp/krakenbackup/kraken.db /opt/Kraken/Kraken/kraken.db
    cp /tmp/krakenbackup/*.png /opt/Kraken/static/Web_Scout/
    rm -rf /tmp/krakenbackup
    printf "\033[1;31mRestoration complete.\033[0m\n"
}

adduser(){
    if [ -z "$1" ]
    then
        display_usage
        printf "\033[1;31mA username and password must be provided.\033[0m\n"
        return 0
    fi
    if [ -z "$2" ]
    then
        display_usage
        printf "\033[1;31mA password must be provided.\033[0m\n"
        return 0
    fi

    echo "from django.contrib.auth.models import User; User.objects.create_superuser('$1', '$1@kraken.com', '$2')" | python /opt/Kraken/manage.py shell
    echo ""
    printf "\033[1;31mUser $1 added.\033[0m\n"
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    reset|restart)
        printf "\033[1;31mRestarting Kraken.\033[0m\n"
        stop
        start
        ;;
    update)
        update
        ;;
    backup)
        backup
        ;;
    restore)
        restore
        ;;
    adduser)
        adduser $2 $3
        ;;
    *)
        display_usage
        exit 1
esac

exit 0