# Create your views here.
# coding=utf-8
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from setssh.models import SSH
import os, stat
def setssh(request):
    if request.method == 'POST':
        userName = request.POST['name'].strip()  
        key = request.POST['ssh_rsa'].strip()    
        
        success = True
        name_error = False
        ssh_error = False
        if userName == None or userName == '':
            name_error = True
            success = False
        
        if key == None or key == '':
            ssh_error = True
            success = False
        user = SSH(name=userName, ssh_rsa=key)
        if not success:
            return render_to_response("register.html", {'name_error':name_error, 'ssh_error':ssh_error, "user": user}, context_instance=RequestContext(request))
        else :
            users = SSH.objects.filter(name=userName)
            if users == None or users.count() == 0:
                user.save()  
            else :
                users[0].name = userName
                users[0].ssh_rsa = key
                users[0].save()
            writeFile()
            return render_to_response("set_success.html", { "user": user})  
    return render_to_response("setssh.html", context_instance=RequestContext(request))

def writeFile():
    items = SSH.objects.all()
    os.chmod("~/.ssh/authorized_keys", stat.S_IWRITE | stat.S_IRGRP | stat.S_IRGRP)
    file_handler = open('~/.ssh/authorized_keys', 'w')
    for item in items:
        file_handler.write(item.ssh_rsa)
        file_handler.write('\n')
    file_handler.flush()
    file_handler.close()
    os.chmod("~/.ssh/authorized_keys", stat.S_IREAD | stat.S_IRGRP | stat.S_IRGRP) 

