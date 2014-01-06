#!/usr/bin/python
# -*- coding:utf8 -*-
import os
import stat
import sys
import time
import subprocess
import urllib2
import urllib
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

# common
DEBUG = 0
if conf.has_option('common', 'debug'):
    DEBUG = conf.getint('common', 'debug')

# reviewboard
RB_SERVER = None
USERNAME = None
PASSWORD = None

# rule
MIN_SHIP_IT_COUNT = None
MAX_SUBMIT_TIME = None
BRANCH_REGEX = ur".*"
IGNORE_PATH = None

# git
GIT_USERNAME = None
GIT_PASSWORD = None
GIT_DIR = None
HOOK_LOG = None
MAIL = None


def debug(s):
    if not DEBUG:
        return
    f = open(os.path.join(get_os_log_dir(), 'reviewboard-git-hooks', 'debug.log'), 'at')
    print >>f, str(datetime.now()), s
    f.close()

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

    def open(self, path, ext_headers = {}, post_datas = None):
        url = urljoin(self._server, path)
        return self.abs_open(url, ext_headers, post_datas)

    def abs_open(self, url, ext_headers, post_datas):
        debug('url open:%s' % url)
        r = urllib2.Request(url)
        for k in ext_headers:
            v = ext_headers.get(k)
            r.add_header(k, v)
        r.add_header('Authorization', 'Basic ' + self._auth)
        
        if post_datas != None:
            data = urllib.urlencode(post_datas)
            r.add_data(data)
        
        try:
            rsp = self._opener.open(r)
            return rsp.read()
        except urllib2.URLError, e:
            raise GitError(str(e))

def load_reviewboard_config(conf_file):
    conf = ConfigParser.ConfigParser()
    if not conf.read(conf_file):
        return

    try:
        global RB_SERVER, USERNAME, PASSWORD
        
        RB_SERVER = conf.get('reviewboard', 'url')
        USERNAME = conf.get('reviewboard', 'username')
        PASSWORD = conf.get('reviewboard', 'password')

    except ValueError:
        raise GitError, 'Please check %s, some value is wrong.'%conf_file

def check_reviewboard_config():
    if RB_SERVER == '' or USERNAME == '' or PASSWORD == '' or RB_SERVER == None or USERNAME == None or PASSWORD == None:
        raise GitError, 'Not set url, username, password for reviewboard in config.'

def load_git_config(conf_file):
    conf = ConfigParser.ConfigParser()
    if not conf.read(conf_file):
        return
    
    try:
        global GIT_USERNAME, GIT_PASSWORD, GIT_DIR, HOOK_LOG, MAIL
        
        GIT_USERNAME = conf.get('git', 'username')
        GIT_PASSWORD = conf.get('git', 'password')
        GIT_DIR = conf.get('git', 'dir')
        HOOK_LOG = conf.get('git', 'hook_log')
        
        if conf.has_option('git', 'mail'):
            MAIL = conf.get('git', 'mail')
    except ValueError:
        raise GitError, 'Please check %s, some value is wrong.'%conf_file
    except ConfigParser.Error:
        raise GitError, 'Please check %s, some value is wrong.'%conf_file

def check_git_config():
    if GIT_USERNAME == '' or  HOOK_LOG == '':
        raise GitError, 'Not define username, hook_log for git in config.'

def load_rule_config(conf_file):
    conf = ConfigParser.ConfigParser()
    if not conf.read(conf_file):
        return
    
    try:
        global MIN_SHIP_IT_COUNT, MAX_SUBMIT_TIME, BRANCH_REGEX, IGNORE_PATH
        
        if conf.has_option('rule', 'min_ship_it_count'):
            MIN_SHIP_IT_COUNT = conf.getint('rule', 'min_ship_it_count')
        
        if conf.has_option('rule', 'max_submit_time'):
            MAX_SUBMIT_TIME = conf.getint('rule', 'max_submit_time')
        
        if conf.has_option('rule', 'branch_name'):
            BRANCH_REGEX = conf.get('rule', 'branch_name')
        
        if conf.has_option('rule', 'ignore_path'):
            ignore_path = conf.get('rule', 'ignore_path')
            IGNORE_PATH = split(ignore_path)
    except ValueError:
        raise GitError, 'Please check %s, some value is wrong.'%conf_file

def check_rule_config():
    if MIN_SHIP_IT_COUNT == None or MAX_SUBMIT_TIME == None:
        raise GitError, 'Not define min_ship_it_count, max_submit_time for rule in config.'

def write_file(file_path, lines):
    file = None
    try:
        dir_path = os.path.dirname(file_path)
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path, 0777)
        
        file = open(file_path, 'w')
        for line in lines:
            print >>file, line
    except Exception, e:
        raise GitError(str(e))
    finally:
        if file:
            file.close()


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
    rsp = opener.open('/api/repositories/')
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
    
    rsp = opener.open('/api/review-requests/?status=submitted&repository=' + str(repos_id) + '&last-updated-from=' + earliest_time)
    rsp_json = json.loads(rsp)
    if rsp_json['stat'] != 'ok':
        raise GitError, "Get review requests error."
    
    return rsp_json['review_requests']

def get_diff_content(opener, diff):
    header = {'Accept':'text/x-patch'}
    rsp = opener.open(diff['links']['self']['href'], header)
    return rsp

def get_diff(opener, review_req):
    rsp = opener.open(review_req['links']['diffs']['href'])
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
    rsp = opener.open(review_req['links']['changes']['href'])
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
    
    rsp = opener.open(review_req['links']['reviews']['href'])
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

def check_receive(repos_path, branch, diff_file):
    conf_file = os.path.join(OS_CONF_DIR, 'reviewboard-git-hooks', 'conf.ini')
    load_reviewboard_config(conf_file)
    load_rule_config(conf_file)
    
    conf_file = os.path.join(repos_path, 'hooks', 'conf.ini')
    load_rule_config(conf_file)
    
    check_reviewboard_config()
    check_rule_config()
    
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

def config_repos(repos_path):
    conf_file = os.path.join(OS_CONF_DIR, 'reviewboard-git-hooks', 'conf.ini')
    load_git_config(conf_file)
    check_git_config()
    
    curent_user = os.popen('id -un').read().replace('\n', '')
    if curent_user != GIT_USERNAME:
        cmd = {'name':GIT_USERNAME, 'passwd':GIT_PASSWORD, 'cmd':sys.argv[0], 'repos':repos_path}
        result = os.system('sudo -u "%(name)s" -p "%(passwd)s" "%(cmd)s" install "%(repos)s"'%cmd)
        exit(result >> 8)
    
    repos_name = os.path.basename(repos_path)
    file_update = os.path.join(repos_path, 'hooks', 'update')
    file_post_update = os.path.join(repos_path, 'hooks', 'post-update')
    
    
    update_sh = ['#!/bin/sh',
    '. git-sh-setup',
    'echo "%(repos_name)s:update: $*" >> "%(log_file)s"'%{'repos_name':repos_name, 'log_file':HOOK_LOG},
    'DIFF_FILE="/tmp/git_diff_${RANDOM}.txt"',
    'git diff --full-index "$2" "$3" >> "${DIFF_FILE}"',
    'git-check-reviewboard check_review "`pwd`" "$1" "${DIFF_FILE}"',
    'res=`echo $?`',
    'rm -f "${DIFF_FILE}"',
    'exit ${res}']
    
    write_file(file_update, update_sh)
        
    post_update_sh = list()
    post_update_sh.append('#!/bin/sh')
    post_update_sh.append('echo "%(repos_name)s:post-update: $*" >> "%(log_file)s"'%{'repos_name':repos_name, 'log_file':HOOK_LOG})
    post_update_sh.append('git push --mirror >> "%(log_file)s" 2>> "%(log_file)s"'%{'log_file':HOOK_LOG})
    
    post_update_sh.append('if [ $? -ne 0 ]; then')
    post_update_sh.append('	echo "Failed push to GitLab on $git_path" >> "%(log_file)s"'%{'log_file':HOOK_LOG})
    if MAIL != None and MAIL != '':
        post_update_sh.append('	echo "Failed push to GitLab on $git_path" | mail -s "Reviewboard push failed" "%s"'%MAIL)
    post_update_sh.append('fi')
    
    write_file(file_post_update, post_update_sh)
    
    os.chmod(file_update, stat.S_IRWXU + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)
    os.chmod(file_post_update, stat.S_IRWXU + stat.S_IRGRP + stat.S_IXGRP + stat.S_IROTH + stat.S_IXOTH)

def create_repos_mirror(remote_path, local_path):
    if os.path.exists(local_path):
        raise GitError, "Target path \'%s\' has been exist.\nPlease connect to admin or use another repostory name."%local_path
    
    result = os.system('git clone --mirror "%(remote_path)s" "%(local_path)s"'%{'remote_path':remote_path, 'local_path':local_path})
    if result != 0:
        raise GitError, "Clone remote repository failed."

def rb_create_repos(repos_name, local_path, remote_path):
    opener = Opener(RB_SERVER, USERNAME, PASSWORD)
    
    fields = {
        'name':repos_name,
        'tool':'Git',
        'path':local_path,
        'mirror_path':remote_path,
        #'raw_file_url':,
        'username':GIT_USERNAME,
        'password':GIT_PASSWORD,
        #'public':,
        #'bug_tracker':,
        'encoding':'utf-8'
        #'trust_host':,
    }
    rsp = opener.open('/api/repositories/', {}, fields)
    print type(rsp)
    print rsp

def create_repos(remote_path, repos_name):
    conf_file = os.path.join(OS_CONF_DIR, 'reviewboard-git-hooks', 'conf.ini')
    load_reviewboard_config(conf_file)
    load_git_config(conf_file)
    
    check_reviewboard_config()
    check_git_config()
    
    curent_user = os.popen('id -un').read().replace('\n', '')
    if curent_user != GIT_USERNAME:
        cmd = {'username':GIT_USERNAME, 'passwd':GIT_PASSWORD, 'cmd':sys.argv[0], 'path':remote_path, 'name':repos_name}
        result = os.system('sudo -u "%(username)s" -p "%(passwd)s" "%(cmd)s" mkrepo "%(path)s" "%(name)s"'%cmd)
        exit(result >> 8)
    
    local_path = os.path.join(GIT_DIR, repos_name)
    create_repos_mirror(remote_path, local_path)
    
    rb_create_repos(repos_name, local_path, remote_path)
    
    config_repos(local_path)

def help_msg():
    name = os.path.basename(sys.argv[0])
    line1 = 'Usage:'
    line2 = '  %s mkrepo {repository_remote_path} {repository_name}'%name
    line3 = '  %s install {repository_path}'%name
    line4 = '  %s check_review {repository_path} {branch} {diff_file}'%name
    
    return '%(line1)s\n%(line2)s\n%(line3)s\n%(line4)s'%{'line1':line1, 'line2':line2, 'line3':line3, 'line4':line4}

def _main():
    debug('command:' + str(sys.argv))
    if len(sys.argv) < 2:
        raise GitError, help_msg()
    
    command = sys.argv[1]
    if command == 'mkrepo':
        if len(sys.argv) != 4:
            raise GitError, help_msg()
        
        remote_path = sys.argv[2]
        repos_name = sys.argv[3]
        
        create_repos(remote_path, repos_name)
    elif command == 'install':
        if len(sys.argv) != 3:
            raise GitError, help_msg()
        
        repos_path = sys.argv[2]
        
        config_repos(repos_path)
    elif command == 'check_review':
        if len(sys.argv) != 5:
            raise GitError, help_msg()
        
        repos_path = sys.argv[2]
        branch = sys.argv[3]
        diff_file = sys.argv[4]
        
        check_receive(repos_path, branch, diff_file)
    else:
        raise GitError, help_msg()

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