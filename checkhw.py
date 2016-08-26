#!/usr/bin/python
from subprocess import PIPE, Popen
import json
import xml.etree.ElementTree as ET

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
	"ram": ""
}

#ethernet
core = root.find("node")
for n in core.findall("node"):
	nid = n.get("id")
	if nid == "pci":
		for pn in n.findall("node"):
			if pn.get("id") == "network":
				attrs["eth0"] = pn.find("logicalname").text
				attrs["eth0.hwaddr"] = pn.find("businfo").text
	if nid[0:3] == "cpu":
		attrs["cpu"][int(nid[4:])] = {
			"manufacturer": n.find("vendor").text,
			"model": n.find("product").text,
			"speed": str(int(n.find("size").text)/1000000),
			"vendor": n.find("vendor").text
		}
	if nid == "memory":
		attrs["ram"] = str(int(n.find("node").find("size").text)/1048576)

# sorry abou this next bit, its awful I know
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
for cpu in attrs["cpu"]:
	ccpu = {}
	if cpu >= len(thw["cpu"]):
		t = attrs["cpu"][cpu]
		t["correction"] = "excess"
		result["cpu"][cpu] = t
		continue
	for a in attrs["cpu"][cpu]:	
		t = attrs["cpu"][cpu][a]
		v = thw["cpu"][cpu][a]
			
		cobj = {}
		cobj["correct"] = (t==v)
		if t==v: cobj["target"] = t
		cobj["detected"] = v
		ccpu[a] = cobj
	result["cpu"][cpu] = ccpu
for i in range(0,len(thw["cpu"])):
	if i not in attrs["cpu"]:
		t = thw["cpu"][i]
		t["correction"] = "excess"
		result["cpu"][cpu] = t




print json.dumps(result, indent=4)
