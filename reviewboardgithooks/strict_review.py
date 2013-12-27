#!/usr/bin/python
# -*- coding:utf8 -*-
import os
import sys
import time
import subprocess
import urllib2
import cookielib
import base64
import re
import shelve
from datetime import datetime
import ConfigParser
try:
    import json
except ImportError:
    import simplejson as json

from urlparse import urljoin

#from .utils import get_cmd_output, split

def get_cmd_output(cmd):
    return os.popen(' '.join(cmd)).read()

def split(s):
#    return set([i.strip() for i in shlex.split(s, posix = False) if i.strip()])
    return set([i.strip() for i in s.split(',') if i.strip()])

def get_os_conf_dir():
    platform = sys.platform
    if platform.startswith('win'):
        try:
            return os.environ['ALLUSERSPROFILE']
        except KeyError:
            print >>sys.stderr, 'Unspported operation system:%s'%platform
            sys.exit(1)
    return '/etc'

def get_os_temp_dir():
    import tempfile
    return tempfile.gettempdir()

def get_os_log_dir():
    platform = sys.platform
    if platform.startswith('win'):
        return get_os_conf_dir()
    return '/var/log'

OS_CONF_DIR = get_os_conf_dir()

conf = ConfigParser.ConfigParser()

conf_file = os.path.join(OS_CONF_DIR, 'reviewboard-git-hooks', 'conf.ini')
if not conf.read(conf_file):
    print >> sys.stderr, 'Invalid configuration file:%s'%conf_file
    exit(1)


COOKIE_FILE = os.path.join(get_os_temp_dir(), 'reviewboard-git-hooks-cookies.txt')

DEBUG = conf.getint('common', 'debug')

def debug(s):
    if not DEBUG:
        return
    f = open(os.path.join(get_os_log_dir(), 'reviewboard-git-hooks', 'debug.log'), 'at')
    print >>f, str(datetime.now()), s
    f.close()

try:
    RB_SERVER = conf.get('reviewboard', 'url')
    USERNAME = conf.get('reviewboard', 'username')
    PASSWORD = conf.get('reviewboard', 'password')
    
    MIN_SHIP_IT_COUNT = conf.getint('rule', 'min_ship_it_count')
    MAX_SUBMIT_TIME = conf.getint('rule', 'max_submit_time')
    if conf.has_option('rule', 'branch_name'):
        BRANCH_REGEX = conf.get('rule', 'branch_name')
    else:
        BRANCH_REGEX = ur".*"
    
    if conf.has_option('rule', 'ignore_path'):
        ignore_path = conf.get('rule', 'ignore_path')
        IGNORE_PATH = split(ignore_path)
    else:
        IGNORE_PATH = None
except ValueError:
    print >> sys.stderr, 'Please check %s, some value is not be set.'%conf_file
    exit(1)

if RB_SERVER == '' or USERNAME == '' or PASSWORD == '':
    print >> sys.stderr, 'Please check %s, some value is not be set.'%conf_file
    exit(1)

class GitError(StandardError):
    pass

class Opener(object):
    def __init__(self, server, username, password, cookie_file = None):
        self._server = server
        if cookie_file is None:
            cookie_file = COOKIE_FILE
        self._auth = base64.b64encode(username + ':' + password)
        cookie_jar = cookielib.MozillaCookieJar(cookie_file)
        cookie_handler = urllib2.HTTPCookieProcessor(cookie_jar)
        self._opener = urllib2.build_opener(cookie_handler)

    def open(self, path, ext_headers, *a, **k):
        url = urljoin(self._server, path)
        return self.abs_open(url, ext_headers, *a, **k)

    def abs_open(self, url, ext_headers, *a, **k):
        debug('url open:%s' % url)
        r = urllib2.Request(url)
        for k in ext_headers:
            v = ext_headers.get(k)
            r.add_header(k, v)
        r.add_header('Authorization', 'Basic ' + self._auth)
        try:
            rsp = self._opener.open(r)
            return rsp.read()
        except urllib2.URLError, e:
            raise GitError(str(e))


def read_file(file_path):
    file = None
    try:
        file = open(file_path)
        result = file.read()
    except Exception, e:
        raise GitError(str(e))
    finally:
        if file:
            file.close()
    return result

def get_repos(opener, repo_path):
    rsp = opener.open('/api/repositories/', {})
    rsp_json = json.loads(rsp)
    if rsp_json['stat'] != 'ok':
        raise GitError, "Get repositories error."
    
    for repository in rsp_json['repositories']:
        path = repository['path']
        if path == repo_path:
            return repository
    
    return None

def get_review_reqs(opener, repos_id):
    earliest_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - MAX_SUBMIT_TIME))
    
    rsp = opener.open('/api/review-requests/?status=submitted&repository=' + str(repos_id) + '&last-updated-from=' + earliest_time, {})
    rsp_json = json.loads(rsp)
    if rsp_json['stat'] != 'ok':
        raise GitError, "Get review requests error."
    
    return rsp_json['review_requests']

def get_diff_content(opener, diff):
    header = {'Accept':'text/x-patch'}
    rsp = opener.open(diff['links']['self']['href'], header)
    return rsp

def get_diff(opener, review_req):
    rsp = opener.open(review_req['links']['diffs']['href'], {})
    rsp_json = json.loads(rsp)
    if rsp_json['stat'] != 'ok':
        raise GitError, "Get diff info error."
    
    diffs = rsp_json['diffs']
    
    diff_count = len(diffs)
    if diff_count > 0:
        diff = diffs[diff_count - 1]
        content = get_diff_content(opener, diff)
        diff['content'] = content
        return diff
    
    return None

def get_review_req(opener, repos_id, diff):
    review_reqs = get_review_reqs(opener, repos_id)
    
    for review_req in review_reqs:
        review_diff = get_diff(opener, review_req)
        if review_diff != None and review_diff['content'] == diff:
            review_req['diff_time'] = review_diff['timestamp'];
            return review_req
    
    return None

def get_latest_pending_time(opener, review_req):
    rsp = opener.open(review_req['links']['changes']['href'], {})
    rsp_json = json.loads(rsp)
    if rsp_json['stat'] != 'ok':
        raise GitError, "Get review status changes error."
    
    time = None
    for change in rsp_json['changes']:
        if change['fields_changed'].has_key('status') and change['fields_changed']['status']['new'] != 'S':
            new_time = datetime.strptime(change['timestamp'], "%Y-%m-%dT%H:%M:%Sz")
            if time == None or new_time > time:
                time = new_time
    return time

def check_review(opener, review_req):
    pending_time = get_latest_pending_time(opener, review_req)
    diff_time = datetime.strptime(review_req['diff_time'], "%Y-%m-%dT%H:%M:%Sz")
    
    begin_time = diff_time;
    if pending_time != None and pending_time > begin_time:
        begin_time = pending_time
    
    submitter = review_reqreview_req['links']['submitter']['title']
    
    rsp = opener.open(review_req['links']['reviews']['href'], {})
    rsp_json = json.loads(rsp)
    if rsp_json['stat'] != 'ok':
        raise GitError, "Get reviews error."
    
    ship_it_users = set()
    for review in rsp_json['reviews']:
        ship_it = int(review['ship_it'])
        time = datetime.strptime(review['timestamp'], "%Y-%m-%dT%H:%M:%Sz")
        user = review['links']['user']['title']
        if ship_it and time >= begin_time and user != submitter:
            ship_it_users.add(review['links']['user']['title'])
    
    if len(ship_it_users) < MIN_SHIP_IT_COUNT:
        raise GitError, "Not enough user ship it.\n未获得足够的ship it\nLatest review open time is %s."%begin_time

def check_branch(name):
    if re.match(BRANCH_REGEX, name) == None:
        raise GitError, "Branch(%s) is not allowed to push to reviewboard."%name

def _main():
    debug('command:' + str(sys.argv))
    if len(sys.argv) != 4:
        raise GitError, 'Usage:\n  %s {repository_path} {branch} {diff_file}'%sys.argv[0]
    
    repos_path = sys.argv[1]
    branch = sys.argv[2]
    diff_file = sys.argv[3]
    
    check_branch(branch)
    
    diff = read_file(diff_file)
    
    opener = Opener(RB_SERVER, USERNAME, PASSWORD)
    repos = get_repos(opener, repos_path)
    if repos == None:
        raise GitError, "Not found repository with path:%s"%repos_path
    
    review_req = get_review_req(opener, repos['id'], diff)
    
    if review_req == None:
        raise GitError, "Not found the same diff in submitted review during cutting time.\n在有效时间范围内，未发现与所提交内容匹配的已关闭review"
        
    check_review(opener, review_req)
    #print json.dumps(review_req)
    

def main():
    try:
        _main()
    except GitError, e:
        print >> sys.stderr, str(e)
        exit(1)
    except Exception, e:
        print >> sys.stderr, str(e)
        import traceback
        traceback.print_exc(file=sys.stderr)
        exit(1)
    else:
        exit(0)

main()