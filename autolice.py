#! /usr/bin/python2
# coding=utf-8
import re
import subprocess
import sys

# map from SVN log names to real names
contributors = {
    'anya' : 'Anya Helene Bagge',
    'biz002' : 'Tero Hasu',
    'eva' : 'Anya Helene Bagge'
}
# list of copyright owners that should have their years updated from the log
autoYear = []
# list of copyright owners that should be added automatically (or when
# a particular contributor is in the log)
autoCopyright = {
    "University of Bergen" : "*",
    "Anya Helene Bagge" : "Anya Helene Bagge",
    "Tero Hasu" : "Tero Hasu"
}

standard_licenses = [("", {"GPLv3+", "EPLv1"})]

# format for copyright lines
fmt_copyright = "Copyright (c) %s %s\n"
# format for contributor lines, when the contributor was found in the log
fmt_contrib_from_log = "* %s\n"
# format for contributor lines, when the contributor was only found in the previous header
fmt_contrib_from_file = "+ %s\n"
moreInfo_notice = "See the file COPYRIGHT for more information.\n"
# GPLv3 licence notice
gpl_notice = "This program is free software: you can redistribute it and/or modify\nit under the terms of the GNU General Public License as published by\nthe Free Software Foundation, either version 3 of the License, or\n(at your option) any later version. See http://www.gnu.org/licenses/\n"
# EPL license notice
epl_notice = "All rights reserved. This program and the accompanying materials\nare made available under the terms of the Eclipse Public License v1.0\nwhich accompanies this distribution, and is available at\nhttp://www.eclipse.org/legal/epl-v10.html\n"
mit_notice = 'Permission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the "Software"), to deal\nin the Software without restriction, including without limitation the rights\nto use, copy, modify, merge, publish, distribute, sublicense, and/or sell\ncopies of the Software, and to permit persons to whom the Software is\nfurnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in\nall copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\nFITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\nAUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\nLIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\nOUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\nTHE SOFTWARE.'

license_notices = {
    "GPLv3+" : gpl_notice,
    "EPLv1" : epl_notice,
    "MIT" : mit_notice
}

re_Empty = re.compile(r'^\s*$') # empty lines
re_CommentStartLine = re.compile(r'^\s*/\*\s?(.*)$') # start of comment
re_CommentEndLine = re.compile(r'^\s*(.*)\*/') # mid-comment line starting with a *
re_CommentMidLine = re.compile(r'^\s*\*\s?(.*)$') # end of comment
re_SvnLog = re.compile(r'^[^|]*\|\s*([^ ]*)\s*\|\s*([0-9][0-9][0-9][0-9])-') # svn log line
re_eplLine = re.compile(r'.*(All rights reserved.\s*This program and the accompanying|Eclipse Public License|accompanies this distribution, and).*') # lines in an EPL notice
re_eplIdLine = re.compile(r'.*(http://www.eclipse.org/legal/epl-v10.html).*') # lines identifying an EPLv1.0 notice
re_gplLine = re.compile(r'.*(free software: you can redistribute it|GNU General Public License|any later version\.|http://www.gnu.org/licenses/).*') # lines in a GPL notice
re_gplIdLine = re.compile(r'.*(Free Software Foundation, either version 3 of the License, or).*') # lines identifying a GPLv3+ notice
re_mitLine = re.compile(r'.*(hereby granted, free of charge|software and associated documentation|Software without restriction|copy, modify, merge, publish, distribute, sublicense|and to permit persons to|do so, subject to the following conditions|substantial portions of the Software|WITHOUT WARRANTY OF ANY KIND|BUT NOT LIMITED TO THE WARRANTIES|PARTICULAR PURPOSE AND NONINFRINGEMENT|BE LIABLE FOR ANY CLAIM|WHETHER IN AN ACTION OF CONTRACT|THE SOFTWARE).*')
re_moreInfoLine = re.compile(r'.*See.*for more info.*')
re_copyright = re.compile(r'\s*Copyright\s*(\([cC]\)|©)\s*([0-9–, -]*)\s*(.*)$') # copyright lines
re_contribs = re.compile(r'^\s*Contributor') # contributor heading
re_contrib = re.compile(r'^\s*[*+]\s*(\w([\w\s.]|\S-\S)*)\s*') # individual contributor lines (only name is kept, the rest is stripped)
re_decoration = re.compile(r'^\W*$') # contentless lines


def autoLicenseFile(fileName):
    global currentFile
    currentFile = fileName
    (copy, code) = extractCopyrightComment(loadFile(fileName))
    (contribs, first, last) = extractContributorsAndYears(getSvnLog(fileName))
    (moreContribs, copyrights, oldLicenses, more) = decodeCopyright(copy)

    copyrightLines = []
    for k in copyrights:
        y = copyrights[k]
        if k in autoYear:
            if first == last:
                y = first
            else:
                y = "%d-%d" % (first, last)
        if k not in autoCopyright:
            copyrightLines.append(fmt_copyright % (y, k))
    for k in autoCopyright.keys():
        if autoCopyright[k] == "*" or autoCopyright[k] in contribs:
            if first == last:
                y = first
            else:
                y = "%d-%d" % (first, last)
            copyrightLines.append(fmt_copyright % (y, k))
    copyrightLines.sort()

    allContribs = list(contribs.union(moreContribs))
    allContribs.sort()

    licenses = set()
    for (path,lics) in standard_licenses:
        if fileName.startswith(path):
            licenses = licenses.union(lics)

    if oldLicenses != set() and oldLicenses != licenses:
        error("Non-standard license: " + repr(oldLicenses))
        licenses = oldLicenses
    licenses = list(licenses)
    licenses.sort()
    
    notice = "/**************************************************************************\n"
    if more != '':
        notice = "/*\n" + more + "*/" + notice
    for l in copyrightLines:
        notice = notice + l
    notice = notice + "\n"

    for l in licenses:
        notice = notice + license_notices[l]
        notice = notice + "\n"
    notice = notice + "\n"
    
    notice = notice + moreInfo_notice + "\n"

    notice = notice + "Contributors:\n"
    for c in allContribs:
        if c in contribs:
            notice = notice + fmt_contrib_from_log % c
        else:
            notice = notice + fmt_contrib_from_file % c

    notice = notice.replace("\n", "\n * ")
    notice = notice + "\n *************************************************************************/\n"
    
    writeFile(fileName, notice + code)


def getSvnLog(fileName):
    log = subprocess.check_output(["svn", "log", "-q", fileName])
    return log

def extractContributorsAndYears(log):
    names = set()
    firstYear = 3000
    lastYear = 0
    for l in log.split('\n'):
        mo = re_SvnLog.match(l)
        if mo != None:
            name = mo.group(1)
            year = mo.group(2)
            if name == 'eva':
                print l
            firstYear = min(int(year), firstYear)
            lastYear = max(int(year), lastYear)
            if name in contributors:
                name = contributors[name]
            else:
                print "Unknown contributor: ", name
            names.add(name)
    
    return (names, firstYear, lastYear)

def loadFile(fileName):
    f = open(fileName, "r")
    lines = f.readlines()
    f.close()
    return lines

def writeFile(fileName, s):
    f = open(fileName, "w")
    f.write(s)
    f.close()

def extractCopyrightComment(lines):
    mode = 's'
    cr = ''
    rest = ''
    for l in lines:
        if mode == 's':
            mo = re_CommentStartLine.match(l)
            if mo != None:
                if re_CommentEndLine.match(l):
                    rest = rest + l
                else:
                    cr = cr + mo.group(1) + "\n"
                    mode = 'c'
            elif re_Empty.match(l) == None:
                rest = rest + l
                mode = ''
        elif mode == 'c':
            mo = re_CommentEndLine.match(l)
            if mo != None:
                cr = cr + mo.group(1) + "\n"
                mode = ''
            else:
                mo = re_CommentMidLine.match(l)
                if mo != None:
                    cr = cr + mo.group(1) + "\n"
                else:
                    cr = cr + l
        elif mode == '':
            rest = rest + l
    return (cr, rest)


def decodeCopyright(copy):
    epl = False
    gpl = False
    contribs = set()
    copyrights = {}
    mode = 'n'
    licenses = set()
    more = ''

    for l in copy.split('\n'):
        mo = re_copyright.match(l)
        if mo != None:
            copyrights[mo.group(3).strip()] = mo.group(2).strip()
            mode = 'n'
        elif re_eplIdLine.match(l):
            licenses.add("EPLv1")
            mode = 'n'
        elif re_gplIdLine.match(l):
            licenses.add("GPLv3+")
            mode = 'n'
        elif re_gplIdLine.match(l):
            licenses.add("MIT")
            mode = 'n'
        elif re_eplLine.match(l) or re_gplLine.match(l) or re_mitLine.match(l) or re_moreInfoLine.match(l):
            mode = 'n'
        elif re_contribs.match(l):
            mode = 'c'
        elif mode == 'c':
            mo = re_contrib.match(l)
            if mo != None:
                contribs.add(mo.group(1).strip())
            elif re_decoration.match(l) != None:
                mode = 'n'
            else:
                mode = 'n'
                error("Strange copyright line: " + l)
                more = more + l
        elif re_decoration.match(l) == None:
            error("Strange copyright line: " + l)
            more = more + l

    return (contribs, copyrights, licenses, more)

currentFile = ""
def error(s):
    print currentFile, ": ", s


for f in sys.argv[1:]:
    print "Processing: ", f
    autoLicenseFile(f)
