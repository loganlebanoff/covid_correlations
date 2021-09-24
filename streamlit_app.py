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
from matplotlib.offsetbox import (TextArea, DrawingArea, OffsetImage,
                                  AnnotationBbox)
import textwrap

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
st.markdown('Look at examples below, or change the options in the left sidebar by clicking on the "**>**" arrow.')

def get_row_value(daterow, row, population, daterow_idx, field):
    today_cases = daterow[field]
    if today_cases is None:
        cases = 0
    else:
        today_cases = today_cases / population * 100000
        lastweek_cases = row['actualsTimeseries'][daterow_idx-7][field]
        if lastweek_cases is None:
            lastweek_cases = 0
        else:
            lastweek_cases = lastweek_cases / population * 100000
        cases = today_cases - lastweek_cases
    return cases

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
    date2deaths = defaultdict(list)
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
            if daterow_idx >= 7:
                try:
                    date = daterow['date']
                    cases = get_row_value(daterow, row, population, daterow_idx, 'cases')
                    date2cases[date].append(cases)
                    deaths = get_row_value(daterow, row, population, daterow_idx, 'deaths')
                    date2deaths[date].append(deaths)
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
    date2maskmandate = defaultdict(list)
    for state, start in state2startmaskmandate.items():
        end = state2endmaskmandate[state]
        for date in ealier_dates:
            if date >= start and date <= end:
                date2maskmandate[date.strftime('%Y-%m-%d')].append(1)
            else:
                date2maskmandate[date.strftime('%Y-%m-%d')].append(0)

    with open('data/political_party.tsv') as f:
        lines = f.read().splitlines()
    political_tuples = []
    for line in lines:
        items = line.strip().split('\t')
        state = us_state_to_abbrev[items[0]]
        dem_leaning = int(items[3])
        political_tuples.append((state, dem_leaning))
    politicals = []
    for state, dem_leaning in sorted(political_tuples):
        politicals.append(dem_leaning)

    with open('data/age.tsv') as f:
        lines = f.read().splitlines()
    age_tuples = []
    for line in lines:
        items = line.strip().split('\t')
        if items[1].strip() not in us_state_to_abbrev:
            continue
        state = us_state_to_abbrev[items[1].strip()]
        age = float(items[2])
        age_tuples.append((state, age))
    ages = []
    for state, age in sorted(age_tuples):
        ages.append(age)



    return dates, ealier_dates, date2temps, date2cases, date2deaths, date2maskmandate, date2vaccines, vaccines_today, politicals, ages, states

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


dates, ealier_dates, date2temps, date2cases, date2deaths, date2maskmandate, date2vaccines, vaccines_today, politicals, ages, states = load_data()



X_choices = {
    'Temperature': {
        'title': 'Temperature',
        'x_label': 'State Temperature (°F)',
        'date': 'delayed',
        'var': date2temps,
        'correlations': [],
        'p_values': [],
        'values': [],
        'caption': 'Positive correlation shows that more cases happen in hot states. Negative correlation shows that more cases happen in cold states. There seems to be an interesting pattern that there is a positive correlation during the summer (hotter states have more cases), and negative during the winter (colder states have more cases). Temperature information was taken from Visual Crossing Weather API (https://www.visualcrossing.com/weather-api). I used a 14-day rolling average for daily temperature.',
    },
    'Vaccinations Completed': {
        'title': 'Vaccinations Completed',
        'x_label': 'State Vaccines Completed',
        'date': 'delayed',
        'var': date2vaccines,
        'correlations': [],
        'p_values': [],
        'values': [],
        'caption': 'Vaccinations are based on how many people were fully-vaccinated at that point in time. We would expect to see a negative correlation as more vaccines are administered, which is what we do see.',
    },
    'Vaccinations Completed (Numbers Reported Right Now)': {
        'title': 'Vaccinations Completed (Numbers Reported Right Now)',
        'x_label': 'State Vaccines Completed',
        'date': 'none',
        'var': vaccines_today,
        'correlations': [],
        'p_values': [],
        'values': [],
        'caption': 'Vaccinations are based on how many people are currently fully-vaccinated right now. This is to see if there are possible spurious correlations based on vaccinations. For example, you can see that right now, there is a strong negative correlation between vaccinations and cases, which is in support of vaccinating. However, the same correlation exists between TODAY\'S vaccination rate and SEPTEMBER OF LAST YEAR\'S cases, which is obviously a spurious correlation since today\'s vaccinations couldn\'t possible have had an effect on last year\'s case numbers. Vaccinations likely do have a large causal effect, but there is clearly another underlying cause leading to the correlation for last year.',
    },
    'Mask Mandate': {
        'title': 'Mask Mandate',
        'x_label': 'State Has Mask Mandate (1 if yes, 0 if no)',
        'date': 'delayed',
        'var': date2maskmandate,
        'correlations': [],
        'p_values': [],
        'values': [],
        'caption': 'Mask mandates do not seem to show a strong correlation with case numbers. Mask Mandate information was taken from Start Date and End Date found in this table: https://en.wikipedia.org/wiki/Face_masks_during_the_COVID-19_pandemic_in_the_United_States#Summary_of_orders_and_recommendations_issued_by_states. It is coarse and not very accurate.'
    },
    'Political Leaning': {
        'title': 'State Political Leaning by Democratic Advantage',
        'x_label': 'Democratic Advantage (%)',
        'date': 'none',
        'var': politicals,
        'correlations': [],
        'p_values': [],
        'values': [],
        'caption': 'Political Leaning information is based on how many percentage points that the Democratic party has over the Republican party, and was taken from a Gallup 2017 poll: https://news.gallup.com/poll/226643/2017-party-affiliation-state.aspx.'
    },
    'Median Age': {
        'title': 'State Median Age',
        'x_label': 'Median Age (years)',
        'date': 'none',
        'var': ages,
        'correlations': [],
        'p_values': [],
        'values': [],
        'caption': 'Age information taken from https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_median_age'
    }
}

Y_choices = {
    'Cases': {
        'title': 'Cases',
        'y_label': 'Daily Cases per 100k',
        'var': date2cases,
    },
    'Deaths': {
        'title': 'Deaths',
        'y_label': 'Daily Deaths per 100k',
        'var': date2deaths,
    },
}

example_options = {
    'Cold States': {
        'annotations': [
            {
                'annotation_text' : '''The line is pointing down, which is a negative correlation. In this case, that means states that are cold happen to have more COVID cases than warmer states.''',
                'xy': (85, 300),
                'textxy': (95, 500),
            }
        ],
        'X' : ['Temperature'],
        'Y': 0,
        'mode': 0,
        'date': end_date,
        'delay': 0,
        'p': False,
    },
    'Hot States': {
        'annotations': [
            {
                'annotation_text' : '''If we change the date to July 20, just 2 months in the past, then we see a positive correlation (states that are hot happen to have more COVID cases than colder states.''',
                'xy': (90, 120),
                'textxy': (95, 230),
                'color': '#ffdd80'
            }
        ],
        'X' : ['Temperature'],
        'Y': 0,
        'mode': 0,
        'date': datetime.date(2021, 7, 20),
        'delay': 0,
        'p': False,
    },
    'Temperature Correlation Over Time': {
        'annotations': [
            {
                'annotation_text' : '''''',
                'xy': (end_date, -0.2),
                'textxy': (end_date, -0.6),
            },
            {
                'annotation_text' : 'If we look at Correlation Over Time, then we see the same two phenomena at the same time, and we can see how the correlation changes over time.',
                'xy': (datetime.date(2021, 7, 17), 0.28),
                'textxy': (datetime.date(2021, 1, 1), 0.4),
                'color': '#ffdd80',
            },
            {
                'annotation_text' : 'Interestingly, it seems to follow the pattern that hot states get more cases in the summer (so people gather inside in those states), and cold states get more cases in the winter (again, so people gather inside).',
                'xy': (datetime.date(2020, 10, 15), -0.5),
                'textxy': (datetime.date(2020, 4, 1), -0.5),
            },
            {
                'annotation_text' : '',
                'xy': (datetime.date(2020, 7, 15), 0),
                'textxy': (datetime.date(2020, 7, 1), -0.275),
                'color': '#ffdd80'
            },
        ],
        'X' : ['Temperature'],
        'Y': 0,
        'mode': 1,
        'date': end_date,
        'xy': (end_date, -0.2),
        'textxy': (end_date, -0.6),
        'delay': 0,
        'p': False,
    },
    'Vaccinations': {
        'annotations': [
            {
                'annotation_text': 'States with more fully-vaccinated people have fewer cases, with a very strong correlation (-0.646).',
                'xy': (67500, 275),
                'textxy': (60000, 600),
            }
        ],
        'X' : ['Vaccinations Completed'],
        'Y': 0,
        'mode': 0,
        'date': end_date,
        'delay': 0,
        'p': False,
    },
    'Spurious Vaccinations Correlation': {
        'annotations': [
            {
                'annotation_text': '''This time we're looking at how states' vaccination rate TODAY correlates with their case load over time. Obviously, since the vaccine was only beginning to be rolled out at the end of 2020, then there shouldn't be much correlation during the span of 2020. However, we do see a huge correlation in Sep 2020 at a similar magnitude as the one we see for Sep 2021. Clearly the correlation in 2020 is spurious and must be due to some third causal factor, maybe the state's political leanings, temperature, etc.''',
                'xy': (datetime.date(2021, 9, 1), -0.7),
                'textxy': (datetime.date(2021, 3, 15), -0.55),
                'fontsize': 8,
                'alpha': 0.9,
            },
            {
                'annotation_text': '',
                'xy': (datetime.date(2020, 9, 15), -0.65),
                'textxy': (datetime.date(2020, 12, 1), -0.7),
            },
        ],
        'X' : ['Vaccinations Completed (Numbers Reported Right Now)'],
        'Y': 0,
        'mode': 1,
        'date': end_date,
        'delay': 0,
        'p': False,
    },
    'Political Leaning': {
        'annotations': [
            {
                'annotation_text': '''How does a state's political leaning correlate with that state's number of COVID cases? It looks like the spitting image of the previous vaccinations correlations! Just compare to the graph below. That seems to explain the previous phenomenon.''',
                'xy': (datetime.date(2021, 3, 15), -0.55),
                'textxy': (datetime.date(2021, 3, 16), -0.56),
                'alpha': 0.9
            },
        ],
        'X' : ['Political Leaning', 'Vaccinations Completed (Numbers Reported Right Now)'],
        'Y': 0,
        'mode': 1,
        'date': end_date,
        'delay': 0,
        'p': False,
    },
}
if 'selected_example_idx' not in st.session_state:
    st.session_state['selected_example_idx'] = 0
st.markdown('<hr style="margin-bottom: 0px; margin-top: 0px;">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1,4,1])
with col1:
    prev_button = st.button('Previous')
with col3:
    next_button = st.button('  Next  ')
if prev_button and (st.session_state['selected_example_idx'] > 0):
    st.session_state['selected_example_idx'] -= 1
if next_button and (st.session_state['selected_example_idx'] < len(list(example_options.keys()))-1):
    st.session_state['selected_example_idx'] += 1
selected_example_key = list(example_options.keys())[st.session_state['selected_example_idx']]
header_selected_example = 'Example: ' + selected_example_key
page_out_of = f"{st.session_state['selected_example_idx']+1}/{len(list(example_options.keys()))}"
col2.markdown(f"<h3 style='text-align: center; margin-bottom: 0px; padding-bottom: 0px'>{header_selected_example}</h3>", unsafe_allow_html=True)
col2.markdown(f"<p style='text-align: center; margin-top: 0px; padding-bottom: 3px'>{page_out_of}</p>", unsafe_allow_html=True)
st.markdown('<hr style="margin-bottom: 0px; margin-top: 0px;">', unsafe_allow_html=True)
selected_example = example_options[selected_example_key]

selected_X_keys = st.sidebar.multiselect('Select X data:', X_choices.keys(), default=selected_example['X'], key='x' + selected_example_key)
selected_Y_key = st.sidebar.selectbox('Select Y data:', Y_choices.keys(), index=selected_example['Y'], key='y' + selected_example_key)
mode_choices = ['Single date correlation', 'Correlation over time']
mode = st.sidebar.selectbox('Correlation at single date or Correlation over time', mode_choices, index=selected_example['mode'], key='mode' + selected_example_key, help='See correlation at a specific date, or see how correlation has changed over time during the entire pandemic.')
delay = st.sidebar.slider('# Days to delay', 0, 30, selected_example['delay'], key='delay' + selected_example_key, help='For example, if you think there may be a 14-day delay between the start of a mask mandate and a corresponding reduction in COVID cases, then set this to 14')
if mode == 'Single date correlation':
    selected_date = st.sidebar.slider('Date', start_date, end_date, value=selected_example['date'], step=datetime.timedelta(days=1), key='date' + selected_example_key)
    dates = [selected_date]
else:
    selected_date = end_date
if mode == 'Correlation over time':
    show_pvalues = st.sidebar.checkbox('Show P-Values', selected_example['p'], key='p' + selected_example_key, help='A low p-value (p < 0.05) indicates the correlation is not likely due to mere chance')
else:
    show_pvalues = False

is_using_selected_example = True
if selected_X_keys != selected_example['X']:
    is_using_selected_example = False
if selected_Y_key != list(Y_choices.keys())[selected_example['Y']]:
    is_using_selected_example = False
if mode != mode_choices[selected_example['mode']]:
    is_using_selected_example = False
if delay != selected_example['delay']:
    is_using_selected_example = False
if selected_date != selected_example['date']:
    is_using_selected_example = False
if show_pvalues != selected_example['p']:
    is_using_selected_example = False

X = [X_choices[k] for k in selected_X_keys]
y = Y_choices[selected_Y_key]

us_cases = []
all_corrs = []
all_ps = []
for date in dates:
    date_str = date.strftime('%Y-%m-%d')
    delayed_date_str = (date + datetime.timedelta(days=-delay)).strftime('%Y-%m-%d')
    y_values = y['var']
    y_val = y_values[date_str]
    us_cases.append(np.mean(y_val))

    for x in X:
        if x['date'] == 'delayed':
            x_values = x['var'][delayed_date_str]
        elif x['date'] == 'current':
            x_values = x['var'][date_str]
        elif x['date'] == 'none':
            x_values = x['var']
        if len(x_values) != len(y_val):
            print(x_values)
            print(y_val)
            print(delayed_date_str)
            print(date2maskmandate[delayed_date_str])
        corr, p = pearsonr(x_values, y_val)
        if np.isnan(corr):
            corr = 0
            p = 0
        x['correlations'].append(corr)
        x['p_values'].append(p)
        x['values'].append(x_values)


for x_idx, x in enumerate(X):
    if mode == 'Single date correlation':
        values = x['values'][0]
        fig, ax1 = plt.subplots()
        ax1.set_title(x['title'] + '-' + y['title'] + ' Correlation')
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.05, 0.95, "Pearson Correlation: {:.4f}\nP-Value: {:.6f}".format(x['correlations'][0], x['p_values'][0]), verticalalignment='top', bbox=props, transform=ax1.transAxes)
        ax1.scatter(values, y_val, color='blue')
        ax1.set_xlabel(x['x_label'])
        ax1.set_ylabel(y['y_label'])
        best_fit_x = list(np.unique(values))
        if len(best_fit_x) > 1:
            best_fit_y = np.poly1d(np.polyfit(values, y_val, 1))(np.unique(values))
            ax1.plot(best_fit_x, best_fit_y, color='blue')
        for val, case, state in zip(values, y_val, states):
            ax1.annotate(state, (val, case), color='blue')
    else:
        correlations = np.array(x['correlations'])
        fig, ax1 = plt.subplots()
        ax1.set_title(x['title'] + '-' + y['title'] + ' Correlation')
        ax1.set_ylabel('Correlation/P-Value')
        ax1.plot(dates, correlations, label='Pearson Correlations', color='black')
        if show_pvalues:
            line, = ax1.plot(dates, x['p_values'], label='P-Values', linestyle='dashed', color='gray')
        plt.xticks(rotation=90)
        ax1.legend()
        ax1.fill_between(dates, correlations, 0, where=correlations > 0, interpolate=True, color='red', alpha=0.3)
        ax1.fill_between(dates, correlations, 0, where=correlations < 0, interpolate=True, color='blue', alpha=0.3)
    if is_using_selected_example and x_idx == 0:
        for annotation in selected_example['annotations']:
            fontsize = annotation['fontsize'] if 'fontsize' in annotation else None
            alpha = annotation['alpha'] if 'alpha' in annotation else None
            color = annotation['color'] if 'color' in annotation else '#7af6ff'
            is_bbox_visible = annotation['annotation_text'] != ''
            annotation_text = '\n'.join(l for line in annotation['annotation_text'].splitlines() for l in textwrap.wrap(line, width=30))
            ab = AnnotationBbox(TextArea(annotation_text, textprops=dict(ha='center', fontsize=fontsize)), annotation['xy'], annotation['textxy'],
                         arrowprops=dict(arrowstyle="fancy", connectionstyle='angle3', facecolor=color, edgecolor='black'), bboxprops =
                                dict(facecolor=color,boxstyle='round',color='black',visible=is_bbox_visible,alpha=alpha))
            ax1.add_artist(ab)
    st.write(fig)
    st.caption(x['caption'])

if mode != 'Single date correlation':
    fig3, ax3 = plt.subplots()
    ax3.set_title(f'US {y["title"]}')
    ax3.set_ylabel(y["y_label"])
    ax3.plot(dates, us_cases, label=f'US {y["title"]}')
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

st.caption('COVID cases, deaths, and vaccinations are taken from COVID Act Now API (https://covidactnow.org/). I used 7-day rolling average for daily cases and deaths, while vaccinations are the total number of people fully-vaccinated. Cases, deaths, and vaccinations are per 100k population in that state.')


st.markdown('<hr>', unsafe_allow_html=True)

st.caption('Created by Logan Lebanoff. Contact me at loganlebanoff@gmail.com if you have any suggestions or other correlations you would like to see. Source code: https://github.com/loganlebanoff/covid_correlations.')
# hide_menu = """<style>
# footer:before{
#     content:'%s';
#     display:block;
#     position:relative;
# }
# </style>""" % (footer_text)
# st.markdown(hide_menu, unsafe_allow_html=True)

hide_streamlit_style = """<style>
            #MainMenu {visibility: hidden;}
            </style>"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

a=0