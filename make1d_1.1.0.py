#!/usr/bin/python
import sys
import os
import ConfigParser
import re

from UserString import MutableString

"""
ChangeLog:

1.1.0: checks config file for defects before processing it

1.0.9.1: debug attribute in config files is now optional

1.0.9: 	added RemoveNulls method to sterilize input from null characters
		fixed issue with multiple-runs-per-file feature with extracting the zero time

1.0.8: 	hack to handle runs that are all in the same file 

"""


def RemoveNulls(str):
	outstr= MutableString()
	for char in str:
		if ord(char) != 0:
			outstr+=char
	return outstr.data

#parser class and related functions##
#this parses an iterable item (file,list,string) based on a series of delimeters.
#these delimeters can be a tuple, character, or string
#everything between the delimeters is defined as 'relevant', whereas everything
#outside the delimeters is defined as 'irrelevant'
class parser():
	def __init__(self, parsee="", arm_tup="", dearm_tup="",debug = False):
		self.arm_tup = tup_check_(arm_tup)
		self.dearm_tup = tup_check_(dearm_tup)
		#print type(arm_tup), dearm_tup
		
		self.full_list = self.parse_(parsee,self.arm_tup,self.dearm_tup,debug)
	#returns a list of all items
	def full(self, concat = False):
		ret_list = []
		for i in self.full_list:
			if concat == True: ret_list.append(concat_(i))
			else: ret_list.append(i)
				
		return ret_list
	#returns a list of relevant items
	def relevant(self, concat = False):
		ret_list = []
		for i in range(len(self.full_list)):
			#print i
			if self.full_list[i]==''.join(self.arm_tup) or self.full_list[i]==''.join(self.dearm_tup) : pass
			try:
				if self.full_list[i-1]==''.join(self.arm_tup) and self.full_list[i+1]==''.join(self.dearm_tup):
					if concat == True: ret_list.append(concat_(self.full_list[i]))
					else: ret_list.append(self.full_list[i])
			except(IndexError):pass
		return ret_list
	
	def not_relevant(self, concat = False):
		ret_list = []
		for i in range(len(self.full_list)):
			if self.full_list[i]==''.join(self.arm_tup) or self.full_list[i]==''.join(self.dearm_tup) : pass
			try:
				if self.full_list[i-1]!=''.join(self.arm_tup) or self.full_list[i+1]!=''.join(self.dearm_tup):
					if concat == True: ret_list.append(concat_(self.full_list[i]))
					else: ret_list.append(self.full_list[i])
			except(IndexError):pass
		
		return ret_list
	
	def parse_(self,parsee, arm_tup, dearm_tup, debug=False):
		i_count = 					0
		arm_count=					0
		dearm_count=				0
		full_list=					[]
		curr_info = 				[]
		armed = False
		dearmed = False

		#print arm_tup,dearm_tup
		
		for i in parsee:
			i = RemoveNulls(i)
			i = i.strip()
			i_count += 1
			if debug == True: 
				print i
				#print i,re.match(i,"(\t)*%s"%arm_tup[arm_count])
				#print i.find('\t')
				#for char in i: print ord(char)
					
			if i == arm_tup[arm_count]:
				if debug == True: print "ARM_TUP",arm_count
				arm_count+=1
				armed = True
			elif i == dearm_tup[dearm_count]:
				if debug == True: print "DEARM_TUP",dearm_count
				dearm_count += 1
				dearmed = True
			else:
				arm_count = 0
				dearm_count = 0
			
			if i == arm_tup[-1] and armed == True:
				if debug == True: print "LOG RELV"
				full_list.append(curr_info)
				full_list.append(''.join(arm_tup))
				curr_info = []
				armed = False	
				arm_count = 0
				continue
			if i == dearm_tup[-1] and dearmed == True:
				if debug == True: print "LOG NRELV"
				full_list.append(curr_info)
				full_list.append(''.join(dearm_tup))
				curr_info = []
				dearmed = False
				dearm_count = 0
				continue

			curr_info.append(i)
			
		if len(curr_info) != 0: full_list.append(curr_info)
		return full_list
	
	def is_relevant_(self,string):
		try:
			if self.full_list[self.full_list.index(string)-1]==''.join(self.arm_tup) \
					and self.full_list[self.full_list.index(string)+1]==''.join(self.dearm_tup):
				return True
		except(IndexError):pass

		return False

#concatenates a list of strings into a single string
def concat_(alist):
	i = alist[::]
	return ''.join(i)
#


def tup_check_(delim):
	if type(delim) == str:
		delim = (delim,)
	elif type(delim) == list:
		delim = tuple(delim)
	elif type(delim) != tuple:
		raise TypeError
	return delim

#metainfo class. This is in charge of extracting information about the run from
	#the filename passed to it.
#in the configuration file, we define rules like:
	# dm2_run<run>-<subject>-<session>.txt
# so when we pass dm2_run1-2-1.txt, the metainfo object finds run: 1, subject: 2, and session: 1
# this uses the parser class to figure out stuff from the rules, and demonstrates its utility:
# the parser will find everything between the < >, and define that as 'relevant' (the tags we want), versus
# everything else, which is just extraneous information we are not using.

# we use one metainfo object per 'source rule', that is, it can only generate metainfo from one file pattern,
# we can then use it to generate file names (of our 1Ds) based on the rules for the 1D, and the metainfo gleaned
# from the source file

# it also will do some checking about the file, but it only measures the length of the filename, and
# nothing else, so it is kind of naive
# this presents a potential problem when dealing with, say, subjects 10 and over, because of the extra character
# in the filename, but there is a hack that will deal with 2-digit items (shown below)
class metainfo():
	def __init__(self, source_rules="", filename="", arm_delim="<", dearm_delim=">"):
		self.arm_delim = arm_delim
		self.dearm_delim = dearm_delim
		self.parsed_ = parser(source_rules,self.arm_delim,self.dearm_delim) #just the object, not a list
		self.sourcetags = self.taglist_(self.parsed_) #dictionary mapping each tag to its value
		self.metatags = self.build_metainfo_(filename) #need to define self.sourcetags first before calling this
	
	def metainfotags(self):
		return self.metatags
	
	def get_tag(self,key):
		return self.metatags[key]
	
	def set_tag(self,key,value):
		self.metatags[key] = value
	
	def is_tag(self,astring):
		return (astring[0] == self.arm_delim) & (astring[-1] == self.dearm_delim)
	
	def get_tagname_(self,atag):
		if self.is_tag(atag):
			return atag[1:-1]
		else:
			print 'Not a tag:',atag
			raise TypeError
	
	# taglist_ iterates through the "full" list from the parser object
	# and generates a list that has the 'tags' as one object
	# example:
	# for rules 	
	# dm2_run<run>-<subject>-<session>.txt
	# parser_object.full() returns [[d,m,2,_,r,u,n],<,[r,u,n],>,[-],<,[s,u,b,j,e,c,t],>, [-], <, [s,e,s,s,i,o,n],>, [.,t,x,t]]
	# and parser_object.relevant(concat=True) returns ['run','subject','session']
	# so taglist_ returns [d,m,2,run,-,subject,-,session,.,t,x,t],
	# which is the same length as the filename.
	def taglist_(self, parser_object):
		#print string
		ret_list = []
	#	s = parser(string,self.arm_delim,self.dearm_delim)
		#print s.not_relevant()
		#print parser_object.full()
		for i in parser_object.full():
			#print self.parsed_.full_list[i]
			
			if parser_object.is_relevant_(i):
				ret_list.append(self.arm_delim \
						+ ''.join(i) \
							+ self.dearm_delim)
			elif i == self.arm_delim \
				or i == self.dearm_delim: pass
			else:
				#ret_list.append(i)
				for x in i:
					ret_list.append(x)
				
		return ret_list

	#so if taglist_ returns [d,m,2,run,-,subject,-,session,.,t,x,t], then build_metainfo iterates through the filename. (say, dm2_run1-1-1.txt)
	#when the iteration finds mismatching items, it knows that is where a tag value is located, and appends to the dictionary accordingly.
	def build_metainfo_(self,filename=""):
#		if len(self.sourcetags) != len(filename):
#			print "possible bad filename %s: should be of length %i"%(filename, len(self.sourcetags))
#			print self.sourcetags
#			#raise TypeError

		tag_dic = {}


		i = 0
		for a in self.sourcetags:
			if self.is_tag(a):
				delim = self.sourcetags.index(a)+1

				try:
					if filename[i] != self.sourcetags[delim]: 
						oldi = i
						while filename[i] != self.sourcetags[delim]:
							i+=1

				except IndexError:
					print 'error while trying to extract metadata:'
					print 'with rules:',self.sourcetags
					print 'against:',filename
					raise IndexError

				#print filename[oldi:i:] 
				tag_dic[self.get_tagname_(a)] = filename[oldi:i:]

		#print tag_dic
		return tag_dic
	
	#builds a filename according to 'rules' and basically works the opposite way as taglist_
	#it iterates through the dest_rules, and inserts the info for each tag at the proper place.
	def build_filename(self, dest_rules):
		parsed_dest = parser(dest_rules,self.arm_delim,self.dearm_delim)
		drl = self.taglist_(parsed_dest)

		ret_list = []
		#print self.metatags
		for st in drl:
			#print st
			
			if self.is_tag(st):
				stname = self.get_tagname_(st)
				if stname in self.metatags:
					ret_list.append(self.metatags[stname])
				else:
					print ret_list
					print dest_rules
					raise IndexError
			else:
				ret_list.append(st)
		
		try: return ''.join(ret_list)
		except TypeError: 
			print "TypeError: ",ret_list
			return ""

# helper funcs for regex_condition
def with_index(seq):
    for i in xrange(len(seq)):
        yield i, seq[i]

def replace_all(seq, obj, replacement):
    for i, elem in with_index(seq):
        if elem == obj:
            seq[i] = replacement

# HACK: replaces element in sequence if previous element and next element match up also
def replace_all_conditions(seq, obj, replacement, prev, next):
    for i, elem in with_index(seq):
		#print len(seq)
		if (i == 0) | (i == len(seq)-1): 
			continue
		#	print i,seq[i]
		elif (elem == obj) & (seq[i-1]== prev) & (seq[i+1] == next):
			seq[i] = replacement
#regex_condition class. handles matching of an item within a dictionary (a trial, in our case)
#uses the parser class to parse the pseudo-regex rules defined in the [1D] section
# so the rules (type=uu|fu)(offer2.RESP=1) are parsed into two conditions type=uu|fu and offer2.RESP=1, 
# both of which must be met for match() to ring true.

# the stuff after the equals sign (uu|fu) is a true regular expression, using the re module
class regex_condition():
	def __init__(self,regex_string):
		self.c_dic = {}
		self.c_pos = {}
		self.conditions = []
		#print regex_string
		if regex_string.count("(") != regex_string.count(")") \
		or regex_string.count("=") > regex_string.count("(")+1 \
		or regex_string.count("=") > regex_string.count(")")+1:
			print "improper regex string in config:"
			print "\t",regex_string
			raise TypeError
		if regex_string.count("(") >= 1:
			re_parser = parser(regex_string,'(',')')
			self.conditions = re_parser.full(concat=True)[1::]
# replace some of the blanks with & symbols, for backwards rc file compatibility
			replace_all_conditions(self.conditions,'','&',')','(')

			index = 0
			for condition in self.conditions:
				if condition.count('=') == 1:
					att,val = condition.split('=',1)
					self.c_dic[att] = val
					self.c_pos[att] = index
				index += 1


#			print re_parser.relevant(concat=True)
#			print re_parser.not_relevant(concat=True)
#			print re_parser.full(concat=True)[1::]
#			
#			print "".join(re_parser.full(concat=True))

		else:
			#print regex_string+" does not contain ()"
			try:
				att,val = regex_string.split('=',1)
				self.conditions = [regex_string]
				self.c_dic[att] = val
				self.c_pos[att] = 0
				self.c_pos
			except:
				print self.conditions
				print regex_string
				raise ValueError
#		print self.conditions
		
#		print self.c_dic;

	def match(self,dictionary):
		conds = self.conditions[::]
		i = 0
		for condition in conds:

			
			if self.valid_condition(condition):

				att,val = condition.split('=')

				if att in dictionary:
					try:
						if re.match(val,dictionary[att])== None:
							conds[i] = '0'
						else:
							conds[i] = '1'
					except TypeError:
						return False
				else:
					conds[i] = '0'
		
			i+=1
#		print dictionary
#		print ''.join(conds)
#		print self.conditions
#		print ''.join(conds)
#		print  bool(eval(''.join(conds))) 
#		print
		return bool(eval(''.join(conds)))

	def valid_condition(self,astring):
		return astring.count('=') == 1


def add_to_dic(dic,key,value):
	#key.strip()
	#value.strip()
	if key in dic:
		dic[key].append(value)
	else:
		dic[key] = []
		dic[key].append(value)

#obsolete after I made the regex_condition class
def re_match_bool(regex_str,string):
	if re.match(regex_str,string) == None: return False
	else: return True

def match_in_dict(adict,key,regex_str):
	if re.match(regex_str,adict[key]) == None: return False
	else: return True

#gives a couple more options when dealing with ConfigParser objects
#ConfigParser normally creates a dictionary mapping each parameter with its value,
#but only allows one value per parameter.
#This will split each value according to a split delimeter (comma in our case), and returns a list
#of values for each parameter
def make_dic_from_config(ConfigParser_object, section, split_delim = ""):
	out_dic = {}
	for i in ConfigParser_object.options(section):
		if split_delim == "":
			out_dic[i] = ConfigParser_object.get(section,i)
		else:
			out_dic[i] = tuple(ConfigParser_object.get(section,i).split(split_delim))
	return out_dic

#creates the trial dictionary
def make_dic_from_list(alist,main_split,tuple_split=""):
	out_dic = {}
	for i in alist:
		try: key, val = i.split(main_split,1)
		except ValueError:
			key = i
			val = "none here"
#			print i
		key = key.strip()
		val = val.strip()
		if val == '': val = 0 #for nonresponse
		if tuple_split == "":
			out_dic[key] = val
		else:
			out_dic[key] = tuple(val.split(tuple_split))
	return out_dic

#writes a list to a file
def write_list(out_file, alist):
	appendstr = ' '
	if len(alist) <= 1:
		appendstr = ' *'
	if len(alist) == 0:
		out_file.write('*')
	else:
		for item in alist:
			out_file.write(str(item))
			out_file.write(appendstr)
	out_file.write('\n')

def reset_lists(adict):
	for item in adict:
		adict[item] = []

#for debugging
def print_dic(adict):
	for item in adict:
		print item,":",adict[item]


	
debug = 0 
def debug(level, astring):
	if level <= debug: 
		print astring

def checkRawConfig(cfile):
	dupcheck = []
	onedees = False
	quit = False
	count = 0
	for line in cfile:
		count += 1
		if line.strip() == "[1D]":
			onedees = True
		if line[0].strip() in ["#","\n","\r\n","","\t"," "]: 
			continue
		else:
			a = line.split('=',1)
			if a[0] in dupcheck:
				quit = True
				print "Config error on line %i: duplicate rule: %s "%(count,a[0])#\"%s: %s\""%(count,a[0],a[1])
			else:
				dupcheck.append(a[0])

			if onedees == True and len(a) == 2  and len(a[1].split(',')) != 3:
				quit = True
				print "Config error on line %i: malformed rule: %s "%(count,a[0])#\"%s: %s\""%(count, a[0],a[1])
	
	if quit == True: sys.exit(1)


	
#*************Script starts here***************

#initializations
import glob
from optparse import OptionParser



#dictionarys we are using for sorting
#ALL HAVE THE SAME KEYS
#d_opts: exactly what is defined in [1D]
#d_lists: contains filenames as keys, list of values we want to write as objects
#d_files: contains filenames as keys, file objects as values
if len(sys.argv)==1:
	print 'Usage: (python) %s <config file> <run-1.txt> <run-2.txt>...' %(sys.argv[0])
	sys.exit()
#parser = OptionParser()
#parser.add_option("-c", "--config", action="store",help="use configuation file", metavar="FILE")

#(options,args) = parser.parse_args()

conf_file = sys.argv[1]
input_list	= sys.argv[2::]
input_list.sort()

if len(input_list) == 1: input_list = glob.glob(input_list[0]) #so we can pass wildcards

c = ConfigParser.ConfigParser()
c.read(os.path.abspath(conf_file))

if c.has_option('ATTR','debug'):
	debug = c.get('ATTR','debug')
else: 
	debug = 0

lv = 'Level: ' + c.get('ATTR','trial_level')
st = c.get('ATTR','trial_start_delim')
et = c.get('ATTR','trial_end_delim')

#os_dir = c.get('ATTR','out_directory')

time_zero_attribute = c.get('ATTR','time_zero')
subtract = float(c.get('ATTR','subtract'))
convert_seconds = False
one_run_per_file = False

eprime_file_rules = c.get('ATTR','in_filename')
d_file_rules = c.get('ATTR','out_filename')
os_dir_rules = c.get('ATTR','out_directory')


if(c.get('ATTR','convert_seconds') == "yes"):
	convert_seconds = True
	#print "converting times to seconds"

if(c.get('ATTR','one_run_per_file') == "yes"):
	one_run_per_file = True

num_trials_per_run = int(c.get('ATTR','num_trials_in_run'))


d_opts = make_dic_from_config(c,'1D',',')
d_files = {}
d_lists = {}
d_match = {}
d_rec = {}
d_att = {}
d_sec = {}


checkRawConfig(open(conf_file,"r"))


meto = metainfo(eprime_file_rules,os.path.basename(input_list[0])) 	#creates metainfo for the subject from the first run. this only works because we are running this script for ONLY one subject at a time

#print d_opts

for i in d_opts: #initializes stuff that stays constant for the subject
	#print i	
	meto.set_tag('dname', i)#required to build filename
	#print meto.metainfotags()
	out_filename = meto.build_filename(d_file_rules)
	out_dir = meto.build_filename(os_dir_rules)
	#print out_filename, os.path.abspath(out_filename)
	d_lists[i] = []
	d_files[i] = open(os.path.abspath(out_filename),'w')




	
#meat of the script
#1.opens each file, getting the metainfo based on the filename
#2.parses the file to find the trials, using the parser class
#3.converts each trial to a dictionary
#4.iterates through each 1D to perform the necessary sorting procedures:
#	if the 1D's match object is true for the trial, it records the value defined in d_opts[1D][0] and appends it
#	to the corresponding list in d_lists
#5.at the end of the file (which we are assuming for the time being to be the end of the run), it clears the lists from d_lists
#	and writes them to the corresponding 1D files



if one_run_per_file:
	for fn in input_list:
#	print filename
		filename = os.path.basename(fn)	
		dirname = os.path.dirname(os.path.abspath(fn))
		curr_file = open(os.path.abspath(fn),'r')
		time_zero = 0

		parsed_file = parser(curr_file,(lv,st),et) #creates parsed object from file
		#print len(parsed_file.not_relevant())
		#print parsed_file.not_relevant()
		for nontrial in parsed_file.not_relevant():
			#stuff to do with non trials, like extracting miscellaneous info
			#so far, the value representing "time-zero" has always been here, so I'm putting it here
			non_dic = make_dic_from_list(nontrial,":")
			
			if time_zero_attribute.isdigit():
				time_zero = float(time_zero_attribute) + subtract
			else: 
				#print non_dic[time_zero_attribute]
				try: time_zero = float(non_dic[time_zero_attribute]) + subtract
				except KeyError:
					#print time_zero_attribute
					#print_dic(non_dic)
					pass
		
		print filename, "time zero:",time_zero
		
		#print d_opts
		trial_count = 0
		for trial in parsed_file.relevant():	#iterate through each trial in the run or file
			trial_count += 1
			trial_dic = make_dic_from_list(trial,":")
			
			for oneD in d_opts:
				cond = regex_condition(d_opts[oneD][1])
				if cond.match(trial_dic):
					try: 
						rec_value = trial_dic[d_opts[oneD][0]]
						if d_opts[oneD][2] in ('TimeNoOnset','NoOnset','NotOnsetTime','time-no-onset'):
							rec_value = (float(rec_value))
							#if convert_seconds == True:
								#rec_value /= 1000.0
								#print "converting %s to seconds" %(rec_value)
						elif d_opts[oneD][2] in ('OnsetTime','onsettime','onset','Onsettime','onsetTime','time'):
							rec_value = (float(rec_value)-time_zero)
							if convert_seconds == True:
								rec_value /= 1000.0
								#print "converting %s to seconds" %(rec_value)  
					except KeyError:
						print d_opts[oneD][0],'not in trial',trial_count
					except IndexError:
						pass
					#print trial_dic[d_opts[oneD][0]]
					d_lists[oneD].append(rec_value)


		for i in d_lists:
			try:
				write_list(d_files[i],d_lists[i])
			except IOError:
				print d_lists[i]
				print d_files[i]
		reset_lists(d_lists)
		
		curr_file.close()

	for i in d_files:
		d_files[i].close()


else:
	assert len(input_list) == 1
	fn = input_list[0]
	filename = os.path.basename(fn)	
	dirname = os.path.dirname(os.path.abspath(fn))
	curr_file = open(os.path.abspath(fn),'r')
	time_zero = 0

	parsed_file = parser(curr_file,(lv,st),et) #creates parsed object from file
	#print len(parsed_file.not_relevant())
	#print parsed_file.not_relevant()
	for nontrial in parsed_file.not_relevant():
		#stuff to do with non trials, like extracting miscellaneous info
		#so far, the value representing "time-zero" has always been here, so I'm putting it here
		non_dic = make_dic_from_list(nontrial,":")
		
		if time_zero_attribute.isdigit():
			time_zero = float(time_zero_attribute) + subtract
		else: 
			#print non_dic[time_zero_attribute]
			try: time_zero = float(non_dic[time_zero_attribute]) + subtract
			except KeyError:
				#print time_zero_attribute
				#print_dic(non_dic)
				pass
	
	
	#print d_opts
	trial_count = 1
	run_count = 1
	total_count = 1
	for trial in parsed_file.relevant():	#iterate through each trial in the run or file

		trial_dic = make_dic_from_list(trial,":")

		if trial_count == num_trials_per_run:
			trial_count = 1
			run_count+=1
			for i in d_lists:
				try:
					write_list(d_files[i],d_lists[i])
				except IOError:
					print d_lists[i]
					print d_files[i]
			reset_lists(d_lists)
	
			continue

			
		if trial_count == 1:
			time_zero =  float(trial_dic[time_zero_attribute])
			print filename, "run: %i"%(run_count), "time zero:",time_zero


	   # debug(1, "hello") #"run: %d -- trial: %d -- total: %d"%(run_count,trial_count,total_count))

		trial_count += 1
		total_count += 1

		
		for oneD in d_opts:
			cond = regex_condition(d_opts[oneD][1])
			if cond.match(trial_dic):
				try: 
					rec_value = trial_dic[d_opts[oneD][0]]
					if d_opts[oneD][2] in ('TimeNoOnset','NoOnset','NotOnsetTime','time-no-onset'):
						rec_value = (float(rec_value))
						#if convert_seconds == True:
							#rec_value /= 1000.0
							#print "converting %s to seconds" %(rec_value)
					elif d_opts[oneD][2] in ('OnsetTime','onsettime','onset','Onsettime','onsetTime','time'):
						rec_value = (float(rec_value)-time_zero)
						if convert_seconds == True:
							rec_value /= 1000.0
							#print "converting %s to seconds" %(rec_value)  
				except KeyError:
					print d_opts[oneD][0],'not in trial',trial_count
				#except IndexError:
				#	pass
				#print trial_dic[d_opts[oneD][0]]
				d_lists[oneD].append(rec_value)

	
	for i in d_files:
		d_files[i].close()

