docker run -p 8086:8086 --name=influx -e INFLUXDB_DB=db0 -e INFLUXDB_ADMIN_USER=admin -e INFLUXDB_ADMIN_PASSWORD=admin -e INFLUXDB_USER=grafana -e INFLUXDB_USER_PASSWORD=6r@f@n@7 -v $PWD:/var/lib/influxdb influxdb &
docker run -p 3000:3000 --name=grafana -d --name=grafana grafana/grafana
