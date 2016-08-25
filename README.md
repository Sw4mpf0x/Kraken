# Kraken - Web Interface Enumeration Tool
Kraken is a tool to help make your pentest workflow more efficient when enumerating and reviewing web interfaces on a target network. This is done by using a database (currently Postgresql) to track web interface data metadata. This allows you to take notes and mark interfaces that use default credentials configured or HTTP communications. Once you are done, you can view these systems and the notes you took in the Reports section. 

## Installation

Clone the repository down and run the following commands:

```# chmod 755 setup.sh```

```# ./setup.sh```

Once setup is complete, open your browser and visit http://localhost:8000 and use the following default credentials to log in:

admin:2wsxXSW@

Password change and add user functionality can be found at http://localhost:8000/admin

## Usage

To get started, make your way over to Web Scout's Setup page. Web Scout is what you will use to scan for, and review, the web interfaces available to you on a given network. Kraken will parse port data from an Nmap XML file. The parser will look for either 'HTTP' to be present in the port entry, or one of the following known HTTP ports:

```80,280,443,591,593,981,1311,2031,2480,3181,4444,4445,4567,4711,4712,5104,5280,7000,7001,7002,8000,8008,8011,8012,8013,8014,8042,8069,8080,8081,8243,8280,8281,8443,8531,8887,8888,9080,9443,11371,12443,16080,18091,18092```

Web Scout's Setup page provide file upload functionality for you to provide your XML file. This will parse the Nmap XML data into the SQLite database. The progress field will notify you when complete. The last step for setup is to click the "Take Screenshots" button. This may take a while depending on how many screenshots need to be taken. The screenshot-taking Celery task currently uses 5 threads, each with a Selenium headless PhantomJS web driver, so it can be fairly resource intensive. Progress can be tracked by looking at the progress field. During the screenshot taking process, interfaces are identified by type if possible, and any known default credentials are displayed in the 'viewer.html' page.

Once all of your screenshots are taken, visit Web Scout's main page to see the listing of your web interfaces. Each host gets a 'well'. Each web interace hosted by that host is grouped into that well along with IP, hostname, and basic port information. Clicking a screenshot thumbnail will popup a larger image along with more detailed information about that interface and host. Within this popup you can take notes and check the check boxes for HTTP Authentication, Default Credentials, and reviewed. Hit save to record those notes in the database. All of your notes can be reviewed in Logs>Reports.

You can cycle through the interfaces on each page using the popup by either clicking the Next/Previous buttons or hitting the right/left arrows on your keyboard. Clicking "Open with viewer" will open another tab where that interface will attempt to load into an iframe with a Kraken toolbar at the top. The toolbar allows you to take the same notes you can with the popup and provides you with any known default credentials if possible. There is also a link in case the page is not able to load in the iframe. My workflow is to go through a couple of Web Scout pages using the popup and open web interfaces in the background as I go (Ctrl + left-click for Windows or Option + left-click for Mac). I then go through the tabs and take notes as I go. 

## Troubleshooting

If you run the setup script more than once and Kraken is not working, you may find that you have double entries in 

/etc/apache2/ports.conf

/etc/apache2/sites-available/000-default.conf

Simply delete the double entry so that there is a single, unique entry in each file, restart the Apache service, and you should be back up and running.

If you run into other issues, try executing the following command before performing further troubleshooting:

```# Kraken start```

Django's debugging has been left on to assist in further troubleshooting. 
