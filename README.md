# Welcome
`socrata` command for Splunk allows import of datasets found on https://opendata.socrata.com and http://www.opendatanetwork.com directly into Splunk for further processing and analysis. Gain instant access to thousands unique data sets!

This project is hosted on GitHub, see https://github.com/hire-vladimir/SA-socrata

# Install
App installation is simple, and only needs to be present on the search head. Documentation around app installation can be found at http://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall

# Getting Started
socrata offers many open and private datasets; some can be accessed anonymously, while others will require an API key. More information regarding finding datasets and obtaining the socrata API key can be found at https://dev.socrata.com/consumers/getting-started.html#throttling-and-application-tokens

*Note:* If a particular static/historic dataset is used in search, it is suggested to create a saved search that will run on a set interval of time, such that outputs of `socrata` command will output to a CSV file to be used as lookup.

## Screenshot
![socrata command for splunk example](https://raw.githubusercontent.com/hire-vladimir/SA-socrata/master/static/screenshot.png)

## System requirements
The command was tested on Splunk 6.3+ on CentOS Linux 7.1. Splunk python is used, without other dependencies, therefore command *should* work on other Splunk supported platforms.

## Command syntax
`socrata (<options>)* (<auth_key>)? <socrata_api_endpoint>`

The **socrata_api_endpoint** can be represented in two different ways:
* Direct API endpoint, such as ```https://opendata.socrata.com/resource/e2xy-undq.json```
* If the endpoint is hosted at *opendata.socrata.com*, it can be referred to by the dataset ID as `e2xy-undq`

Instructions on locating API endpoint is outlined at https://dev.socrata.com/consumers/getting-started.html#finding-your-api-endpoint

## Command arguments (optional)
Command implements arguments listed below. There are two types of arguments for this command, **debug**, **metadata**, **append** that are unique to the command, rest are *SODA API* supported arguments; see full description and usage detail at https://dev.socrata.com/consumers/getting-started.html

```debug=<bool> | append=<bool> | metadata=<bool> | auth_token=<socrata_auth_token> | limit=<int> | offset=<int> | select=<SoQL_select_clause> | where=<SoQL_where_clause> | order=<SoQL_order_by_clause> | group=<SoQL_group_by_clause> | q=<SoQL_clause> | query=<SoQL_clause>```

* **debug** - enables verbose logging to socrata.log, see troubleshooting section. defaults false.
* **metadata** - returns metadata about the dataset. defaults *false*
* **append** - if set to *true*, the data returned is appended to the current set of results rather than replacing it. defaults *false*
* **auth_token** - socrata app token, see https://dev.socrata.com/consumers/getting-started.html#throttling-and-application-tokens
* **limit** - limits the number of rows returned. **note:** socrata default limit is set to **1,000** rows. see https://dev.socrata.com/docs/queries/limit.html
* **offset** - see https://dev.socrata.com/docs/paging.html
* **select** - see https://dev.socrata.com/docs/queries/select.html
* **where** - see https://dev.socrata.com/docs/queries/where.html and https://dev.socrata.com/docs/functions/
* **order** - see https://dev.socrata.com/docs/queries/order.html
* **group** - see https://dev.socrata.com/docs/queries/group.html
* **q** - see https://dev.socrata.com/docs/queries/q.html
* **query** - see https://dev.socrata.com/docs/queries/query.html


## Examples
* Will pull down "Precipitation RadNet Laboratory Analysis" dataset, https://opendata.socrata.com/Government/Precipitation-RadNet-Laboratory-Analysis/e2xy-undq using socrata auth_token of XXXXXXXXXXXXXXXXXXXX; auth_token option overwrites the default configured key.
```
... | socrata auth_token=XXXXXXXXXXXXXXXXXXXX https://opendata.socrata.com/resource/cf4r-dfwe.json
```
* Will pull down "Food Inspections in Chicago" dataset, filtering to failed restaurant inspections with violations containing keyword "rodent" with row limit of 50,000
```
... | socrata limit=50000 https://data.cityofchicago.org/resource/4ijn-s7e5.json where="results='Fail' AND facility_type='Restaurant' AND contains(violations, 'rodent')"
```
* Using metadata option will return dataset metadata information as described on https://data.cityofchicago.org for list of locations in NE Illinois, NW Indiana, and SE Wisconsin where alternative vehicle fuels are available.
```
... | socrata metadata=true https://data.cityofchicago.org/resource/f7f2-ggz5.json
```
* Using the debug option will enable additional logging on the command to help troubleshoot data set pulls. See troubleshooting section.
```
... | socrata debug=1 https://data.cityofchicago.org/resource/f7f2-ggz5.json
```
* It is also possible to pass in Splunk variables from previously executed commands. This example will store WHERE filter clause in a variable to be passed to the socrata command, then write output to CSV file.
```
| localop | stats count | eval my_where="material_family = 'Hazardous Material'" | socrata limit=20000 https://data.ny.gov/resource/dzn2-x287.json where=my_where | outputlookup inputlookup_ny_state_spills.csv
```
* Graph food inspection failures in Chicago area restaurants involving rodents by risk (screenshot example)
```
| socrata https://data.cityofchicago.org/resource/4ijn-s7e5.json where="results='Fail' AND facility_type='Restaurant' AND contains(violations, 'rodent')"
| makemv delim="|" violations | eval entity=dba_name." (". license_ . ")"
| geostats latfield=location_latitude longfield=location_longitude dc(entity) by risk
```

# Troubleshooting
This command writes log data to *$SPLUNK_HOME/var/log/splunk/socrata.log*, meaning that data is also ingested into Splunk. Magic, I know. Try searching:
```
index=_internal sourcetype=socrata
```

When debug level logging is required, pass in *debug=true* or *debug=1* argument to the command. This will display enhanced logging in Splunk UI and the log file.
```
... | socrata debug=1 e2xy-undq
```

# Legal
* *socrata* is a registered trademark of socrata.com.
* *Splunk* is a registered trademark of Splunk, Inc.
