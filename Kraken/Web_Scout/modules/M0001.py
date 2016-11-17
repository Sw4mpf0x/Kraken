# Default Credential Check for Xerox WorkCentres
def run(host):
	import requests

	# Post request data and headers
	payload = {'_fun_function':'HTTP_Authenticate_fn','NextPage':'/properties/authentication/luidLogin.php','webUsername':'admin','webPassword':'1111','frmaltDomain':'default'}
	headers = {'Content-Type':'application/x-www-form-urlencoded'}

	# Execute request
	r = requests.post("http://" + host + "/userpost/xerox.set", data=payload, headers=headers)
	# Enter logic here. Result is expected to be either "Success" or "Fail"

	if "window.opener" in r.text:
		return "Success", "admin:1111"
	else:
		return "Fail", ""
