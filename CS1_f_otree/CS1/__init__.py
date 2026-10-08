from otree.api import *
import ast
import json
import random
from urllib.parse import urlencode
from urllib.request import urlopen

doc = """
Follow-up to CS1: does the way spending reactions are elicited change the reaction to an inheritance?

Participants take the role of a 62-year-old planning for retirement and fill out a spending plan in a
lifecycle planning tool (see ToyLifecycleTool.xlsx). They then face two scenarios in random order
(within-subject) in which they inherit a one-time payment either today or in the future, and update
their plan in one of three layouts (between-subject, named after the sheets of the tool):
    natural_2: enter the change in spending per year; the initial plan is shown as a static reminder
    natural_1: enter the change in spending per year; the tool and a graph update dynamically
    reframed:  enter the updated spending per year; the tool and a graph update dynamically
The concluding survey covers demographics and the participant's own expected parental inheritance.
"""


class C(BaseConstants):
    NAME_IN_URL = 'CS1'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    KEYLOG_EVENT_CAP = 2000
    PLAN_YEARS = 8  # years for which spending is planned; spending stays constant afterwards
    PLAN_HORIZON_AGE = 109  # savings are projected up to this age
    LAYOUTS = ['natural_2', 'natural_1', 'reframed']
    ROUND_ORDERS = ['present_first', 'future_first']
    CURRENCIES = {'AUD': 'A$', 'GBP': '£', 'EUR': '€', 'USD': '$'}
    COMPLICATED_WORDS = ['Schadenfreude', 'Bourgeoisie', 'Worcestershire']
    # Change DEFAULT_CURRENCY if looking to change the currency of the experiment.
    DEFAULT_CURRENCY = 'GBP' # ADJUST THIS ONE
    DEFAULT_CURRENCY_SYMBOL = CURRENCIES[DEFAULT_CURRENCY]


RECAPTCHA_VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'


class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    # CREATING SESSION -
    prolific_id = models.StringField(blank=True, label='Your Prolific ID')
    layout = models.StringField()  # natural_2 = change in spending, natural_1 = change in spending + dynamic tool, reframed = updated spending + dynamic tool
    round_order = models.StringField()  # present_first / future_first
    mother_father = models.IntegerField(initial=0)  # mother = 1, father = 2
    inh_followup_frame = models.IntegerField()  # spending frame = 1, saving frame = 2
    # BOT SCREENING (Attention checks?)
    attention1 = models.IntegerField(initial=2)
    attention2 = models.IntegerField(initial=2)
    attention3 = models.IntegerField(initial=2)
    attention4 = models.IntegerField(initial=2)
    recaptcha_response = models.LongStringField(blank=True)
    recaptcha_verified = models.BooleanField(initial=False)

    lines = models.IntegerField(
        label="Which of the two lines above is longer?",
        choices=[[1, "Blue Line"],[2,"Red Line"],[3,"None (they are the same)"]],
        widget=widgets.RadioSelectHorizontal()
    )
    cafewall = models.IntegerField(
        label="Are all the gray lines above perfectly straight/horizontal or slanted/diagonal?",
        choices=[[1,"Straight/Horizontal"],[2,"Slanted/Diagonal"]],
        widget = widgets.RadioSelectHorizontal(),
    )
    can = models.StringField(
        label="What color is the can depicted above?",
        max_length=6
    )
    words = models.StringField()

    ComplicatedWord_Corrections = models.IntegerField(initial=0)
    AI_Test2 = models.StringField(label='', initial='[]')
    keylog_timing_tuples = models.LongStringField(initial='')
    checks = models.IntegerField(initial=2)

    # Leave Page
    isLeaving = models.BooleanField(choices=((True, 'leaving'), (False, 'notleaving')),
                                    initial=0)

    # INSTRUCTIONS_WELCOMESCREEN
    browser_first = models.CharField()
    # ------------------------------------------------------------------------------------------------------------
    # ---------------------------------------- LIFECYCLE PLANNING TOOL -------------------------------------------
    # ------------------------------------------------------------------------------------------------------------
    # y1..y8 are the plan years (ages 63 to 70 with the default parameters).
    # depletion_age = last age with non-negative total savings (empty if they last beyond C.PLAN_HORIZON_AGE)
    # bequest = total savings left at the bequest age

    # Plan_Baseline: initial spending plan
    base_spend_y1 = models.IntegerField(blank=True)
    base_spend_y2 = models.IntegerField(blank=True)
    base_spend_y3 = models.IntegerField(blank=True)
    base_spend_y4 = models.IntegerField(blank=True)
    base_spend_y5 = models.IntegerField(blank=True)
    base_spend_y6 = models.IntegerField(blank=True)
    base_spend_y7 = models.IntegerField(blank=True)
    base_spend_y8 = models.IntegerField(blank=True)
    base_depletion_age = models.IntegerField(blank=True)
    base_bequest = models.FloatField(blank=True)

    # Plan_Scenario / Plan_Update with the inheritance today.
    # The natural layouts ask for the change in spending, the reframed layout for the updated spending;
    # the one that was not asked is derived (spend = base_spend + change).
    # min=None: changes can be negative (oTree's default minimum for numbers is 0).
    present_scenario_warning = models.IntegerField(initial=0)  # 1 = pressed Next within 10 seconds, 0 = waited 10 seconds
    present_change_y1 = models.IntegerField(blank=True, min=None)
    present_change_y2 = models.IntegerField(blank=True, min=None)
    present_change_y3 = models.IntegerField(blank=True, min=None)
    present_change_y4 = models.IntegerField(blank=True, min=None)
    present_change_y5 = models.IntegerField(blank=True, min=None)
    present_change_y6 = models.IntegerField(blank=True, min=None)
    present_change_y7 = models.IntegerField(blank=True, min=None)
    present_change_y8 = models.IntegerField(blank=True, min=None)
    present_spend_y1 = models.IntegerField(blank=True)
    present_spend_y2 = models.IntegerField(blank=True)
    present_spend_y3 = models.IntegerField(blank=True)
    present_spend_y4 = models.IntegerField(blank=True)
    present_spend_y5 = models.IntegerField(blank=True)
    present_spend_y6 = models.IntegerField(blank=True)
    present_spend_y7 = models.IntegerField(blank=True)
    present_spend_y8 = models.IntegerField(blank=True)
    present_depletion_age = models.IntegerField(blank=True)
    present_bequest = models.FloatField(blank=True)

    # Plan_Scenario / Plan_Update with the inheritance in the future
    future_scenario_warning = models.IntegerField(initial=0)  # 1 = pressed Next within 10 seconds, 0 = waited 10 seconds
    future_change_y1 = models.IntegerField(blank=True, min=None)
    future_change_y2 = models.IntegerField(blank=True, min=None)
    future_change_y3 = models.IntegerField(blank=True, min=None)
    future_change_y4 = models.IntegerField(blank=True, min=None)
    future_change_y5 = models.IntegerField(blank=True, min=None)
    future_change_y6 = models.IntegerField(blank=True, min=None)
    future_change_y7 = models.IntegerField(blank=True, min=None)
    future_change_y8 = models.IntegerField(blank=True, min=None)
    future_spend_y1 = models.IntegerField(blank=True)
    future_spend_y2 = models.IntegerField(blank=True)
    future_spend_y3 = models.IntegerField(blank=True)
    future_spend_y4 = models.IntegerField(blank=True)
    future_spend_y5 = models.IntegerField(blank=True)
    future_spend_y6 = models.IntegerField(blank=True)
    future_spend_y7 = models.IntegerField(blank=True)
    future_spend_y8 = models.IntegerField(blank=True)
    future_depletion_age = models.IntegerField(blank=True)
    future_bequest = models.FloatField(blank=True)

    # ------------------------------------------------------------------------------------------------------------
    # ----------------------------------------- DEMOGRAPHICS (From SAE0) -----------------------------------------
    # ------------------------------------------------------------------------------------------------------------

    # Demographics 1
    Demographics_Age = models.IntegerField(
        label='What is your age?', min=18, max=100)

    Demographics_AgeExpectation = models.IntegerField(
        label='People have different expectations about their longevity. Please estimate the age until which you expect to live:', min=18, max=130
    )

    Demographics_Sex = models.IntegerField(initial=None,
                                           choices=[
                                               [1, 'Male'],
                                               [2, 'Female'],
                                               [3, 'Other'],
                                               [4, 'Prefer not to say'],
                                           ],
                                           verbose_name='What is your gender?',
                                           widget=widgets.RadioSelect())

    Demographics_Education = models.IntegerField(
        label='What is the highest level of education you have completed?',
        widget=widgets.RadioSelect(),
        choices=[
            [0, 'Less than high school'],
            [1, 'High school or equivalent (A-Levels, GED, etc.)'],
            [2, 'Some college or university'],
            [3, 'Undergraduate degree (Bachelor’s)'],
            [4, 'Master’s degree or higher (post-graduate degree)'],
            [5, 'Prefer not to say']
        ])

    Demographics_Children = models.IntegerField(initial=None,
                                                choices=[
                                                    [1, 'Yes'],
                                                    [2, 'No'],
                                                    [3, 'Prefer not so say'],
                                                ],
                                                verbose_name='Do you have children?',
                                                widget=widgets.RadioSelect())
    
    Demographics_Mother = models.IntegerField(
        label="What is your mother's age? Please leave this field empty if your mother has passed away, you do not know, or you do not want to respond. Enter an estimate if you are uncertain.", min=18, max=130, blank=True)

    Demographics_Father = models.IntegerField(
        label="What is your father's age? Please leave this field empty if your father has passed away, you do not know, or you do not want to respond. Enter an estimate if you are uncertain.", min=18, max=130, blank=True)

    Demographics_MotherInheritance = models.IntegerField(
        label=f"How much do you expect to inherit from your mother (in {C.DEFAULT_CURRENCY_SYMBOL})? Please enter the approximate value of the inheritance if your mother has passed away already, or 42 if you do not know / do not want to respond.", min=0, max=100_000_000, blank=True)

    Demographics_FatherInheritance = models.IntegerField(
        label=f"How much do you expect to inherit from your father (in {C.DEFAULT_CURRENCY_SYMBOL})? Please enter the approximate value of the inheritance if your father has passed away already, or 42 if you do not know / do not want to respond.", min=0, max=100_000_000, blank=True)

    # Concluding survey inheritance follow-up
    inh_followup_effect = models.IntegerField(blank=True)
    inh_followup_effect_order = models.StringField(blank=True)
    inh_followup_thought = models.IntegerField(blank=True)
    inh_followup_why = models.LongStringField(blank=True, label='Please explain why:')
    inh_followup_reason_i = models.IntegerField(blank=True, min=1, max=5, label='I keep future payments such as this one in a different budget than the budget that I use to determine my current spending')
    inh_followup_reason_ii = models.IntegerField(blank=True, min=1, max=5, label='It would be morally wrong to spend the inheritance before I receive it')
    inh_followup_reason_iii = models.IntegerField(blank=True, min=1, max=5, label="I wouldn't know how to increase spending using the inheritance I receive in the future")
    inh_followup_reason_iv = models.IntegerField(blank=True, min=1, max=5, label='I cannot increase spending before receiving the inheritance because I have little savings and cannot access credit')
    inh_followup_reason_v = models.IntegerField(blank=True, min=1, max=5, label='Spending the inheritance in advance would require me to borrow, which I do not want to do')
    inh_followup_reason_vi = models.IntegerField(blank=True, min=1, max=5, label='I consider that there is too much uncertainty in the timing and value of the inheritance')
    inh_followup_reason_vii = models.IntegerField(blank=True, min=1, max=5, label='I worry that my parent would reduce my inheritance if I spent some of it in advance')
    inh_followup_reason_other = models.LongStringField(blank=True, label='Other reason. Please specify:')
    inh_followup_reason_order = models.StringField(blank=True)

    # Feedback
    OpenFeedback = models.LongStringField(
        label='Please describe in short any feedback you might have on this survey.', blank=True)


KEYLOG_TIMING_STATE_KEY = 'keylog_timing_state'


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _verify_recaptcha_token(token, secret):
    payload = urlencode({'secret': secret, 'response': token}).encode('utf-8')

    try:
        with urlopen(RECAPTCHA_VERIFY_URL, data=payload, timeout=8) as response:
            body = response.read(8192).decode('utf-8')  # cap at 8 KB; real response is <1 KB
    except Exception:
        return False, 'network'

    try:
        result = json.loads(body)
    except (TypeError, ValueError):
        return False, 'invalid_response'

    if not isinstance(result, dict):
        return False, 'invalid_response'

    if result.get('success'):
        return True, 'ok'

    error_codes = result.get('error-codes') or []
    if 'timeout-or-duplicate' in error_codes:
        return False, 'expired'

    return False, 'invalid'


def _get_keylog_timing_state(player: Player):
    state = player.participant.vars.get(KEYLOG_TIMING_STATE_KEY)
    return state if isinstance(state, dict) else {}


def _serialize_keylog_timing_tuples(state):
    tuples = []
    for field_name in sorted(state):
        field_state = state.get(field_name)
        if not isinstance(field_state, dict):
            continue

        first_t = _safe_float(field_state.get('first_t'))
        prev_t = _safe_float(field_state.get('prev_t'))
        min_gap = _safe_float(field_state.get('min_gap'))

        try:
            count = int(field_state.get('count', 0))
        except (TypeError, ValueError):
            count = 0

        if count <= 0 or first_t is None or prev_t is None:
            continue

        tuples.append((field_name, min_gap, prev_t - first_t))

    return ', '.join(str(item) for item in tuples)


def _append_keylog_event(player: Player, _storage_field: str, data):
    if not isinstance(data, dict):
        return

    field_name = str(data.get('field') or 'unknown')[:64]  # cap to prevent storage bloat
    event_t = _safe_float(data.get('t'))
    if event_t is None:
        return

    state = _get_keylog_timing_state(player)
    field_state = state.get(field_name)

    if not isinstance(field_state, dict):
        state[field_name] = {
            'first_t': event_t,
            'prev_t': event_t,
            'min_gap': None,
            'count': 1,
        }
        player.participant.vars[KEYLOG_TIMING_STATE_KEY] = state
        player.keylog_timing_tuples = _serialize_keylog_timing_tuples(state)
        return

    try:
        count = int(field_state.get('count', 0))
    except (TypeError, ValueError):
        count = 0

    if count >= C.KEYLOG_EVENT_CAP:
        player.participant.vars[KEYLOG_TIMING_STATE_KEY] = state
        player.keylog_timing_tuples = _serialize_keylog_timing_tuples(state)
        return

    first_t = _safe_float(field_state.get('first_t'))
    if first_t is None:
        first_t = event_t

    prev_t = _safe_float(field_state.get('prev_t'))
    min_gap = _safe_float(field_state.get('min_gap'))

    if prev_t is not None:
        gap = event_t - prev_t
        if gap >= 0:
            min_gap = gap if min_gap is None else min(min_gap, gap)

    field_state['first_t'] = first_t
    field_state['prev_t'] = event_t
    field_state['min_gap'] = min_gap
    field_state['count'] = count + 1

    state[field_name] = field_state
    player.participant.vars[KEYLOG_TIMING_STATE_KEY] = state
    player.keylog_timing_tuples = _serialize_keylog_timing_tuples(state)


# ------------------------------------------------------------------------------------------------------------
# ---------------------------------------- LIFECYCLE PLANNING TOOL -------------------------------------------
# ------------------------------------------------------------------------------------------------------------
# Parameters of the tool. They can be changed per session in SESSION_CONFIGS (settings.py);
# these defaults are the assumptions of ToyLifecycleTool.xlsx.
PLAN_PARAM_DEFAULTS = dict(
    initial_wealth=120000,
    salary=30253,
    pension=17264,
    interest_rate=0.03,
    inheritance=50000,
    current_age=62,
    retirement_age=67,  # first age at which income = pension
    inheritance_delay_years=2,  # future scenario: years between the first plan year and the inheritance
    bequest_age=90,
)
PLAN_YEAR_NUMBERS = range(1, C.PLAN_YEARS + 1)


def _money(value):
    value = round(value)
    sign = '-' if value < 0 else ''
    return f'{sign}{C.DEFAULT_CURRENCY_SYMBOL}{abs(value):,}'


def _plan_params(player: Player):
    config = player.session.config
    p = {key: config.get(key, default) for key, default in PLAN_PARAM_DEFAULTS.items()}
    p['first_age'] = p['current_age'] + 1
    p['last_age'] = p['current_age'] + C.PLAN_YEARS
    return p


def _plan_ages(p):
    return list(range(p['first_age'], p['last_age'] + 1))


def _plan_income(p, age):
    return p['pension'] if age >= p['retirement_age'] else p['salary']


def _plan_inheritance_age(p, timing):
    if timing == 'present':
        return p['first_age']
    if timing == 'future':
        return p['first_age'] + p['inheritance_delay_years']
    return None


def _plan_scenario_timing(player: Player, scenario_number):
    timings = ['present', 'future'] if player.round_order == 'present_first' else ['future', 'present']
    return timings[scenario_number - 1]


def _plan_base_spending(player: Player):
    return [player.field_maybe_none(f'base_spend_y{i}') for i in PLAN_YEAR_NUMBERS]


def _plan_project(p, spending, inheritance_age=None):
    """Projects total savings for a spending plan with one entry per plan year, as in ToyLifecycleTool.xlsx.

    After the last plan year, spending stays at the level of the last plan year. Returns the rows of
    the plan years, the last age at which total savings are still non-negative (None if they last
    beyond C.PLAN_HORIZON_AGE) and the total savings at the bequest age.
    """
    rows = []
    total = p['initial_wealth']
    depletion_age = None
    bequest = None
    for age in range(p['first_age'], C.PLAN_HORIZON_AGE + 1):
        year = age - p['first_age']
        income = _plan_income(p, age)
        inheritance = p['inheritance'] if age == inheritance_age else 0
        saving = income - spending[min(year, C.PLAN_YEARS - 1)] + inheritance
        # savings carried over from the previous year earn interest
        total = total + saving if year == 0 else total * (1 + p['interest_rate']) + saving
        if year < C.PLAN_YEARS:
            rows.append(dict(age=age, income=income, inheritance=inheritance, saving=saving, total=total))
        if total < 0 and depletion_age is None:
            depletion_age = age - 1
        if age == p['bequest_age']:
            bequest = total
    return rows, depletion_age, bequest


def _plan_notes(p, depletion_age, bequest):
    # Keep the wording in sync with notes() in CS1/partials/plan_tool.html
    if depletion_age is None:
        used_up = (f'If you keep your spending constant after age {p["last_age"]}, '
                   f'your overall savings will last beyond age {C.PLAN_HORIZON_AGE}.')
    else:
        used_up = (f'If you keep your spending constant after age {p["last_age"]}, '
                   f'your overall savings will be used up by age {depletion_age}.')
    if bequest is None or bequest < 0:
        left = f'If you pass on at age {p["bequest_age"]}, you will not leave a bequest.'
    else:
        left = f'If you pass on at age {p["bequest_age"]}, you will leave a bequest of {_money(bequest)}.'
    return [used_up, left]


def _plan_error(p, spending, inheritance_age=None, base_spending=None):
    """Error message if a spending plan is incomplete or not feasible, otherwise None.

    base_spending is passed when the participant entered changes in spending rather than spending.
    Keep the rules and wording in sync with planError() in CS1/partials/plan_tool.html
    """
    if any(amount is None for amount in spending):
        return 'Please enter a number for every year.'

    for year, age in enumerate(_plan_ages(p)):
        if spending[year] < 0:
            if base_spending:
                return (f'You cannot reduce your spending at age {age} by more than the '
                        f'{_money(base_spending[year])} you planned to spend in that year.')
            return f'Your spending at age {age} cannot be negative.'

    rows, _, _ = _plan_project(p, spending, inheritance_age)
    for row in rows:
        if row['total'] < 0:
            return (f'With these entries your total savings would be used up at age {row["age"]}, '
                    f'i.e. before the end of the {C.PLAN_YEARS} years. '
                    'You cannot spend more than you have: please reduce your spending in some of the years.')


def _plan_scenario_text(player: Player, timing):
    p = _plan_params(player)
    relation = 'father' if player.mother_father == 2 else 'mother'
    amount = _money(p['inheritance'])
    if timing == 'future':
        delay = p['inheritance_delay_years']
        years = '1 year' if delay == 1 else f'{delay} years'
        return (
            f'Suppose that today you learn that your {relation} has been diagnosed with a terminal disease. '
            f'You inherit {amount} after taxes from your {relation} in {years}. '
            'This is a one-time payment you had not expected until today.'
        )
    return (
        f'Suppose that today you learn that your {relation} passed away last night. '
        f'You inherit {amount} after taxes from your {relation} today. '
        'This is a one-time payment you had not expected until today.'
    )


def _plan_vars(player: Player, timing=None):
    """Template variables shared by the planning-tool pages."""
    p = _plan_params(player)
    ages = _plan_ages(p)
    inheritance_age = _plan_inheritance_age(p, timing)

    base_spending = _plan_base_spending(player)
    has_base = None not in base_spending
    base_rows, base_notes = [], []
    if has_base:
        base_rows, depletion_age, bequest = _plan_project(p, base_spending)
        base_notes = _plan_notes(p, depletion_age, bequest)

    years = []
    for year, age in enumerate(ages):
        row = dict(
            number=year + 1,
            age=age,
            income=_money(_plan_income(p, age)),
            inheritance=_money(p['inheritance'] if age == inheritance_age else 0),
            is_inheritance_year=age == inheritance_age,
        )
        if has_base:
            row.update(
                base_spend=_money(base_spending[year]),
                base_saving=_money(base_rows[year]['saving']),
                base_saving_negative=base_rows[year]['saving'] < 0,
                base_total=_money(base_rows[year]['total']),
            )
        years.append(row)

    # smallest range of the vertical axis of the graph, so that it does not rescale with every keystroke
    if player.layout == 'reframed' and has_base:
        chart_min_scale = max(base_spending)
    else:
        chart_min_scale = p['inheritance'] / 5

    work_years = sum(1 for age in ages if age < p['retirement_age'])
    return dict(
        testing=player.session.config['testing'],
        layout=player.layout,
        years=years,
        plan_years=C.PLAN_YEARS,
        work_years=work_years,
        retirement_years=C.PLAN_YEARS - work_years,
        current_age=p['current_age'],
        first_age=p['first_age'],
        last_age=p['last_age'],
        last_work_age=p['retirement_age'] - 1,
        retirement_age=p['retirement_age'],
        initial_wealth=_money(p['initial_wealth']),
        salary=_money(p['salary']),
        pension=_money(p['pension']),
        interest_percent=f'{p["interest_rate"] * 100:g}',
        base_notes=base_notes,
        chart_min_scale=chart_min_scale,
    )


def _plan_js_vars(player: Player, mode, fields, timing=None):
    """Data for CS1/partials/plan_tool.html.

    mode: 'baseline' (spending is entered), 'change' (change in spending is entered) or
    'level' (updated spending is entered).
    """
    p = _plan_params(player)
    return dict(
        mode=mode,
        dynamic=mode == 'baseline' or player.layout != 'natural_2',
        fields=fields,
        ages=_plan_ages(p),
        base_spend=_plan_base_spending(player) if mode != 'baseline' else [],
        initial_wealth=p['initial_wealth'],
        salary=p['salary'],
        pension=p['pension'],
        retirement_age=p['retirement_age'],
        interest_rate=p['interest_rate'],
        inheritance=p['inheritance'],
        inheritance_age=_plan_inheritance_age(p, timing),
        bequest_age=p['bequest_age'],
        horizon_age=C.PLAN_HORIZON_AGE,
        currency=C.DEFAULT_CURRENCY_SYMBOL,
    )


def _plan_scenario_vars(player: Player, scenario_number):
    timing = _plan_scenario_timing(player, scenario_number)
    context = _plan_vars(player, timing)
    context.update(
        scenario_number=scenario_number,
        scenario_text=_plan_scenario_text(player, timing),
        warning_field=f'{timing}_scenario_warning',
    )
    return context


def _plan_update_fields(player: Player, scenario_number):
    timing = _plan_scenario_timing(player, scenario_number)
    entered = 'spend' if player.layout == 'reframed' else 'change'
    return [f'{timing}_{entered}_y{i}' for i in PLAN_YEAR_NUMBERS]


def _plan_update_js_vars(player: Player, scenario_number):
    mode = 'level' if player.layout == 'reframed' else 'change'
    return _plan_js_vars(
        player, mode, _plan_update_fields(player, scenario_number),
        _plan_scenario_timing(player, scenario_number),
    )


def _plan_update_error(player: Player, values, scenario_number):
    p = _plan_params(player)
    inheritance_age = _plan_inheritance_age(p, _plan_scenario_timing(player, scenario_number))
    entries = [values.get(field) for field in _plan_update_fields(player, scenario_number)]
    if player.layout == 'reframed':
        return _plan_error(p, entries, inheritance_age)

    base_spending = _plan_base_spending(player)
    spending = [None if change is None else base + change for base, change in zip(base_spending, entries)]
    return _plan_error(p, spending, inheritance_age, base_spending)


def _plan_update_store(player: Player, scenario_number):
    """Derives the measure that was not entered (change or spending) and stores the projection."""
    p = _plan_params(player)
    timing = _plan_scenario_timing(player, scenario_number)
    spending = []
    for i, base in zip(PLAN_YEAR_NUMBERS, _plan_base_spending(player)):
        if player.layout == 'reframed':
            spend = getattr(player, f'{timing}_spend_y{i}')
            setattr(player, f'{timing}_change_y{i}', spend - base)
        else:
            spend = base + getattr(player, f'{timing}_change_y{i}')
            setattr(player, f'{timing}_spend_y{i}', spend)
        spending.append(spend)

    _plan_store_projection(player, timing, p, spending, _plan_inheritance_age(p, timing))


def _plan_store_projection(player: Player, prefix, p, spending, inheritance_age=None):
    _, depletion_age, bequest = _plan_project(p, spending, inheritance_age)
    if depletion_age is not None:
        setattr(player, f'{prefix}_depletion_age', depletion_age)
    if bequest is not None:
        setattr(player, f'{prefix}_bequest', round(bequest, 2))


# ------------------------------------------------------------------------------------------------------------
# ------------------------------------------- FUNCTIONS --------------------------------------------
# ------------------------------------------------------------------------------------------------------------
def creating_session(subsession: Subsession):
    if subsession.round_number == 1:
        # Between-subject cells: input layout x order of the two scenarios x framing of the own-inheritance follow-up.
        # The layout changes fastest, so that small sessions are balanced on it first.
        cells = [
            (layout, round_order, frame)
            for frame in [1, 2]
            for round_order in C.ROUND_ORDERS
            for layout in C.LAYOUTS
        ]

        for i, player in enumerate(subsession.get_players()):
            player.layout, player.round_order, player.inh_followup_frame = cells[i % len(cells)]
            player.mother_father = random.randint(1, 2)


# ------------------------------------------------------------------------------------------------------------
# ------------------------------------------------ PAGES --------------------------------------------
# ------------------------------------------------------------------------------------------------------------
class Instructions_WelcomeScreen(Page):
    template_name = 'CS1/Instructions_WelcomeScreen.html'
    form_model = 'player'
    form_fields = ['browser_first', 'prolific_id', 'isLeaving']

    @staticmethod
    def error_message(player: Player, value):
        prolific_id = (value.get('prolific_id') or '').strip()
        if not prolific_id:
            return {'prolific_id': 'Please enter your Prolific ID. Currently, the ID field is empty.'}
        if len(prolific_id) != 24:
            id_len = len(prolific_id)
            return {
                'prolific_id': (
                    'Your Prolific ID is not correct! The ID you inserted has {} characters. '
                    'The Prolific ID is 24 characters long.'
                ).format(id_len)
            }

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        return {'testing': player.session.config["testing"]}

class LeavePage(Page):
    template_name = 'CS1/LeavePage.html'
    @staticmethod
    def is_displayed(player: Player):
        return player.isLeaving

class BotScreening(Page):
    form_model = 'player'
    form_fields = ['recaptcha_response']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        return {
            'testing': player.session.config["testing"],
            'recaptcha_site_key': player.session.config.get('recaptcha_site_key', ''),
        }

    @staticmethod
    def error_message(player: Player, values):
        token = (values.get('recaptcha_response') or '').strip()
        if not token:
            player.recaptcha_verified = False
            return 'Please complete the CAPTCHA before continuing.'

        require_server_verification = bool(
            player.session.config.get('recaptcha_enforce_server_verification', True)
        )
        if not require_server_verification:
            player.recaptcha_verified = True
            return

        secret_key = str(player.session.config.get('recaptcha_secret_key') or '').strip()
        if not secret_key:
            if player.session.config.get('testing'):
                player.recaptcha_verified = True
                return
            player.recaptcha_verified = False
            return 'CAPTCHA verification is temporarily unavailable. Please contact the researcher.'

        verified, reason = _verify_recaptcha_token(token, secret_key)
        if not verified:
            player.recaptcha_verified = False
            if reason == 'expired':
                return 'Your CAPTCHA has expired. Please complete it again.'
            if reason in {'network', 'invalid_response'}:
                return 'CAPTCHA verification service is unavailable right now. Please try again.'
            return 'CAPTCHA verification failed. Please complete the CAPTCHA and try again.'

        player.recaptcha_verified = True

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.recaptcha_response = ''

class AttentionCheck1_AI(Page):
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS

    def before_next_page(player, timeout_happened):
        answer1 = player.can
        if answer1.upper() == "RED":
            player.attention1 = 1
        else:
            player.attention1 = 0

    form_model = 'player'
    form_fields = ['can']

class AttentionCheck2_AI(Page):

    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS 

    @staticmethod
    def vars_for_template(player: Player):
        insertWord = ', '.join(C.COMPLICATED_WORDS)
        return {
                'insertWord': insertWord,
        }
    @staticmethod
    def live_method(player, data):
        if not isinstance(data, list) or len(data) < 2:
            return
        try:
            tmpEntry = ast.literal_eval(player.AI_Test2)
            if not isinstance(tmpEntry, list):
                tmpEntry = []
        except (ValueError, SyntaxError):
            tmpEntry = []
        tmpEntry.append(data[0])
        player.AI_Test2 = str(tmpEntry)

        if isinstance(data[1], str) and data[1].startswith("delete"):
            print('delete')
            player.ComplicatedWord_Corrections += 1
            print(player.ComplicatedWord_Corrections)

    form_model = 'player'
    form_fields = ['words']

class AttentionCheck3_AI(Page):

    def is_displayed(player):
        return player.round_number == 1

    def before_next_page(player, timeout_happened):
        if player.lines == 1:
            player.attention3 = 1
        else:
            player.attention3 = 0

    form_model = 'player'
    form_fields = ['lines']


class AttentionCheck4_AI(Page):

    def is_displayed(player):
        return player.round_number == 1

    def before_next_page(player, timeout_happened):
        if player.cafewall == 2:
            player.attention4 = 1
        else:
            player.attention4 = 0
        if player.attention3 == 1 and player.attention4 == 1:
            player.checks = 1
        else:
            player.checks = 0

    form_model = 'player'
    form_fields = ['cafewall']


class AttentionCheckResult(Page):
    @staticmethod
    def is_displayed(player: Player):
        # return not player.session.config["testing"] and player.round_number == 1
        return player.round_number == 1

# ------------------------------------------------------------------------------------------------------------
# ---------------------------------------- LIFECYCLE PLANNING TOOL -------------------------------------------
# ------------------------------------------------------------------------------------------------------------
class Plan_Intro(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return _plan_vars(player)


class Plan_Baseline(Page):
    form_model = 'player'
    form_fields = [
        'base_spend_y1', 'base_spend_y2', 'base_spend_y3', 'base_spend_y4',
        'base_spend_y5', 'base_spend_y6', 'base_spend_y7', 'base_spend_y8']

    @staticmethod
    def vars_for_template(player: Player):
        return _plan_vars(player)

    @staticmethod
    def js_vars(player: Player):
        return _plan_js_vars(player, 'baseline', Plan_Baseline.form_fields)

    @staticmethod
    def error_message(player: Player, values):
        return _plan_error(_plan_params(player), [values.get(field) for field in Plan_Baseline.form_fields])

    @staticmethod
    def live_method(player: Player, data):
        _append_keylog_event(player, 'plan_keylog', data)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        _plan_store_projection(player, 'base', _plan_params(player), _plan_base_spending(player))


# The two scenarios (inheritance today / in the future) are shown in the order given by player.round_order.
class Plan_Scenario_1(Page):
    template_name = 'CS1/Plan_Scenario.html'
    form_model = 'player'

    @staticmethod
    def get_form_fields(player: Player):
        return [f'{_plan_scenario_timing(player, 1)}_scenario_warning']

    @staticmethod
    def vars_for_template(player: Player):
        return _plan_scenario_vars(player, 1)


class Plan_Update_1(Page):
    template_name = 'CS1/Plan_Update.html'
    form_model = 'player'

    @staticmethod
    def get_form_fields(player: Player):
        return _plan_update_fields(player, 1)

    @staticmethod
    def vars_for_template(player: Player):
        return _plan_scenario_vars(player, 1)

    @staticmethod
    def js_vars(player: Player):
        return _plan_update_js_vars(player, 1)

    @staticmethod
    def error_message(player: Player, values):
        return _plan_update_error(player, values, 1)

    @staticmethod
    def live_method(player: Player, data):
        _append_keylog_event(player, 'plan_keylog', data)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        _plan_update_store(player, 1)


class Plan_Scenario_2(Page):
    template_name = 'CS1/Plan_Scenario.html'
    form_model = 'player'

    @staticmethod
    def get_form_fields(player: Player):
        return [f'{_plan_scenario_timing(player, 2)}_scenario_warning']

    @staticmethod
    def vars_for_template(player: Player):
        return _plan_scenario_vars(player, 2)


class Plan_Update_2(Page):
    template_name = 'CS1/Plan_Update.html'
    form_model = 'player'

    @staticmethod
    def get_form_fields(player: Player):
        return _plan_update_fields(player, 2)

    @staticmethod
    def vars_for_template(player: Player):
        return _plan_scenario_vars(player, 2)

    @staticmethod
    def js_vars(player: Player):
        return _plan_update_js_vars(player, 2)

    @staticmethod
    def error_message(player: Player, values):
        return _plan_update_error(player, values, 2)

    @staticmethod
    def live_method(player: Player, data):
        _append_keylog_event(player, 'plan_keylog', data)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        _plan_update_store(player, 2)


# ------------------------------------------------------------------------------------------------------------
# ----------------------------------- RESULTS + PARTICIPANT INFORMATION --------------------------------------
# ------------------------------------------------------------------------------------------------------------
class ResultsWaitPage(WaitPage):
    pass


def _qualifies_for_inheritance_followup(player: Player):
    mother_age = player.field_maybe_none('Demographics_Mother')
    father_age = player.field_maybe_none('Demographics_Father')
    mother_inh = player.field_maybe_none('Demographics_MotherInheritance')
    father_inh = player.field_maybe_none('Demographics_FatherInheritance')


    mother_qualifies = (
        mother_age is not None and
        mother_inh is not None and
        mother_inh > 0 and
        mother_inh != 42
    )
    father_qualifies = (
        father_age is not None and
        father_inh is not None and
        father_inh > 0 and
        father_inh != 42
    )
    return mother_qualifies or father_qualifies


def _inh_frame_vars(player: Player):
    saving_frame = player.inh_followup_frame == 2
    return dict(saving_frame=saving_frame, frame_word='saving' if saving_frame else 'spending')

class Demographics_1(Page):
    form_model = 'player'
    form_fields = [
        "Demographics_Age",
        "Demographics_AgeExpectation",
        "Demographics_Sex",
        "Demographics_Children",
        "Demographics_Education",
        "Demographics_Mother",
        "Demographics_Father",
        "Demographics_MotherInheritance",
        "Demographics_FatherInheritance"]

    @staticmethod
    def vars_for_template(player: Player):
        return {'testing': player.session.config["testing"]}
    

class Inh_Followup_A(Page):
    form_model = 'player'
    form_fields = ['inh_followup_effect']

    @staticmethod
    def is_displayed(player: Player):
        return _qualifies_for_inheritance_followup(player)

    @staticmethod
    def vars_for_template(player: Player):
        existing_order = player.field_maybe_none('inh_followup_effect_order')
        if not existing_order:
            order = ['1', '2']
            random.shuffle(order)
            player.inh_followup_effect_order = ','.join(order)
        else:
            order = existing_order.split(',')
        return {
            'testing': player.session.config['testing'],
            'order': order,
            'inh_followup_effect': player.field_maybe_none('inh_followup_effect'),
            **_inh_frame_vars(player),
        }

    @staticmethod
    def error_message(player: Player, values):
        if values.get('inh_followup_effect') is None:
            return {'inh_followup_effect': 'This field is required.'}


class Inh_Followup_B(Page):
    form_model = 'player'
    form_fields = ['inh_followup_thought']

    @staticmethod
    def is_displayed(player: Player):
        return (
            _qualifies_for_inheritance_followup(player) and
            player.field_maybe_none('inh_followup_effect') == 2
        )

    @staticmethod
    def vars_for_template(player: Player):
        return {'testing': player.session.config['testing'],
                'inh_followup_thought': player.field_maybe_none('inh_followup_thought'),
                **_inh_frame_vars(player),
        }

    @staticmethod
    def error_message(player: Player, values):
        if values.get('inh_followup_thought') is None:
            return {'inh_followup_thought': 'This field is required.'}


class Inh_Followup_C(Page):
    form_model = 'player'
    form_fields = ['inh_followup_why']

    @staticmethod
    def is_displayed(player: Player):
        return (
            _qualifies_for_inheritance_followup(player) and
            player.field_maybe_none('inh_followup_effect') == 2 and
            player.field_maybe_none('inh_followup_thought') == 2
        )

    @staticmethod
    def vars_for_template(player: Player):
        return {'testing': player.session.config['testing'], **_inh_frame_vars(player)}

    @staticmethod
    def error_message(player: Player, values):
        if not values.get('inh_followup_why') or len(values.get('inh_followup_why', '').strip()) < 1:
            return {'inh_followup_why': 'This field is required.'}


class Inh_Followup_D(Page):
    form_model = 'player'
    form_fields = [
        'inh_followup_reason_i',
        'inh_followup_reason_ii',
        'inh_followup_reason_iii',
        'inh_followup_reason_iv',
        'inh_followup_reason_v',
        'inh_followup_reason_vi',
        'inh_followup_reason_vii',
        'inh_followup_reason_other',
    ]

    @staticmethod
    def is_displayed(player: Player):
        return (
            _qualifies_for_inheritance_followup(player) and
            player.field_maybe_none('inh_followup_effect') == 2 and
            player.field_maybe_none('inh_followup_thought') == 2
        )

    @staticmethod
    def vars_for_template(player: Player):
        reasons = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii']
        existing_order = player.field_maybe_none('inh_followup_reason_order')
        if existing_order:
            reasons = existing_order.split(',')
        else:
            random.shuffle(reasons)
            player.inh_followup_reason_order = ','.join(reasons)

        likert_choices = [
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important'],
        ]

        reason_labels = {
            'i': 'I keep future payments such as this one in a different budget than the budget that I use to determine my current spending',
            'ii': 'It would be morally wrong to spend the inheritance before I receive it',
            'iii': "I wouldn't know how to increase spending using the inheritance I receive in the future",
            'iv': 'I cannot increase spending before receiving the inheritance because I have little savings and cannot access credit',
            'v': 'Spending the inheritance in advance would require me to borrow, which I do not want to do',
            'vi': 'I consider that there is too much uncertainty in the timing and value of the inheritance',
            'vii': 'I worry that my parent would reduce my inheritance if I spent some of it in advance',
        }

        reason_rows = []
        for r in reasons:
            field_name = f'inh_followup_reason_{r}'
            reason_rows.append(dict(
                name=field_name,
                label=reason_labels[r],
                choices=likert_choices,
                value=player.field_maybe_none(field_name),
            ))

        return {
            'testing': player.session.config['testing'],
            'reason_rows': reason_rows,
            **_inh_frame_vars(player),
        }

    @staticmethod
    def error_message(player: Player, values):
        for field in ['inh_followup_reason_i', 'inh_followup_reason_ii', 'inh_followup_reason_iii',
                      'inh_followup_reason_iv', 'inh_followup_reason_v', 'inh_followup_reason_vi',
                      'inh_followup_reason_vii']:
            val = values.get(field)
            if val is not None:
                setattr(player, field, val)

        errors = {}
        for field in ['inh_followup_reason_i', 'inh_followup_reason_ii', 'inh_followup_reason_iii',
                      'inh_followup_reason_iv', 'inh_followup_reason_v', 'inh_followup_reason_vi',
                      'inh_followup_reason_vii']:
            if values.get(field) is None:
                errors[field] = 'This field is required.'
        return errors if errors else None


class Feedback(Page):
    form_model = 'player'
    form_fields = ['OpenFeedback']


class LinkToProlific(Page):
    form_model = 'player'
    template_name = 'CS1/LinkToProlific.html'

class testing(Page):
    form_model = 'player'

#XX

page_sequence = [
    Instructions_WelcomeScreen, LeavePage,

    AttentionCheck3_AI, AttentionCheck4_AI, AttentionCheckResult,

    Plan_Intro, Plan_Baseline,

    Plan_Scenario_1, Plan_Update_1,
    Plan_Scenario_2, Plan_Update_2,

    AttentionCheck1_AI, AttentionCheck2_AI, BotScreening,

    Demographics_1, Inh_Followup_A, Inh_Followup_B, Inh_Followup_C, Inh_Followup_D,

    Feedback, LinkToProlific]
