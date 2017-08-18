#!/bin/sh

# Stop Atlas
curl -H "X-Requested-By: ambari" -XPUT -d '{"ServiceInfo": {"state": "INSTALLED"}}' http://admin:admin@0.hdpf.aws.mine:8080/api/v1/clusters/HDPF/services/ATLAS


# Delete Solr indices
for i in edge_index fulltext_index vertex_index
do
  curl -i "0.hdpf.aws.mine:8886/solr/admin/collections?action=DELETE&name=$i"
done

# Delete Kafka topic
KAFKA_HOME=/usr/hdp/current/kafka-broker
$KAFKA_HOME/bin/kafka-topics.sh --zookeeper 0.hdpf.aws.mine:2181 --delete --topic ATLAS_ENTITIES
$KAFKA_HOME/bin/kafka-topics.sh --zookeeper 0.hdpf.aws.mine:2181 --delete --topic ATLAS_HOOK


# Drop Hbase table
/usr/hdp/current/hbase-client/bin/hbase shell drop-habase-tables.txt

# Start Atlas
curl -H "X-Requested-By: ambari" -XPUT -d '{"ServiceInfo": {"state": "STARTED"}}' http://admin:admin@0.hdpf.aws.mine:8080/api/v1/clusters/HDPF/services/ATLAS

