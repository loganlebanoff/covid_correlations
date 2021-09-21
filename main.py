import os
import requests
import json
import matplotlib.pyplot as plt
import csv
from tqdm import tqdm
import numpy as np
from scipy.stats.stats import pearsonr
import pickle
from dotenv import load_dotenv

load_dotenv()

covidactnow_api_key = os.environ.get('COVID_ACTNOW_API_KEY')
VisualCrossingWebServices_api_key = os.environ.get('VisualCrossingWebServices_API_KEY')
result = requests.get(f'https://api.covidactnow.org/v2/states.timeseries.json?apiKey={covidactnow_api_key}')
data = result.json()



# with open('data.json', 'w') as f:
#     json.dump(data, f, indent=2)

temp_date = '2021-08-04'
case_date = '2021-09-04'

states = []
vaccines = []
cases = []
temps = []
for row in data:
    state = row['state']
    if state == 'MP':
        continue
    states.append(state)
    population = row['population']
    if case_date:
        for daterow_idx, daterow in enumerate(row['actualsTimeseries']):
            if daterow['date'] == case_date:
                try:
                    today_cases = daterow['cases'] / population * 100000
                    lastweek_cases = row['actualsTimeseries'][daterow_idx-7]['cases'] / population * 100000
                    cases.append(today_cases - lastweek_cases)
                    break
                except:
                    import pdb;pdb.set_trace()
    else:
        cases.append(row['actuals']['newCases'] / population * 100000)
    vaccines.append(row['actuals']['vaccinationsCompleted'] / population * 100000)

temp_filename = 'temps_{}.pkl'.format(temp_date)
if os.path.exists(temp_filename):
    with open(temp_filename, 'rb') as f:
        temps = pickle.load(f)
else:
    for state in tqdm(states):
        result = requests.get(f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/weatherdata/history?&aggregateHours=24&startDateTime={temp_date}T00:00:00&endDateTime={temp_date}T00:00:00&unitGroup=us&contentType=csv&dayStartTime=0:0:00&dayEndTime=0:0:00&location={state},US&key={VisualCrossingWebServices_api_key}')
        reader = csv.reader(result.text.strip().splitlines(), delimiter=",", quotechar='"')
        header = next(reader, None)
        rows = []
        for line in reader:
            row = {header[item_idx]: item for item_idx, item in enumerate(line)}
            rows.append(row)
        temp = float(rows[0]['Temperature'])
        temps.append(temp)
    with open(temp_filename, 'wb') as f:
        pickle.dump(temps, f)

print(pearsonr(temps, cases))
print(pearsonr(vaccines, cases))

fig, ax1 = plt.subplots()
# plt.bar(states, vaccines)
ax1.scatter(temps, cases, color='blue')
ax1.plot(np.unique(temps), np.poly1d(np.polyfit(temps, cases, 1))(np.unique(temps)), color='blue')
for temp, case, state in zip(temps, cases, states):
    ax1.annotate(state, (temp, case), color='blue')
ax2 = ax1.twiny()
ax2.scatter(vaccines, cases, color='red')
ax2.plot(np.unique(vaccines), np.poly1d(np.polyfit(vaccines, cases, 1))(np.unique(vaccines)), color='red')
for vaccines, case, state in zip(vaccines, cases, states):
    ax2.annotate(state, (vaccines, case), color='red')
plt.show()

a=0