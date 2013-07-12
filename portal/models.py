from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import ast
import os
from django.http import HttpResponse
from django.shortcuts import render
import time
from portal.ovirt import Ovirt
from portal.cobbler import Cobbler
from portal.foreman import Foreman
import django.utils.simplejson as json
import time,datetime
from random import choice
import json
from django.contrib.auth.decorators import login_required
import logging
import random
from portal.ilo import Ilo
import socket

#default values
DISKSIZE = '10'
DISKFORMAT = 'raw'
MEMORY = 512
CPUS = 1
NUMINTERFACES = 1
NET1 = 'ovirtmgmt'
SUBNET1 = '255.255.255.0'
DISKINTERFACE = 'virtio'
NETINTERFACE = 'virtio'
PHYSICALPORT = 22
VIRTUALPORT = 443 
COBBLERPORT = 80
FOREMANPORT = 80
FOREMANARCH = 'x86_64'
FOREMANENV = 'production'
FOREMANOS = 'rhel'
FOREMANPUPPET = 'puppet'
LDAPSSLPORT = 636

def checkconn(host,port):
        try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((host, port))
		return True
        except socket.error:
                return False


class IpamProvider(models.Model):
	name                = models.CharField(max_length=20)
	host                = models.CharField(max_length=60)
	port                = models.IntegerField(default=80)
	user                = models.CharField(max_length=60)
	password            = models.CharField(max_length=20)
	type	            = models.CharField(max_length=10, default='nuages')
	def __unicode__(self):
		return self.name

class LdapProvider(models.Model):
	name                = models.CharField(max_length=20)
	host                = models.CharField(max_length=60,blank=True, null=True)
	basedn              = models.CharField(max_length=160,blank=True, null=True)
	binddn              = models.CharField(max_length=160)
	bindpassword        = models.CharField(max_length=20)
	secure      	    = models.BooleanField(default=True)
	userfield	    = models.CharField(max_length=60)
	filter              = models.CharField(max_length=160,blank=True, null=True)
	certname	    = models.CharField(max_length=60,blank=True, null=True)
	def __unicode__(self):
		return self.name
	def clean(self):
		if self.secure:
			if not self.certname:
        			raise ValidationError("Secure mode requires to set a cert name")
			elif not os.path.exists("%s/%s" % (os.environ["PWD"], self.certname) ):
        			raise ValidationError("Secure mode requires to put %s in %s" % (self.certname, os.environ["PWD"]) )


class PhysicalProvider(models.Model):
	name                = models.CharField(max_length=20)
	user                = models.CharField(max_length=60)
	password            = models.CharField(max_length=20)
	type                = models.CharField(max_length=20, default='ilo',choices=( ('ilo', 'ilo'),('drac', 'drac'),('ssh', 'ssh'),('fake', 'fake') ))
	def __unicode__(self):
		return self.name

class VirtualProvider(models.Model):
	name                = models.CharField(max_length=20)
	host                = models.CharField(max_length=60,blank=True, null=True)
	port                = models.IntegerField(default=VIRTUALPORT)
	user                = models.CharField(max_length=60)
	password            = models.CharField(max_length=20)
	type                = models.CharField(max_length=20, default='ovirt',choices=( ('ovirt', 'ovirt'),('vsphere', 'vsphere'),('fake', 'fake') ))
	ssl      	    = models.BooleanField(default=True)
	clu                 = models.CharField(max_length=50,blank=True)
	datacenter          = models.CharField(max_length=50, blank=True)
	active        	    = models.BooleanField(default=True)
	def __unicode__(self):
		return self.name
	def clean(self):
    		if not self.host:
        		raise ValidationError("Host cant be blank")

class ForemanProvider(models.Model):
	name                = models.CharField(max_length=20)
	host                = models.CharField(max_length=60,blank=True, null=True)
	port                = models.IntegerField(default=FOREMANPORT)
	user                = models.CharField(max_length=60, blank=True, null=True)
	password            = models.CharField(max_length=20, blank=True, null=True)
	mac                 = models.CharField(max_length=20, blank=True, null=True)
	osid      	    = models.CharField(max_length=20, default=FOREMANOS,  blank=True, null=True)
	envid               = models.CharField(max_length=20, default=FOREMANENV, blank=True, null=True)
	archid              = models.CharField(max_length=20, default=FOREMANARCH, blank=True, null=True)
	puppetid            = models.CharField(max_length=20, default=FOREMANPUPPET, blank=True, null=True)
	ptableid             = models.CharField(max_length=20, blank=True, null=True)
	def __unicode__(self):
		return self.name
	def clean(self):
    		if not self.host:
        		raise ValidationError("Host cant be blank")

class CobblerProvider(models.Model):
	name                = models.CharField(max_length=20)
	host                = models.CharField(max_length=60,blank=True, null=True)
	user                = models.CharField(max_length=60, blank=True)
	password            = models.CharField(max_length=20, blank=True)
	def __unicode__(self):
		return self.name
	def clean(self):
    		if not self.host:
        		raise ValidationError("Host cant be blank")


class Type(models.Model):
	name       = models.CharField(max_length=20)
	parameters = models.TextField(blank=True)
	def __unicode__(self):
		return self.name

class Storage(models.Model):
	name              = models.CharField(max_length=50)
	type              = models.CharField(max_length=20, default='ovirt',choices=( ('ovirt', 'ovirt'),('vsphere', 'vsphere' )))
	provider	  = models.ForeignKey(VirtualProvider)
	datacenter        = models.CharField(max_length=50,blank=True)
	def __unicode__(self):
		return "%s %s" % (self.provider,self.name)

class Profile(models.Model):
	name              = models.CharField(max_length=40)
	physicalprovider  = models.ForeignKey(PhysicalProvider,blank=True,null=True)
	virtualprovider   = models.ForeignKey(VirtualProvider,blank=True,null=True)
	cobblerprovider   = models.ForeignKey(CobblerProvider,blank=True,null=True)
	foremanprovider   = models.ForeignKey(ForemanProvider,blank=True,null=True)
	ipamprovider      = models.ForeignKey(IpamProvider,blank=True,null=True)
	cobblerprofile    = models.CharField(max_length=40,blank=True)
	datacenter        = models.CharField(max_length=50)
	clu               = models.CharField(max_length=50,blank=True)
	guestid           = models.CharField(max_length=20, choices=( ('rhel_6x64', 'rhel_6x64'),('rhel_5x64', 'rhel_5x64'),('windows_xp', 'windows_xp') ))
	memory            = models.IntegerField(default=MEMORY)
	numcpu            = models.IntegerField(default=CPUS)
	disksize1         = models.IntegerField(default=10)
	diskformat1       = models.CharField(max_length=10, default=DISKFORMAT)
	disksize2         = models.IntegerField(blank=True,null=True)
	diskformat2       = models.CharField(max_length=10, default=DISKFORMAT)
	numinterfaces     = models.IntegerField(default=NUMINTERFACES)
	net1              = models.CharField(max_length=10, default=NET1)
	subnet1           = models.GenericIPAddressField(default=SUBNET1, blank=True, null=True, protocol="IPv4")
	net2              = models.CharField(max_length=10, blank=True)
	subnet2           = models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")
	net3              = models.CharField(max_length=10, blank=True)
	subnet3           = models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")
	net4              = models.CharField(max_length=10, blank=True)
	subnet4           = models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")
	diskinterface     = models.CharField(max_length=20, default=DISKINTERFACE)
	netinterface      = models.CharField(max_length=20, default=NETINTERFACE)
	cmdline           = models.CharField(max_length=100,blank=True)
	dns               = models.CharField(max_length=20,blank=True,null=True)
	autostorage       = models.BooleanField(default=False)
	foreman           = models.BooleanField(default=True)
	cobbler           = models.BooleanField(default=True)
	partitioning      = models.BooleanField(default=False)
	iso               = models.BooleanField(default=False)
	hide              = models.BooleanField(default=True)
	console           = models.BooleanField(default=False)
	requireip         = models.BooleanField(default=False)
	def __unicode__(self):
		return self.name
	def clean(self):
    		if self.numinterfaces >=1 and not self.net1:
        		raise ValidationError("Net1 is required")
    		if self.numinterfaces >=2 and not self.net2:
        		raise ValidationError("net2 is required")
    		if self.numinterfaces >=1 and not self.subnet1:
        		raise ValidationError("Subnet1 is required")
    		if self.numinterfaces >=2 and not self.subnet2:
        		raise ValidationError("Subnet2 is required")
    		if self.foreman and not self.dns:
        		raise ValidationError("Foreman requires a DNS domain to be set")
    		if self.foreman and not self.foremanprovider:
        		raise ValidationError("Foreman requires a ForemanProvider to be set")
    		if self.cobbler and not self.cobblerprovider:
        		raise ValidationError("Cobbler requires a CobblerProvider to be set")
    		if not self.physicalprovider and not self.virtualprovider:
        		raise ValidationError("You need to assign at least one physical or virtual provider")
    		if self.cobbler and self.cobblerprovider:
			cobblerprovider = self.cobblerprovider
			connection=checkconn(cobblerprovider.host,COBBLERPORT)
			if not connection:
        			raise ValidationError("Cobbler server cant be reached...")
			cobblerprofile = self.name
			if self.cobblerprofile:
				cobblerprofile = self.cobblerprofile
			cobbler=Cobbler(cobblerprovider.host, cobblerprovider.user, cobblerprovider.password)
			profilefound = cobbler.checkprofile(cobblerprofile)
			if not profilefound:
        			raise ValidationError("Invalid cobbler profile")
		if self.virtualprovider:
			virtualprovider = self.virtualprovider
			if virtualprovider.type == 'ovirt':
				ovirt=Ovirt(virtualprovider.host,virtualprovider.port,virtualprovider.user,virtualprovider.password,virtualprovider.ssl)
				clusterfound = ovirt.checkcluster(self.clu)
				if not clusterfound:
        				raise ValidationError("Invalid Cluster")
				if self.numinterfaces >= 1:
					net1found = ovirt.checknetwork(self.clu,self.net1)
					if not net1found:
        					raise ValidationError("Invalid net1")
				if self.numinterfaces >= 2:
					net2found = ovirt.checknetwork(self.clu,self.net2)
					if not net2found:
        					raise ValidationError("Invalid net2")
				

class VM(models.Model):
	name              = models.CharField(max_length=20)
	storagedomain     = models.CharField(max_length=60,blank=True,null=True)
	physicalprovider  = models.ForeignKey(PhysicalProvider,blank=True,null=True)
	virtualprovider   = models.ForeignKey(VirtualProvider,blank=True,null=True)
	physical          = models.BooleanField(default=False)
	cobblerprovider   = models.ForeignKey(CobblerProvider, blank=True,null=True)
	foremanprovider   = models.ForeignKey(ForemanProvider,blank=True,null=True)
	profile           = models.ForeignKey(Profile)
	ip1               = models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")
	mac1              = models.CharField(max_length=20, blank=True,null=True)
	ip2               = models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")
	mac2              = models.CharField(max_length=20, blank=True,null=True)
	ip3               = models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")
	mac3              = models.CharField(max_length=20,blank=True,null=True)
	ip4               = models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")
	mac4              = models.CharField(max_length=20, blank=True,null=True)
	ipilo             = models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")
	iso	          = models.CharField(max_length=30, default='',choices=( ('xx', '') , ('yy' , '') ))
	hostgroup	  = models.CharField(max_length=30, default='',choices=( ('xx', '') , ('yy' , '') ))
	type	          = models.ForeignKey(Type,blank=True,null=True)
	puppetclasses     = models.TextField(blank=True)
	puppetparameters  = models.TextField(blank=True)
	cobblerparameters = models.TextField(blank=True)
	createdby	  = models.ForeignKey(User,default=1,blank=True)
	status  	  = models.CharField(max_length=20, default='N/A')
	def __unicode__(self):
		if self.virtualprovider:
			return "%s : %s" % (self.virtualprovider.name,self.name)
		else:
			return "physical:%s" % (self.name)
	def save(self, *args, **kwargs):
		name,storagedomain,physicalprovider,virtualprovider,physical,cobblerprovider,foremanprovider,profile,ip1,mac1,ip2,mac2,ip3,mac3,ip4,mac4,type,puppetclasses,puppetparameters,cobblerparameters,createdby,iso,ipilo,hostgroup = self.name,self.storagedomain,self.physicalprovider,self.virtualprovider,self.physical,self.cobblerprovider,self.foremanprovider,self.profile,self.ip1,self.mac1,self.ip2,self.mac2,self.ip3,self.mac3,self.ip4,self.mac4,self.type,self.puppetclasses,self.puppetparameters,self.cobblerparameters,self.createdby,self.iso,self.ipilo,self.hostgroup
		clu,guestid,memory,numcpu,disksize1,diskformat1,disksize2,diskformat2,diskinterface,numinterfaces,net1,subnet1,net2,subnet2,net3,subnet3,net4,subnet4,netinterface,dns,foreman,cobbler=profile.clu,profile.guestid,profile.memory,profile.numcpu,profile.disksize1,profile.diskformat1,profile.disksize2,profile.diskformat2,profile.diskinterface,profile.numinterfaces,profile.net1,profile.subnet1,profile.net2,profile.subnet2,profile.net3,profile.subnet3,profile.net4,profile.subnet4,profile.netinterface,profile.dns,profile.foreman,profile.cobbler
		if profile.ipamprovider:
			ipamprovider=profile.ipamprovider
			connection=checkconn(ipamprovider.host,ipamprovider.port)
			if not connection:
				return "Connectivity issue with Ipam %s!" % ipamprovider.host
			#TODO: RETRIEVE IPS (AND NAME?)
		if physical:
			provider=physicalprovider
			connection=checkconn(ipilo,22)
		else:
			provider=virtualprovider
			connection=checkconn(virtualprovider.host,virtualprovider.port)
		if not connection:
			return "Connectivity issue with %s!" % provider.host
		if cobbler and cobblerprovider:
			connection = checkconn(cobblerprovider.host, COBBLERPORT)
			if not connection:
				return "Connectivity issue with %s!" % cobblerprovider.host
                        cobblerhost, cobbleruser, cobblerpassword = cobblerprovider.host, cobblerprovider.user, cobblerprovider.password
                        cobbler=Cobbler(cobblerhost, cobbleruser, cobblerpassword)
			cobblerfound = cobbler.exists(name)
			if cobblerfound:
				return "Machine %s allready exists within cobbler!" % name
		if foreman and foremanprovider:
			connection = checkconn(foremanprovider.host, foremanprovider.port)
			if not connection:
				return "Connectivity issue with %s!" % foremanprovider.host
                        foremanhost, foremanuser, foremanpassword = foremanprovider.host, foremanprovider.user, foremanprovider.password
                        foreman=Foreman(host=foremanhost, user=foremanuser, password=foremanpassword)
			foremanfound = foreman.exists("%s.%s" %  (name,dns) )
			if foremanfound:
				return "Machine %s.%s allready exists within foreman!" % (name,dns)
		
		cmdline="user=%s" % (createdby.username)
		if profile.cmdline:
                        cmdline="%s %s" % (profile.cmdline,cmdline)
                if physical :
                                cmdline="%s blacklist=lpfc blacklist=qla2xxx blacklist=qla4xxx" % (cmdline)
		if physical and profile.console:
				cmdline="%s console=ttyS0" % (cmdline)
		#storagedomains = profile.storages
                #if len(storagedomains.values_list('name', flat=True)) > 1:
                #        storagedomains=profile.storages
                #        storagedomain=choice(storagedomains.values_list('name', flat=True))
                #else:
                #        storagedomain=storagedomains.values_list('name', flat=True)[0]
                #VM CREATION
                if not physical and virtualprovider.type == 'ovirt':
                        ovirt=Ovirt(virtualprovider.host,virtualprovider.port,virtualprovider.user,virtualprovider.password,virtualprovider.ssl)
                        ovirt.create(name=name, clu=clu, numcpu=numcpu, numinterfaces=numinterfaces, netinterface=netinterface, disksize1=disksize1,diskformat1=diskformat1, disksize2=disksize2,diskformat2=diskformat2, diskinterface=diskinterface, memory=memory, storagedomain=storagedomain, guestid=guestid, net1=net1, net2=net2, net3=net3, net4=net4, mac1=mac1, mac2=mac2, iso=iso)
                        ovirt.close()
                if not physical and virtualprovider.type == 'vsphere':
                        pwd = os.environ["PWD"]
                        #get best datastore
                        storagecommand = "/usr/bin/jython %s/portal/vsphere.py %s %s %s %s %s %s" % (pwd,'getstorage', virtualprovider.host, virtualprovider.user, virtualprovider.password , virtualprovider.datacenter, virtualprovider.clu )
                        storageinfo = os.popen(storagecommand).read()
                        storageinfo= ast.literal_eval(storageinfo)
                        size=0
                        for stor in storageinfo:
                                if storageinfo[stor][1] > size:
                                        ds=stor
                                        size=storageinfo[stor][1]
                        jythoncommand = "/usr/bin/jython %s/portal/vsphere.py %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s" % (pwd,'create', virtualprovider.host, virtualprovider.user, virtualprovider.password , virtualprovider.datacenter, virtualprovider.clu ,name,numcpu, numinterfaces, diskformat1,disksize1,ds,memory,guestid,net1,net2,net3,net4)
                        macaddr = os.popen(jythoncommand).read()
                        vspheremacaddr= ast.literal_eval(macaddr)
                if cobbler and cobblerprovider:
                        if not physical and virtualprovider.type == 'ovirt':
                                macaddr=ovirt.macaddr
                        if not physical and virtualprovider.type == 'vsphere':
                                macaddr=vspheremacaddr
                        if physical:
                                macaddr=[mac1]
				if mac2:
                                	macaddr=[mac1,mac2]
                        cobblerprofile=profile.name
                        if profile.cobblerprofile:
                                cobblerprofile=profile.cobblerprofile
                        cobblerhost, cobbleruser, cobblerpassword = cobblerprovider.host, cobblerprovider.user, cobblerprovider.password
                        cobbler=Cobbler(cobblerhost, cobbleruser, cobblerpassword)
                        if ip1:
                                cobbler.create(name=name,profile=cobblerprofile,numinterfaces=numinterfaces,dns=dns, ip1=ip1, subnet1=subnet1, ip2=ip2, subnet2=subnet2, ip3=ip3, subnet3=subnet3, ip4=ip4, subnet4=subnet4, macaddr=macaddr, parameters=cobblerparameters,cmdline=cmdline)
                        else:
                                cobbler.simplecreate(name=name,profile=cobblerprofile,dns=dns, macaddr=macaddr, parameters=cobblerparameters,cmdline=cmdline)

                if foreman and foremanprovider:
                        foremanhost, foremanport, foremanuser, foremanpassword, foremanos, foremanenv, foremanarch, foremanpuppet, foremanptable = foremanprovider.host, foremanprovider.port, foremanprovider.user, foremanprovider.password, foremanprovider.osid, foremanprovider.envid, foremanprovider.archid, foremanprovider.puppetid, foremanprovider.ptableid
                        Foreman(host=foremanhost, user=foremanuser, password=foremanpassword, name=name,dns=dns,ip=ip1,hostgroup=hostgroup)
		super(VM, self).save(*args, **kwargs)
                if physical:
                        ilo=Ilo(ipilo,physicalprovider.user,physicalprovider.password)
                        ilo.pxe()
                        ilo.reset()
                if not physical and virtualprovider.type == 'ovirt':
                        ovirt=Ovirt(virtualprovider.host,virtualprovider.port,virtualprovider.user,virtualprovider.password,virtualprovider.ssl)
                        ovirt.start(name)
                        ovirt.close()
                if not physical and virtualprovider.type == 'vsphere':
                        startcommand = "/usr/bin/jython %s/portal/vsphere.py %s %s %s %s %s %s %s" % (pwd,'start', virtualprovider.host, virtualprovider.user, virtualprovider.password , virtualprovider.datacenter, virtualprovider.clu ,name )
                        os.popen(startcommand).read()
		return 'OK'

class Default(models.Model):
	name              = models.CharField(max_length=20)
	virtualprovider   = models.ForeignKey(VirtualProvider)
	cobblerprovider   = models.ForeignKey(CobblerProvider)
	foremanprovider   = models.ForeignKey(ForemanProvider)
	consoleip         = models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")
	def __unicode__(self):
		return self.name
	def clean(self):
    		model = self.__class__
    		if (model.objects.count() > 0 and self.id != model.objects.get().id):
        		raise ValidationError("Can only create 1 %s instance" % model.__name__)

#SPECIFIC 

class Apache(models.Model):
	webenvironment   = models.CharField(max_length=20, default='intranet', choices=( ('intranet', 'intranet'),('internet', 'internet') ) )

#Size of /apli (MB)
#SGA size total instances (MB)
class Oracle(models.Model):
	sga         	  = models.CharField(max_length=20, default=1024)
	apli_size         = models.CharField(max_length=20,default=20480)

class Rac(models.Model):
	racvip            = models.GenericIPAddressField(protocol="IPv4")
	racversion        = models.CharField(max_length=4)
	racnodes          = models.IntegerField()
	racasm            = models.CharField(max_length=2,default='NO')


class Sap(models.Model):
	sapsid          = models.IntegerField()
	saptier         = models.CharField(max_length=3)


class Weblogic(models.Model):
	wlversion          = models.CharField(max_length=5,default=1036)
	wlsizeapli         = models.CharField(max_length=5,default=5120)
	wlsizeapp          = models.CharField(max_length=5,default=2048)
	wlsizelog          = models.CharField(max_length=5,default=2048)

class Partitioning(models.Model):
	rootvg         = models.CharField(max_length=15,default='rootvg')
	rootsize       = models.CharField(max_length=7,default=10000)
	varsize        = models.CharField(max_length=7,default=4096)
	homesize       = models.CharField(max_length=7,default=6144)
	tmpsize        = models.CharField(max_length=7,default=2048)
	swapsize       = models.CharField(max_length=7,default=2048)