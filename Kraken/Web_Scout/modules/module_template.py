def run(host):
	import requests

	# Post request data and headers
	payload = {'Username':'admin','Password':'admin'}
	headers = {'Content-Type':'application/x-www-form-urlencoded'}


	# Execute request
	r = requests.post("http://" + host + "/login", data=payload, headers=headers)
	

	# Result is expected to be either "Success" or "Fail". 
	# Also return the password(s) that worked
	if "value" in r.text:
		return "Success", "admin:admin"
	else:
		return "Fail", ""