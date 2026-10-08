from os import environ

DEFAULT_RECAPTCHA_SITE_KEY = '6Ld_izwoAAAAANB5cgcx190wf3VCrppLS067CzHW'
RECAPTCHA_SITE_KEY = environ.get('RECAPTCHA_SITE_KEY', DEFAULT_RECAPTCHA_SITE_KEY)
RECAPTCHA_SECRET_KEY = environ.get('RECAPTCHA_SECRET_KEY', '')
RECAPTCHA_ENFORCE_SERVER_VERIFICATION = (
    environ.get('RECAPTCHA_ENFORCE_SERVER_VERIFICATION', '1' if RECAPTCHA_SECRET_KEY else '0').lower()
    in {'1', 'true', 'yes'}
)

SESSION_CONFIGS = [
    {
        'name': 'CS1',
        'display_name': 'CS1',
        'num_demo_participants': 41,
        'app_sequence': ['CS1'],
        'testing': True,
        # Lifecycle planning tool (defaults as in ToyLifecycleTool.xlsx)
        'initial_wealth': 120000,
        'salary': 30253,
        'pension': 17264,
        'interest_rate': 0.03,
        'inheritance': 50000,
        'current_age': 62,
        'retirement_age': 67,  # first age at which income = pension
        'inheritance_delay_years': 2,  # future scenario: years between the first plan year and the inheritance
        'bequest_age': 90,
    }]

ROOM_DEFAULTS = {}

ROOMS = [
     dict(
     name='Study',
     display_name='Study'
    # participant_label_file='_rooms/econ101.txt',
    )
]
# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00,
    doc="",
    recaptcha_site_key=RECAPTCHA_SITE_KEY,
    recaptcha_secret_key=RECAPTCHA_SECRET_KEY,
    recaptcha_enforce_server_verification=RECAPTCHA_ENFORCE_SERVER_VERIFICATION,
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '3590668820046'
