#!/bin/bash

Help()
{
   # Display Help
   echo "**************Help*****************"
   echo "Create VPC for matching engine demo."
   echo
   echo "Syntax: network_setup [-n|r|p|h]"
   echo "options:"
   echo "n      Network name"
   echo "r      Peering range name"
   echo "p      Project id"
   echo "h      Help"
   echo
}

while getopts ":n:r:p:h" flag
do
    case "${flag}" in
        n) network=${OPTARG};;
        r) peering_range_name=${OPTARG};;
        p) project_id=${OPTARG};;
        h) Help
           exit;;
    esac
done

echo "Using the following settings..."
echo "Network               $network"
echo "Peering range Name    $peering_range_name"
echo "Project id            $project_id"

if [ -z $network ] || [ -z $peering_range_name ] || [ -z $project_id ]
then
    Help
    exit
fi

gcloud compute networks create $network --bgp-routing-mode=regional

gcloud compute firewall-rules create $network-allow-icmp --network $network --priority 65534 --project $project_id --allow icmp

gcloud compute firewall-rules create $network-allow-internal --network $network --priority 65534 --project $project_id --allow all --source-ranges 10.128.0.0/9

gcloud compute firewall-rules create $network-allow-rdp --network $network --priority 65534 --project $project_id --allow tcp:3389

gcloud compute firewall-rules create $network-allow-ssh --network $network --priority 65534 --project $project_id --allow tcp:22

gcloud compute addresses create $peering_range_name --global --prefix-length=16 --network=$network --purpose=VPC_PEERING --project=$project_id --description="peering range for uCAIP."

gcloud services enable servicenetworking.googleapis.com --project=$project_id

gcloud services vpc-peerings connect --service=servicenetworking.googleapis.com --network=$network --ranges=$peering_range_name