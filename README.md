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

## Run

1) Adjust config file and environmental variables

```
TODO
```

2) Build docker image

```
TODO
```

3) Run InfluxDB container

```
TODO
```

4) Run Grafana container

```
TODO
```

5) Schedule Morizon analyzer run

```
TODO
```

## Processing results

TODO
