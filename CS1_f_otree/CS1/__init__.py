from otree.api import *
import ast
import json
import math
import random
from urllib.parse import urlencode
from urllib.request import urlopen

doc = """
This study is about the effect of emotional affection in inheritances on consumption.
It measures how much participants understand being able to move cash flows and the effect different levels of 
emotional affection have on consumption.

This survey asks questions from participants of the survey in three sections: 
Firstly, it asks all participants the same basic information questions.
Secondly, it divides participants into 8 groups with different questions. 
8 groups consist of [Now, Future] * [No emotional attachment, Large emotional attachment] * [Certain, Uncertain] * [Additional Info, No Additional Info]
Thirdly, it moves all participants back to the same main group where each participant has 
the same questions in randomized order.
"""


class C(BaseConstants):
    NAME_IN_URL = 'CS1'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    MIN_TEXT_LENGTH = 1
    KEYLOG_EVENT_CAP = 2000
    ALLOCATION_TARGET_PCT = 100.0
    ALLOCATION_TOLERANCE_PCT = 0.1
    REACTION_SPEND_MIN = -5000
    REACTION_SPEND_MAX = 75000
    REACTION_SPEND_TOTAL_MAX = 75000
    CURRENCIES = {'AUD': 'A$', 'GBP': '£', 'EUR': '€', 'USD': '$'}
    COMPLICATED_WORDS = ['Schadenfreude', 'Bourgeoisie', 'Worcestershire']
    # Change DEFAULT_CURRENCY if looking to change the currency of the experiment.
    DEFAULT_CURRENCY = 'GBP' # ADJUST THIS ONE
    DEFAULT_CURRENCY_SYMBOL = CURRENCIES[DEFAULT_CURRENCY]


RECAPTCHA_VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'


# Divide players into 4 groups in the order of the list 'groups' below.
class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    # CREATING SESSION -
    assigned_group = models.StringField()
    prolific_id = models.StringField(blank=True, label='Your Prolific ID')
    spend_save = models.IntegerField(initial=0)  # spend = 1, save = 2
    future_present = models.IntegerField()  # future = 1, present = 2
    emotional_attachment = models.IntegerField(initial=0)  # tax (no attachment) = 1, parent (large attachment) = 2
    uncertainty = models.IntegerField(initial=0) # uncertainty = 1, certainty = 2
    scenario_info = models.BooleanField()
    info_subtype = models.StringField(initial='0')  # disposable income = '5', net worth = '6', borrowing = '7', example all combo '567', none = '0' 
    mother_father = models.IntegerField(initial=0)  # mother = 1, father = 2
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
    reactions2_keylog = models.LongStringField(initial='{}')
    reactions3_keylog = models.LongStringField(initial='{}')
    reactions6_keylog = models.LongStringField(initial='{}')
    keylog_timing_tuples = models.LongStringField(initial='')
    checks = models.IntegerField(initial=2)

    # Leave Page
    isLeaving = models.BooleanField(choices=((True, 'leaving'), (False, 'notleaving')),
                                    initial=0)

    # INSTRUCTIONS_WELCOMESCREEN
    browser_first = models.CharField()
    # INTRODUCTORY SURVEY
    survey2_fieldorder = models.StringField()
    # ------------------------------------------------------------------------------------------------------------
    # ---------------------------------------- INTRODUCTORY SURVEY --------------------------------------------
    # ------------------------------------------------------------------------------------------------------------
    survey1_spend = models.IntegerField(
        label = "What percentage of your disposable income (your income after taxes) do you spend in an average month?",
        min=0, max=100, blank=False)

    survey1_save = models.IntegerField(
        label = "What percentage of your disposable income (your income after taxes) do you save in an average month?",
        min=0, max=100, blank=False)
    
    survey2_DisposableIncome = models.IntegerField(
        label="Your disposable income now",
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important']
        ],
        blank=True
    )

    survey2_NetWealth = models.IntegerField(
        label="Your current net wealth (your wealth minus any debt, e.g., credit card debt or mortgages)",
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important']
        ],
        blank=True
    )

    survey2_FutureIncome = models.IntegerField(
        label="Your expected regular future income until retirement (e.g., from your job).",
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important']
        ],
        blank=True
    )
    survey2_RetirementIncome = models.IntegerField(
        label="Your expected regular income after retirement (e.g., from pensions and your retirement savings).",
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important']
        ],
        blank=True
    )
    survey2_IrregularPayments = models.IntegerField(
        label="Expected gifts, inheritances, and irregular payments from others.",
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important']
        ],
        blank=True
    )
    survey2_InterestRates = models.IntegerField(
        label="Interest rates or the return on savings (including stocks and changes in housing prices).",
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important']
        ],
        blank=True
    )
    survey2_Inflation = models.IntegerField(
        label="Inflation",
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important']
        ],
        blank=True
    )
    survey2_CreditAccess = models.IntegerField(
        label="Your ability to access credit (if needed)",
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important']
        ],
        blank=True
    )
    survey2_Caution = models.IntegerField(
        label="Caution (preference to avoid risk)",
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important']
        ],
        blank=True
    )
    survey2_Impatience = models.IntegerField(
        label="Impatience (preference to spend more now rather than later)",
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important']
        ],
        blank=True
    )

    survey2_TextBox = models.StringField(
        label="Please list other relevant factors (if any) here:",
        blank=True)

    
    # Survey 3 (Pre-Dem):
    Demographics_Household_Income = models.IntegerField(
        label='Which of the following best describes your total household income last year?',
        widget=widgets.RadioSelect(),
        choices=[
            [0, f"{C.DEFAULT_CURRENCY_SYMBOL}0"],
            [1, f"Less than {C.DEFAULT_CURRENCY_SYMBOL}10,000"],
            [2, f"Between {C.DEFAULT_CURRENCY_SYMBOL}10,000 and {C.DEFAULT_CURRENCY_SYMBOL}20,000"],
            [3, f"Between {C.DEFAULT_CURRENCY_SYMBOL}20,000 and {C.DEFAULT_CURRENCY_SYMBOL}40,000"],
            [4, f"Between {C.DEFAULT_CURRENCY_SYMBOL}40,000 and {C.DEFAULT_CURRENCY_SYMBOL}80,000"],
            [5, f"Between {C.DEFAULT_CURRENCY_SYMBOL}80,000 and {C.DEFAULT_CURRENCY_SYMBOL}160,000"],
            [6, f"Between {C.DEFAULT_CURRENCY_SYMBOL}160,000 and {C.DEFAULT_CURRENCY_SYMBOL}320,000"],
            [7, f"{C.DEFAULT_CURRENCY_SYMBOL}320,000 or more"],
            [8, "Prefer not to say"]
        ])

    Demographics_LiquidWealth = models.IntegerField(
        label='How much easily accessible savings do you own (e.g., money on bank accounts, investments in mutual funds or stocks, or other financial wealth)?',
        widget=widgets.RadioSelect(),
        choices=[
            [0, f"{C.DEFAULT_CURRENCY_SYMBOL}0"],
            [1, f"Less than {C.DEFAULT_CURRENCY_SYMBOL}5,000"],
            [2, f"Between {C.DEFAULT_CURRENCY_SYMBOL}5,000 and {C.DEFAULT_CURRENCY_SYMBOL}10,000"],
            [3, f"Between {C.DEFAULT_CURRENCY_SYMBOL}10,000 and {C.DEFAULT_CURRENCY_SYMBOL}15,000"],
            [4, f"Between {C.DEFAULT_CURRENCY_SYMBOL}15,000 and {C.DEFAULT_CURRENCY_SYMBOL}20,000"],
            [5, f"Between {C.DEFAULT_CURRENCY_SYMBOL}20,000 and {C.DEFAULT_CURRENCY_SYMBOL}25,000"],
            [6, f"{C.DEFAULT_CURRENCY_SYMBOL}25,000 or more"],
            [7, "Prefer not to say"]
        ])

    Demographics_IlliquidWealth = models.IntegerField(
        label='How much other wealth do you own (e.g., value of your home, other real estate you own, or other non-financial assets)?',
        widget=widgets.RadioSelect(),
        choices=[
            [0, f"{C.DEFAULT_CURRENCY_SYMBOL}0"],
            [1, f"Less than {C.DEFAULT_CURRENCY_SYMBOL}20,000"],
            [2, f"Between {C.DEFAULT_CURRENCY_SYMBOL}20,000 and {C.DEFAULT_CURRENCY_SYMBOL}40,000"],
            [3, f"Between {C.DEFAULT_CURRENCY_SYMBOL}40,000 and {C.DEFAULT_CURRENCY_SYMBOL}80,000"],
            [4, f"Between {C.DEFAULT_CURRENCY_SYMBOL}80,000 and {C.DEFAULT_CURRENCY_SYMBOL}160,000"],
            [5, f"Between {C.DEFAULT_CURRENCY_SYMBOL}160,000 and {C.DEFAULT_CURRENCY_SYMBOL}320,000"],
            [6, f"Between {C.DEFAULT_CURRENCY_SYMBOL}320,000 and {C.DEFAULT_CURRENCY_SYMBOL}640,000"],
            [7, f"{C.DEFAULT_CURRENCY_SYMBOL}640,000 or more"],
            [8, "Prefer not to say"]
        ])

    Demographics_DebtWealth = models.IntegerField(
        label='How much debt do you owe (e.g., mortgages, credit card debt, or lines of credit)?',
        widget=widgets.RadioSelect(),
        choices=[
            [0, f"{C.DEFAULT_CURRENCY_SYMBOL}0"],
            [1, f"Less than {C.DEFAULT_CURRENCY_SYMBOL}20,000"],
            [2, f"Between {C.DEFAULT_CURRENCY_SYMBOL}20,000 and {C.DEFAULT_CURRENCY_SYMBOL}40,000"],
            [3, f"Between {C.DEFAULT_CURRENCY_SYMBOL}40,000 and {C.DEFAULT_CURRENCY_SYMBOL}80,000"],
            [4, f"Between {C.DEFAULT_CURRENCY_SYMBOL}80,000 and {C.DEFAULT_CURRENCY_SYMBOL}160,000"],
            [5, f"Between {C.DEFAULT_CURRENCY_SYMBOL}160,000 and {C.DEFAULT_CURRENCY_SYMBOL}320,000"],
            [6, f"Between {C.DEFAULT_CURRENCY_SYMBOL}320,000 and {C.DEFAULT_CURRENCY_SYMBOL}640,000"],
            [7, f"{C.DEFAULT_CURRENCY_SYMBOL}640,000 or more"],
            [8, "Prefer not to say"]
        ])

    Demographics_LiquidityConstraints_1 = models.IntegerField(
        label='Please assess the following statement: "I would be able to spend more today by using my disposable income."',
        widget=widgets.RadioSelectHorizontal,
        choices=[
            [1, 'Strongly disagree'],
            [2, 'Disagree'],
            [3, 'Neutral'],
            [4, 'Agree'],
            [5, 'Strongly agree'],
            [6, 'Do not know'],
            [7, 'Prefer not to say'],
        ])

    Demographics_LiquidityConstraints_2 = models.IntegerField(
        label='Please assess the following statement: "I would be able to spend more today by using my net wealth (e.g., savings invested in bank accounts or stocks)."',
        widget=widgets.RadioSelectHorizontal,
        choices=[
            [1, 'Strongly disagree'],
            [2, 'Disagree'],
            [3, 'Neutral'],
            [4, 'Agree'],
            [5, 'Strongly agree'],
            [6, 'Do not know'],
            [7, 'Prefer not to say'],
        ])

    Demographics_LiquidityConstraints_3 = models.IntegerField(
        label='Please assess the following statement: "I would be able to spend more today by borrowing money (e.g., using consumer credit).”',
        widget=widgets.RadioSelectHorizontal,
        choices=[
            [1, 'Strongly disagree'],
            [2, 'Disagree'],
            [3, 'Neutral'],
            [4, 'Agree'],
            [5, 'Strongly agree'],
            [6, 'Do not know'],
            [7, 'Prefer not to say'],
        ])


    scenario_warning = models.IntegerField(initial=0) # 1 = pressed confirm before 10 seconds, 0 = waited 10 seconds or pressed cancel

    # COMPREHENSION TEST
    comp_q1_timing = models.IntegerField(
        label='When is the payment made?',
        choices=[
            [1, 'Today'],
            [2, 'In 2 years'],
            [3, 'In 4 years'],
        ],
        widget=widgets.RadioSelect,
    )

    comp_q2_amount = models.IntegerField(
        label='How large is the payment?',
        choices=[
            [1, f'{C.DEFAULT_CURRENCY_SYMBOL}5 000'],
            [2, f'{C.DEFAULT_CURRENCY_SYMBOL}25 000'],
            [3, f'{C.DEFAULT_CURRENCY_SYMBOL}50 000'],
        ],
        widget=widgets.RadioSelect,
    )

    comp_q3_reason = models.IntegerField(
        label='Why are you receiving the payment?',
        choices=[
            [1, 'Salary'],
            [2, 'Inheritance'],
            [3, 'Tax refund'],
        ],
        widget=widgets.RadioSelect,
    )

    comp_failed_attempts = models.IntegerField(initial=0)
    comp_wrong_history = models.LongStringField(initial='')

    
    # ------------------------------------------------------------------------------------------------------------
    # --------------------------------------------- REACTIONS --------------------------------------------
    # ------------------------------------------------------------------------------------------------------------

    # Reactions_1
    react3 = models.LongStringField(
        label='How will you adjust your behavior in Year 1 and Year 2 (if at all)? Please consider your spending and saving, as well as your career plans (e.g., would you work more or less hours, or retire).', blank=False)

    react4 = models.LongStringField(
        label='How will you adjust your behavior in Year 3 and Year 4 (if at all)? Please consider your spending and saving, as well as your career plans (e.g., would you work more or less hours, or retire).', blank=False)

    react5 = models.LongStringField(
        label='How will you adjust your behavior for the rest of your life after Year 4 (if at all)? Please consider your spending and saving, as well as your career plans (e.g., would you work more or less hours, or retire).', blank=False)

    """
    react6 = models.LongStringField(
        label='How does this scenario affect your career plans in Year 1 and Year 2 (if at all, e.g., would you work more or less hours, or retire)?', blank=False)

    react7 = models.LongStringField(
        label='How does this scenario affect your career plans in Year 3 and Year 4 (if at all, e.g., would you work more or less hours, or retire)?', blank=False)

    react8 = models.LongStringField(
        label='How does this scenario affect your career plans for the rest of your life after Year 4 (if at all, e.g., would you work more or less hours, or retire)?', blank=False)
    """
    # Reactions_2
    react_yr1 = models.IntegerField(
        label='Year 1 from now:', min=C.REACTION_SPEND_MIN, max=C.REACTION_SPEND_MAX, blank=False)

    react_yr2 = models.IntegerField(
        label='Year 2 from now:', min=C.REACTION_SPEND_MIN, max=C.REACTION_SPEND_MAX, blank=False)

    react_yr3 = models.IntegerField(
        label='Year 3 from now:', min=C.REACTION_SPEND_MIN, max=C.REACTION_SPEND_MAX, blank=False)

    react_yr4 = models.IntegerField(
        label='Year 4 from now:', min=C.REACTION_SPEND_MIN, max=C.REACTION_SPEND_MAX, blank=False)

    react_yr5 = models.IntegerField(
        label='Rest of your life (total):', min=C.REACTION_SPEND_MIN, max=C.REACTION_SPEND_MAX, blank=False)


    react_yr1_initial = models.IntegerField(blank=True)
    react_yr2_initial = models.IntegerField(blank=True)
    react_yr3_initial = models.IntegerField(blank=True)
    react_yr4_initial = models.IntegerField(blank=True)
    react_yr5_initial = models.IntegerField(blank=True)

    # Reactions_2_Followup_B
    react9 = models.LongStringField(
        label='Please explain briefly why you would adjust your spending like this over the upcoming years:', blank=True)
    
    # Reactions_2_Follow-up_A1
    react_followup1 = models.LongStringField(blank=True, label='You expressed that the future payment affects your spending plans mostly after you receive the payment, not before. Briefly explain why.')

    # Reactions_2_Follow-up_A2
    react_followup2_i = models.IntegerField(blank=True, min=1, max=5, label='I keep future payments such as this one in a different budget than the budget that I use to determine my current spending')
    react_followup2_ii = models.IntegerField(blank=True, min=1, max=5, label='It would be morally wrong to spend the money before I receive it')
    react_followup2_iii = models.IntegerField(blank=True, min=1, max=5, label='I wouldn\'t know how to increase spending using the money I receive in the future')
    react_followup2_iv = models.IntegerField(blank=True, min=1, max=5, label='I cannot increase spending before receiving the money because I have little savings and cannot access credit')
    react_followup2_v = models.IntegerField(blank=True, min=1, max=5, label='Spending money in advance would require me to borrow, which I do not want to do')
    react_followup2_vi = models.IntegerField(blank=True, min=1, max=5, label='I consider that there is too much uncertainty in the timing and value of the payment')
    react_followup2_other = models.LongStringField(blank=True, label='Other reason. Please specify:')
    react_followup2_order = models.LongStringField(blank=True)

    # Reactions_3
    react_durable_yr1 = models.FloatField(
        label='Durable goods (e.g., cars, furniture, jewelry, etc.):', min=None, blank=False)
    react_durable_yr2 = models.FloatField(min=None, blank=False)
    react_durable_yr3 = models.FloatField(min=None, blank=False)

    react_nondurable_services_yr1 = models.FloatField(
        label='Non-durable goods and services that do not last for a long time (e.g., food, clothes, vacation, etc.):', min=None, blank=False)
    react_nondurable_services_yr2 = models.FloatField(min=None, blank=False)
    react_nondurable_services_yr3 = models.FloatField(min=None, blank=False)

    # Randomized display order of the durable vs. non-durable rows shown on Reactions_3
    reac3_order_dur_nondur = models.StringField(blank=True)

    # Reactions_4
    react_alloc_self_yr1 = models.FloatField(label='yourself', min=0, max=100, blank=False)
    react_alloc_self_yr2 = models.FloatField(min=0, max=100, blank=False)
    react_alloc_self_yr3 = models.FloatField(min=0, max=100, blank=False)

    react_alloc_parents_yr1 = models.FloatField(label='your parents', min=0, max=100, blank=False)
    react_alloc_parents_yr2 = models.FloatField(min=0, max=100, blank=False)
    react_alloc_parents_yr3 = models.FloatField(min=0, max=100, blank=False)

    react_alloc_other_family_yr1 = models.FloatField(label='other family (e.g., children) or friends', min=0, max=100, blank=False)
    react_alloc_other_family_yr2 = models.FloatField(min=0, max=100, blank=False)
    react_alloc_other_family_yr3 = models.FloatField(min=0, max=100, blank=False)

    react_alloc_others_yr1 = models.FloatField(label='others (e.g., donations to a charity)', min=0, max=100, blank=False)
    react_alloc_others_yr2 = models.FloatField(min=0, max=100, blank=False)
    react_alloc_others_yr3 = models.FloatField(min=0, max=100, blank=False)

    # Reactions_5
    react20 = models.LongStringField(
        label='How (if at all) does your emotional response to this scenario affect your spending decisions?', blank=False)

    react21_yr1 = models.IntegerField(
        label='Years 1 and 2 from now:', widget=widgets.RadioSelect(),
        choices=[
            [1, 'Inappropriate'],
            [2, 'Neutral'],
            [3, 'Appropriate'],
        ])
    react21_yr2 = models.IntegerField(
        label='Years 3 and 4 from now:', widget=widgets.RadioSelect(),
        choices=[
            [1, 'Inappropriate'],
            [2, 'Neutral'],
            [3, 'Appropriate'],
        ])
    react21_yr3 = models.IntegerField(
        label='Rest of your life:', widget=widgets.RadioSelect(),
        choices=[
            [1, 'Inappropriate'],
            [2, 'Neutral'],
            [3, 'Appropriate'],
        ])
    
    react22_yr1 = models.IntegerField(
        label='Years 1 and 2 from now:', widget=widgets.RadioSelect(),
        choices=[
            [1, 'Inappropriate'],
            [2, 'Neutral'],
            [3, 'Appropriate'],
        ])
    react22_yr2 = models.IntegerField(
        label='Years 3 and 4 from now:', widget=widgets.RadioSelect(),
        choices=[
            [1, 'Inappropriate'],
            [2, 'Neutral'],
            [3, 'Appropriate'],
        ])
    react22_yr3 = models.IntegerField(
        label='Rest of your life:', widget=widgets.RadioSelect(),
        choices=[
            [1, 'Inappropriate'],
            [2, 'Neutral'],
            [3, 'Appropriate'],
        ])
    
    react23_yr1 = models.IntegerField(
        label='Years 1 and 2 from now:', widget=widgets.RadioSelect(),
        choices=[
            [1, 'Inappropriate'],
            [2, 'Neutral'],
            [3, 'Appropriate'],
        ])
    react23_yr2 = models.IntegerField(
        label='Years 3 and 4 from now:', widget=widgets.RadioSelect(),
        choices=[
            [1, 'Inappropriate'],
            [2, 'Neutral'],
            [3, 'Appropriate'],
        ])
    react23_yr3 = models.IntegerField(
        label='Rest of your life:', widget=widgets.RadioSelect(),
        choices=[
            [1, 'Inappropriate'],
            [2, 'Neutral'],
            [3, 'Appropriate'],
        ])
    react23_why = models.LongStringField(
        label='Explain briefly why you/your parents/others would think increasing spending on yourself in the different periods is (not) appropriate.', blank=False
    )

    # Reactions_6
    react_uncertainty_timing = models.IntegerField(
        label='Did you assume there is any uncertainty about the timing of the payment?',
        widget=widgets.RadioSelect(),
        choices=[
            [1, 'No uncertainty'],
            [2, 'Slightly uncertain'],
            [3, 'Moderately uncertain'],
            [4, 'Uncertain'],
            [5, 'Very uncertain'],
        ])

    react_uncertainty_amount = models.IntegerField(
        label='Did you assume there is any uncertainty about the amount of the payment?',
        widget=widgets.RadioSelect(),
        choices=[
            [1, 'No uncertainty'],
            [2, 'Slightly uncertain'],
            [3, 'Moderately uncertain'],
            [4, 'Uncertain'],
            [5, 'Very uncertain'],
        ])


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

    # Demographics 2
    Demographics_RiskAversion = models.IntegerField(
        label='In general, how willing or unwilling are you to take risks? Please select a category between 1 ("Completely unwilling to take risks") to 7 ("Very willing to take risks").',
        choices=range(1, 8),
        initial=None,
        widget=widgets.RadioSelectHorizontal()
    )

    Demographics_Sacrifice = models.IntegerField(
        label='In general, how willing or unwilling are you to give up something that is beneficial for you today in order to benefit more from that in the future? Please select a category between 1 ("Completely unwilling to give up") to 7 ("Very willing to give up").',
        choices = range(1, 8),
        initial = None,
        widget = widgets.RadioSelectHorizontal()
    )

    Demographics_FinInterest = models.IntegerField(
        label='Are you interested in financial markets? Please select a category between 1 ("not at all") and 7 ("very much").',
        choices=range(1, 8),
        initial=None,
        widget=widgets.RadioSelectHorizontal()
    )

    Demographics_PurchaseRegret = models.IntegerField(
        label='People sometimes buy things that they later wish they had not bought. How often do you or other household members make purchases that you later regret?',
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Never'],
            [2, 'Rarely'],
            [3, 'Sometimes'],
            [4, 'Often'],
            [5, 'Very often'],
        ])
    
    Demographics_Debt = models.IntegerField(
        verbose_name='Please assess the following statement: "Debt is an integral part of life today." Please select a category between 1 (“Strongly disagree”) to 5 (“Strongly agree”).',
        choices=range(1, 6),
        initial=None,
        widget=widgets.RadioSelectHorizontal(),
        blank=False)

    Demographics_DebtAverage = models.IntegerField(
        verbose_name='What do you think, how does the average participant in this survey rate the following statement: "There is no excuse for borrowing money." Please select a category between 1 (“Strongly disagree”) to 5 (“Strongly agree”).',
        choices=range(1, 6),
        initial=None,
        widget=widgets.RadioSelectHorizontal(),
        blank=False)

    Demographics_Anxious = models.IntegerField(
        label='"Thinking about my personal finances can make me feel anxious."',
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Strongly disagree'],
            [2, 'Disagree'],
            [3, 'Neutral'],
            [4, 'Agree'],
            [5, 'Strongly agree'],
        ])

    Demographics_Choices = models.IntegerField(
        label='"I carefully think about the time spent, effort, and cost resulting from choices I make."',
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Strongly disagree'],
            [2, 'Disagree'],
            [3, 'Neutral'],
            [4, 'Agree'],
            [5, 'Strongly agree'],
        ])

    Demographics_Knowledge = models.IntegerField(
        label='"I know a lot about investing into stocks."',
        widget=widgets.RadioSelect,
        choices=[
            [1, 'Strongly disagree'],
            [2, 'Disagree'],
            [3, 'Neutral'],
            [4, 'Agree'],
            [5, 'Strongly agree'],
        ])

    # Demographics 3
    interest_rate_inflation = models.IntegerField(
        label='Imagine that the interest rate on your savings account was 1% per year and inflation was 2% per year. After 1 year, would you be able to buy:',
        widget=widgets.RadioSelect,
        choices=[
            [1,
                f"More than today with the money in this account ({C.DEFAULT_CURRENCY_SYMBOL}1,000)"],
            [2,
                f"Exactly the same as today with the money in this account ({C.DEFAULT_CURRENCY_SYMBOL}1,000)"],
            [3,
                f"Less than today with the money in this account ({C.DEFAULT_CURRENCY_SYMBOL}1,000)"],
            [4, "Don’t know"],
            [5, "Prefer not to say"]
        ])

    bonds_riskier = models.IntegerField(
        label='Do you think that the following statement is true or false? “Bonds are normally riskier than stocks.”',
        widget=widgets.RadioSelect,
        choices=[
            [1, "True"],
            [2, "False"],
            [3, "Don’t know"],
            [4, "Prefer not to say"]]
    )

    highest_return_asset = models.IntegerField(
        label='Considering a long time period (for example, 10 or 20 years), which asset described below normally gives the highest return?',
        widget=widgets.RadioSelect,
        choices=[
            [1, "Savings accounts"],
            [2, "Stocks"],
            [3, "Bonds"],
            [4, "Don’t know"],
            [5, "Prefer not to say"]
        ])

    risk_spreading_money = models.IntegerField(
        label='When an investor spreads their money among different assets, does the risk of losing a lot of money:',
        widget=widgets.RadioSelect,
        choices=[
            [1, "Increase"],
            [2, "Decrease"],
            [3, "Stay the same"],
            [4, "Don’t know"],
            [5, "Prefer not to say"]
        ])

    savings_interest = models.IntegerField(
        label=f'Suppose you have {C.DEFAULT_CURRENCY_SYMBOL}100 in a savings account and the interest rate is 2% per year and you never withdraw money or interest payments. After 5 years, how much would you have in this account in total?',
        widget=widgets.RadioSelect,
        choices=[[1, f"More than {C.DEFAULT_CURRENCY_SYMBOL}110"],
                 [2, f"Exactly {C.DEFAULT_CURRENCY_SYMBOL}110"],
                 [3, f"Less than {C.DEFAULT_CURRENCY_SYMBOL}110"],
                 [4, "Don’t know"],
                 [5, "Prefer not to say"]
        ])

    stock_mutual_fund = models.IntegerField(
        label=f'Do you think that the following statement is true or false? "A stock mutual fund combines the money of many investors to buy a variety of stocks"',
        widget=widgets.RadioSelect,
        choices=[
            [1, "True"],
            [2, "False"],
            [3, "Don’t know"],
            [4, "Prefer not to say"]]
    )

    mortgage_payments = models.IntegerField(
        label=f'Do you think that the following statement is true or false? "A 15-year mortgage typically requires higher monthly payments than a 30-year mortgage, but the total interest paid over the life of the loan will be less."',
        widget=widgets.RadioSelect,
        choices=[
            [1, "True"],
            [2, "False"],
            [3, "Don’t know"],
            [4, "Prefer not to say"]]
    )

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


_TEXT_MAX_LENGTH = 10000

def _text_length_ok(value, min_length=C.MIN_TEXT_LENGTH):
    text = (value or '').strip()
    return min_length <= len(text) <= _TEXT_MAX_LENGTH


def _min_text_error():
    return 'Please provide a response.'


KEYLOG_TIMING_STATE_KEY = 'keylog_timing_state'
COMPREHENSION_ATTEMPTS_KEY = 'comprehension_failed_attempts'
COMPREHENSION_WRONG_HISTORY_KEY = 'comprehension_wrong_history'


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


def _ensure_comprehension_tracking(player: Player):
    attempts = player.participant.vars.get(COMPREHENSION_ATTEMPTS_KEY)
    history = player.participant.vars.get(COMPREHENSION_WRONG_HISTORY_KEY)

    if attempts is None:
        attempts = player.field_maybe_none('comp_failed_attempts') or 0
    if history is None:
        history = player.field_maybe_none('comp_wrong_history') or ''

    try:
        attempts = int(attempts)
    except (TypeError, ValueError):
        attempts = 0

    history = str(history or '').strip()

    player.participant.vars[COMPREHENSION_ATTEMPTS_KEY] = attempts
    player.participant.vars[COMPREHENSION_WRONG_HISTORY_KEY] = history
    return attempts, history


def _append_comprehension_failure(player: Player, wrong_ids):
    attempts, history = _ensure_comprehension_tracking(player)
    attempts += 1
    attempt_entry = ','.join(wrong_ids)
    history = f'{history};{attempt_entry}' if history else attempt_entry

    player.participant.vars[COMPREHENSION_ATTEMPTS_KEY] = attempts
    player.participant.vars[COMPREHENSION_WRONG_HISTORY_KEY] = history
    player.comp_failed_attempts = attempts
    player.comp_wrong_history = history


def _get_scenario_reminder_text(player: Player):
    if player.emotional_attachment == 2:
        variation = player.participant.vars.get('variation')
        relation = 'father' if variation == 2 else 'mother'
        if player.future_present == 1:
            scenario_text = (
                f'Suppose that today you learn that your {relation} has been diagnosed with a terminal disease. '
                f'You inherit {C.DEFAULT_CURRENCY_SYMBOL}50 000 after taxes from your {relation} in 2 years. '
                'This is a one-time payment you had not expected until today.'
            )
        else:
            scenario_text = (
                f'Suppose that today you learn that your {relation} passed away last night. '
                f'You inherit {C.DEFAULT_CURRENCY_SYMBOL}50 000 after taxes from your {relation} today. '
                'This is a one-time payment you had not expected until today.'
            )
    else:
        if player.future_present == 1:
            scenario_text = (
                'Suppose that today you learn that the government has discovered an error in your taxes that concerns multiple years. '
                f'You receive a {C.DEFAULT_CURRENCY_SYMBOL}50 000 refund in 2 years. '
                'This is a one-time payment you had not expected until today.'
            )
        else:
            scenario_text = (
                'Suppose that today you learn that the government has discovered an error in your taxes that concerns multiple years. '
                f'You receive a {C.DEFAULT_CURRENCY_SYMBOL}50 000 refund today. '
                'This is a one-time payment you had not expected until today.'
            )

    if player.uncertainty == 1:
        uncertainty_text = (
            'Assume that, while there is always some uncertainty in the exact timing and amount of such payments, '
            'there is very little uncertainty in this scenario.'
        )
    else:
        uncertainty_text = 'Assume there is no uncertainty in the timing or amount of the payment.'

    scenario_text = scenario_text + ' ' + uncertainty_text


    info_text = ''
    info_personal_text = ''
    if player.scenario_info:
        info_text = (
            "Many people don't think about future income or cash they'll receive later when deciding how much to spend now. "
            'This applies both to irregular future income (like the above) and regular future income (like salaries). '
            'However, your ability to spend today depends not just on your current income, wealth, and debt, '
            'but also on the money you expect to receive in the future. '
            'If you anticipate future income, you can choose to spend some of it now by dipping into your savings, '
            'saving less than usual, or borrowing (for example, using a credit card or a line of credit).'
        )

        subtype = player.field_maybe_none('info_subtype') or ''
        borrowing_part = 'borrowing money (e.g., using consumer credit)'
        ability_parts = []
        if '5' in subtype:
            ability_parts.append('your disposable income')
        if '6' in subtype:
            ability_parts.append('your net wealth (e.g., savings invested in bank accounts or stocks)')
        if '7' in subtype:
            ability_parts.append(borrowing_part)

        if ability_parts:
            if len(ability_parts) == 1:
                ability_text = ability_parts[0]
            elif len(ability_parts) == 2:
                ability_text = f'{ability_parts[0]} and {ability_parts[1]}'
            else:
                ability_text = f'{ability_parts[0]}, {ability_parts[1]} and {ability_parts[2]}'
            # 'borrowing money ...' alone reads 'by borrowing money ...' in the scenario templates
            lead_in = 'by ' if ability_parts[0] == borrowing_part else 'by using '
            info_personal_text = (
                f'You stated that you would be able to spend more today {lead_in}{ability_text}. '
                'That means you can increase today\'s spending in anticipation of future income if you like.'
            )

    return scenario_text, info_text, info_personal_text



def _comprehension_wrong_ids(player: Player, values):
    wrong_ids = []

    expected_timing = 2 if player.future_present == 1 else 1
    if values.get('comp_q1_timing') != expected_timing:
        wrong_ids.append('1')

    if values.get('comp_q2_amount') != 3:
        wrong_ids.append('2')

    expected_reason = 3 if player.emotional_attachment == 1 else 2
    if values.get('comp_q3_reason') != expected_reason:
        wrong_ids.append('3')

    return wrong_ids


# ------------------------------------------------------------------------------------------------------------
# ------------------------------------------- FUNCTIONS --------------------------------------------
# ------------------------------------------------------------------------------------------------------------
def creating_session(subsession: Subsession):
    if subsession.round_number == 1:
        # FU = Future, PR = Present; LAR = Large (parent) NO = None (tax); C = Certainty, U = Uncertainty; I = Information
        groups = [
            'FU_LAR_C', 'FU_NO_C', 'PR_LAR_C', 'PR_NO_C',
            'FU_LAR_U', 'FU_NO_U', 'PR_LAR_U', 'PR_NO_U',
            'FU_LAR_C_I', 'FU_NO_C_I', 'PR_LAR_C_I', 'PR_NO_C_I',
            'FU_LAR_U_I', 'FU_NO_U_I', 'PR_LAR_U_I', 'PR_NO_U_I',
        ]

        for i, player in enumerate(subsession.get_players()):
            assigned_group = groups[i % len(groups)]
            player.participant.vars['assigned_group'] = assigned_group
            player.assigned_group = assigned_group

            parts = assigned_group.split('_')
            player.future_present = 1 if parts[0] == 'FU' else 2
            player.emotional_attachment = 2 if parts[1] == 'LAR' else 1
            player.uncertainty = 2 if parts[2] == 'C' else 1
            player.scenario_info = parts[-1] == 'I'


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
# --------------------------------------- INTRODUCTORY SURVEY --------------------------------------------
# ------------------------------------------------------------------------------------------------------------
class Survey_1(Page):
    form_model = 'player'

    @staticmethod
    def get_form_fields(player: Player):
        if 'spend_save' not in player.participant.vars:
            player.participant.vars['spend_save'] = random.randint(1, 2)  # spend = 1; save = 2
        if player.participant.vars['spend_save'] == 1:
            return ['survey1_spend']
        elif player.participant.vars['spend_save'] == 2:
            return ['survey1_save']

    @staticmethod
    def vars_for_template(player: Player):
        value = player.field_maybe_none('survey1_spend') or 0  # Defaults to 0 if None
        remaining_percentage = 100 - value

        return {
            'form_value': value,
            'remaining_percentage': remaining_percentage,
            'spend_save': player.participant.vars['spend_save'],
            'testing': player.session.config["testing"]}

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.spend_save = player.participant.vars['spend_save']


class Survey_2(Page):
    form_model = 'player'
    form_fields = [
        'survey2_DisposableIncome',
        'survey2_NetWealth',
        'survey2_FutureIncome',
        'survey2_RetirementIncome',
        'survey2_IrregularPayments',
        'survey2_InterestRates',
        'survey2_Inflation',
        'survey2_CreditAccess',
        'survey2_Caution',
        'survey2_Impatience',
        'survey2_TextBox']

    @staticmethod
    def vars_for_template(player: Player):
        if 'spend_save' not in player.participant.vars:
            player.participant.vars['spend_save'] = random.randint(1, 2)  # spend = 1; save = 2

        # Randomize the order of the fields, excluding textbox
        static_fields = ['survey2_TextBox']
        if 'randomized_fields' not in player.participant.vars:
            randomized_fields = random.sample(
                [field for field in Survey_2.form_fields if field not in static_fields],
                len(Survey_2.form_fields) - len(static_fields))
            player.participant.vars['randomized_fields'] = randomized_fields
        else:
            randomized_fields = player.participant.vars['randomized_fields']

        survey2_labels = {
            'survey2_DisposableIncome': "Your disposable income now",
            'survey2_NetWealth': "Your current net wealth (your wealth minus any debt, e.g., credit card debt or mortgages)",
            'survey2_FutureIncome': "Your expected regular future income until retirement (e.g., from your job)",
            'survey2_RetirementIncome': "Your expected regular income after retirement (e.g., from pensions and your retirement savings)",
            'survey2_IrregularPayments': "Expected gifts, inheritances, and irregular payments from others",
            'survey2_InterestRates': "Interest rates or the return on savings (including stocks and changes in housing prices)",
            'survey2_Inflation': "Inflation",
            'survey2_CreditAccess': "Your ability to access credit (if needed)",
            'survey2_Caution': "Caution (preference to avoid risk)",
            'survey2_Impatience': "Impatience (preference to spend more now rather than later)",
        }
        likert_choices = [
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important'],
        ]

        survey2_rows = []
        for field_name in randomized_fields:
            survey2_rows.append(dict(
                name=field_name,
                label=survey2_labels.get(field_name, field_name),
                choices=likert_choices,
                value=player.field_maybe_none(field_name),
            ))

        return {'spend_save': player.participant.vars['spend_save'],
                'randomized_fields': randomized_fields,
                'survey2_rows': survey2_rows,
                'testing': player.session.config["testing"]}

    @staticmethod
    def error_message(player: Player, values):
        for field in ['survey2_DisposableIncome', 'survey2_NetWealth', 'survey2_FutureIncome',
                      'survey2_RetirementIncome', 'survey2_IrregularPayments', 'survey2_InterestRates',
                      'survey2_Inflation', 'survey2_CreditAccess', 'survey2_Caution', 'survey2_Impatience']:
            val = values.get(field)
            if val is not None:
                setattr(player, field, val)
        errors = {}
        for field in ['survey2_DisposableIncome', 'survey2_NetWealth', 'survey2_FutureIncome',
                      'survey2_RetirementIncome', 'survey2_IrregularPayments', 'survey2_InterestRates',
                      'survey2_Inflation', 'survey2_CreditAccess', 'survey2_Caution', 'survey2_Impatience']:
            if values.get(field) is None:
                errors[field] = 'This field is required.'
        return errors if errors else None

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.survey2_fieldorder = ', '.join(player.participant.vars['randomized_fields'])

    


class Survey_3(Page):
    form_model = 'player'
    form_fields = [
        "Demographics_Household_Income",
        "Demographics_LiquidWealth",
        "Demographics_IlliquidWealth",
        "Demographics_DebtWealth",
        "Demographics_LiquidityConstraints_1",
        "Demographics_LiquidityConstraints_2",
        "Demographics_LiquidityConstraints_3",
    ]

    @staticmethod
    def vars_for_template(player: Player):
        return {'testing': player.session.config["testing"]}
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        q5 = player.Demographics_LiquidityConstraints_1
        q6 = player.Demographics_LiquidityConstraints_2
        q7 = player.Demographics_LiquidityConstraints_3

        agreed = []
        if q5 in [4, 5]:
            agreed.append('5')
        if q6 in [4, 5]:
            agreed.append('6')
        if q7 in [4, 5]:
            agreed.append('7')

        player.info_subtype = ''.join(agreed) if agreed else '0'

# ------------------------------------------------------------------------------------------------------------
# --------------------------------------------- SCENARIO --------------------------------------------
# ------------------------------------------------------------------------------------------------------------

def get_timeline_vars(player: Player):
    paymentgr = (player.participant.vars.get('assigned_group') or 'FU_NO').split("_")
    if paymentgr[0] == "FU":
        payment_position = 2
    else:
        payment_position = 0
    if paymentgr[1] == "NO":
        payment_label = "Tax Refund Payment"
    else:
        payment_label = "Inheritance Payment"
    
    return payment_position,payment_label


class FU_LAR_C(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']

    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'FU_LAR_C'

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = random.randint(1, 2)
        payment_position, payment_label = get_timeline_vars(player)
        return {
            'testing': player.session.config["testing"],
            'variation': player.participant.vars['variation'],
            'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.mother_father = player.participant.vars['variation']


class FU_LAR_U(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']

    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'FU_LAR_U'

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = random.randint(1, 2)
        payment_position, payment_label = get_timeline_vars(player)
        return {
            'testing': player.session.config["testing"],
            'variation': player.participant.vars['variation'],
            'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.mother_father = player.participant.vars['variation']


class FU_NO_C(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']
    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'FU_NO_C'

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}


class FU_NO_U(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']
    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'FU_NO_U'

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}


class PR_LAR_C(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']
    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'PR_LAR_C'

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = random.randint(1, 2)

        return {'testing': player.session.config["testing"],
                'variation': player.participant.vars['variation'],
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.mother_father = player.participant.vars['variation']


class PR_LAR_U(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']
    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'PR_LAR_U'

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = random.randint(1, 2)

        return {'testing': player.session.config["testing"],
                'variation': player.participant.vars['variation'],
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.mother_father = player.participant.vars['variation']


class PR_NO_C(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']
    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'PR_NO_C'

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}


class PR_NO_U(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']
    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'PR_NO_U'

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}


# WITH INFORMATION PARAGRAPH AT THE START
class FU_LAR_C_I(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']

    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'FU_LAR_C_I'

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = random.randint(1, 2)
        payment_position, payment_label = get_timeline_vars(player)
        return {
            'testing': player.session.config["testing"],
            'variation': player.participant.vars['variation'],
            'info_subtype': player.info_subtype,
            'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.mother_father = player.participant.vars['variation']


class FU_LAR_U_I(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']

    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'FU_LAR_U_I'

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = random.randint(1, 2)
        payment_position, payment_label = get_timeline_vars(player)
        return {
            'testing': player.session.config["testing"],
            'variation': player.participant.vars['variation'],
            'info_subtype': player.info_subtype,
            'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.mother_father = player.participant.vars['variation']


class FU_NO_C_I(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']

    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'FU_NO_C_I'

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'info_subtype': player.info_subtype,
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}


class FU_NO_U_I(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']

    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'FU_NO_U_I'

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'info_subtype': player.info_subtype,
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}


class PR_LAR_C_I(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']

    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'PR_LAR_C_I'

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = random.randint(1, 2)
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'variation': player.participant.vars['variation'],
                'info_subtype': player.info_subtype,
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.mother_father = player.participant.vars['variation']

class PR_LAR_U_I(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']

    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'PR_LAR_U_I'

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = random.randint(1, 2)
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'variation': player.participant.vars['variation'],
                'info_subtype': player.info_subtype,
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.mother_father = player.participant.vars['variation']


class PR_NO_C_I(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']

    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'PR_NO_C_I'

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'scenario_warning': player.scenario_warning,
                'info_subtype': player.info_subtype,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25
                }


class PR_NO_U_I(Page):
    form_model = 'player'
    form_fields = ['scenario_warning']

    def is_displayed(player: Player):
        return player.participant.vars.get('assigned_group') == 'PR_NO_U_I'

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'info_subtype': player.info_subtype,
                'scenario_warning': player.scenario_warning,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25
                }


class ComprehensionTest(Page):
    form_model = 'player'

    @staticmethod
    def get_form_fields(player: Player):
        fields = ['comp_q1_timing', 'comp_q2_amount', 'comp_q3_reason']
        return fields

    @staticmethod
    def vars_for_template(player: Player):
        failed_attempts, wrong_history = _ensure_comprehension_tracking(player)
        payment_position, payment_label = get_timeline_vars(player)
        scenario_text, info_text, info_personal_text = _get_scenario_reminder_text(player)

        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = 'Not Set'

        return {
            'testing': player.session.config["testing"],
            'show_retry_reminder': failed_attempts > 0,
            'failed_attempts': failed_attempts,
            'wrong_history': wrong_history,
            'group': player.participant.vars['assigned_group'],
            'variation': player.participant.vars['variation'],
            'info_subtype': player.info_subtype,
            'scenario_text': scenario_text,
            'scenario_info_text': info_text,
            'scenario_info_personal_text': info_personal_text,
            'expected_q1': 2 if player.future_present == 1 else 1,
            'expected_q3': 3 if player.emotional_attachment == 1 else 2,
            'payment_position': payment_position,
            'payment_label': payment_label,
            'arrow_left_percent': payment_position * 25,
        }

    @staticmethod
    def error_message(player: Player, values):
        errors = {}
        wrong_msg = 'Please review the scenario and update this response.'

        expected_timing = 2 if player.future_present == 1 else 1
        if values.get('comp_q1_timing') != expected_timing:
            errors['comp_q1_timing'] = wrong_msg

        if values.get('comp_q2_amount') != 3:
            errors['comp_q2_amount'] = wrong_msg

        expected_reason = 3 if player.emotional_attachment == 1 else 2
        if values.get('comp_q3_reason') != expected_reason:
            errors['comp_q3_reason'] = wrong_msg

        if errors:
            wrong_ids = _comprehension_wrong_ids(player, values)
            if wrong_ids:
                _append_comprehension_failure(player, wrong_ids)
            return errors

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        failed_attempts, wrong_history = _ensure_comprehension_tracking(player)
        player.comp_failed_attempts = failed_attempts
        player.comp_wrong_history = wrong_history


# ------------------------------------------------------------------------------------------------------------
# --------------------------------------------- REACTIONS --------------------------------------------
# ------------------------------------------------------------------------------------------------------------

class Reactions_1(Page):
    form_model = 'player'
    form_fields = ['react3', 'react4', 'react5']

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = 'Not Set'
        
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'group': player.participant.vars['assigned_group'],
                'variation': player.participant.vars['variation'],
                'info_subtype': player.info_subtype,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def error_message(player: Player, values):
        errors = {}
        for field in ['react3', 'react4', 'react5']:
            if not _text_length_ok(values.get(field)):
                errors[field] = _min_text_error()
        return errors if errors else None

    @staticmethod
    def live_method(player: Player, data):
        _append_keylog_event(player, 'reactions2_keylog', data)


class Reactions_2(Page):
    form_model = 'player'
    form_fields = ['react_yr1', 'react_yr2', 'react_yr3', 'react_yr4', 'react_yr5']

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = 'Not Set'
        
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'group': player.participant.vars['assigned_group'],
                'variation': player.participant.vars['variation'],
                'info_subtype': player.info_subtype,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def error_message(player: Player, values):
        total_fields = ['react_yr1', 'react_yr2', 'react_yr3', 'react_yr4', 'react_yr5']
        errors = {}
        total = 0
        for field in total_fields:
            value = values.get(field)
            if value is None:
                total = None
                break
            if value < C.REACTION_SPEND_MIN or value > C.REACTION_SPEND_MAX:
                errors[field] = (
                    f'Please enter a value between {C.REACTION_SPEND_MIN} and '
                    f'{C.REACTION_SPEND_MAX}.'
                )
            total += value

        if not errors and total is not None and total > C.REACTION_SPEND_TOTAL_MAX:
            total_msg = (
                f'Your total change in spending sums up to more than {C.DEFAULT_CURRENCY_SYMBOL}{C.REACTION_SPEND_TOTAL_MAX}, '
                'i.e., much more than the payment you receive. '
                f'Please change your responses to stay below a total change of {C.DEFAULT_CURRENCY_SYMBOL}{C.REACTION_SPEND_TOTAL_MAX} in spending.'
            )
            for field in total_fields:
                errors[field] = total_msg

        return errors if errors else None

    @staticmethod
    def live_method(player: Player, data):
        if data.get('type') == 'initial_values':
            player.react_yr1_initial = data.get('yr1')
            player.react_yr2_initial = data.get('yr2')
            player.react_yr3_initial = data.get('yr3')
            player.react_yr4_initial = data.get('yr4')
            player.react_yr5_initial = data.get('yr5')
        else:
            _append_keylog_event(player, 'reactions3_keylog', data)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        for field in ['react_yr1', 'react_yr2', 'react_yr3', 'react_yr4', 'react_yr5']:
            initial_field = field + '_initial'
            if player.field_maybe_none(initial_field) is None:
                setattr(player, initial_field, player.field_maybe_none(field))

def _reactions2_backloaded(player: Player):
    """True when the spending change is concentrated after the payment is
    received (Years 3-4) rather than before it (Years 1-2). This is the
    condition that routes future-payment participants to Followup A1/A2.

    Magnitudes are compared so the check still works when reactions are
    negative (planned spending reductions): what matters is where the bulk
    of the *change* sits, not its sign. When there is no Year 3-4 change,
    it is never treated as back-loaded (so an early-only change, including
    all-zero - goes to Followup B instead).
    """
    before = (
        (player.field_maybe_none('react_yr1') or 0) +
        (player.field_maybe_none('react_yr2') or 0)
    )
    after = (
        (player.field_maybe_none('react_yr3') or 0) +
        (player.field_maybe_none('react_yr4') or 0)
    )
    return player.future_present == 1 and abs(before) < 0.5 * abs(after)


class Reactions_2_Followup_B(Page):
    form_model = 'player'
    form_fields = ['react9']

    @staticmethod
    def is_displayed(player: Player):
        # Shown whenever the A1/A2 follow-up branch does not apply.
        # This includes the all-zero case: those participants see this page and then skip Reactions_3 and Reactions_4.
        return not _reactions2_backloaded(player)
    
    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        return {
            'testing': player.session.config['testing'],
            'group': player.assigned_group,
            'variation': player.participant.vars.get('variation'),
            'info_subtype': player.info_subtype,
            'react_yr1': player.react_yr1,
            'react_yr2': player.react_yr2,
            'react_yr3': player.react_yr3,
            'react_yr4': player.react_yr4,
            'react_yr5': player.react_yr5,
            'payment_position': payment_position,
            'payment_label': payment_label,
            'arrow_left_percent': payment_position * 25
        }
    
    @staticmethod
    def error_message(player: Player, values):
        errors = {}
        if not values.get('react9') or len(values.get('react9', '').strip()) < 1:
            errors['react9'] = 'This field is required.'
        return errors if errors else None


class Reactions_2_Followup_A1(Page):
    form_model = 'player'
    form_fields = ['react_followup1']

    @staticmethod
    def is_displayed(player: Player):
        return _reactions2_backloaded(player)

    @staticmethod
    def vars_for_template(player: Player):
        payment_position, payment_label = get_timeline_vars(player)
        return {
            'testing': player.session.config['testing'],
            'group': player.assigned_group,
            'variation': player.participant.vars.get('variation'),
            'info_subtype': player.info_subtype,
            'react_yr1': player.react_yr1,
            'react_yr2': player.react_yr2,
            'react_yr3': player.react_yr3,
            'react_yr4': player.react_yr4,
            'react_yr5': player.react_yr5,
            'payment_position': payment_position,
            'payment_label': payment_label,
            'arrow_left_percent': payment_position * 25
        }
    
    @staticmethod
    def error_message(player: Player, values):
        errors = {}
        if not values.get('react_followup1') or len(values.get('react_followup1', '').strip()) < 1:
            errors['react_followup1'] = 'This field is required.'
        return errors if errors else None


class Reactions_2_Followup_A2(Page):
    form_model = 'player'
    form_fields = [
        'react_followup2_i',
        'react_followup2_ii',
        'react_followup2_iii',
        'react_followup2_iv',
        'react_followup2_v',
        'react_followup2_vi',
        'react_followup2_other'
    ]

    @staticmethod
    def is_displayed(player: Player):
        return _reactions2_backloaded(player)

    @staticmethod
    def vars_for_template(player: Player):
        reasons = ['i', 'ii', 'iii', 'iv', 'v', 'vi']
        payment_position, payment_label = get_timeline_vars(player)

        existing_order = player.field_maybe_none('react_followup2_order')
        if existing_order:
            reasons = existing_order.split(',')
        else:
            random.shuffle(reasons)
            player.react_followup2_order = ','.join(reasons)

        likert_choices = [
            [1, 'Not important'],
            [2, 'Slightly Important'],
            [3, 'Moderately Important'],
            [4, 'Important'],
            [5, 'Very Important'],
        ]

        reason_labels = {
            'i': 'I keep future payments such as this one in a different budget than the budget that I use to determine my current spending',
            'ii': 'It would be morally wrong to spend the money before I receive it',
            'iii': "I wouldn't know how to increase spending using the money I receive in the future",
            'iv': 'I cannot increase spending before receiving the money because I have little savings and cannot access credit',
            'v': 'Spending money in advance would require me to borrow, which I do not want to do',
            'vi': 'I consider that there is too much uncertainty in the timing and value of the payment',
        }

        reason_rows = []
        for r in reasons:
            field_name = f'react_followup2_{r}'
            reason_rows.append(dict(
                name=field_name,
                label=reason_labels[r],
                choices=likert_choices,
                value=player.field_maybe_none(field_name),
            ))

        return {
            'testing': player.session.config['testing'],
            'group': player.assigned_group,
            'variation': player.participant.vars.get('variation'),
            'info_subtype': player.info_subtype,
            'react_yr1': player.react_yr1,
            'react_yr2': player.react_yr2,
            'react_yr3': player.react_yr3,
            'react_yr4': player.react_yr4,
            'react_yr5': player.react_yr5,
            'reason_rows': reason_rows,
            'payment_position': payment_position,
            'payment_label': payment_label,
            'arrow_left_percent': payment_position * 25,
        }
    
    @staticmethod
    def error_message(player: Player, values):
        # Save submitted values so they persist on re-render
        for field in ['react_followup2_i', 'react_followup2_ii', 'react_followup2_iii',
                    'react_followup2_iv', 'react_followup2_v', 'react_followup2_vi']:
            val = values.get(field)
            if val is not None:
                setattr(player, field, val)

        errors = {}
        for field in ['react_followup2_i', 'react_followup2_ii', 'react_followup2_iii',
                    'react_followup2_iv', 'react_followup2_v', 'react_followup2_vi']:
            if values.get(field) is None:
                errors[field] = 'This field is required.'
        return errors if errors else None
    

class Reactions_3(Page):
    form_model = 'player'
    form_fields = [
        'react_durable_yr1', 'react_durable_yr2', 'react_durable_yr3',
        'react_nondurable_services_yr1', 'react_nondurable_services_yr2', 'react_nondurable_services_yr3']

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = 'Not Set'
        
        payment_position, payment_label = get_timeline_vars(player)

        row_order = player.participant.vars.get('react5_row_order')
        valid_order = isinstance(row_order, (list, tuple)) and set(row_order) == {
            'durable',
            'nondurable_services',
        }
        if not valid_order:
            row_order = ['durable', 'nondurable_services']
            random.shuffle(row_order)
            player.participant.vars['react5_row_order'] = row_order
        else:
            row_order = list(row_order)

        # Record the randomized row order on the player so it is exported in the oTree data.
        player.reac3_order_dur_nondur = ', '.join(row_order)

        return {'testing': player.session.config["testing"],
                'group': player.participant.vars['assigned_group'],
                'variation': player.participant.vars['variation'],
                'info_subtype': player.info_subtype,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25,
                'react5_row_order': row_order,
                'allocation_target': C.ALLOCATION_TARGET_PCT,
                'allocation_tolerance': C.ALLOCATION_TOLERANCE_PCT}

    @staticmethod
    def error_message(player: Player, values):
        fields = [
            'react_durable_yr1', 'react_durable_yr2', 'react_durable_yr3',
            'react_nondurable_services_yr1', 'react_nondurable_services_yr2', 'react_nondurable_services_yr3',
        ]
        errors = {}
        nums = {}
        for field in fields:
            value = values.get(field)
            if value is None:
                errors[field] = 'Please enter a percentage for this field.'
                continue
            try:
                num = float(value)
            except (TypeError, ValueError):
                errors[field] = 'Please enter a valid number.'
                continue
            if not math.isfinite(num):
                errors[field] = 'Please enter a finite number.'
                continue
            nums[field] = num
            if nums[field] < 0 or nums[field] > 100:
                errors[field] = 'Please enter a percentage between 0 and 100.'

        if errors:
            return errors

        tolerance = C.ALLOCATION_TOLERANCE_PCT
        target = C.ALLOCATION_TARGET_PCT
        column_fields = {
            'Years 1 and 2': ['react_durable_yr1', 'react_nondurable_services_yr1'],
            'Years 3 and 4': ['react_durable_yr2', 'react_nondurable_services_yr2'],
            'Rest of your life': ['react_durable_yr3', 'react_nondurable_services_yr3'],
        }
        column_totals = {
            name: sum(nums[field] for field in fields)
            for name, fields in column_fields.items()
        }

        for name, total in column_totals.items():
            if abs(total - target) > tolerance:
                message = (
                    f'Each time period total must sum to {target:.1f}%. '
                    f'Current total for {name}: {total:.1f}%.'
                )
                for field in column_fields[name]:
                    errors[field] = message

        return errors if errors else None

    @staticmethod
    def is_displayed(player: Player):
        fields = [player.react_yr1, player.react_yr2, player.react_yr3, player.react_yr4, player.react_yr5]
        return not all(f is f == 0 for f in fields)


class Reactions_4(Page):
    form_model = 'player'
    form_fields = [
        'react_alloc_self_yr1', 'react_alloc_self_yr2', 'react_alloc_self_yr3',
        'react_alloc_parents_yr1', 'react_alloc_parents_yr2', 'react_alloc_parents_yr3',
        'react_alloc_other_family_yr1', 'react_alloc_other_family_yr2', 'react_alloc_other_family_yr3',
        'react_alloc_others_yr1', 'react_alloc_others_yr2', 'react_alloc_others_yr3',
    ]

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = 'Not Set'

        payment_position, payment_label = get_timeline_vars(player)
        return {
            'testing': player.session.config["testing"],
            'group': player.participant.vars['assigned_group'],
            'variation': player.participant.vars['variation'],
            'info_subtype': player.info_subtype,
            'payment_position': payment_position,
            'payment_label': payment_label,
            'arrow_left_percent': payment_position * 25,
            'allocation_target': C.ALLOCATION_TARGET_PCT,
            'allocation_tolerance': C.ALLOCATION_TOLERANCE_PCT,
        }

    @staticmethod
    def error_message(player: Player, values):
        fields_by_column = {
                'Years 1 and 2': ['react_alloc_self_yr1', 'react_alloc_parents_yr1', 'react_alloc_other_family_yr1', 'react_alloc_others_yr1'],
                'Years 3 and 4': ['react_alloc_self_yr2', 'react_alloc_parents_yr2', 'react_alloc_other_family_yr2', 'react_alloc_others_yr2'],
                'Rest of your life': ['react_alloc_self_yr3', 'react_alloc_parents_yr3', 'react_alloc_other_family_yr3', 'react_alloc_others_yr3'],
        }

        errors = {}

        for col_name, fields in fields_by_column.items():
            nums = []
            for field in fields:
                value = values.get(field)
                if value is None:
                    errors[field] = 'Please enter a percentage for this field.'
                    continue
                try:
                    num = float(value)
                except (TypeError, ValueError):
                    errors[field] = 'Please enter a valid number.'
                    continue
                if not math.isfinite(num):
                    errors[field] = 'Please enter a finite number.'
                    continue
                if num < 0 or num > 100:
                    errors[field] = 'Please enter a percentage between 0 and 100.'
                    continue
                nums.append((field, num))

            if len(nums) == 4:
                total = sum(n for _, n in nums)
                if abs(total - C.ALLOCATION_TARGET_PCT) > C.ALLOCATION_TOLERANCE_PCT:
                    msg = f'The four percentages must sum to 100.0%. Current total for {col_name}: {total:.1f}%.'
                    for field, _ in nums:
                        errors[field] = msg

        return errors if errors else None

    @staticmethod
    def is_displayed(player: Player):
        fields = [player.react_yr1, player.react_yr2, player.react_yr3, player.react_yr4, player.react_yr5]
        return not all(f is f == 0 for f in fields)


class Reactions_5(Page):
    form_model = 'player'
    form_fields = [
        'react20',
        'react21_yr1', 'react21_yr2', 'react21_yr3',
        'react22_yr1', 'react22_yr2', 'react22_yr3',
        'react23_yr1', 'react23_yr2', 'react23_yr3', 
        'react23_why']

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = 'Not Set'
        payment_position, payment_label = get_timeline_vars(player)
        return {'testing': player.session.config["testing"],
                'group': player.participant.vars['assigned_group'],
                'variation': player.participant.vars['variation'],
                'info_subtype': player.info_subtype,
                'payment_position':payment_position,
                'payment_label': payment_label,
                'arrow_left_percent': payment_position*25}

    @staticmethod
    def error_message(player, values):
        errors = {}
        min_msg = 'Please provide an explanation when this is required.'

        # For react23 group:
        if (values.get("react23_yr1") == 1 or
                values.get("react23_yr2") == 1 or
                values.get("react23_yr3") == 1):
            if not _text_length_ok(values.get("react23_why")):
                errors["react23_why"] = min_msg

        return errors if errors else None

    @staticmethod
    def live_method(player: Player, data):
        _append_keylog_event(player, 'reactions6_keylog', data)


class Reactions_6(Page):
    form_model = 'player'
    form_fields = ['react_uncertainty_timing', 'react_uncertainty_amount']

    @staticmethod
    def vars_for_template(player: Player):
        if 'variation' not in player.participant.vars:
            player.participant.vars['variation'] = 'Not Set'

        payment_position, payment_label = get_timeline_vars(player)
        return {
            'testing': player.session.config["testing"],
            'group': player.participant.vars['assigned_group'],
            'variation': player.participant.vars['variation'],
            'info_subtype': player.info_subtype,
            'payment_position': payment_position,
            'payment_label': payment_label,
            'arrow_left_percent': payment_position * 25,
        }


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
        return {'testing': player.session.config['testing']}

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


class Demographics_2(Page):
    form_model = 'player'
    form_fields = [
        "Demographics_RiskAversion",
        "Demographics_Sacrifice",
        "Demographics_FinInterest",
        "Demographics_PurchaseRegret",
        "Demographics_Debt",
        "Demographics_DebtAverage",        
        "Demographics_Anxious",
        "Demographics_Choices",
        "Demographics_Knowledge",]

    @staticmethod
    def vars_for_template(player: Player):
        return {'testing': player.session.config["testing"]}


class Demographics_3(Page):
    form_model = 'player'
    form_fields = [
        "interest_rate_inflation",
        "bonds_riskier",
        "highest_return_asset",
        "risk_spreading_money",
        "savings_interest",
        "stock_mutual_fund",
        "mortgage_payments"]

    @staticmethod
    def vars_for_template(player: Player):
        return {'testing': player.session.config["testing"]}


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

    Survey_1, Survey_2, Survey_3,

    FU_LAR_C, FU_NO_C, PR_LAR_C, PR_NO_C,
    FU_LAR_U, FU_NO_U, PR_LAR_U, PR_NO_U,

    FU_LAR_C_I, FU_NO_C_I, PR_LAR_C_I, PR_NO_C_I,
    FU_LAR_U_I, FU_NO_U_I, PR_LAR_U_I, PR_NO_U_I,

    ComprehensionTest,

    Reactions_1, Reactions_2, Reactions_2_Followup_A1, Reactions_2_Followup_A2, Reactions_2_Followup_B, Reactions_3, Reactions_4,
    Reactions_5, Reactions_6,

    AttentionCheck1_AI, AttentionCheck2_AI, BotScreening,

    Demographics_1, Inh_Followup_A, Inh_Followup_B, Inh_Followup_C, Inh_Followup_D, Demographics_2, Demographics_3,

    Feedback, LinkToProlific]
