import sys
import subprocess
import getopt
import json
from os import listdir
from os.path import isfile, join
import re
import urllib2
import base64
from datetime import datetime
import yaml
from jinja2 import Template

confStream = open('aws-config.yml', 'r')
conf = yaml.load(confStream)

region = conf['region']

def loadServiceSpecs():
    specDir = 'spot-fleet-specifications'
    specFiles = [f for f in listdir(specDir) if isfile(join(specDir, f))]
    specs = {}
    for s in specFiles:
        m = re.search('(.+)\.json', s)
        if m:
            with open(join(specDir, s)) as f:
                specs[m.group(1)] = json.load(f)
    return specs

services = loadServiceSpecs()

amiServices = {v['LaunchSpecifications'][0]['ImageId']: k for k, v in services.items()}

def get(d, k):
    return d[k] if k in d else 'N/A'

def queryServices():
    p = subprocess.Popen(['aws', '--region', region, 'ec2', 'describe-instances'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    described = json.loads(out)
    
    services = {}
    for reservation in described['Reservations']:
        for instance in reservation['Instances']:
            if instance['ImageId'] in amiServices:
                ins = {'InstanceId': get(instance, 'InstanceId'),
                        'PublicIpAddress': get(instance, 'PublicIpAddress'),
                        'PrivateIpAddress': get(instance, 'PrivateIpAddress')}
                services[amiServices[instance['ImageId']]] = ins

    return services;

def printServices():
    print json.dumps(queryServices(), ensure_ascii=False)

def createAmi(serviceName):
    services = queryServices()
    service = services[serviceName]
    if not service:
        print '%s was not found.' % serviceName
        return

    # Get cluster version using Ambari API
    m = re.search('\d+\.(.+)', serviceName)
    if not m:
        print '%s was not a valid serviceName.' % serviceName
        return

    r = urllib2.Request('http://0.%s.aws.mine:8080/api/v1/clusters' % m.group(1))
    authHeader = base64.b64encode('admin:admin')
    r.add_header('Authorization', 'Basic %s' % authHeader)
    clusters = json.load(urllib2.urlopen(r))

    instanceId = service['InstanceId']
    name = '%s-%s-%s' % (clusters['items'][0]['Clusters']['version'], serviceName, datetime.now().strftime('%Y%m%d%H'))

    p = subprocess.Popen(['aws', '--region', region, 'ec2', 'create-image',
            '--instance-id', instanceId, '--name', name],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    print out, err

def queryUnusedSnapshots():
    p = subprocess.Popen(['aws', '--region', region, 'ec2', 'describe-snapshots', '--owner-ids', conf['account']],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    snapshots = json.loads(out)['Snapshots']

    p = subprocess.Popen(['aws', '--region', region, 'ec2', 'describe-images', '--owners', conf['account']],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    images = json.loads(out)['Images']

    snapshotToImage = {x['BlockDeviceMappings'][0]['Ebs']['SnapshotId']: x for x in images}

    return [x for x in snapshots if x['SnapshotId'] not in snapshotToImage]


def listUnusedSnapshots():
    snapshots = queryUnusedSnapshots()
    volumeSize = 0
    for snapshot in snapshots:
        volumeSize += snapshot['VolumeSize']
        print json.dumps(snapshot, ensure_ascii=False)

    if volumeSize > 0:
        print 'Total volume size: {} GiB'.format(volumeSize)

def deleteUnusedSnapshots():
    snapshots = queryUnusedSnapshots()
    for snapshot in snapshots:
        print json.dumps(snapshot, ensure_ascii=False)
        p = subprocess.Popen(['aws', '--region', region, 'ec2', 'delete-snapshot', '--snapshot-id', snapshot['SnapshotId']],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        print out, err



def updateRoute53():
    services = queryServices()
    toResource = lambda k, v: {
            'Action': 'UPSERT',
            'ResourceRecordSet': {
                'Name': '{}.aws.mine'.format(k),
                'Type': 'A',
                'TTL': 300,
                'ResourceRecords': [{'Value': v['PrivateIpAddress']}]
            }
        }
    resourceRecords = [toResource(k, v) for k, v in services.items()]
    
    updateRequest = {
            'Comment': 'Update service resource records.',
            'Changes': resourceRecords
        }

    p = subprocess.Popen(['aws', 'route53', 'change-resource-record-sets',
            '--hosted-zone-id', 'Z1JH57GTYVMW6Q',
            '--change-batch', json.dumps(updateRequest, ensure_ascii=False)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    print out

def generatePublicHosts():
    services = queryServices()
    toHosts = lambda k, v: '{} {}.aws.mine'.format(v['PublicIpAddress'], k)
    for k, v in services.items():
        print toHosts(k, v)

def generatePrivateHosts():
    services = queryServices()
    toHosts = lambda k, v: '{} {}.aws.mine'.format(v['PrivateIpAddress'], k)
    for k, v in services.items():
        print toHosts(k, v)

def main():
    commands = {
            'query-services': printServices,
            'update-route53': updateRoute53,
            'generate-public-hosts': generatePublicHosts,
            'generate-private-hosts': generatePrivateHosts,
            'create-ami': createAmi,
            'list-unused-snapshots': listUnusedSnapshots,
            'delete-unused-snapshots': deleteUnusedSnapshots
        }

    opts, args = getopt.getopt(sys.argv[1:], 'h', ['help'])
    if len(args) == 0:
        print 'A command is required. {}'.format(commands.keys())
        sys.exit(1)

    cmd = args[0]
    if cmd not in commands:
        print 'Command {} was not defined.'.format(cmd)
        sys.exit(1)

    command = commands[cmd]
    arglen = command.__code__.co_argcount

    if arglen == 0:
        command()
    else:
        command(args[1])

if __name__ == "__main__":
    main()
