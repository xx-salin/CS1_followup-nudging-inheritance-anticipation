"""
capture_cs1_screenshots.py
==========================
Automated Playwright screenshot script for the CS1 follow-up experiment.

One run captures every variation of the study with as few pictures as possible:

  01_full_run/       participant 1 (change frame, no tool, inheritance today first),
                     every page in the order a participant sees them, including
                     the pop-ups (read-the-scenario alert, comprehension test
                     reminder after a wrong answer, warning for a plan without
                     any change)
  02_variations/     only the pages that look different for the other
                     participants: the plan-update page of each group in both
                     rounds, the scenario pages in the other order, and the
                     inheritance follow-up screens in the other framing
  index.md           what each picture shows

HOW TO USE
----------
1. Start oTree:  otree devserver
2. Run this script (no arguments needed from VS Code)
3. Optional, afterwards:  otree resetdb

The script creates its own session. Participants 1-5 cover all treatment
cells that look different (groups x round, scenario order); after them it only
continues with further participants until the follow-up screens were seen in
both the spend and the save framing, which are drawn at random.

PARTICIPANTS
------------
  1        "full run": no change in spending in the first round (shows the
           warning), first answers the comprehension test wrongly (shows the
           reminder), then the entries of ToyLifecycleTool.xlsx
  2 and on the entries of ToyLifecycleTool.xlsx, correct answers
  all      expect an inheritance from their parents and say it does not affect
           them, so they see all four follow-up screens

NOTES
-----
BotScreening: the Next button is disabled on load by JS. The script
  calls window.onCaptchaVerified('automation-bypass') to re-enable it,
  then clicks it (needs 'testing': True in settings.py).
"""

import argparse
import json as _json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# Config (edit here or pass as CLI args)
# ---------------------------------------------------------------------------
BASE_URL   = "http://127.0.0.1:8000/"
APP_NAME   = "CS1"
CELLS_NEEDED = 5             # participants 1-5 show all treatment variations
MAX_PARTICIPANTS = 16        # further participants only for the spend/save framing
MAX_STEPS  = 200
OUT_DIR    = "screenshots"
HEADED     = True            # False = headless

# ---------------------------------------------------------------------------
# Treatment cells (must match creating_session order in __init__.py)
# layout (2 x 2) x order of the scenarios
# ---------------------------------------------------------------------------
GROUPS = [
    f"{layout}_{round_order}"
    for round_order in ["present_first", "future_first"]
    for layout in ["natural_2", "reframed_2", "natural_1", "reframed"]
]

PLAN_YEARS = range(1, 9)
# plan of ToyLifecycleTool.xlsx; with other tool parameters in settings.py, plan_values_for_page()
# takes the plan from the page instead
BASE_SPENDING = [27000, 27000, 27000, 27000, 25000, 25000, 25000, 25000]
# changes in spending of the sheets "Natural_1" (also used for the level groups)
SHEET_CHANGES = dict(present=[30000, 10000, 5000, 5000, 0, 0, 0, 0],
                     future=[2500, 2500, 25000, 10000, 5000, 5000, 0, 0])


def _plan_values(prefix, amounts):
    return {f"{prefix}_y{year}": str(amount) for year, amount in zip(PLAN_YEARS, amounts)}


def _reaction_values(present_changes, future_changes):
    """Entries for the Plan_Update pages: the change groups show the *_change_*
    inputs, the level groups the *_spend_* inputs."""
    values = {}
    for timing, changes in [("present", present_changes), ("future", future_changes)]:
        values.update(_plan_values(f"{timing}_change", changes))
        values.update(_plan_values(
            f"{timing}_spend", [base + change for base, change in zip(BASE_SPENDING, changes)]))
    return values


def plan_values_for_page(page, number_values):
    """Spending entries that follow the plan a planning-tool page is based on (its js_vars), so
    that the script works whatever the tool parameters in settings.py are (retirement age etc.):
    the baseline gets the plan of the page's "Skip for testing" button, and the level groups
    the change in spending added to the participant's initial plan."""
    cfg = page.evaluate("() => (typeof js_vars === 'undefined' ? null : js_vars)")
    if not cfg or not cfg.get("fields"):
        return number_values
    values = dict(number_values)
    if cfg["mode"] == "baseline":
        values.update(_plan_values("base_spend", cfg["example_spend"]))
    elif cfg["mode"] == "level":
        timing = cfg["fields"][0].split("_")[0]  # present / future
        changes = [int(values[f"{timing}_change_y{year}"]) for year in PLAN_YEARS]
        values.update(_plan_values(
            f"{timing}_spend", [base + change for base, change in zip(cfg["base_spend"], changes)]))
    return values


# ---------------------------------------------------------------------------
# Answers
# ---------------------------------------------------------------------------
TEXT_VALUES = {
    "prolific_id":           "A" * 24,
    "browser_first":         "Chrome",
    "can":                   "red",
    "words":                 "test",
    "inh_followup_why":      "I have considered this but prefer to keep my plans unchanged until I receive the inheritance.",
    "inh_followup_reason_other": "",
    "OpenFeedback":          "The survey was clear and well-structured.",
}

NUMBER_VALUES = {
    "Demographics_Age":            "35",
    "Demographics_AgeExpectation": "80",
    # an inheritance is expected → the follow-up screens are shown
    "Demographics_Mother":            "65",
    "Demographics_Father":            "68",
    "Demographics_MotherInheritance": "50000",
    "Demographics_FatherInheritance": "50000",
    **_reaction_values(SHEET_CHANGES["present"], SHEET_CHANGES["future"]),
}

RADIO_VALUES = {
    "lines":    "1",
    "cafewall": "2",
    # Plan_Comprehension (correct answers: today / in 2 years, the full amount, inheritance)
    "present_comp_q1_timing": "1",
    "future_comp_q1_timing":  "2",
    "present_comp_q2_amount": "3",
    "future_comp_q2_amount":  "3",
    "present_comp_q3_reason": "2",
    "future_comp_q3_reason":  "2",
    # Demographics_1
    "Demographics_Sex":      "1",
    "Demographics_Education":"3",
    "Demographics_Children": "2",
    # Inh_Followup_A (2 = no effect → B), Inh_Followup_B (2 = have thought about it → C and D)
    "inh_followup_effect":  "2",
    "inh_followup_thought": "2",
    # Inh_Followup_D
    **{f"inh_followup_reason_{r}": "3" for r in ["i", "ii", "iii", "iv", "v", "vi", "vii"]},
}

# participant 1 ("full run"): no change in its first round (present), wrong answers first
FULL_RUN_NUMBER_VALUES = {**NUMBER_VALUES, **_plan_values("present_change", [0] * 8),
                          **_plan_values("present_spend", BASE_SPENDING)}
WRONG_COMPREHENSION = {"present_comp_q1_timing": "3", "present_comp_q2_amount": "1"}

# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def normalize_url(base_url, maybe_relative):
    return urljoin(base_url.rstrip("/") + "/", maybe_relative)


def unique_participant_links(page, base_url):
    links = page.eval_on_selector_all(
        "a[href]", "els => els.map(e => e.getAttribute('href'))"
    )
    results, seen = [], set()
    for href in links:
        if not href or "/InitializeParticipant/" not in href:
            continue
        full = normalize_url(base_url, href)
        if full not in seen:
            seen.add(full)
            results.append(full)
    return results


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------

def create_session_and_get_links(page, base_url, app_name, expected_links):
    """Try REST API → admin page → demo page to create a session and get links."""

    # Strategy 1: oTree 5 REST API
    api_url = normalize_url(base_url, "api/sessions")
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        response = page.request.post(
            api_url,
            data=_json.dumps({
                "session_config_name": app_name,
                "num_participants": expected_links,
                "modified_session_config_fields": {
                    "testing": True,
                    "recaptcha_enforce_server_verification": False,
                },
            }),
            headers={"Content-Type": "application/json"},
        )
        if response.ok:
            body = response.json()
            session_code = body.get("code") or body.get("session_code")
            if session_code:
                # Try participants endpoint
                lresp = page.request.get(
                    normalize_url(base_url, f"api/sessions/{session_code}/participants")
                )
                if lresp.ok:
                    urls = []
                    for p in lresp.json():
                        token = p.get("_url_param") or p.get("code")
                        if token:
                            urls.append(normalize_url(base_url, f"InitializeParticipant/{token}"))
                    if len(urls) >= expected_links:
                        print(f"  [session] REST API → {session_code}")
                        return urls[:expected_links]
                # Fallback: scrape session monitor
                page.goto(normalize_url(base_url, f"SessionMonitor/{session_code}"),
                          wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                links = unique_participant_links(page, base_url)
                if len(links) >= expected_links:
                    print(f"  [session] REST API + monitor scrape → {session_code}")
                    return links[:expected_links]
    except Exception as e:
        print(f"  [session] REST API failed ({e}), trying admin page…")

    # Strategy 2: Admin sessions page
    for admin_path in ["sessions", "create_session"]:
        try:
            page.goto(normalize_url(base_url, admin_path), wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            for btn_text in ["Create new session", "Create session", "New session"]:
                btn = page.locator(f"text={btn_text}").first
                if btn.count() > 0:
                    btn.click()
                    page.wait_for_load_state("domcontentloaded")
                    break
            if page.locator("select[name='session_config']").count() > 0:
                page.select_option("select[name='session_config']", app_name)
                page.wait_for_timeout(500)
            filled = False
            for sel in ["input[name='num_participants']", "input[name='num-demo-participants']",
                        "input[name='num_demo_participants']", "input[type='number']"]:
                if page.locator(sel).count() > 0:
                    page.fill(sel, str(expected_links))
                    filled = True
                    break
            if not filled:
                continue
            for sel in ["button[type='submit']", "input[type='submit']",
                        "button:has-text('Create')", "button:has-text('Start')"]:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.click()
                    break
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)
            links = unique_participant_links(page, base_url)
            if links:
                print(f"  [session] Admin page /{admin_path}")
                return links[:expected_links]
            matches = re.findall(r"/InitializeParticipant/[A-Za-z0-9_-]+", page.content())
            urls, seen = [], set()
            for m in matches:
                full = normalize_url(base_url, m)
                if full not in seen:
                    seen.add(full)
                    urls.append(full)
            if urls:
                print(f"  [session] Admin page /{admin_path} (regex scrape)")
                return urls[:expected_links]
        except Exception as e:
            print(f"  [session] Admin page /{admin_path} failed ({e})")

    # Strategy 3: Demo page (gives only 1 link — warns but continues)
    try:
        page.goto(normalize_url(base_url, f"demo/{app_name}"), wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        for btn_text in ["Play", "Start", "Demo"]:
            btn = page.locator(f"button:has-text('{btn_text}'), a:has-text('{btn_text}')").first
            if btn.count() > 0:
                btn.click()
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(2000)
                break
        try:
            page.wait_for_url(lambda u: f"/demo/{app_name}" not in u, timeout=15000)
        except PlaywrightTimeoutError:
            pass
        links = unique_participant_links(page, base_url)
        if not links and "/InitializeParticipant/" in page.url:
            links = [page.url]
        if links:
            print(f"  [session] WARNING: demo page returned {len(links)}/{expected_links} links.")
            return links
    except Exception as e:
        print(f"  [session] Demo page failed ({e})")

    raise RuntimeError(
        f"Could not create session with {expected_links} participants.\n"
        f"Open {normalize_url(base_url, 'sessions')} manually, create a '{app_name}' "
        f"session with {expected_links} participants, then rerun."
    )


# ---------------------------------------------------------------------------
# Page label resolution
# ---------------------------------------------------------------------------

def safe_page_label(url):
    parts = [p for p in urlparse(url).path.split("/") if p]
    return parts[-2] if len(parts) >= 2 else "page"


def resolve_page_label(page):
    label = safe_page_label(page.url)
    if page.locator("input[name='Demographics_Age']").count() > 0:
        return "Demographics_1"
    return label


# ---------------------------------------------------------------------------
# Field filling
# ---------------------------------------------------------------------------

def fill_fields(page, number_values, blank_fields, radio_values):
    number_values = plan_values_for_page(page, number_values)

    # Hidden recaptcha bypass
    for sel in ["textarea[name='recaptcha_response']", "input[name='recaptcha_response']"]:
        if page.locator(sel).count() > 0:
            page.eval_on_selector(
                sel,
                "el => { el.value = 'automation-bypass'; "
                "el.dispatchEvent(new Event('input',{bubbles:true})); "
                "el.dispatchEvent(new Event('change',{bubbles:true})); }"
            )

    # Textareas
    for ta in page.locator("textarea[name]").all():
        name = ta.get_attribute("name")
        if not name or name in blank_fields:
            continue
        try:
            if not ta.is_visible():
                continue
        except Exception:
            continue
        value = TEXT_VALUES.get(name, "test response for automated screenshot run")
        try:
            ta.fill(value)
        except Exception:
            pass

    # Selects
    for sel_el in page.locator("select[name]").all():
        name = sel_el.get_attribute("name")
        if not name or name in blank_fields:
            continue
        value = radio_values.get(name)
        if value is not None:
            try:
                sel_el.select_option(value=value)
                continue
            except Exception:
                pass
        options = sel_el.locator("option").all()
        for opt in options:
            v = opt.get_attribute("value")
            if v:
                try:
                    sel_el.select_option(value=v)
                except Exception:
                    pass
                break

    # Text / number inputs
    for inp in page.locator(
        "input[name]:not([type='radio']):not([type='checkbox'])"
        ":not([type='hidden']):not([type='submit'])"
    ).all():
        name = inp.get_attribute("name")
        if not name:
            continue
        if name in blank_fields:
            try:
                inp.fill("")
            except Exception:
                pass
            continue
        try:
            if not inp.is_visible():
                continue
        except Exception:
            continue
        input_type = (inp.get_attribute("type") or "text").lower()
        if input_type in {"number", "range"}:
            value = number_values.get(name, "5")
        else:
            value = TEXT_VALUES.get(name, number_values.get(name, "test"))
        if value:
            try:
                inp.fill(str(value))
            except Exception:
                pass

    # Radios
    radio_names = page.eval_on_selector_all(
        "input[type='radio'][name]",
        "els => [...new Set(els.map(e => e.name))]",
    )
    for name in radio_names:
        if name in blank_fields:
            continue
        preferred = radio_values.get(name)
        if preferred is not None:
            selector = f"input[type='radio'][name='{name}'][value='{preferred}']"
            if page.locator(selector).count() > 0:
                try:
                    page.check(selector, force=True)
                except Exception:
                    page.eval_on_selector(
                        selector,
                        "el => { el.checked=true; el.dispatchEvent(new Event('change',{bubbles:true})); }"
                    )
                continue
        first = page.locator(f"input[type='radio'][name='{name}']").first
        if first.count() > 0:
            try:
                first.check(force=True)
            except Exception:
                first.evaluate(
                    "el => { el.checked=true; el.dispatchEvent(new Event('change',{bubbles:true})); }"
                )

    # Keep isLeaving unchecked
    if page.locator("input[type='checkbox'][name='isLeaving']").count() > 0:
        try:
            page.uncheck("input[type='checkbox'][name='isLeaving']", force=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def next_button_locator(page):
    for selector in [
        "button.otree-btn-next",
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Next')",
        "button:has-text('Continue')",
    ]:
        loc = page.locator(selector)
        if loc.count() > 0:
            return loc.first
    return None


def fast_forward_bot_screening(page):
    """Bypass BotScreening.html.

    The page disables #nextBtn on load via setNextEnabled(false).
    It only re-enables after onCaptchaVerified(token) is called.
    We bypass by: filling the hidden token input directly, calling
    the callback to enable the button, then clicking it.
    """
    try:
        page.evaluate("""
            () => {
                // Fill the hidden recaptcha token
                const inp = document.getElementById('id_recaptcha_response');
                if (inp) {
                    inp.value = 'automation-bypass';
                }
                // Call the verified callback to enable the Next button
                if (typeof window.onCaptchaVerified === 'function') {
                    window.onCaptchaVerified('automation-bypass');
                } else {
                    // Fallback: force-enable the button directly
                    const btn = document.querySelector('.otree-btn-next');
                    if (btn) {
                        btn.disabled = false;
                        btn.classList.remove('disabled');
                        btn.style.pointerEvents = '';
                        btn.style.opacity = '';
                    }
                }
            }
        """)
        page.wait_for_timeout(200)
        btn = page.locator(".otree-btn-next").first
        if btn.count() > 0:
            url_before = page.url
            try:
                with page.expect_navigation(wait_until="domcontentloaded", timeout=10000):
                    btn.click()
            except PlaywrightTimeoutError:
                pass
            return True
    except Exception:
        pass
    return False


def force_advance_form(page):
    try:
        page.evaluate("""
            () => {
                const form = document.querySelector('form');
                if (form) { form.submit(); return true; }
                const btn = document.querySelector(
                    'button.otree-btn-next, button[type="submit"], input[type="submit"]');
                if (btn) { btn.click(); return true; }
                return false;
            }
        """)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------

def capture_page(page, target):
    for selector in ["div.otree-body", "main", "form", "div.container", "body"]:
        loc = page.locator(selector).first
        if loc.count() > 0:
            try:
                loc.screenshot(path=str(target))
                return
            except Exception:
                pass
    page.screenshot(path=str(target), full_page=False)




# ---------------------------------------------------------------------------
# Which variation a page shows
# ---------------------------------------------------------------------------

def page_variant(page, label, state):
    """Name of the variation a page shows. A page is only captured the first time its
    variation appears (participant 1 captures every page)."""
    if label.startswith("Plan_Scenario"):
        timing = "present" if "passed away last night" in page.content() else "future"
        return f"{label}_{timing}"
    if label.startswith("Plan_Comprehension"):
        return "Plan_Comprehension"  # the same in both rounds
    if label.startswith("Plan_Update"):
        cfg = page.evaluate("() => js_vars")
        timing = cfg["fields"][0].split("_")[0]
        entered = "level" if cfg["mode"] == "level" else "change"
        tool = "tool" if cfg["dynamic"] else "notool"
        return f"Plan_Update_{entered}_{tool}_{timing}"
    if label.startswith("Inh_Followup"):
        if label == "Inh_Followup_A":
            state["frame"] = "save" if "save less" in page.content() else "spend"
        return f"{label}_{state.get('frame', 'spend')}frame"
    return label


FOLLOWUP_KEYS = {f"Inh_Followup_{screen}_{frame}frame" for screen in "ABCD" for frame in ["spend", "save"]}


class Capture:
    """Takes each screenshot once and keeps a list of them for index.md."""

    def __init__(self, out_dir):
        self.out_dir = out_dir
        self.seen = set()
        self.index = []

    def shot(self, page, key, folder, participant, force=False, window=False):
        if key in self.seen and not force:
            return
        self.seen.add(key)
        target = self.out_dir / folder / f"{len(self.index) + 1:02d}_{key}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        # oTree's "Debug info" panel and the "Skip for testing" buttons are not part of what participants see
        page.evaluate("() => document.querySelectorAll('.debug-info, #skipBtn').forEach(e => e.style.display = 'none')")
        if window:  # pop-ups cover the window, not the page
            page.screenshot(path=str(target), full_page=False)
        else:
            capture_page(page, target)
        self.index.append((target.relative_to(self.out_dir), participant, key))

    def write_index(self):
        lines = ["# Screenshots", "", "| Picture | Participant (group, round order) | Shows |", "|---|---|---|"]
        for path, participant, key in self.index:
            lines.append(f"| {path} | {participant} | {key.replace('_', ' ')} |")
        (self.out_dir / "index.md").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def submit(page, click, timeout=10000):
    """Clicks and waits for the next page; falls back to submitting the form directly."""
    url_before = page.url
    try:
        with page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
            click()
    except PlaywrightTimeoutError:
        pass
    if page.url == url_before:
        force_advance_form(page)
        page.wait_for_load_state("domcontentloaded")


def run_participant(page, url, number, group, capture, max_steps):
    full_run = number == 1
    folder = "01_full_run" if full_run else "02_variations"
    who = f"P{number} ({group})"
    number_values = FULL_RUN_NUMBER_VALUES if full_run else NUMBER_VALUES
    state = {}
    wrong_answer_shown = not full_run
    page.goto(url, wait_until="domcontentloaded")

    for _ in range(max_steps):
        page.wait_for_load_state("domcontentloaded")
        label = resolve_page_label(page)
        key = page_variant(page, label, state)
        plan_update = label.startswith("Plan_Update")

        if not plan_update:  # the plan-update pages are captured after the entries are typed
            capture.shot(page, key, folder, who, force=full_run)
        if label == "LinkToProlific":
            return

        # BotScreening: the Next button is enabled through the page's own callback
        if label == "BotScreening":
            fast_forward_bot_screening(page)
            continue

        # Scenario pages: Next within 10 seconds shows the read-the-scenario alert
        if page.locator("#nextBtn").count() > 0:
            page.locator("#nextBtn").click()
            page.wait_for_timeout(400)
            if page.locator("#quick-alert").is_visible():
                capture.shot(page, "Plan_Scenario_alert", folder, who, window=True)
                page.locator("#quick-alert-ok").click()
            submit(page, lambda: page.locator("#nextBtn").click())
            continue

        # Comprehension test: participant 1 first answers wrongly, which shows the reminder
        if label.startswith("Plan_Comprehension") and not wrong_answer_shown:
            fill_fields(page, number_values, set(), {**RADIO_VALUES, **WRONG_COMPREHENSION})
            page.locator("button.otree-btn-next").click()
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(300)
            capture.shot(page, "Plan_Comprehension_reminder", folder, who, force=True)
            wrong_answer_shown = True

        fill_fields(page, number_values, set(), RADIO_VALUES)

        # Plan-update pages: captured with the entries; a plan without any change shows the warning
        if plan_update:
            page.wait_for_timeout(300)
            capture.shot(page, key, folder, who, force=full_run)
            url_before = page.url
            page.locator("button.otree-btn-next").click()
            page.wait_for_timeout(400)
            if page.url == url_before and page.locator("#plan-warning").is_visible():
                capture.shot(page, "Plan_Update_warning", folder, who, window=True)
                page.locator("#plan-warning-proceed").click()
            try:
                page.wait_for_url(lambda u: u != url_before, timeout=15000)
            except PlaywrightTimeoutError:
                force_advance_form(page)
            continue

        button = next_button_locator(page)
        if button is None:
            print(f"    stopped on {label}: no Next button")
            return
        submit(page, button.click)
    print(f"    stopped after {max_steps} pages")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--app", default=APP_NAME)
    parser.add_argument("--max-participants", type=int, default=MAX_PARTICIPANTS)
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS)
    parser.add_argument("--out", default=OUT_DIR)
    parser.add_argument("--headed", action="store_true", default=HEADED)
    parser.add_argument("--no-headed", dest="headed", action="store_false")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_dir = Path(args.out) / f"{args.app}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    capture = Capture(out_dir)

    print(f"\n{'='*60}\n  CS1 Screenshot Capture\n  Output: {out_dir.resolve()}\n{'='*60}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        setup_page = browser.new_page(viewport={"width": 1440, "height": 1100})
        links = create_session_and_get_links(
            page=setup_page, base_url=args.base_url, app_name=args.app,
            expected_links=args.max_participants)
        setup_page.close()

        for number, url in enumerate(links, start=1):
            done = number > CELLS_NEEDED and FOLLOWUP_KEYS <= capture.seen
            if done:
                break
            group = GROUPS[(number - 1) % len(GROUPS)]
            print(f"  P{number} {group}")
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            run_participant(page, url, number, group, capture, args.max_steps)
            page.close()
        browser.close()

    capture.write_index()
    missing = FOLLOWUP_KEYS - capture.seen
    print(f"\nDone: {len(capture.index)} screenshots in {out_dir.resolve()} (see index.md)")
    if missing:
        print(f"Not captured (the random spend/save framing did not come up): {sorted(missing)}")
    print("Optional: otree resetdb")


if __name__ == "__main__":
    main()
