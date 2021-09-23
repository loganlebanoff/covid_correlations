import os
import requests
import json
import matplotlib.pyplot as plt
from tqdm import tqdm
import numpy as np
from scipy.stats.stats import pearsonr
from collections import defaultdict
from dotenv import load_dotenv
import datetime
import dateutil.parser
import streamlit as st

us_state_to_abbrev = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}
states = list(sorted(us_state_to_abbrev.values()))

earlier_start_date = datetime.date(2020, 3, 1)
start_date = datetime.date(2020, 4, 1)
end_date = datetime.date(2021, 9, 20)
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')

st.title('COVID-19 Correlation Explorer')
st.subheader('Find out what relationships exist between number of COVID cases and several other factors, including vaccination rate, temperature, and mask mandates among U.S. states.')

@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def load_data():

    load_dotenv()

    covidactnow_api_key = os.environ.get('COVID_ACTNOW_API_KEY')
    # VisualCrossingWebServices_api_key = os.environ.get('VisualCrossingWebServices_API_KEY')
    result = requests.get(f'https://api.covidactnow.org/v2/states.timeseries.json?apiKey={covidactnow_api_key}')
    data = result.json()


    # with open('data/covid_data.json', 'w') as f:
    #     json.dump(data, f, indent=2)

    vaccines_today = []
    temps = []
    date2temps = defaultdict(list)
    date2cases = defaultdict(list)
    date2vaccines = defaultdict(list)
    dates = [start_date + datetime.timedelta(days=x) for x in range((end_date-start_date).days + 1)]
    ealier_dates = [earlier_start_date + datetime.timedelta(days=x) for x in range((end_date-earlier_start_date).days + 1)]
    for row in data:
        state = row['state']
        if state not in us_state_to_abbrev.values():
            continue
        population = row['population']
        prev_vaccines = 0
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
                    if 'vaccinationsCompleted' in daterow and daterow['vaccinationsCompleted'] is not None:
                        vaccines = int(daterow['vaccinationsCompleted'])
                        vaccines = vaccines / population * 100000
                    else:
                        vaccines = prev_vaccines
                    prev_vaccines = vaccines
                    date2vaccines[date].append(vaccines)
                except:
                    print(daterow)
                    print(date)
                    print(state)
                    raise
        vaccines_today.append(row['actuals']['vaccinationsCompleted'] / population * 100000)


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

        with open('data/mask_mandate.tsv') as f:
            lines = f.read().splitlines()
        state2startmaskmandate = {}
        state2endmaskmandate = {}
        cur_state = None
        for line in lines:
            if '\t' in line:
                items = line.strip().split('\t')
                cur_state = items[0]
                start = items[1]
                end = items[2]
                if start == 'N/A':
                    start = datetime.date(1970, 1, 1)
                else:
                    start = dateutil.parser.parse(start).date()
                if end == 'N/A':
                    end = datetime.date(1970, 1, 1)
                elif end == 'Ongoing':
                    end = datetime.date.today()
                else:
                    end = dateutil.parser.parse(end).date()
                state2startmaskmandate[cur_state] = start
                state2endmaskmandate[cur_state] = end
        print(len(list(state2startmaskmandate.keys())))
        date2maskmandate = defaultdict(list)
        for state, start in state2startmaskmandate.items():
            end = state2endmaskmandate[state]
            for date in ealier_dates:
                if date >= start and date <= end:
                    date2maskmandate[date.strftime('%Y-%m-%d')].append(1)
                else:
                    date2maskmandate[date.strftime('%Y-%m-%d')].append(0)

    return dates, ealier_dates, date2temps, date2cases, date2maskmandate, date2vaccines, vaccines_today, states

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

dates, ealier_dates, date2temps, date2cases, date2maskmandate, date2vaccines, vaccines_today, states = load_data()



X_choices = {
    'Temperature-Cases Correlation': {
        'title': 'Temperature-Cases Correlation',
        'x_label': 'Temperature (°F)',
        'date': 'delayed',
        'var': date2temps,
        'correlations': [],
        'p_values': [],
        'values': [],
    },
    'Total Vaccines Administered-Cases Correlation': {
        'title': 'Total Vaccines Administered-Cases Correlation',
        'x_label': 'Vaccines',
        'date': 'delayed',
        'var': date2vaccines,
        'correlations': [],
        'p_values': [],
        'values': [],
    },
    'Total Vaccines Administered (Numbers Reported Right Now)-Cases Correlation': {
        'title': 'Total Vaccines Administered (Numbers Reported Right Now)-Cases Correlation',
        'x_label': 'Vaccines',
        'date': 'none',
        'var': vaccines_today,
        'correlations': [],
        'p_values': [],
        'values': [],
    },
    'Mask Mandate-Cases Correlation': {
        'title': 'Mask Mandate-Cases Correlation',
        'x_label': 'Has Mask Mandate (1 if yes, 0 if no)',
        'date': 'delayed',
        'var': date2maskmandate,
        'correlations': [],
        'p_values': [],
        'values': [],
    }
}

footer_text = 'Where did I get my data? Temperature information was taken from Visual Crossing Weather API (https://www.visualcrossing.com/weather-api). I used a 14-day rolling average for temperature. COVID cases and vaccinations were taken from COVID Act Now API (https://covidactnow.org/). I used 7-day rolling average for cases, while vaccinations were the total number of people fully-vaccinated at that point in time. Both cases and vaccinations were per 100k population in that state. Mask Mandate information was taken from Start Date and End Date found in this table: https://en.wikipedia.org/wiki/Face_masks_during_the_COVID-19_pandemic_in_the_United_States#Summary_of_orders_and_recommendations_issued_by_states. Source code is here: https://github.com/loganlebanoff/covid_correlations. Created by Logan Lebanoff. Contact me at loganlebanoff@gmail.com if you have any suggestions or other correlations you would like to see.'
hide_menu = """
<style>
footer:before{
    content:'%s';
    display:block;
    position:relative;
}
</style>
""" % (footer_text)
st.markdown(hide_menu, unsafe_allow_html=True)

selected_X_keys = st.sidebar.multiselect('Select data:', X_choices.keys(), ['Temperature-Cases Correlation'])
mode = st.sidebar.selectbox('Correlation at single date or Correlation over time', ['Single date correlation', 'Correlation over time'], help='See correlation at a specific date, or see how correlation has changed over time during the entire pandemic.')
delay = st.sidebar.slider('# Days to delay', 0, 30, 0, help='For example, if you think there may be a 14-day delay between the start of a mask mandate and a corresponding reduction in COVID cases, then set this to 14')
if mode == 'Single date correlation':
    selected_date = st.sidebar.slider('Date', start_date, end_date, value=end_date, step=datetime.timedelta(days=1))
    dates = [selected_date]
if mode == 'Correlation over time':
    show_pvalues = st.sidebar.checkbox('Show P-Values', False, help='A low p-value (p < 0.05) indicates the correlation is not likely due to mere chance')

X = [X_choices[k] for k in selected_X_keys]

us_cases = []
all_corrs = []
all_ps = []
for date in dates:
    date_str = date.strftime('%Y-%m-%d')
    delayed_date_str = (date + datetime.timedelta(days=-delay)).strftime('%Y-%m-%d')
    cases = date2cases[date_str]
    us_cases.append(np.mean(cases))

    for x in X:
        if x['date'] == 'delayed':
            x_values = x['var'][delayed_date_str]
        elif x['date'] == 'current':
            x_values = x['var'][date_str]
        elif x['date'] == 'none':
            x_values = x['var']
        if len(x_values) != len(cases):
            print(x_values)
            print(cases)
            print(delayed_date_str)
            print(date2maskmandate[delayed_date_str])
        corr, p = pearsonr(x_values, cases)
        if np.isnan(corr):
            corr = 0
            p = 0
        x['correlations'].append(corr)
        x['p_values'].append(p)
        x['values'].append(x_values)


for x in X:
    if mode == 'Single date correlation':
        values = x['values'][0]
        print(values)
        fig, ax1 = plt.subplots()
        ax1.set_title(x['title'])
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.05, 0.95, "Pearson Correlation: {:.4f}\nP-Value: {:.6f}".format(x['correlations'][0], x['p_values'][0]), verticalalignment='top', bbox=props, transform=ax1.transAxes)
        ax1.scatter(values, cases, color='blue')
        ax1.set_xlabel(x['x_label'])
        ax1.set_ylabel('Daily Cases per 100k')
        print(np.unique(values))
        print(cases)
        best_fit_x = list(np.unique(values))
        if len(best_fit_x) > 1:
            best_fit_y = np.poly1d(np.polyfit(values, cases, 1))(np.unique(values))
            ax1.plot(best_fit_x, best_fit_y, color='blue')
        for val, case, state in zip(values, cases, states):
            ax1.annotate(state, (val, case), color='blue')
        st.write(fig)
    else:
        correlations = np.array(x['correlations'])
        fig1, ax1 = plt.subplots()
        ax1.set_title(x['title'])
        ax1.set_ylabel('Correlation/P-Value')
        ax1.plot(dates, correlations, label='Pearson Correlations', color='black')
        if show_pvalues:
            line, = ax1.plot(dates, x['p_values'], label='P-Values', linestyle='dashed', color='gray')
        plt.xticks(rotation=90)
        ax1.legend()
        ax1.fill_between(dates, correlations, 0, where=correlations > 0, interpolate=True, color='red', alpha=0.3)
        ax1.fill_between(dates, correlations, 0, where=correlations < 0, interpolate=True, color='blue', alpha=0.3)
        st.write(fig1)

if mode != 'Single date correlation':
    fig3, ax3 = plt.subplots()
    ax3.set_title('US cases')
    ax3.set_ylabel('Daily Cases per 100k')
    ax3.plot(dates, us_cases, label='US Cases per 100k')
    plt.xticks(rotation=90)
    ax3.axvspan(datetime.date(2020, 4, 1), datetime.date(2020, 6, 1),
               label="1st Wave", color="green", alpha=0.1)
    ax3.axvspan(datetime.date(2020, 6, 1), datetime.date(2020, 9, 1),
               label="2nd Wave", color="blue", alpha=0.1)
    ax3.axvspan(datetime.date(2020, 9, 1), datetime.date(2021, 3, 15),
               label="3rd Wave", color="red", alpha=0.1)
    ax3.axvspan(datetime.date(2021, 3, 15), datetime.date(2021, 6, 15),
               label="4th Wave?", color="orange", alpha=0.1)
    ax3.axvspan(datetime.date(2021, 6, 15), datetime.date(2021, 9, 20),
               label="5th Wave", color="purple", alpha=0.1)
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