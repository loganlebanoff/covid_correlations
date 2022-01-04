import os
import requests
import json
import matplotlib.pyplot as plt
from tqdm import tqdm
import numpy as np
from scipy.stats.stats import pearsonr, spearmanr
from collections import defaultdict
from dotenv import load_dotenv
import datetime
import dateutil.parser
import streamlit as st
from matplotlib.offsetbox import (TextArea, DrawingArea, OffsetImage,
                                  AnnotationBbox)
import textwrap
import csv

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
abbrev_to_us_state = {v: k for k, v in us_state_to_abbrev.items()}

earlier_start_date = datetime.date(2020, 3, 1)
start_date = datetime.date(2020, 4, 1)
end_date = datetime.date.today()
end_date_temp = datetime.date(2021, 9, 20)
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')


st.title('COVID-19 Correlation Explorer')
st.subheader('Find out what relationships exist between a U.S. state\'s number of COVID cases and several other factors, including vaccination rate, temperature, and mask mandates.')
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
        cases = (today_cases - lastweek_cases) * 7  # TODO: multiply by 7 but then need to fix all the annotation coords
    return cases, today_cases or 0

@st.cache(suppress_st_warning=True, allow_output_mutation=True, show_spinner=False)
def load_data():

    load_dotenv()

    covidactnow_api_key = os.environ.get('COVID_ACTNOW_API_KEY')
    # VisualCrossingWebServices_api_key = os.environ.get('VisualCrossingWebServices_API_KEY')
    result = requests.get(f'https://api.covidactnow.org/v2/states.timeseries.json?apiKey={covidactnow_api_key}')
    data = result.json()
    a=0

    # with open('data/covid_data.json', 'w') as f:
    #     json.dump(data, f, indent=2)

    vaccines_today = []
    temps = []
    date2temps = defaultdict(list)
    date2cases = defaultdict(list)
    date2deaths = defaultdict(list)
    date2totalcases = defaultdict(list)
    date2totaldeaths = defaultdict(list)
    date2vaccines = defaultdict(list)
    dates = [start_date + datetime.timedelta(days=x) for x in range((end_date-start_date).days + 1)]
    ealier_dates = [earlier_start_date + datetime.timedelta(days=x) for x in range((end_date-earlier_start_date).days + 1)]
    for row in data:
        state = row['state']
        if state not in us_state_to_abbrev.values():
            continue
        population = row['population']
        prev_vaccines = 0
        vaccinationsCompleted = row['actuals']['vaccinationsCompleted']
        maxvaccinationsCompleted = 0
        for daterow_idx, daterow in enumerate(row['actualsTimeseries']):
            if daterow_idx >= 7:
                try:
                    date = daterow['date']
                    # if state == 'WY' and date == '2021-06-29':
                    #     import pdb;pdb.set_trace()
                    cases, totalcases = get_row_value(daterow, row, population, daterow_idx, 'cases')
                    date2cases[date].append(cases)
                    date2totalcases[date].append(totalcases)
                    deaths, totaldeaths = get_row_value(daterow, row, population, daterow_idx, 'deaths')
                    date2deaths[date].append(deaths)
                    date2totaldeaths[date].append(totaldeaths)
                    if 'vaccinationsCompleted' in daterow and daterow['vaccinationsCompleted'] is not None:
                        vaccines = int(daterow['vaccinationsCompleted'])
                        maxvaccinationsCompleted = max(maxvaccinationsCompleted, vaccines)
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
        if vaccinationsCompleted is None:
            vaccinationsCompleted = maxvaccinationsCompleted
        vaccines_today.append(vaccinationsCompleted / population * 100000)


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

    with open('data/population_density.tsv') as f:
        lines = f.read().splitlines()
    density_tuples = []
    for line in lines:
        items = line.strip().split('\t')
        if items[1].strip() not in states:
            continue
        state = items[1].strip()
        density = float(items[5].strip())
        density_tuples.append((state, density))
    densities = []
    for state, density in sorted(density_tuples):
        densities.append(density)

    with open("data/uninsured.csv") as f:
        reader = csv.reader(f, delimiter=",", quotechar='"')
        next(reader, None)  # skip the headers
        data = [row for row in reader]
    uninsured_tuples = []
    for row in data:
        if row[0] not in us_state_to_abbrev:
            continue
        state = us_state_to_abbrev[row[0]]
        uninsured = float(row[6]) * 100
        uninsured_tuples.append((state, uninsured))
    uninsureds = []
    for state, uninsured in sorted(uninsured_tuples):
        uninsureds.append(uninsured)

    with open("data/household_income.json") as f:
        data = json.load(f)
    data = {item['State']: item['HouseholdIncome'] for item in data}
    household_incomes = []
    for state in states:
        full_state_name = abbrev_to_us_state[state]
        household_income = data[full_state_name]
        household_incomes.append(household_income)

    with open('data/healthcare_ranking.tsv') as f:
        lines = f.read().splitlines()
    healthcare_ranking_tuples = []
    cur_rank = 1
    for line in lines:
        if line.strip() not in us_state_to_abbrev:
            continue
        state = us_state_to_abbrev[line.strip()]
        healthcare_ranking = cur_rank
        healthcare_ranking_tuples.append((state, healthcare_ranking))
        cur_rank += 1
    healthcare_rankings = []
    for state, healthcare_ranking in sorted(healthcare_ranking_tuples):
        healthcare_rankings.append(healthcare_ranking)


    return dates, ealier_dates, date2temps, date2cases, date2deaths, date2totalcases, date2totaldeaths, date2maskmandate, date2vaccines, vaccines_today, politicals, ages, densities, uninsureds, household_incomes, healthcare_rankings, states

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

with st.spinner(text="Fetching data. This will take only about 5 seconds..."):
    dates, ealier_dates, date2temps, date2cases, date2deaths, date2totalcases, date2totaldeaths, date2maskmandate, date2vaccines, vaccines_today, politicals, ages, densities, uninsureds, household_incomes, healthcare_rankings, states = load_data()

def date2totalcasessincefunc(date, date2totalcases=None, sincedate=None):
    res = []
    for i in range(len(date2totalcases[date])):
        val = date2totalcases[date][i] - date2totalcases[sincedate][i]
        res.append(val)
    return res
def date2totaldeathssincefunc(date, date2totaldeaths=None, sincedate=None):
    res = []
    for i in range(len(date2totaldeaths[date])):
        print(sincedate)
        print(date)
        print(date2totaldeaths['2020-04-01'])
        val = date2totaldeaths[date][i] - date2totaldeaths[sincedate][i]
        res.append(val)
    return res


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
    },
    'Population Density': {
        'title': 'State Population Density',
        'x_label': 'Population Density (people/km^2)',
        'date': 'none',
        'var': densities,
        'correlations': [],
        'p_values': [],
        'values': [],
        'caption': 'The measure used here is "population-weighted population density," which takes into account urbanization. For example, New York state actually is not #1 in simple population density (since it is a fairly big state). However, most people living in New York are actually densely populated in NYC. Population-weighted population density takes this into account. Data and idea taken from https://wernerantweiler.ca/blog.php?item=2020-04-12&fbclid=IwAR2CHyOg5bFw3Rbu0c4-m8pc0D4cX2GVfCkzupUoCmUbL4NB1WQAaIZOx0s'
    },
    'Uninsured Rate': {
        'title': 'State Uninsured Rate',
        'x_label': 'Percent Uninsured (%)',
        'date': 'none',
        'var': uninsureds,
        'correlations': [],
        'p_values': [],
        'values': [],
        'caption': 'Percent uninsured information taken from https://www.kff.org/other/state-indicator/total-population/?currentTimeframe=0&sortModel=%7B%22colId%22:%22Location%22,%22sort%22:%22asc%22%7D'
    },
    'Median Household Income': {
        'title': 'State Median Household Income',
        'x_label': 'Median Household Income ($)',
        'date': 'none',
        'var': household_incomes,
        'correlations': [],
        'p_values': [],
        'values': [],
        'caption': 'Household income information taken from https://worldpopulationreview.com/state-rankings/median-household-income-by-state which took its data from the Census ACS survey https://www.census.gov/library/visualizations/interactive/2019-median-household-income.html'
    },
    'Healthcare Ranking': {
        'title': 'State Healthcare Ranking',
        'x_label': 'Healthcare Ranking',
        'date': 'none',
        'var': healthcare_rankings,
        'correlations': [],
        'p_values': [],
        'values': [],
        'caption': 'Healthcare rankings are {1-50} with lower numbers being better, e.g. Hawaii is #1 with the best healthcare quality and Alabama is #50 with the worst. Healthcare ranking information taken from https://www.usnews.com/news/best-states/rankings/health-care/healthcare-quality'
    },
}

Y_choices = {
    'Daily Cases': {
        'title': 'Daily Cases',
        'y_label': 'Daily Cases per 100k',
        'var': date2cases,
    },
    'Daily Deaths': {
        'title': 'Daily Deaths',
        'y_label': 'Daily Deaths per 100k',
        'var': date2deaths,
    },
    'Total Cases': {
        'title': 'Total Cases',
        'y_label': 'Total Cases per 100k',
        'var': date2totalcases,
    },
    'Total Deaths': {
        'title': 'Total Deaths',
        'y_label': 'Total Deaths per 100k',
        'var': date2totaldeaths,
    },
    'Total Vaccinations': {
        'title': 'Total Vaccinations',
        'y_label': 'Total Vaccinations per 100k',
        'var': date2vaccines,
    },
    'Total Cases Since XX': {
        'title': 'Total Cases Since XX',
        'y_label': 'Total Cases per 100k',
        'var': date2totalcasessincefunc,
        'var_kwargs': {
            'date2totalcases': date2totalcases,
        }
    },
    'Total Deaths Since XX': {
        'title': 'Total Deaths Since XX',
        'y_label': 'Total Deaths per 100k',
        'var': date2totaldeathssincefunc,
        'var_kwargs': {
            'date2totaldeaths': date2totaldeaths,
        }
    },
}

example_options = {
    'Cold States': {
        'annotations': [
            {
                'annotation_text' : '''The line has a downward trend, which is a negative correlation. In this case, that means states that are cold happen to have more COVID cases than warmer states.''',
                'xy': (85, 2100),
                'textxy': (95, 3500),
            }
        ],
        'X' : ['Temperature'],
        'Y': 0,
        'mode': 0,
        'date': end_date_temp,
        'delay': 0,
        'p': False,
        'coefficient': 'Pearson Correlation',
    },
    'Hot States': {
        'annotations': [
            {
                'annotation_text' : '''If we change the date to July 20, just 2 months in the past, then we see a positive correlation (states that are hot happen to have more COVID cases than colder states.''',
                'xy': (90, 840),
                'textxy': (95, 1610),
                'color': '#ffdd80'
            }
        ],
        'X' : ['Temperature'],
        'Y': 0,
        'mode': 0,
        'date': datetime.date(2021, 7, 20),
        'delay': 0,
        'p': False,
        'coefficient': 'Pearson Correlation',
    },
    'Temperature Correlation Over Time': {
        'annotations': [
            {
                'annotation_text' : '''''',
                'xy': (end_date_temp, -0.2),
                'textxy': (end_date_temp, -0.6),
            },
            {
                'annotation_text' : 'If we look at Correlation Over Time, then we see the same two phenomena at the same time, and we can see how the correlation changes over time.',
                'xy': (datetime.date(2021, 7, 17), 0.28),
                'textxy': (datetime.date(2021, 1, 1), 0.35),
                'color': '#ffdd80',
                'alpha': 0.9
            },
            {
                'annotation_text' : 'Interestingly, it seems to follow the pattern that hot states get more cases in the summer (so people gather inside in those states), and cold states get more cases in the winter (again, so people gather inside).',
                'xy': (datetime.date(2020, 10, 15), -0.5),
                'textxy': (datetime.date(2020, 4, 1), -0.6),
                'alpha': 0.9
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
        'date': end_date_temp,
        'xy': (end_date_temp, -0.2),
        'textxy': (end_date_temp, -0.6),
        'delay': 0,
        'p': False,
        'coefficient': 'Pearson Correlation',
    },
    'Vaccinations': {
        'annotations': [
            {
                'annotation_text': 'States with more fully-vaccinated people have fewer cases, with a very strong correlation (-0.646).',
                'xy': (67500, 1925),
                'textxy': (60000, 4200),
            }
        ],
        'X' : ['Vaccinations Completed'],
        'Y': 0,
        'mode': 0,
        'date': end_date,
        'delay': 0,
        'p': False,
        'coefficient': 'Pearson Correlation',
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
        'coefficient': 'Pearson Correlation',
    },
    'Political Leaning': {
        'annotations': [
            {
                'annotation_text': '''How does a state's political leaning correlate with that state's number of COVID cases? This graph looks like the spitting image of the previous vaccinations correlations! Just compare to the graph below. That seems to explain the previous phenomenon.''',
                'xy': (datetime.date(2021, 3, 15), -0.55),
                'textxy': (datetime.date(2021, 3, 16), -0.56),
                'alpha': 0.9,
                'color': '#ffdd80'
            },
        ],
        'X' : ['Political Leaning', 'Vaccinations Completed (Numbers Reported Right Now)'],
        'Y': 0,
        'mode': 1,
        'date': end_date,
        'delay': 0,
        'p': False,
        'coefficient': 'Pearson Correlation',
    },
    'Mask Mandates': {
        'annotations': [
            {
                'annotation_text': '''Relatively weak correlation between state mask mandates and cases.''',
                'xy': (datetime.date(2020, 11, 2), 0.31),
                'textxy': (datetime.date(2020, 11, 1), 0.3),
            },
        ],
        'X' : ['Mask Mandate'],
        'Y': 0,
        'mode': 1,
        'date': end_date,
        'delay': 0,
        'p': False,
        'coefficient': 'Pearson Correlation',
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
advanced_options = st.sidebar.expander('Advanced Options')
coefficient_options = ['Pearson Correlation', 'Spearman Correlation']
correlation_coefficient = advanced_options.selectbox('Correlation Coefficient', coefficient_options, coefficient_options.index(selected_example['coefficient']), key='coefficient' + selected_example_key, help='Pearson correlation is probably the most common measure for correlation, but it is susceptible to outliers. Spearman correlation is more robust to outliers.')
sincedate = advanced_options.slider('Since Date', start_date, end_date, value=start_date, step=datetime.timedelta(days=1), key='date' + selected_example_key, help='This only applies to "Total Cases Since XX" and "Total Deaths Since XX"')

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
if correlation_coefficient != selected_example['coefficient']:
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
    print(isinstance(y_values, dict))
    if isinstance(y_values, dict):
        y_val = y_values[date_str]
    else:
        var_kwargs = y['var_kwargs']
        var_kwargs['sincedate'] = str(sincedate)
        y_val = y_values(date_str, **var_kwargs)
    us_cases.append(np.mean(y_val))

    for x in X:
        if x['date'] == 'delayed':
            x_values = x['var'][delayed_date_str]
        elif x['date'] == 'current':
            x_values = x['var'][date_str]
        elif x['date'] == 'none':
            x_values = x['var']
        else:
            x_values = None
        is_incomplete = False
        if x_values is None:
            is_incomplete = True
            corr = 0
            p = 0
        else:
            if len(x_values) < len(y_val):
                y_val = y_val[:len(x_values)]
            if len(x_values) != len(y_val):
                print(x_values)
                print(y_val)
                print(delayed_date_str)
                print(date2maskmandate[delayed_date_str])
            if correlation_coefficient == 'Pearson Correlation':
                corr, p = pearsonr(x_values, y_val)
            else:
                corr, p = spearmanr(x_values, y_val)
            if np.isnan(corr):
                corr = 0
                p = 0
        if is_incomplete:
            x_values.extend([0] * (len(dates) - len(x_values)))
        x['correlations'].append(corr)
        x['p_values'].append(p)
        x['values'].append(x_values)


for x_idx, x in enumerate(X):
    if mode == 'Single date correlation':
        values = x['values'][0]
        fig, ax1 = plt.subplots()
        ax1.set_title(x['title'] + '-' + y['title'] + ' Correlation')
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.05, 0.95, "{}: {:.4f}\nP-Value: {:.15f}".format(correlation_coefficient, x['correlations'][0], x['p_values'][0]), verticalalignment='top', bbox=props, transform=ax1.transAxes)
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
        ax1.plot(dates, correlations, label=correlation_coefficient + 's', color='black')
        if show_pvalues:
            line, = ax1.plot(dates, x['p_values'], label='P-Values', linestyle='dashed', color='gray')
        plt.xticks(rotation=90)
        ax1.legend()
        ax1.fill_between(dates, correlations, 0, where=correlations > 0, interpolate=True, color='red', alpha=0.3)
        ax1.fill_between(dates, correlations, 0, where=correlations < 0, interpolate=True, color='blue', alpha=0.3)
    if is_using_selected_example and x_idx == 0:
        for annotation in selected_example['annotations']:
            fontsize = annotation['fontsize'] if 'fontsize' in annotation else 12
            width = fontsize * 2
            alpha = annotation['alpha'] if 'alpha' in annotation else None
            color = annotation['color'] if 'color' in annotation else '#7af6ff'
            is_bbox_visible = annotation['annotation_text'] != ''
            annotation_text = '\n'.join(l for line in annotation['annotation_text'].splitlines() for l in textwrap.wrap(line, width=25 + (12-fontsize)))
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
