#!/usr/bin/python
#
# vim:expandtab:shiftwidth=4:ts=4:smarttab:
#

import urllib,urllib2
import re
import tempfile
import sys
import os
import tempfile
import difflib
import time

HOME=os.getenv("HOME", "")
CONFIGFILE="%s/.acdp" % HOME

# regexps
# login failure
login_failure=re.compile('.*Login Failed. Please try again.*')
# month listing
list_entry = re.compile('<tr class="row1">\n\s*<td align="center">(\d+)</td>\n\s*<td align="left">(.*)</td>\n\s*<td align="center">(\d+)</td>\n\s*<td align="left"></td>\n\s*<td align="left">(.*)</td>')
# project listing
project_entry = re.compile('\?proj_id=(\d+)">(.*)</a>')
# editable entry
pyacdp_entry = re.compile('([+-]) (\d+)\s*(\d+)\s*(\d+)\s*(.*)')

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


def leave(name_in, name_out, retcode=0):
    """Cleanups temporary files"""
    os.unlink(name_in)
    os.unlink(name_out)
    sys.exit(retcode)

if __name__ == "__main__":
    acdp = ACDP()
    fd_in, name_in = tempfile.mkstemp(suffix='acdp')
    fd_in = open(name_in, "w")
    fd_out, name_out = tempfile.mkstemp(suffix='acdp')
    fd_out = open(name_out, "w")
    login = None
    passwd = None

    if len(sys.argv) < 3:
        print "Usage: %s <month> <year>" % sys.argv[0]
        leave(name_in, name_out, 1)

    month = int(sys.argv[1])
    year = int(sys.argv[2])

    try:
        print CONFIGFILE
        fd = open(CONFIGFILE, "r")
        login = fd.readline().strip()
        passwd = fd.readline().strip()
        fd.close()
    except:
        print "Error: please create %s, containing my.mandriva login on first line\nand password on 2nd" % CONFIGFILE
        leave(name_in, name_out, 1)

    # login
    if not acdp.login(login, passwd):
        print "Unable to login."
        leave(name_in, name_out, 1)
    recent_projects = acdp.list_recent()
    hours = acdp.list_hours(year, month)

    projects_cache = {}
    projects_rev_cache = {}
    print >>fd_in, "# acdp data for %s / %s" % (month, year)
    print >>fd_in, "# cache of recent projects:"
    projects = {}
    for id, project in recent_projects:
        projects_cache[project] = id
        projects_rev_cache[id] = project
        print >>fd_in, "# %s - %s" % (id, project)
        projects[project] = []
    print >> fd_in

    for day, project, hours, descr in hours:
        if project not in projects:
            projects[project] = []
        projects[project].append((day, hours, descr))

    for project in projects:
        print >>fd_in, "- %s" % project
        print >>fd_in, "# %pid\tday\thours\tdescription"
        for day, hours, descr in projects[project]:
            pid = projects_cache.get(project, '-1')
            print >>fd_in, "%s\t%s\t%s\t%s" % (pid, day, hours, descr)
        print >>fd_in

    # generate diffable files
    fd_in.close()
    with open(name_in, "r") as fd_in:
        data_in = fd_in.read()
    fd_out.write(data_in)
    fd_out.close()

    # edit output file
    editor = os.getenv("VISUAL")
    if not editor:
        print "Error: VISUAL not defined, don't know what editor to use"
        leave(name_in, name_out, 1)

    if os.system("%s %s" % (editor, name_in)) != 0:
        print "Unable to edit file, aborting."
        leave(name_in, name_out, 1)

    # calculate diff
    fromdate = time.ctime(os.stat(name_out).st_mtime)
    todate = time.ctime(os.stat(name_in).st_mtime)
    fromlines = open(name_out, "U").readlines()
    tolines = open(name_in, "U").readlines()

    diff = difflib.ndiff(fromlines, tolines)
    changes = []
    for l in diff:
        res = pyacdp_entry.findall(l)
        if res:
            changes.append(res)

    print changes

    leave(name_in, name_out)
