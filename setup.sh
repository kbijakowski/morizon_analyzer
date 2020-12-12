mkdir -p _influx_data
mkdir -p _morizon_analyzer_logs

docker run -p 127.0.0.1:8086:8086 --name=influx -e INFLUXDB_DB=db0 -e INFLUXDB_ADMIN_USER=admin -e INFLUXDB_ADMIN_PASSWORD=Serious@dmin333 -e INFLUXDB_USER=influx_user -e INFLUXDB_USER_PASSWORD=Str@ngeYe@r2020 -v $PWD/_influx_data:/var/lib/influxdb influxdb &
docker run -p 3000:3000 --name=grafana -d --name=grafana grafana/grafana
docker build . --tag morizon_analyzer

INFLUXDB_HOST=$(docker inspect --format '{{ .NetworkSettings.IPAddress }}' influx)
docker run -e INFLUXDB_HOST=$INFLUXDB_HOST -v $PWD/_morizon_analyzer_logs:/root/morizon_analyzer/logs morizon_analyzer
