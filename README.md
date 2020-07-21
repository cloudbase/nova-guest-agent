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
docker run -h=`hostname` --network host -v /etc/nova-guest:/etc/nova-guest:ro -v nova_guest_api_logs:/var/log/nova-guest:rw -d --name nova_guest_api docker.example.com/nova-guest-api:latest
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
docker run -h=`hostname` --network host -v /run:/run:shared -v /etc/nova-guest:/etc/nova-guest:ro -v nova_guest_agent_logs:/var/log/nova-guest:rw -d --name nova_guest_agent docker.example.com/nova-guest-agent:latest
```

The ```/run``` volume is needed in order to give the ```nova_guest_agent``` container access to ```libvirt```.