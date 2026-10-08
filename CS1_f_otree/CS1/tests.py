from otree.api import Bot, Submission, SubmissionMustFail, expect

from . import *
from . import _plan_ages, _plan_income, _plan_inheritance_age, _plan_params, _plan_scenario_timing, _plan_update_fields

# Run with:  otree test CS1 12
# 12 participants cover every cell of layout x scenario order x follow-up framing.
#
# The projections stored by the planning tool (formulas) are compared with a plain year-by-year
# calculation, whatever the tool parameters in settings.py are. With the default parameters, the
# entries and results of ToyLifecycleTool.xlsx are used as well.
SHEET_BASE_SPENDING = [27000, 27000, 27000, 27000, 25000, 25000, 25000, 25000]
SHEET_UPDATED_SPENDING = [31000, 31000, 31000, 31000, 27000, 27000, 27000, 27000]  # sheets "Reframed"
SHEET_CHANGES = dict(  # sheets "Natural_1" and "Natural_2"
    present=[30000, 10000, 5000, 5000, 0, 0, 0, 0],
    future=[2500, 2500, 25000, 10000, 5000, 5000, 0, 0],
)
# (depletion age, bequest)
SHEET_BASE_RESULT = (93, 27896.49)
SHEET_RESULTS = dict(
    spend=dict(present=(93, 36090.19), future=(93, 29714.64)),
    change=dict(present=(94, 30123.50), future=(94, 29519.85)),
)


def year_by_year(p, spending, inheritance_age=None):
    """Depletion age and bequest calculated one year at a time, without the formulas of the tool."""
    total = p['initial_wealth']
    depletion_age = bequest = None
    for age in range(p['first_age'], p['first_age'] + 1500):
        year = age - p['first_age']
        if year < C.PLAN_YEARS:
            saving = _plan_income(p, age) - spending[year] + (p['inheritance'] if age == inheritance_age else 0)
        else:
            saving = (p['pension'] - spending[-1]) * (1 + p['growth_rate']) ** (age - p['last_age'])
        total = total + saving if year == 0 else total * (1 + p['interest_rate']) + saving
        if total < -1e-6 and depletion_age is None:
            depletion_age = age - 1
        if age == p['bequest_age']:
            bequest = total
        if depletion_age is not None and bequest is not None:
            break
    return depletion_age, bequest


class PlayerBot(Bot):
    # sheet_entries: spends part of the inheritance, expects an own inheritance (follow-up questions)
    # spends_less: reduces spending in some years, expects no own inheritance
    cases = ['sheet_entries', 'spends_less']

    def stored(self, field):
        # Read through a fresh self.player: a player object kept across submissions holds outdated values
        return self.player.field_maybe_none(field)

    def check_projection(self, prefix, p, spending, inheritance_age=None):
        depletion_age, bequest = year_by_year(p, spending, inheritance_age)
        expect(self.stored(f'{prefix}_depletion_age'), depletion_age)
        expect(abs(self.stored(f'{prefix}_bequest') - bequest) < 0.011, True)

    def play_round(self):
        expect(self.player.layout, 'in', C.LAYOUTS)
        expect(self.player.round_order, 'in', C.ROUND_ORDERS)
        p = _plan_params(self.player)
        sheet_parameters = all(p[name] == value for name, value in PLAN_PARAM_DEFAULTS.items())

        yield Instructions_WelcomeScreen, dict(prolific_id='A' * 24, browser_first='bot', isLeaving=False)
        yield AttentionCheck3_AI, dict(lines=1)
        yield AttentionCheck4_AI, dict(cafewall=2)
        yield AttentionCheckResult

        yield Plan_Intro
        if sheet_parameters:
            base = SHEET_BASE_SPENDING
        else:
            # saves a tenth of the salary, spends a third more than the pension
            base = [
                round(_plan_income(p, age) * (0.9 if age < p['retirement_age'] else 4 / 3))
                for age in _plan_ages(p)]
        base_fields = Plan_Baseline.form_fields
        beyond_means = p['initial_wealth'] + p['salary'] + p['pension'] + p['inheritance'] + 1
        yield SubmissionMustFail(Plan_Baseline, dict(zip(base_fields[:-1], base)))  # a year is missing
        yield SubmissionMustFail(Plan_Baseline, dict(zip(base_fields, [-1] + base[1:])))
        yield SubmissionMustFail(Plan_Baseline, dict(zip(base_fields, [beyond_means] + base[1:])))  # savings used up
        yield Plan_Baseline, dict(zip(base_fields, base))
        self.check_projection('base', p, base)
        if sheet_parameters:
            expect((self.stored('base_depletion_age'), self.stored('base_bequest')), SHEET_BASE_RESULT)

        entered = 'spend' if self.player.layout == 'reframed' else 'change'
        update_pages = [(Plan_Scenario_1, Plan_Update_1), (Plan_Scenario_2, Plan_Update_2)]
        for scenario_number, (scenario_page, update_page) in enumerate(update_pages, start=1):
            timing = _plan_scenario_timing(self.player, scenario_number)
            inheritance_age = _plan_inheritance_age(p, timing)
            fields = _plan_update_fields(self.player, scenario_number)
            expect(fields[0], f'{timing}_{entered}_y1')
            inheritance_today = 'passed away last night' in self.html

            # the page submits through its own button, which the HTML check does not recognise
            yield Submission(scenario_page, {f'{timing}_scenario_warning': 0}, check_html=False)
            expect(inheritance_today, timing == 'present')

            from_sheet = sheet_parameters and self.case == 'sheet_entries'
            if from_sheet and entered == 'spend':
                spending = SHEET_UPDATED_SPENDING
            elif from_sheet:
                spending = [base_year + change for base_year, change in zip(base, SHEET_CHANGES[timing])]
            elif self.case == 'sheet_entries':
                extra = min(p['inheritance'], p['initial_wealth'])
                shares = [0.3, 0.2, 0.1, 0.1, 0, 0, 0, 0]
                spending = [base_year + round(share * extra) for base_year, share in zip(base, shares)]
            else:
                spending = [round(base[0] * 0.96)] + base[1:-1] + [round(base[-1] * 0.96)]
            changes = [spend - base_year for spend, base_year in zip(spending, base)]

            if entered == 'spend':
                entries = spending
                infeasible = [beyond_means] + entries[1:]  # savings used up
            else:
                entries = changes
                infeasible = [-base[0] - 1] + entries[1:]  # negative spending
            yield SubmissionMustFail(update_page, dict(zip(fields[:-1], entries)))  # a year is missing
            yield SubmissionMustFail(update_page, dict(zip(fields, infeasible)))
            yield update_page, dict(zip(fields, entries))

            for year, (spend, change) in enumerate(zip(spending, changes), start=1):
                expect(self.stored(f'{timing}_spend_y{year}'), spend)
                expect(self.stored(f'{timing}_change_y{year}'), change)
            self.check_projection(timing, p, spending, inheritance_age)
            if from_sheet:
                result = (self.stored(f'{timing}_depletion_age'), self.stored(f'{timing}_bequest'))
                expect(result, SHEET_RESULTS[entered][timing])

        yield AttentionCheck1_AI, dict(can='red')
        yield AttentionCheck2_AI, dict(words='test')
        if self.case == 'sheet_entries':
            yield BotScreening, dict(recaptcha_response='bot-token')
            expect(self.stored('recaptcha_verified'), True)
        else:
            # "Skip for testing" button
            yield BotScreening, dict(recaptcha_response=C.TESTING_SKIP_TOKEN)
            expect(self.stored('recaptcha_verified'), False)

        demographics = dict(
            Demographics_Age=40, Demographics_AgeExpectation=85,
            Demographics_Sex=1, Demographics_Children=2, Demographics_Education=3)
        if self.case == 'sheet_entries':
            demographics.update(Demographics_Mother=70, Demographics_MotherInheritance=50000)
            yield Demographics_1, demographics

            saving_frame = self.player.inh_followup_frame == 2
            frame_word = 'saving' if saving_frame else 'spending'
            expect(f'no effect on my current {frame_word}', 'in', self.html)
            expect('save less' in self.html, saving_frame)
            yield Inh_Followup_A, dict(inh_followup_effect=2)
            expect(f'does not affect your current {frame_word}', 'in', self.html)
            yield Inh_Followup_B, dict(inh_followup_thought=2)
            yield Inh_Followup_C, dict(inh_followup_why='I prefer to wait until I receive it.')
            yield Inh_Followup_D, dict(
                inh_followup_reason_i=3, inh_followup_reason_ii=2, inh_followup_reason_iii=2,
                inh_followup_reason_iv=2, inh_followup_reason_v=3, inh_followup_reason_vi=2,
                inh_followup_reason_vii=2, inh_followup_reason_other='')
        else:
            yield Demographics_1, demographics

        yield Feedback, dict(OpenFeedback='')
        expect('Prolific', 'in', self.html)
