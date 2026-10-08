from otree.api import Bot, Submission, SubmissionMustFail, expect

from . import *
from . import _plan_scenario_timing, _plan_update_fields

# Run with:  otree test CS1 12
# 12 participants cover every cell of layout x scenario order x follow-up framing.

# Entries and results of ToyLifecycleTool.xlsx (default parameters), used to check the projection
BASE_SPENDING = [27000, 27000, 27000, 27000, 25000, 25000, 25000, 25000]
LOWER_SPENDING = [26000, 27000, 27000, 27000, 25000, 25000, 25000, 24000]  # spends less than planned in some years
UPDATED_SPENDING = [31000, 31000, 31000, 31000, 27000, 27000, 27000, 27000]  # sheets "Reframed"
CHANGES = dict(  # sheets "Natural_1" and "Natural_2"
    present=[30000, 10000, 5000, 5000, 0, 0, 0, 0],
    future=[2500, 2500, 25000, 10000, 5000, 5000, 0, 0],
)
# (depletion age, bequest) by entered measure and scenario
EXPECTED = dict(
    spend=dict(present=(93, 36090.19), future=(93, 29714.64)),
    change=dict(present=(94, 30123.50), future=(94, 29519.85)),
)


class PlayerBot(Bot):
    # sheet_entries: entries of the tool's sheets, expects an own inheritance (follow-up questions)
    # spends_less: reduces spending in some years, expects no own inheritance
    cases = ['sheet_entries', 'spends_less']

    def stored(self, field):
        # Read through a fresh self.player: a player object kept across submissions holds outdated values
        return getattr(self.player, field)

    def play_round(self):
        expect(self.player.layout, 'in', C.LAYOUTS)
        expect(self.player.round_order, 'in', C.ROUND_ORDERS)

        yield Instructions_WelcomeScreen, dict(prolific_id='A' * 24, browser_first='bot', isLeaving=False)
        yield AttentionCheck3_AI, dict(lines=1)
        yield AttentionCheck4_AI, dict(cafewall=2)
        yield AttentionCheckResult

        yield Plan_Intro
        base_fields = Plan_Baseline.form_fields
        yield SubmissionMustFail(Plan_Baseline, dict(zip(base_fields[:-1], BASE_SPENDING)))  # a year is missing
        yield SubmissionMustFail(Plan_Baseline, dict(zip(base_fields, [-1] + BASE_SPENDING[1:])))
        yield SubmissionMustFail(Plan_Baseline, dict(zip(base_fields, [200000] + BASE_SPENDING[1:])))  # savings used up
        yield Plan_Baseline, dict(zip(base_fields, BASE_SPENDING))
        expect(self.stored('base_depletion_age'), 93)
        expect(self.stored('base_bequest'), 27896.49)

        entered = 'spend' if self.player.layout == 'reframed' else 'change'
        update_pages = [(Plan_Scenario_1, Plan_Update_1), (Plan_Scenario_2, Plan_Update_2)]
        for scenario_number, (scenario_page, update_page) in enumerate(update_pages, start=1):
            timing = _plan_scenario_timing(self.player, scenario_number)
            fields = _plan_update_fields(self.player, scenario_number)
            expect(fields[0], f'{timing}_{entered}_y1')
            inheritance_today = 'passed away last night' in self.html

            # the page submits through its own button, which the HTML check does not recognise
            yield Submission(scenario_page, {f'{timing}_scenario_warning': 0}, check_html=False)
            expect(inheritance_today, timing == 'present')

            if entered == 'spend':
                entries = UPDATED_SPENDING if self.case == 'sheet_entries' else LOWER_SPENDING
                infeasible = [300000] + entries[1:]  # savings used up
            elif self.case == 'sheet_entries':
                entries = CHANGES[timing]
                infeasible = [-BASE_SPENDING[0] - 1] + entries[1:]  # negative spending
            else:
                entries = [lower - base for lower, base in zip(LOWER_SPENDING, BASE_SPENDING)]
                infeasible = [-BASE_SPENDING[0] - 1] + entries[1:]  # negative spending
            yield SubmissionMustFail(update_page, dict(zip(fields[:-1], entries)))  # a year is missing
            yield SubmissionMustFail(update_page, dict(zip(fields, infeasible)))
            yield update_page, dict(zip(fields, entries))

            if self.case == 'sheet_entries':
                depletion_age, bequest = EXPECTED[entered][timing]
                expect(self.stored(f'{timing}_depletion_age'), depletion_age)
                expect(self.stored(f'{timing}_bequest'), bequest)
            else:
                expect(self.stored(f'{timing}_change_y1'), -1000)
                expect(self.stored(f'{timing}_spend_y8'), 24000)
            for year, base in enumerate(BASE_SPENDING, start=1):
                expect(self.stored(f'{timing}_spend_y{year}') - self.stored(f'{timing}_change_y{year}'), base)
            expect(self.stored(f'{timing}_{entered}_y1'), entries[0])

        yield AttentionCheck1_AI, dict(can='red')
        yield AttentionCheck2_AI, dict(words='test')
        yield BotScreening, dict(recaptcha_response='bot-token')

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
