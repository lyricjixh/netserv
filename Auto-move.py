#!/usr/bin/env python3

import sys
import csv
import os
import requests
import yaml
from cvprac.cvp_client import CvpClient
import argparse
import ssl
import logging
from jinja2 import Environment, FileSystemLoader
ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings() 

def Main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cvp', default='192.168.101.35', help='CVP Server IP')
    parser.add_argument('--username', default='cvpadmin', help='CVP username')
    parser.add_argument('--password', default='password123', help='Cloudvision password')
    parser.add_argument('--logging', default='', help='Logging levels info, error, or debug')
    parser.add_argument('--devlist', default='devices.csv', help='YAML/CSV file with list of approved devices.')
    parser.add_argument('--template', default='jinja', help='Template format, either Jinja or plain text.')
    args = parser.parse_args()

    # Only enable logging when necessary
    if args.logging != '':
        logginglevel = args.logging
        formattedlevel = logginglevel.upper()

        # Open logfile
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',filename='cvpmove.log', level=formattedlevel, datefmt='%Y-%m-%d %H:%M:%S')
    else:
        ()
        
    # Open variable file either csv or yaml
    filetype = args.devlist.split('.')
    
    if filetype[1] == 'yml':
        # Open YAML variable file
        with open(os.path.join(sys.path[0],args.devlist), 'r') as vars_:
            data = yaml.safe_load(vars_)
    
    elif filetype[1] == 'csv':
        devices = []
        with open(os.path.join(sys.path[0],args.devlist), 'r') as vars_:
            for line in csv.DictReader(vars_):
                devices.append(line)
        data = {'all': devices}
    
    else:
        logging.info('Please enter a valid file type.')

    # CVPRAC connect to CVP
    clnt = CvpClient()
    try:
        clnt.connect(nodes=[args.cvp], username=args.username, password=args.password)
    except:
        logging.error('Unable to login to Cloudvision')

    # Get devices from Undefined container in CVP and add their MAC to a list
    try:
        undefined = clnt.api.get_devices_in_container('Undefined')
    except:
        logging.error('Unable to get devices from Cloudvision.')

    undef = []
    for unprov in undefined:
        undef.append(unprov['systemMacAddress'])

    # Compare list of devices in CVP undefined container to list of approved devices defined in YAML file
    # If the the device is defined in the YAML file then provision it to the proper container
    for dev in data['all']:
        if dev['mac'] in undef:
            device = clnt.api.get_device_by_mac(dev['mac'])
            #Need to determine if the container exist
            try:
                ContainerExist(clnt, dev)
            except:
                logging.error('Unable to determine if container exist')

            try:
                if dev['size'] == 'xlarge' or dev['size'] == 'xl':
                    tsk = clnt.api.deploy_device(device=device, container=dev['fabric'] + '_' + dev['sitenumber'] + '_' + dev['container'])
                else:
                    tsk = clnt.api.deploy_device(device=device, container=dev['sitenumber'] + '_' + dev['container'])
                
                Execute(clnt, tsk['data']['taskIds'])
                con = Configlet(clnt, dev, args.cvp, args.username, args.password, args.template)
                
                if con != None and con != 'reconcile':
                    assign = AssignConfiglet(clnt, dev, con)
                    Execute(clnt, assign['data']['taskIds'])
                
                elif con == 'reconcile':
                    cfglets = Containercfg(clnt, dev)
                    Execute(clnt, cfglets['data']['taskIds'])
                else:
                    ()
            except:
                logging.error('Unable to deploy device.')
        else:
            logging.info('device ' + str(undef) + ' not approved for deployment or already provisioned.')

#Check if container exist
def ContainerExist(clnt, data):
    try:
        if data['sitename'] != '':
            site = clnt.api.get_container_by_name(name=data['sitename'])
            territory = clnt.api.get_container_by_name(name=data['territory'])
            subcontainer = clnt.api.get_container_by_name(name=data['sitenumber'] + '_' + data['nettype'])
            if site == None:
                clnt.api.add_container(container_name=data['sitename'], parent_name=territory['name'], parent_key=territory['key'])
                CreateSubContainers(clnt,data)
            elif site != None and subcontainer == None:
                CreateSubContainers(clnt,data)
            elif subcontainer == None:
                CreateSubContainers(clnt,data)
            elif subcontainer != None:
                return 'Containers Exist'
    except:
        logging.info('Error creating parent containers')
        return 'Failure'

#Create sub containers under the sitename depending on size of site
def CreateSubContainers(clnt, data):
    try:
        if data['size'] == 'small':
            pkey = clnt.api.get_container_by_name(name=data['sitename'])
            containers = {}
            containers['_leaf'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_leaf')
            for k, v in iter(containers.items()):
                if v == None:
                    clnt.api.add_container(container_name=data['sitenumber'] + k, parent_name=data['sitename'], parent_key=pkey['key'])
            else:
                ()
        elif data['size'] == 'medium':
            pkey = clnt.api.get_container_by_name(name=data['sitename'])
            containers = {}
            containers['_leaf'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_leaf')
            containers['_superspine'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_superspine')
            containers['_borderleaf'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_borderleaf')
            for k, v in iter(containers.items()):
                if v == None:
                    clnt.api.add_container(container_name=data['sitenumber'] + k, parent_name=data['sitename'], parent_key=pkey['key'])
            else:
                ()
        elif data['size'] == 'large':
            pkey = clnt.api.get_container_by_name(name=data['sitename'])
            containers = {}
            containers['_leaf'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_leaf')
            containers['_superspine'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_superspine')
            containers['_borderleaf'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_borderleaf')
            containers['_spine'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_spine')
            for k, v in iter(containers.items()):
                if v == None:
                    clnt.api.add_container(container_name=data['sitenumber'] + k, parent_name=data['sitename'], parent_key=pkey['key'])
            else:
                ()
        elif data['size'] == 'xlarge':
            count = 1
            while count <= int(data['fabric_count']):
                fabric = clnt.api.get_container_by_name(name='fabric_' + str(count))
                if fabric == None:
                    mainkey = clnt.api.get_container_by_name(name=data['sitename'])
                    clnt.api.add_container(container_name='fabric_' + str(count), parent_name=data['sitename'], parent_key=mainkey['key'])
                    pkey = clnt.api.get_container_by_name(name='fabric_' + str(count))
                    containers = {}
                    containers['_leaf'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_leaf')
                    containers['_superspine'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_superspine')
                    containers['_borderleaf'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_borderleaf')
                    containers['_spine'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_spine')
                    for k, v in iter(containers.items()):
                        if v == None:
                            clnt.api.add_container(container_name='fabric_'+ str(count) + '_' + data['sitenumber'] + k, parent_name=data['sitename'], parent_key=pkey['key'])
                        else:
                            ()
                elif fabric != None:
                    pkey = clnt.api.get_container_by_name(name='fabric_' + str(count))
                    containers = {}
                    containers['_leaf'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_leaf')
                    containers['_superspine'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_superspine')
                    containers['_borderleaf'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_borderleaf')
                    containers['_spine'] = clnt.api.get_container_by_name(name=data['sitenumber'] + '_spine')
                    for k, v in iter(containers.items()):
                        if v == None:
                            clnt.api.add_container(container_name='fabric_'+ str(count) + '_' + data['sitenumber'] + k, parent_name=data['sitename'], parent_key=pkey['key'])
                        else:
                            ()
                count += 1
        else:
            ()
    except:
        logging.info('Unable to create sub containers for site ' + str(data['sitename']))

#Create configlet for management or reconcile if switch is not ZTP
def Configlet(clnt, data, cvp, user, password, template):
    l = []
    try:
        config = clnt.api.get_configlets(start=0, end=0)
        ztp = clnt.api.get_device_by_mac(data['mac'])
    except:
        logging.error('Unable to get list of configlets.')

    for configlet in config['data']:
        l.append(configlet['name'])
    
    if data['hostname'] + str('_mgmt') in l:
        logging.info('Configlet ' + str(data['hostname'] + '_mgmt') + ' already exist')
    elif ztp['ztpMode'] == 'true' or data['ztp'] == 'true' or data['ztp'] == 'TRUE':
        #Render configuration template to push to cvp as a configlet
        try:
            if template == 'jinja':
                THIS_DIR = os.path.dirname(os.path.abspath(__file__))
                j2_env = Environment(loader=FileSystemLoader(THIS_DIR),
                         trim_blocks=True)
                if data['nettype'] == 'leaf':
                    conf = j2_env.get_template('leaf.j2').render(hostname = data['hostname'], mgmtint = data['mgmtint'], mgmtip = data['mgmtip'], mgmtmask = data['mgmtmask'], mgmtgateway = data['mgmtgateway'], cvp=cvp)
                elif data['nettype'] == 'spine':
                    conf = j2_env.get_template('spine.j2').render(hostname = data['hostname'], mgmtint = data['mgmtint'], mgmtip = data['mgmtip'], mgmtmask = data['mgmtmask'], mgmtgateway = data['mgmtgateway'], cvp=cvp)
                
                elif data['nettype'] == 'borderleaf' or 'border leaf':
                    conf = j2_env.get_template('borderleaf.j2').render(hostname = data['hostname'], mgmtint = data['mgmtint'], mgmtip = data['mgmtip'], mgmtmask = data['mgmtmask'], mgmtgateway = data['mgmtgateway'], cvp=cvp)
                
                elif data['nettype'] == 'serviceleaf' or 'service leaf':
                    conf = j2_env.get_template('serviceleaf.j2').render(hostname = data['hostname'], mgmtint = data['mgmtint'], mgmtip = data['mgmtip'], mgmtmask = data['mgmtmask'], mgmtgateway = data['mgmtgateway'], cvp=cvp)
            
            #Plain text file templates find and replace.  Not the prefered method but an option.
            elif template == 'text' or template == 'txt':
                if data['nettype'] == 'leaf':
                    #Dictionary of words to replace and what to replace them with
                    replace = {'*hostname*': data['hostname'], '*mgmtint*': data['mgmtint'],'*mgmtip*': data['mgmtip'],'*mgmtmask*': data['mgmtmask'], '*mgmtgateway*': data['mgmtgateway'], '*cvp*': cvp}
                    with open(os.path.join(sys.path[0],'leaf.txt'), 'r') as file :
                        conf = file.read()
                    for k, v in iter(replace.items()):
                        conf = conf.replace(k, v)
                
                elif data['nettype'] == 'spine':
                    #Dictionary of words to replace and what to replace them with
                    replace = {'*hostname*': data['hostname'], '*mgmtint*': data['mgmtint'],'*mgmtip*': data['mgmtip'],'*mgmtmask*': data['mgmtmask'], '*mgmtgateway*': data['mgmtgateway'], '*cvp*': cvp}
                    with open(os.path.join(sys.path[0],'spine.txt'), 'r') as file :
                        conf = file.read()
                    for k, v in iter(replace.items()):
                        conf = conf.replace(k, v)
                
                elif data['nettype'] == 'borderleaf' or 'border leaf':
                    #Dictionary of words to replace and what to replace them with
                    replace = {'*hostname*': data['hostname'], '*mgmtint*': data['mgmtint'],'*mgmtip*': data['mgmtip'],'*mgmtmask*': data['mgmtmask'], '*mgmtgateway*': data['mgmtgateway'], '*cvp*': cvp}
                    with open(os.path.join(sys.path[0],'borderleaf.txt'), 'r') as file :
                        conf = file.read()
                    for k, v in iter(replace.items()):
                        conf = conf.replace(k, v)
                
                elif data['nettype'] == 'serviceleaf' or 'service leaf':
                    #Dictionary of words to replace and what to replace them with
                    replace = {'*hostname*': data['hostname'], '*mgmtint*': data['mgmtint'],'*mgmtip*': data['mgmtip'],'*mgmtmask*': data['mgmtmask'], '*mgmtgateway*': data['mgmtgateway'], '*cvp*': cvp}
                    with open(os.path.join(sys.path[0],'serviceleaf.txt'), 'r') as file :
                        conf = file.read()
                    for k, v in iter(replace.items()):
                        conf = conf.replace(k, v)
        except:
            logging.error('Unable to render template')
        
        #Push configlet to CVP
        try:
            if data['hostname'] + '_cfglt' in l:
                devconf = clnt.api.get_configlet_by_name(name=data['hostname'] + '_cfglt')
                usexisting = input('Configlet ' +  data['hostname'] + '_cfglt already exist Y/N? ')
                if usexisting == 'y' or usexisting == 'Y' or usexisting == 'yes' or usexisting == 'Yes':
                    return devconf
                else:
                    logging.error('Configlet with the same name already exist and you have selected to not use the existing.  Please delete the existing configlet and try again.')
                    ()

            else:
                clnt.api.add_configlet(name=data['hostname'] + '_cfglt', config=conf)
                cfgltdata = clnt.api.get_configlet_by_name(name=data['hostname'] + '_cfglt')
                return cfgltdata
        except:
            logging.error('Unable to create configlet ' + str(data['hostname'] + '_cfglt'))
    else:
        try:
            container = clnt.api.get_container_by_name(name=data['container'])
            ckey = container['key']
            login = 'https://{server}/cvpservice/login/authenticate.do'.format(server=cvp)
            resp = requests.post(login, headers={'content-type': 'application/json'}, json={'userId': user, 'password': password}, verify=False)
            jresp = resp.json()
            token = jresp['cookie']['Value']
            url = 'https://{server}/cvpservice/provisioning/containerLevelReconcile.do?containerId={container}&reconcileAll=false'.format(server=cvp, container=ckey)
            response = requests.get(url, auth=(user, password), headers={'Cookie': 'access_token=' + str(token)}, verify=False)
            if response.status_code == 200:
                reconcile = 'reconcile'
            return reconcile
        except:
            logging.error('Unable to reconcile container.')


# function to assign configlet to new device
def AssignConfiglet(clnt, dev, con):
    try:
        device = clnt.api.get_device_by_mac(dev['mac'])
    except:
        logging.error('Unable to get device information from Cloudvision')
    cfglets = [{'name': dev['hostname'] + '_cfglt', 'key': con['key']}]
    try:
        task = clnt.api.apply_configlets_to_device(app_name=dev['hostname'] + '_cfglt', dev=device, new_configlets=cfglets)
        return task
    except:
        logging.error('Error applying configlet to device.')


def Containercfg(clnt, data):
    cfglets = clnt.api.get_configlets_by_device_id(data['mac'])
    cfglist = []
    for configlet in cfglets:
        cfglist.append({'name': configlet['name'], 'key': configlet['key']})
    device = clnt.api.get_device_by_mac(data['mac'])
    task = clnt.api.apply_configlets_to_device(app_name='container_configlet', dev=device, new_configlets=cfglist)
    return task


# Function to run task if they are for the devices we provisioned
def Execute(clnt, tasks):
    for task in tasks:
        try:
            clnt.api.execute_task(task_id=task)
        except:
            logging.info('Task ID ' + str(task) + ' is ' + ' failed to execute.')
    

if __name__ == '__main__':
   Main()