import sys
import subprocess
import getopt
import json

serviceAmis = {'0.hdp': 'ami-9f3c64ff', '1.hdp': 'ami-783a6218', '2.hdp': 'ami-043b6364'}
amiServices = {v: k for k, v in serviceAmis.items()}

region = 'us-west-1'


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
    opts, args = getopt.getopt(sys.argv[1:], 'h', ['help'])
    if len(args) != 1:
        print 'A command is required.'
        sys.exit(1)

    cmd = args[0]
    if cmd == 'query-services':
        print json.dumps(queryServices(), ensure_ascii=False)
    elif cmd == 'update-route53':
        updateRoute53()
    elif cmd == 'generate-public-hosts':
        generatePublicHosts()
    elif cmd == 'generate-private-hosts':
        generatePrivateHosts()
    else:
        print 'Command {} was not defined.'.format(cmd)
        sys.exit(1)

if __name__ == "__main__":
    main()
