# Nova Guest Integration

This project aims to add functionality  ```qemu-guest-agent```.


## Building the docker containers

```bash
docker build --file Dockerfile-agent -t docker.example.com/nova-guest-agent:latest .
docker build --file Dockerfile-api -t docker.example.com/nova-guest-api:latest .
```

## Deploying nova-guest-api

This component usually gets deployed on one of the controller nodes.

Create a folder for the config files

```bash
mkdir /etc/nova-guest
```

Create a volume for logs

```bash
docker volume create nova_guest_api_logs
```

Create the configs for the API service

```bash
cp nova-guest/etc/api-paste.ini /etc/nova-guest
cp nova-guest/etc/nova-guest.conf /etc/nova-guest
```

Edit the ```nova-guest.conf``` file to suit your environment.

Deploy the container

```bash
docker run -h=`hostname` --network host -v /etc/nova-guest:/etc/nova-guest:ro \
    -v nova_guest_api_logs:/var/log/nova-guest:rw \
    -d --name nova_guest_api \
    docker.example.com/nova-guest-api:latest
```

## Deploy the nova-guest-agent container

This component must be run on the compute node itself. It is imperative that the ```host``` setting in the config file match the hostname advertised by the ```nova-compute``` service. Essentially, whatever value shows up in ```openstack hypervisor list``` for the compute node you are installing the agent on.

By default this is the hostname of the compute node itself.

Create a folder for the config files

```bash
mkdir /etc/nova-guest
```

Create a volume for logs

```bash
docker volume create nova_guest_agent_logs
```

Create the configs for the API service

```bash
cp nova-guest/etc/nova-guest.conf /etc/nova-guest
```

Edit the ```nova-guest.conf``` file to suit your environment.

Deploy the container

```bash
docker run -h=`hostname` --network host -v /run:/run:shared \
    -v /etc/nova-guest:/etc/nova-guest:ro \
    -v nova_guest_agent_logs:/var/log/nova-guest:rw \
    -d --name nova_guest_agent \
    docker.example.com/nova-guest-agent:latest
```

The ```/run``` volume is needed in order to give the ```nova_guest_agent``` container access to ```libvirt```.


## Create endpoints

We will need to create a new service type, then add the necessary endpoints. By default the service runs on port 4224.

Create the service.

```bash
openstack service create --name nova-guest --description "Nova guest agent integration" guest-agent
```

Add the endpoints:

```bash
openstack endpoint create --region RegionOne \
    guest-agent admin "http://192.168.100.4:4224/v1/%(tenant_id)s"
openstack endpoint create --region RegionOne \
    guest-agent internal "http://192.168.100.4:4224/v1/%(tenant_id)s"
openstack endpoint create --region RegionOne \
    guest-agent public "https://192.168.100.4:4224/v1/%(tenant_id)s"
```

## Using the API

Currently this agent only has one function. To apply networking config on an instance. For the purposes of this example, we will assume that the instance ID of the VM we are trying to apply networking for, is ```b6b4177b-3ca1-4d0f-a3a4-ad46d82a6f62```.

### Fetch keystone token

```bash
TOKEN=$(openstack token issue --format json | jq -r .id)
```

The ```TOKEN``` variable should now hold a valid keystone token we can use to authenticate against the guest agent API:

```bash
:~$ echo $TOKEN
gAAAAABfMUVpUyiPUHTgoO5oKJqh6-qcp_yTqpSWfwZIoQKNASGrlr4wwcOTYmUeI-LPFtU26pCRoI2zNbGGigeGRx96N2gaGS1wCovaBox-VPuEs0IYGROQjHoVJTwOKD_vM9GeoVppPCCWRQAQ7yz-FvxSb9tc86pkDk4_1VcZpWzlGRrsUYk
```

### Call apply networking

URI:

```
POST /v1/{PROJECT_ID}/networking/{INSTANCE_ID}/actions
```

Body:

```json
{
    "apply-networking": null
}
```

Example:

```bash
curl -g -i \
    -X POST http://192.168.100.4:4224/v1/f4edce581ecb4eaabbb68fea5fee5b81/networking/b6b4177b-3ca1-4d0f-a3a4-ad46d82a6f62/actions \
    -H "Content-Type: application/json" \
    -H "User-Agent: nova-guest keystoneauth1/4.2.0 python-requests/2.24.0 CPython/3.6.8" \
    -H "X-Auth-Token: $TOKEN" -d '{"apply-networking": null}'
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 176
X-Openstack-Request-Id: req-122e78dd-a61e-4294-9957-6d2ddbee674c
Date: Mon, 10 Aug 2020 13:02:53 GMT

{"apply-networking": {"success": true, "message": {"exited": true, "exitcode": 0, "signal": 0, "out-truncated": false, "err-truncated": false, "out-data": "", "err-data": ""}}}
```

## Important note

If the result is success, the output of the script executed inside the VM will be returned as part of the response. Take care not to mistakingly expose any sensitive information.
