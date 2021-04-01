

# Morizon analyzer

A docker enabled tool dedicated to tracking offers of real estates published in morizon.pl

## Features

The implementation supports 2 main features:

1) Long-term tracking and trend setting of:
    * average price
    * average price per squared meter
    * number of offers

    for real estates matchin given criteria.

2) Daily reports generartion (webpage with offer names, prices and links to details in morizon.pl)

## Implementation

The soultion has been implemented as a python script dedicated to be run (periodically) as docker container.
In general good idea is to schedule this for the end of each day using cron.

To gather and process results in a convenient way 2 additional docker containers may be run:
* InfluxDB (to store results)
* Grafana (to visualize results)

## Prerequisites

* Docker (tested with 20.10.5 version)
* Docker compose (tested with 1.28.6 version)

## Run

1) Adjust config file

    Make changes to `config.yaml` file to select thing which you would like to track.
    File structure is:

    * `influx` - section containing credentials used to connect to InfluxDB (these may be overridden also using environmental variables: `INFLUXDB_HOST`, `INFLUXDB_PORT`, `INFLUXDB_DB`)
    * `queries` - description about what to fetch - consists of two main sections:
        * `analytics` - list of dictionaries containing criteria about Morizon offers for which prices will be tracked. Supported keys are:
            * `city` - name of the city
            * `district` - name of the district
            * `filter_price_from` - lower boundary for price - values:
                * 244 - *apartamentowiec*
                * 245 - *blok*
                * 246 - *dom wielorodzinny*
                * 247 - *kamienica*
            * `filter_price_to` - upper boundary for price
            * `filter_dict_building_type` - type of the building
            * `filter_living_area_from` - lower boundary for living area (in squared meters)
            * `filter_number_of_rooms_from` - lower boundary for number of rooms
            * `filter_date_filter` - period of time from offer publication (in days) - Morizon standard values: *1*, *3*, *7*, *30*, *90*, *180*
            * `filter_floor_from` - lower boundary for floor number
            * `filter_with_price` - it true include select offers with price only
        * `reporting` - list of dictionaries containing criteria about Morizon offers for which reports will be generated. The same format like for *analytics*.


2) Create all containers using docker compose (also Morizon Analyzer image will be built)

    ```
        docker-compose up
    ```


3) Configure periodic run of Morizon Analyzer to enable dayli data gathering

    open:

    ```
        crontab -e
    ```
    
    and type in:

    ```
        50 23 * * * docker run --network morizon_analyzer_network --rm -e INFLUXDB_HOST="192.168.254.2" -v $PWD/data/reports:/morizon_analyzer/data/reports morizon_analyzer

    ```

    than save and close editor.
    Morizon Analyzer docker container will be run each 23:50 day to collect information about prices and generate daily report.


## Check running service

By running:

```
    docker ps
```

you should see 3 containers running:

```
dd874a08f3a2        httpd:2.4                   "httpd-foreground"       6 days ago          Up 3 days           0.0.0.0:3001->80/tcp       morizon_analyzer_reports_server
ab3310258880        grafana/grafana:latest      "/run.sh"                6 days ago          Up 29 hours         0.0.0.0:3000->3000/tcp     morizon_analyzer_grafana
328a4c84f665        influxdb:1.8.3              "/entrypoint.sh infl…"   6 days ago          Up 3 days           127.0.0.1:8086->8086/tcp   morizon_analyzer_influx
```

(container `morizon_analyzer` will be run only for few seconds to gather data, publish results to InfluxDB and generate report)

Grafana dashboard should be available on:

```
    127.0.0.1:3000
```

Reports should be available on:

```
    127.0.0.1:3001
```


## Configure Grafana

1. Open Grafana dashboard in browser

   ```
      127.0.0.1:3000
   ```

   Login with username: ***admin*** and login: ***admin***.
   You will be asked about credentials change.
   Type new password and continue.

2. Configure InfluxDB datasource

   From menu bar on the left side choose *Configuration* option (second button from the bottom) and then *Data source*.
   Click *Add data source* button on the opened page.
   Select *InfluxDB*.
   Type *URL*: ***http://192.168.254.2:8086*** and *Database*: ***db0*** then click *Save & Test* - Grafana will try to contact InfluxDB - 
   you will be informed about result of this operation.

3. Import dashboards

   From menu bar on the left side choose *Create* option (second button from the top) and then *Import*.
   In new page click on *Upload JSON file* choose one of JSON files located in *grafana* directory, then click *OK*.
   Repeat for the rest of JSON files in *grafana* directory.

4. Enjoy :)

![](https://user-images.githubusercontent.com/20417307/113344354-3e219180-9331-11eb-8756-bd91ad4658cd.png)

![](https://user-images.githubusercontent.com/20417307/113344355-3f52be80-9331-11eb-96e4-ce0ec4839fdb.png)
