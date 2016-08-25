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

ignore = [
	"kernel-firmware",	# -> linux-firmware
	"util-linux-ng",	# -> util-linux
	"iptables-ipv6",	# -> iptables-services
	"cryptsetup-luks",	# -> cryptsetup
	"procps",		# -> procps-ng
	"yum-autoupdate",	# -> yum-cron		???
	"man",			# -> man-db
	"eject" 		# -> util-linux		???
]

hostname = cl("hostname")[0][:-1]
url = "http://aquilon.gridpp.rl.ac.uk/profiles/{0}.json".format(hostname)


rraw = cl("ccm /software/packages --format json")[0]
rjson = "".join(rraw.split('\n')[2:])
c = json.loads(rjson)

fullpkgsrw = cl('rpm -qa --queryformat "%{NAME};%{VERSION};%{RELEASE}\n" | sort -t\; -k 1')[0]
fpkgs = set([])
for fpkgrw in fullpkgsrw.split("\n")[:-1]:
	fpkgn = fpkgrw.split(";")[0]
	fpkgs.add(fpkgn)

targetPkg = c.keys()
tpkg = set()
for pd in targetPkg:
	p = parse(pd)
	tpkg.add(p)
altpkg = set()

missing = set()
excess = set()
updates = {}


for p in tpkg - fpkgs:
	# try whatprovides for containing packages
	ptntlsr = cl("repoquery --whatprovides " + p +" --qf='%{NAME}'")[0].split("\n")[:-1]
	ptntls = set(ptntlsr)
	gdptn = ptntls & fpkgs
	badptn = ptntls - gdptn
	if len(gdptn) == 0:
		missing.add(p)
	else:
		updates[p] = list(gdptn)
		altpkg = gdptn | altpkg

for p in fpkgs - tpkg - altpkg:
	req = cl("rpm --test -e "+p)[1]
	if req == 0:
		excess.add(p)

if(outputtype == 0):
	for m in missing:
		print '\033[91m' + m
	
	for u in updates:
		print '\033[93m' + u + " --> " + ", ".join(updates[u])

	for e in excess:
		print '\033[92m'+e

if(outputtype == 1):
	jobj = {}
	jobj["missing"] = list(missing)
	jobj["updates"] = updates
	jobj["excess"] = list(excess)
	print json.dumps(jobj, indent=4)

print "\033[0m"
