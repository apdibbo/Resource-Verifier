#!/usr/bin/python
from subprocess import PIPE, Popen
import json
import xml.etree.ElementTree as ET
import sys

outputformat = 0 # 0=pretty, 1=json
if len(sys.argv) > 1:
	if sys.argv[1] == "-h":
		print "Usage: {0} [-h] [--json]".format(sys.argv[0])
		sys.exit(0)
	if sys.argv[1] == "--json":
		outputformat = 1


def cl(c):
	p = Popen(c, shell=True, stdout=PIPE, stderr = PIPE)
	return (p.communicate()[0], p.returncode)

thwr = cl("ccm /hardware --format json")[0]
thwj = "".join(thwr.split('\n')[2:])
thw = json.loads(thwj)


rhwr = cl("lshw -xml")[0]
root = ET.fromstring(rhwr)

attrs = {
	"eth0": "",
	"eth0.hwaddr": "",
	"cpu": {},
	"ram": "",
	"harddisks": {}
}

#ethernet
core = root.find("node")
for n in core.findall("node"):
	nid = n.get("id")
	if nid == "pci":
		for pn in n.findall("node"):
			if pn.get("id") == "network":
				attrs["eth0"] = pn.find("logicalname").text
				attrs["eth0.hwaddr"] = pn.find("serial").text
	if nid[0:3] == "cpu":
		attrs["cpu"][int(nid[4:])] = {
			"manufacturer": n.find("vendor").text,
			"model": n.find("product").text,
			"speed": str(int(n.find("size").text)/1000000),
			"vendor": n.find("vendor").text
		}
	if nid == "memory":
		attrs["ram"] = str(int(n.find("node").find("size").text)/1048576)

rwlsblk = cl("lsblk --raw")[0]
sl = rwlsblk.split("\n")[:-1]
sl.reverse()
for d in sl:
	if len(d.split()) < 6:
		continue
	if d.split()[5] == "disk":
		s = d.split()[3]
		n = int(s[:-1])
		u = s[-1]
		sizes = ["K", "M", "G", "T", "P"]
		sf = sizes.index(u.upper())-1
		mbn = n*(1024**sf)
	
		attrs["harddisks"][d.split()[0]] = str(mbn)
# sorry abou this next bit, it's awful I know
result = {}

result["eth"] = {}
result["eth"]["hwaddr"] = {}
t = thw["cards"]["nic"]["eth0"]["hwaddr"]
result["eth"]["hwaddr"]["correct"] = (attrs["eth0.hwaddr"] == t)
if attrs["eth0.hwaddr"] != t: result["eth"]["hwaddr"]["target"] = t
result["eth"]["hwaddr"]["detected"] = attrs["eth0.hwaddr"]

result["ram"] = {}
sizes = [int(x["size"]) for x in thw["ram"]]
t = sum(sizes)
result["ram"]["correct"] = (attrs["ram"] == t)
if attrs["ram"] != t: result["ram"]["target"] = t
result["ram"]["detected"] = attrs["ram"]

result["cpu"] = {}

result["cpu"]["correct"] = {}
result["cpu"]["missing"] = {}
result["cpu"]["excess"] = {}
for cpu in attrs["cpu"]:
	ccpu = {}
	if cpu >= len(thw["cpu"]):
		t = attrs["cpu"][cpu]
		result["cpu"]["excess"][cpu] = t
		continue
	for a in attrs["cpu"][cpu]:	
		t = str(attrs["cpu"][cpu][a])
		v = str(thw["cpu"][cpu][a])
			
		cobj = {}
		cobj["correct"] = (t==v)
		if t!=v: cobj["target"] = t
		cobj["detected"] = v
		ccpu[a] = cobj
	result["cpu"]["correct"][cpu] = ccpu
for i in range(0,len(thw["cpu"])):
	if i not in attrs["cpu"]:
		t = thw["cpu"][i]
		result["cpu"]["missing"][cpu] = t


rhd = attrs["harddisks"]
rhd["sda"] = rhd["vda"]

rhds = set(rhd.keys())
thds = set(thw["harddisks"].keys())

result["hds"] = {}

result["hds"]["excess"] = {}
for i in rhds-thds: # excess
	result["hds"]["excess"][i] = rhd[i]

result["hds"]["missing"] = {}
for i in thds-rhds:
	result["hds"]["missing"][i] = thw["harddisks"][i]["capacity"]


result["hds"]["correct"] = {}
for i in thds&rhds:
	obj = {}
	obj["correct"] = (rhd[i] == thw["harddisks"][i]["capacity"])
	obj["detected"] = rhd[i]
	if rhd[i] != thw["harddisks"][i]["capacity"]: obj["target"] = thw["harddisks"][i]["capacity"]
	result["hds"]["correct"][i] = obj
if outputformat == 1:
	print json.dumps(result, indent=4)
if outputformat == 0:
	for r in result:
		res = result[r]
		print r + ":"
		if r == "eth":
			print "  - Hardware address: {0}".format(res["hwaddr"]["detected"]) + ((" --> {0}".format(res["hwaddr"]["target"])) if not res["hwaddr"]["correct"] else "")
		if r == "ram":
			print "  - Size: {0}M".format(res["detected"]) + ((" --> {0}M".format(res["target"])) if not res["correct"] else "")
		if r == "hds":
			if len(res["correct"]) > 0:
				print "    Correct:"
			for i in res["correct"]:
				print "      - {0}: {1}M".format(i, res["correct"][i]["detected"]) + ((" --> {0}M".format(res["correct"][i]["target"])) if not res["correct"][i]["correct"] else "")
			if len(res["missing"]) > 0:
				print "    Missing:"
			for i in res["missing"]:
				print "      - {0}: {1}M".format(i, res["missing"][i])
			if len(res["excess"]) > 0:
				print "    Excess:"
			for i in res["excess"]:
				print "      - {0}: {1}M".format(i, res["excess"][i])

		if r == "cpu":
			mu = {
				"speed":["MHz", "Speed"],
				"model":["", "Model"],
				"vendor":["", "Vendor"],
				"manufacturer":["", "Manufacturer"]
			}
			if len(res["correct"]) > 0:
				print "    Correct:"
			for i in res["correct"]:
				print "      + " + str(i) + ": "
				ress = res["correct"][i]
				for j in ress:
					print "          - {0}: {1}{2}".format(mu[j][1], ress[j]["detected"], mu[j][0]) + ((" --> {0}{1}".format(ress[j]["target"], mu[j][0])) if not ress[j]["correct"] else "")
			if len(res["missing"]) > 0:
				print "    Missing:"
			for i in res["missing"]:
				print "      + " + str(i) + ": "
				ress = res["missing"][i]
				for j in ress:
					print "          - {0}: {1}{2}".format(mu[j][1], ress[j], mu[j][0])


			if len(res["excess"]) > 0:
				print "    Missing:"
			for i in res["excess"]:
				print "      + " + str(i) + ": "
				ress = res["excess"][i]
				for j in ress:
					print "          - {0}: {1}{2}".format(mu[j][1], ress[j], mu[j][0])


		
