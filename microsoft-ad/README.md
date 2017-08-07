1. Create Microsoft AD from AWS Console.
    - When it is created, a Security Group with its Directory ID is also created.
    - The created Security Group should be added to the Inbound list of the EC2 instance Security Group.
2. Copy Directory ID, something like 'd-xxxxxxxxxx'
3. Edit ssm-config.json with Directory ID and DNS addresses
4. Perform following commands to create an ssm document

    ```bash
    # Get existing document
    aws ssm get-document --region ap-northeast-1 --name "ad.config.aws.mine"
    
    # Delete if it exists
    aws ssm delete-document --region ap-northeast-1 --name "ad.config.aws.mine"
    
    # Create a new document
    aws ssm create-document --region ap-northeast-1 --content file://ssm-config.json --name "ad.config.aws.mine"
    ```
5. Start an EC2 instance
6. Associate the EC2 instance and the ssm document

    ```bash
    aws ssm create-association --region ap-northeast-1 --name "ad.config.aws.mine" --instance-id i-xxxxxxxxxxxxx
    ```

7. Login to the EC2 instance with local Administrator user via RDP
8. Open Network Connection `%SystemRoot%\system32\control.exe ncpa.cpl` to configure DNS
    - Be extremely careful NOT to disable the network! Operate your mouse very carefully!
    - Set Preferred DNS server and Alternate DNS server
9. Open System Properties `%SystemRoot%\system32\control.exe sysdm.cpl` to change domain
    - Click 'Change'
    - Specify 'aws.mine' to Domain under 'Member of'
    - Specify Admin and its password into the dialog
    - You should see 'Welcome to the aws.mine domain.' message
    - Click 'Restart Now'
    - TODO: Restart will take XX minutes, wait patiently
10. Once the instance gets ready, login from RDP as "aws.mine\Admin"

See AWS docs for detail.

http://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/ec2-join-aws-domain.html

To use a Spot Instance with AD, the instance needs to be added manually.
http://docs.aws.amazon.com/directoryservice/latest/admin-guide/join_windows_instance.html


