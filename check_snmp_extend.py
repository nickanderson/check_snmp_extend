#!/usr/bin/python
#-*- coding: utf-8 -*-

# Original Author: tntteam@free.fr

# As of version .2 Nick Anderson cloned the script and
# maintains a git repository. Patches Welcome!
# https://github.com/nickanderson/check_snmp_extend

###################################################
#
# IMPORT
#
###################################################

from sys import exit
from sys import argv
import commands, signal



###################################################
#
# Initial values
#
###################################################

version="0.1"
overall_status = -1

ok=0
unknown=1
warning=2
critical=3

state = {
	ok			: "OK",
	unknown		: "UNKNOWN",
	warning		: "WARNING",
	critical	: "CRITICAL"
}

state_nagios = {
	"OK"		:	0,
	"WARNING"	:	1,
	"CRITICAL"	:	2,
	"UNKNOWN"	:	3
}
state_nagios_text = {
	0	: "OK",
	1	: "WARNING",
	2	: "CRITICAL",
	3	: "UNKNOWN"
}

exit_codes = {
	0	:	state_nagios["OK"],
	1	:	state_nagios["UNKNOWN"],
	2	:	state_nagios["WARNING"],
	3	:	state_nagios["CRITICAL"]
}

config = {
	"debug"						:	False,
	"host"						:	"",
	"timeout"					:	10,
	"extend_name"				:	"ALL",
	"snmp_version"				:	"1",
	"community"					:	"",
	"output_longoutput"			:	False,
	"output_perfdata"			:	False,
	"output_complete_summary"	:	False
}


summary=""
long_output=""
perfdata=""
ok_count=0
not_ok_count=0


###################################################
#
# Timeout()
#       Timeout a function (src : http://programming-guides.com/python/timeout-a-function)
###################################################
class TimeoutException(Exception):
    pass

def timeout():
	def timeout_function(f):
		def f2(*args):
			def timeout_handler(signum, frame):
				raise TimeoutException()

			old_handler = signal.signal(signal.SIGALRM, timeout_handler)
			signal.alarm(config['timeout']) # triger alarm in timeout_time seconds
			try:
				retval = f()
			except TimeoutException:
				error("TIMEOUT")
			finally:
				signal.signal(signal.SIGALRM, old_handler)
				signal.alarm(0)
			return retval
		return f2
	return timeout_function

	
def clean_line_result(text):
	ret = ['', '']
	
	text2=text.split('=',1)
	#plugin name :
	ret[0]=text2[0].split('.',1)[1].replace('"','').strip()
	#return code removing the ending \n:
	ret[1]=int(text2[1].rstrip('\n'))
	return ret
	
def clean_line_output(text):
	ret = ['', '', '', '']
	
	text2=text.split('=',1)
	#plugin name :
	ret[0]=text2[0].split('.',1)[1].replace('"','').strip()
	#return (code, text, etc.) removing the ending \n
	text3=text2[1].rstrip('\n')
	#return summary
	ret[1]=text3.split('|',1)[0].split('\n')[0].strip()
	#return perfdata
	try:
		ret[2]=text3.split('|',1)[1].split('\n')[0].strip()
		try: #more perfdata (nagios syntax guide says it's correct -_-)
			ret[2]="%s %s" % (ret[2], text3.split('|',2)[2].strip())
		except IndexError:
			pass
	except IndexError:
			pass
	#return long output
	try: #split on | left side because we can have perfdata after long output
		ret[3]=text3.split('\n')[1].split('|')[0].strip()
	except IndexError:
		pass

	return ret

###################################################
#				
# check_snmp_extend()
#	check all SNMP exec
###################################################
def check_snmp_extend():
	global overall_status, ok_count, not_ok_count
	
	output_table={}
	
	timeoutstr="Timeout: No Response from " + config['host']
	noexecstr="::nsExtendResult = No Such Instance currently exists at this OID"
	
	snmp_request="snmpwalk -v%s -c %s -OQ %s 'NET-SNMP-EXTEND-MIB::nsExtendResult'" % (config['snmp_version'], config['community'], config['host'])
	results=commands.getoutput(snmp_request).split("NET-SNMP-EXTEND-MIB")
	if config['debug']:
		debug("snmp request: %s" % (snmp_request))
		debug(results)
	
	if results[0] == timeoutstr:
		error("No response from: %s. Maybe community is not good ?" % (config['host']) )
	if results[1] == noexecstr:
		error("No exec/extend snmp found for this server: %s." % (config['host']) )
	
	snmp_request="snmpwalk -v%s -c %s -OQ %s 'NET-SNMP-EXTEND-MIB::nsExtendOutputFull'" % (config['snmp_version'], config['community'], config['host'])
	outputs=commands.getoutput(snmp_request).split("NET-SNMP-EXTEND-MIB")
	if config['debug']:
		debug("snmp request: %s" % (snmp_request))
		debug(outputs)

	if results[0] == timeoutstr:
		error("No response from: %s. Maybe community is not good ?" % (config['host']) )
	if results[1] == noexecstr:
		error("No exec/extend snmp found for this server: %s." % (config['host']) )	
		
	for i in range(1,len(results)): #skip 0 as it's empty because of split
		cleaned_result=clean_line_result(results[i])
		
		plugin_name=cleaned_result[0]
		plugin_return_code=int(cleaned_result[1])
		if not plugin_name in output_table :
			output_table[plugin_name]={
				"Name"			:	"",
				"Result"		:	unknown,
				"Summary"		:	"",
				"Perfdata"		:	"",
				"LongOutput"	:	""
			}
		
		#output_table[plugin_name]["Name"]=plugin_name
		output_table[plugin_name]["Result"]=plugin_return_code
	
	for i in range(1,len(outputs)): #skip 0 as it's empty because of split
		cleaned_output=clean_line_output(outputs[i])
		
		plugin_name=cleaned_output[0]
		plugin_return_summary=cleaned_output[1]
		plugin_return_perfdata=cleaned_output[2]
		plugin_return_long_output=cleaned_output[3]
		
		if not plugin_name in output_table :
			output_table[plugin_name]={
				"Name"			:	"",
				"Result"		:	unknown,
				"Summary"		:	"",
				"Perfdata"		:	"",
				"LongOutput"	:	""
			}
			
		#output_table[plugin_name]["Name"]=plugin_name
		output_table[plugin_name]["Summary"]=plugin_return_summary
		output_table[plugin_name]["Perfdata"]=plugin_return_perfdata
		output_table[plugin_name]["LongOutput"]=plugin_return_long_output
	
		
	
	for snmp_extend in output_table.items():
	
		#stupid nagios rules, unknown return code is > critical ...
		#so a dirty method is applied here to avoid this
		if snmp_extend[1]["Result"]==state_nagios["OK"]:
			overall_status = max(overall_status,ok)
		elif snmp_extend[1]["Result"]==state_nagios["WARNING"]:
			overall_status = max(overall_status,warning)
		elif snmp_extend[1]["Result"]==state_nagios["CRITICAL"]:
			overall_status = max(overall_status,critical)
		else:
			overall_status = max(overall_status,unknown)
			
		if config['output_complete_summary']:
			add_summary("%s=%s, " % (snmp_extend[0],snmp_extend[1]["Summary"]) )
		else:
			add_summary("%s=%s, " % (snmp_extend[0],state_nagios_text[snmp_extend[1]["Result"]]) )
		
		if snmp_extend[1]["Perfdata"] != "" and config['output_perfdata']:
			add_perfdata("%s" % (snmp_extend[1]["Perfdata"]) )
	
		if snmp_extend[1]["LongOutput"] != "" and config['output_longoutput']:
			add_long_output("%s=%s, " % (snmp_extend[0], snmp_extend[1]["LongOutput"]) )
	
		if snmp_extend[1]["Result"] > ok:
			not_ok_count+=1
		else:
			ok_count+=1
		
		if config['debug']:
			debug("extend name: %s, summary: %s, perfdata: %s, longoutput: %s" % (snmp_extend[0], snmp_extend[1]["Summary"], snmp_extend[1]["Perfdata"], snmp_extend[1]["LongOutput"]) )

	
		
###################################################
#				
# check_this_snmp_extend()
#	check this SNMP exec (config['exec_name'])
###################################################
def check_this_snmp_extend():
	global overall_status
	
	output_table={}
	
	timeoutstr="Timeout: No Response from " + config['host']
	noexecstr="No Such Instance currently exists at this OID"
	
	snmp_request="snmpwalk -v%s -c %s -OQv %s 'NET-SNMP-EXTEND-MIB::nsExtendResult.\"%s\"'" % (config['snmp_version'], config['community'], config['host'], config['exec_name'])
	result=commands.getoutput(snmp_request)
	if config['debug']:
		debug("snmp request: %s" % (snmp_request))
		debug(result)
	
	if result == noexecstr:
		error("This exec module is not found for this server: %s" % (config['exec_name']) )
	if result == timeoutstr:
		error("No response from: %s. Maybe community is not good ?" % (config['host']) )
		
	snmp_request="snmpwalk -v%s -c %s -OQv %s 'NET-SNMP-EXTEND-MIB::nsExtendOutputFull.\"%s\"'" % (config['snmp_version'], config['community'], config['host'], config['exec_name'])
	output=commands.getoutput(snmp_request)
	if config['debug']:
		debug("snmp request: %s" % (snmp_request))
		debug(output)
	
	if result == noexecstr:
		error("This exec module is not found for this server: %s" % (config['exec_name']) )
	if result == timeoutstr:
		error("No response from: %s. Maybe community is not good ?" % (config['host']) )
		
	overall_status = int(result)

	
	add_summary(output)


###################################################
#				
# parse_arguments()	
#	parse script arguments
###################################################
def parse_arguments():
	global config
	
	arguments = argv[1:]
	while len(arguments) > 0:
		arg = arguments.pop(0)
		if arg == '--help':
			print_help()
			exit(exit_codes[unknown])
		elif arg == '--debug':
			config['debug'] = True
		elif arg == '--output-longoutput':
			config['output_longoutput'] = True
		elif arg == '--output-perfdata':
			config['output_perfdata'] = True
		elif arg == '--output-complete-summary':
			config['output_complete_summary'] = True
		elif arg == '--snmp-version':
			config['snmp_version'] = arguments.pop(0)
		elif arg == '--community':
			config['community'] = arguments.pop(0)
		elif arg == '--host':
			config['host'] = arguments.pop(0)
		elif arg == '--exec-name':
			config['exec_name'] = arguments.pop(0)			
		elif arg == '--timeout':
			config['timeout'] = int(arguments.pop(0))
		else:
			error("UNKNOWN ARG %s" % arg)

	if config['host'] == "" or config['community'] == "" or config['exec_name'] == "":
		error("Missing mandatory args. Read help. RTFM !")

	
###################################################
#				
# print_help()	
#	print help text
###################################################
def print_help():
	print ""
	print "check_snmp_extend version %s" % version
	print "This plugin checks snmp extends (exec)"
	print ""
	print "Usage: %s --host hostname --snmp-version snmpversion --community communityname --exec-name exec_name" % argv[0]
	print "Usage: %s --help" % argv[0]
	print ""
	print "--snmp-version: version of snmp to use (only v1 and v2 can be used atm)"
	print "Should be 1 or 2c"
	print ""
	print "--exec-name: name of the snmp exec (extend) to check or ALL to check all available on this host"
	print ""
	print "Optional output parameters (works only with ALL mode): "
	print "--output-complete-summary: instead of output name:STATUS, name:STATUS, it output the complete summary of"
	print "all exec plugins you specified: name:FULL OUTPUT, name:FULL OUTPUT"
	print ""
	print "--output-perfdata: Output perf data (what is after the |)"
	print ""
	print "--output-longoutput: Output long outpout (what is after the \\n)"
	print ""
	print ""
	print "Options: "
	print "--debug : print debug infos"
	print "--timeout X : timeout the plugin after X seconds (default: 10)"
	print ""
	print ""
	print "HOW TO ADD A SNMP EXEC (EXTEND) :"
	print "edit /etc/snmp/snmpd.conf"
	print "add a line like this :"
	print ""
	print "exec yesterday /bin/date --date=yesterday"
	print "(This should output the current date -1 day)"
	print ""
	print "Then restart your snmpd daemon (service snmpd restart)"
	print ""
	print "Call this plugin like this to check this snmp extend :"
	print "%s --host localhost --snmpversion 2c --community public --name yesterday"  % argv[0]
	print "This should output :"
	print "Mon Mar 28 11:12:24 CEST 2011"
	print "(well, you won't get this specific date, but output will be similar...)"
	
	

###################################################
#				
# error(text, exitcode)	
#	print error text
###################################################
def error(errortext, exit_code=unknown):
	print "* Error: %s" % errortext
	#print_help()
	#:print "* Error: %s" % errortext
	exit(exit_codes[exit_code])

###################################################
#				
# debug(text)	
#	print debug text
###################################################
def debug( debugtext ):
	print	debugtext

###################################################
#				
# add_perfdata(text)	
#	append text to perfdata
###################################################
def add_perfdata(text):
	global perfdata
	perfdata = perfdata + text + " "

###################################################
#				
# add_summary(text)	
#	append text to summary
###################################################
def add_summary(text):
	global summary
	summary = summary + text
	
###################################################
#				
# add_long_output(text)	
#	append text to long output
###################################################
def add_long_output(text):
	global long_output
	long_output = long_output + text

###################################################
#				
# main()	
#	main
###################################################
def main():
	parse_arguments()

	do_the_main_stuff()

	end()

###################################################
#
# do_the_main_stuff()
#       Exported from main() to get advantages of timeout function
###################################################
@timeout()
def do_the_main_stuff():
	if config['exec_name'] == 'ALL':
		check_snmp_extend()
	else:
		check_this_snmp_extend()


###################################################
#				
# end()	
#	print the output infos and exit with the correct nagios output code
###################################################
def end():
	global overall_status
	
	if overall_status < 0 or overall_status > 3:
		overall_status = unknown
	
	if config['exec_name']=='ALL':
		message = "%s - ok objects: %s, not ok objects: %s - %s" % (state[overall_status], ok_count, not_ok_count, summary)
		if perfdata != "" and config['output_perfdata']:
			message = "%s | %s" % (message, perfdata)
		if long_output != "" and config['output_longoutput']:
			message = "%s \n %s" % (message, long_output)
		exit_code = exit_codes[overall_status]
	else:
		message = "%s" % (summary)
		exit_code = overall_status
	print message
	
	exit(exit_code)
	
###################################################
#
# __main__
#	call to main()
###################################################
if __name__ == '__main__':
	main()

