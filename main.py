import os
import requests
import json
import matplotlib.pyplot as plt
import csv
from tqdm import tqdm
import numpy as np
from scipy.stats.stats import pearsonr
import pickle
from collections import defaultdict
from dotenv import load_dotenv
import datetime
import streamlit as st

@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def load_data():

    load_dotenv()

    covidactnow_api_key = os.environ.get('COVID_ACTNOW_API_KEY')
    VisualCrossingWebServices_api_key = os.environ.get('VisualCrossingWebServices_API_KEY')
    result = requests.get(f'https://api.covidactnow.org/v2/states.timeseries.json?apiKey={covidactnow_api_key}')
    data = result.json()

    start_date = datetime.date(2020, 4, 1)
    end_date = datetime.date(2021, 9, 20)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')


    # with open('data.json', 'w') as f:
    #     json.dump(data, f, indent=2)

    states = []
    vaccines = []
    temps = []
    date2temps = defaultdict(list)
    date2cases = defaultdict(list)
    dates = [start_date + datetime.timedelta(days=x) for x in range((end_date-start_date).days + 1)]
    for row in data:
        state = row['state']
        if state == 'MP':
            continue
        states.append(state)
        population = row['population']
        for daterow_idx, daterow in enumerate(row['actualsTimeseries']):
            cases = []
            if daterow_idx >= 7:
                try:
                    date = daterow['date']
                    today_cases = daterow['cases']
                    if today_cases is None:
                        cases = 0
                    else:
                        today_cases = today_cases / population * 100000
                        lastweek_cases = row['actualsTimeseries'][daterow_idx-7]['cases']
                        if lastweek_cases is None:
                            lastweek_cases = 0
                        else:
                            lastweek_cases = lastweek_cases / population * 100000
                        cases = today_cases - lastweek_cases
                    date2cases[date].append(cases)
                except:
                    print(daterow)
                    print(date)
                    print(state)
                    raise
        vaccines.append(row['actuals']['vaccinationsCompleted'] / population * 100000)


    for state_idx, state in enumerate(tqdm(states)):
        with open(os.path.join('data', 'temp', state + '.json')) as f:
            temp_data = json.load(f)
        past_7_days = []
        for row in temp_data:
            date = row['Date time'].replace('/', '-')
            date = datetime.datetime.strptime(date, '%m-%d-%Y').date().strftime('%Y-%m-%d')
            temp = float(row['Temperature'])
            if len(past_7_days) >= 14:
                past_7_days = past_7_days[1:]
            past_7_days.append(temp)
            ave_temp = np.mean(past_7_days)
            date2temps[date].append(ave_temp)

    return dates, date2temps, date2cases, vaccines, states

    # temp_filename = 'temps_{}.pkl'.format(temp_date)
    # if os.path.exists(temp_filename):
    # with open(temp_filename, 'rb') as f:
    #     temps = pickle.load(f)
    # else:

    # files = os.listdir(os.path.join('data', 'temp'))
    # for file in files:
    #     os.rename(os.path.join('data', 'temp', file), os.path.join('data', 'temp', file.split('_')[0] + '.json'))
    #
    # start_temp_date = '2020-03-01'
    # end_temp_date = '2021-09-20'
    # # states = ['FL']
    # for state in tqdm(states):
    #
    #     # result = requests.get(f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/weatherdata/history?&aggregateHours=24&startDateTime={temp_date}T00:00:00&endDateTime={temp_date}T00:00:00&unitGroup=us&contentType=csv&dayStartTime=0:0:00&dayEndTime=0:0:00&location={state},US&key={VisualCrossingWebServices_api_key}')
    #
    #     result = requests.get(f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/weatherdata/history?&aggregateHours=24&startDateTime={start_temp_date}T00:00:00&endDateTime={end_temp_date}T00:00:00&unitGroup=us&contentType=csv&dayStartTime=0:0:00&dayEndTime=0:0:00&location={state},US&key={VisualCrossingWebServices_api_key}')
    #     reader = csv.reader(result.text.strip().splitlines(), delimiter=",", quotechar='"')
    #     header = next(reader, None)
    #     rows = []
    #     for line in reader:
    #         row = {header[item_idx]: item for item_idx, item in enumerate(line)}
    #         rows.append(row)
    #     temp_filename = os.path.join('data', 'temp', '{}_{}_{}.json'.format(state, start_temp_date, end_temp_date))
    #     with open(temp_filename, 'w') as f:
    #         json.dump(rows, f, indent=2)

dates, date2temps, date2cases, vaccines, states = load_data()

delay = st.slider('Days Delay', 0, 30, 0)

corrs_temp = []
ps_temp = []
corrs_vacc = []
ps_vacc = []
us_cases = []
for date in dates:
    date_str = date.strftime('%Y-%m-%d')
    delayed_date_str = (date + datetime.timedelta(days=-delay)).strftime('%Y-%m-%d')
    cases = date2cases[date_str]
    temps = date2temps[delayed_date_str]
    us_cases.append(np.mean(cases))

    corr_temp, p_temp = pearsonr(temps, cases)
    corr_vacc, p_vacc = pearsonr(vaccines, cases)
    corrs_temp.append(corr_temp)
    ps_temp.append(p_temp)
    corrs_vacc.append(corr_vacc)
    ps_vacc.append(p_vacc)

fig1, ax1 = plt.subplots()
line, = ax1.plot(dates, ps_temp, label='p_temp', linestyle='dashed')
ax1.plot(dates, corrs_temp, label='corrs_temp')
plt.xticks(rotation=90)
ax1.legend()
st.write(fig1)


fig2, ax2 = plt.subplots()
ax2.plot(dates, ps_vacc, label='p_vacc', linestyle='dashed')
ax2.plot(dates, corrs_vacc, label='corrs_vacc')
plt.xticks(rotation=90)
ax2.legend()
st.write(fig2)


fig3, ax3 = plt.subplots()
ax3.plot(dates, us_cases, label='us_cases')
plt.xticks(rotation=90)
ax3.legend()
st.write(fig3)

# st.line_chart(
#     {
#         'Temperature-cases correlations': corrs_temp,
#         'Temperature-cases p-values': ps_temp,
#         # 'US Cases': us_cases,
#     }
# )
#
# st.line_chart(
#     {
#         'Vaccination-cases correlations': corrs_vacc,
#         'Vaccination-cases p-values': ps_vacc,
#         # 'US Cases': us_cases,
#     }
# )

# fig, ax1 = plt.subplots()
# ax1.plot(dates, corrs_temp, label='corrs_temp')
# ax1.plot(dates, ps_temp, label='p_temp')
# ax1.plot(dates, corrs_vacc, label='corrs_vacc')
# ax1.plot(dates, ps_vacc, label='p_vacc')
# ax1.legend()
# plt.show()

# fig, ax1 = plt.subplots()
# # plt.bar(states, vaccines)
# ax1.scatter(temps, cases, color='blue')
# ax1.plot(np.unique(temps), np.poly1d(np.polyfit(temps, cases, 1))(np.unique(temps)), color='blue')
# for temp, case, state in zip(temps, cases, states):
#     ax1.annotate(state, (temp, case), color='blue')
# ax2 = ax1.twiny()
# ax2.scatter(vaccines, cases, color='red')
# ax2.plot(np.unique(vaccines), np.poly1d(np.polyfit(vaccines, cases, 1))(np.unique(vaccines)), color='red')
# for vaccines, case, state in zip(vaccines, cases, states):
#     ax2.annotate(state, (vaccines, case), color='red')
# plt.show()

a=0