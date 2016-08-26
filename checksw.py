#!/usr/bin/python
from subprocess import Popen, PIPE
import urllib2, json
import argparse
import sys

outputtype = 0
for a in sys.argv:
	if a == "--json":
		outputtype=1
	if a == "-h" or a == "--help":
		print "Usage: {0} [-h] [--json]"
		sys.exit(0)
def cl(c):
	p = Popen(c, shell=True, stdout=PIPE, stderr=PIPE)
	return (p.communicate()[0], p.returncode)

def parse(s):
	st = ""
	i=0
	while i<len(s):
		ch = s[i]
		if ch=="_":
			sq = s[i+1:i+3]
			st = st + chr(int(sq, 16))
			i = i + 2
		else:
			st = st + ch
		i+=1
	return st


hostname = cl("hostname")[0][:-1]
url = "http://aquilon.gridpp.rl.ac.uk/profiles/{0}.json".format(hostname)


rraw = cl("ccm /software/packages --format json")[0]
rjson = "".join(rraw.split('\n')[2:])
c = json.loads(rjson)

fullpkgsrw = cl('rpm -qa --queryformat "%{NAME};%{VERSION};%{RELEASE}\n" | sort -t\; -k 1')[0]
fpkgs = set([])
fpkginfo = {}
for fpkgrw in fullpkgsrw.split("\n")[:-1]:
	fpkgn = fpkgrw.split(";")[0]
	fpkgs.add(fpkgn)
	fpkgv = fpkgrw.split(";")[1] + "-" + fpkgrw.split(";")[2]
	fpkginfo[fpkgn] = fpkgv

targetPkg = c.keys()
tpkg = set()
tpkgin = {}
for pd in targetPkg:
	p = parse(pd)
	tpkg.add(p)
	tpkgin[p] = c[pd]
altpkg = set()

missing = set()
excess = set()
rename = {}
update = {}

for p in tpkg - fpkgs:
	# try whatprovides for containing packages
	ptntlsr = cl("repoquery --whatprovides " + p +" --qf='%{NAME}'")[0].split("\n")[:-1]
	ptntls = set(ptntlsr)
	gdptn = ptntls & fpkgs
	badptn = ptntls - gdptn
	if len(gdptn) == 0:
		missing.add(p)
	else:
		rename[p] = list(gdptn)
		altpkg = gdptn | altpkg

for p in tpkg & fpkgs:
	vers = tpkgin[p]
	if len(vers) > 0: # specified verison provided
		tvers = parse(vers.keys()[0]).split("-")
		tver = tvers[0] + "-" + tvers[1].split('.')[0]
		
		rvers = fpkginfo[p].split("-")
		rver = rvers[0] + "-" + rvers[1].split('.')[0]
		i = 0
		
		acceptable = True
		for n in tver.replace('-','.').split('.'):
			if not (n.isdigit() and rver.replace('-','.').split('.')[i].isdigit()):
				continue
			if int(n) < int(rver.replace('-','.').split('.')[i]):
				acceptable = True
				break
			if int(n) > int(rver.replace('-','.').split('.')[i]):
				acceptable = False
			i += 1
		
		if not acceptable:
			update[p] = {}
			update[p]["required_version"] = tver
			update[p]["current_version"] = rver

for p in fpkgs - tpkg - altpkg:
	req = cl("rpm --test -e "+p)[1]
	if req == 0:
		excess.add(p)

if(outputtype == 0):
	for m in missing:
		print '\033[91m' + m
	
	for r in rename:
		print '\033[93m' + r + " --> " + ", ".join(rename[r])

	for e in excess:
		print '\033[92m'+e

	for u in update:
		print '\033[95m'+ u + ": " + update[u]["current_version"] + " --> " + update[u]["required_version"]
	print "\033[0m"

if(outputtype == 1):
	jobj = {}
	jobj["missing"] = list(missing)
	jobj["rename"] = rename
	jobj["excess"] = list(excess)
	jobj["update"] = update
	print json.dumps(jobj, indent=4)


