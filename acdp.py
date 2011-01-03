#!/usr/bin/python
#
# vim:expandtab:shiftwidth=4:ts=4:
#

import urllib,urllib2
import re
import tempfile
import sys
import os

HOME=os.getenv("HOME", "")
CONFIGFILE="%s/.acdp" % HOME

# regexps
# login failure
login_failure=re.compile('.*Login Failed. Please try again.*')
# month listing
list_entry = re.compile('<tr class="row1">\n\s*<td align="center">(\d+)</td>\n\s*<td align="left">(.*)</td>\n\s*<td align="center">(\d+)</td>\n\s*<td align="left"></td>\n\s*<td align="left">(.*)</td>')
project_entry = re.compile('\?proj_id=(\d+)">(.*)</a>')


DEFAULT_HOST="https://acdp.mandriva.com.br/"

DEBUG=False

class ACDP:
    def __init__(self, host=DEFAULT_HOST):
        self.host = host
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        urllib2.install_opener(self.opener)
        pass

    def login(self, login, passwd):
        url = self.host + '/acdp/login.php'
        params = urllib.urlencode({
            'action': 'login',
            'GoAheadAndLogIn': 'Login',
            'user': login,
            'passwd': passwd
            })
        con = self.opener.open(url, params)
        res = con.read()
        failure = login_failure.findall(res)
        if DEBUG:
            print res
            print failure
        if len(failure) == 0:
            print "Logged in"
            return True
        else:
            print "NOT logged in"
            return False


    def list_hours(self, year, month):
        """Lists acdp hours"""
        url = self.host + '/acdp/relatorio.php?action=personal_month&year=%(year)d&month=%(month)d' % ({'year': year, 'month': month})
        params = urllib.urlencode({
            'detailed': '1'
            })
        con = self.opener.open(url, params)
        res = con.read()
        if DEBUG:
            print res
        hours = list_entry.findall(res)
        return hours

    def list_recent(self):
        """Lists recent projects"""
        url = self.host + '/acdp/horas_projeto.php?action=add'
        con = self.opener.open(url)
        res = con.read()
        res_nl = res.replace('<p>','\n<p>')
        if DEBUG:
            print res_nl
        projects = project_entry.findall(res_nl)
        return projects

if __name__ == "__main__":
    acdp = ACDP()
    login = None
    passwd = None
    try:
        print CONFIGFILE
        fd = open(CONFIGFILE, "r")
        login = fd.readline().strip()
        passwd = fd.readline().strip()
        fd.close()
    except:
        print "Error: please create %s, containing my.mandriva login on first line\nand password on 2nd" % CONFIGFILE
        sys.exit(1)
    if not acdp.login(login, passwd):
        print "Unable to login."
        sys.exit(1)
    recent_projects = acdp.list_recent()
    projects_cache = {}
    print "# recent projects:"
    projects = {}
    for id, project in recent_projects:
        projects_cache[project] = id
        print "# %s - %s" % (id, project)
        projects[project] = []
    print

    hours = acdp.list_hours(2010, 11)
    for day, project, hours, descr in hours:
        if project not in projects:
            projects[project] = []
        projects[project].append((day, hours, descr))

    for project in projects:
        print "- %s" % project
        print "# day\thours\tdescription"
        for day, hours, descr in projects[project]:
            print "%s\t%s\t%s" % (day, hours, descr)
        print
