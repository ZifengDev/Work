#!/usr/bin/python

import sys
import xmlrpclib

def access_confluence(url, username, password, klo_report_file, dest):
    '''
    Access confluence and report some information.
    @param url      The URL of the server.
    @param username Login username.
    @param password Login password.
    '''
    server = xmlrpclib.ServerProxy(url + '/rpc/xmlrpc')
    token = server.confluence2.login(username, password)

    #pages = server.confluence2.getPages(token, space_key)
    page  = server.confluence2.getPage(token, "whetstone", dest)

    file_object = open(klo_report_file)
    klo_report_content = file_object.read()

    page['content'] = klo_report_content

    server.confluence2.updatePage(token, page, {})
    server.confluence2.logout(token)

def main(args):
    if len(args) != 4:
        print "klopublish args num error!"
        return
    #args[0] is the username
    #args[1] is the password
    #args[2] should be the html format file
    #args[3] should be the html destination URL
    #arhs[3] e.g. KLO_Report TOP_FC_ANR
    access_confluence("http://wiki.n.miui.com", args[0], args[1], args[2], args[3])

if __name__ == "__main__":
    main(sys.argv[1:])
