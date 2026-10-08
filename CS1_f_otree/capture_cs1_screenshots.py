"""
capture_cs1_screenshots.py
==========================
Automated Playwright screenshot script for the CS1 oTree experiment.

HOW TO USE
----------
1. Start oTree:  otree devserver
2. Set ACTIVE_PERSONA below to "A", "B", or "C"
3. Run script (no args needed from VS Code)
4. Save screenshots, then:  otree resetdb
5. Change ACTIVE_PERSONA to next letter, repeat

PERSONAS
--------
  A  — spends it      : entries of ToyLifecycleTool.xlsx, expects an own
                         inheritance → full Inh_Followup chain (A→D)
  B  — no reaction    : spending unchanged in every year, expects an own
                         inheritance that affects them → Inh_Followup_A only
  C  — spends less    : lower spending in some years, blank parents →
                         skips the Inh_Followup chain

Needs 12 participant slots (one per treatment cell).

NOTES
-----
BotScreening: the Next button is disabled on load by JS. The script
  calls window.onCaptchaVerified('automation-bypass') to re-enable it,
  then clicks it. No changes to __init__.py needed.

Scenario popup: the scenario pages use a custom #nextBtn (not oTree's
  standard next button) with a DOM #quick-alert div. The script:
    1. Screenshots the page normally
    2. Clicks #nextBtn  → #quick-alert becomes visible
    3. Screenshots the page with the alert showing
    4. Clicks #quick-alert-ok to dismiss it
    5. Clicks #nextBtn again → form.submit() → navigates away
"""

import argparse
import json as _json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


# ===========================================================================
# ★  CHANGE THIS ONE LINE TO SWITCH PERSONA  ★
# ===========================================================================
ACTIVE_PERSONA = "C"   # "A", "B", or "C"
# ===========================================================================


# ---------------------------------------------------------------------------
# Config (edit here or pass as CLI args)
# ---------------------------------------------------------------------------
BASE_URL   = "http://127.0.0.1:8000/"
APP_NAME   = "CS1"
NUM_TREATMENTS = 12          # always 12 for CS1
MAX_STEPS  = 500
OUT_DIR    = "screenshots"
HEADED     = True            # False = headless

# Pages captured only once (same across all treatments)
CAPTURE_ONCE_LABELS = {
    "Instructions_WelcomeScreen",
    "AttentionCheck3_AI",
    "AttentionCheck4_AI",
    "AttentionCheckResult",
}

# ---------------------------------------------------------------------------
# Treatment cells (must match creating_session order in __init__.py)
# layout x order of the scenarios x framing of the own-inheritance follow-up
# ---------------------------------------------------------------------------
GROUPS = [
    f"{layout}_{round_order}_{frame}"
    for frame in ["spendframe", "saveframe"]
    for round_order in ["present_first", "future_first"]
    for layout in ["natural_2", "natural_1", "reframed"]
]

PLAN_YEARS = range(1, 9)
BASE_SPENDING = [27000, 27000, 27000, 27000, 25000, 25000, 25000, 25000]


def _plan_values(prefix, amounts):
    return {f"{prefix}_y{year}": str(amount) for year, amount in zip(PLAN_YEARS, amounts)}


def _reaction_values(present_changes, future_changes):
    """Entries for the Plan_Update pages: the natural layouts show the *_change_*
    inputs, the reframed layout the *_spend_* inputs."""
    values = {}
    for timing, changes in [("present", present_changes), ("future", future_changes)]:
        values.update(_plan_values(f"{timing}_change", changes))
        values.update(_plan_values(
            f"{timing}_spend", [base + change for base, change in zip(BASE_SPENDING, changes)]))
    return values


# ---------------------------------------------------------------------------
# Base field values (shared by all personas)
# ---------------------------------------------------------------------------
TEXT_VALUES = {
    "prolific_id":           "A" * 24,
    "browser_first":         "Chrome",
    "can":                   "red",
    "words":                 "test",
    "inh_followup_why":      "I have considered this but prefer to keep my spending plans unchanged until I receive the inheritance.",
    "inh_followup_reason_other": "",
    "OpenFeedback":          "The survey was clear and well-structured.",
    "AI_Test2":              "[]",
}

NUMBER_VALUES_BASE = {
    "Demographics_Age":            "35",
    "Demographics_AgeExpectation": "80",
    # Plan_Baseline
    **_plan_values("base_spend", BASE_SPENDING),
    # Inh_Followup_D likert
    "inh_followup_reason_i":   "3",
    "inh_followup_reason_ii":  "2",
    "inh_followup_reason_iii": "2",
    "inh_followup_reason_iv":  "2",
    "inh_followup_reason_v":   "3",
    "inh_followup_reason_vi":  "2",
    "inh_followup_reason_vii": "2",
    "refresh_count": "0",
}

RADIO_VALUES_BASE = {
    "lines":    "1",
    "cafewall": "2",
    # Demographics_1
    "Demographics_Sex":      "1",
    "Demographics_Education":"3",
    "Demographics_Children": "2",
    # Inh_Followup_A  (2 = no effect → triggers B/C/D chain)
    "inh_followup_effect":  "2",
    # Inh_Followup_B  (2 = have thought about it → triggers C/D)
    "inh_followup_thought": "2",
}


# ---------------------------------------------------------------------------
# Persona-specific overrides
# ---------------------------------------------------------------------------

# Persona A — spends the inheritance: the entries of ToyLifecycleTool.xlsx
# → qualifies for the Inh_Followup chain, answers "no effect" → A→D
PERSONA_A = {
    "number": {
        "Demographics_Mother":           "65",
        "Demographics_Father":           "68",
        "Demographics_MotherInheritance":"50000",
        "Demographics_FatherInheritance":"50000",
        **_reaction_values(
            present_changes=[30000, 10000, 5000, 5000, 0, 0, 0, 0],
            future_changes=[2500, 2500, 25000, 10000, 5000, 5000, 0, 0]),
    },
    "radio": {},
    "blank": [],
}

# Persona B — no reaction: spending unchanged in every year
# → qualifies for the Inh_Followup chain, answers that the inheritance affects them → A only
PERSONA_B = {
    "number": {
        "Demographics_Mother":           "65",
        "Demographics_Father":           "68",
        "Demographics_MotherInheritance":"50000",
        "Demographics_FatherInheritance":"50000",
        **_reaction_values(present_changes=[0] * 8, future_changes=[0] * 8),
    },
    "radio": {"inh_followup_effect": "1"},
    "blank": [],
}

# Persona C — spends less in some years, blank parents → skips the Inh_Followup chain
PERSONA_C = {
    "number": {
        **_reaction_values(
            present_changes=[-1000, 0, 0, 0, 0, 0, 0, -1000],
            future_changes=[-2000, -2000, 0, 0, 0, 0, 0, 0]),
    },
    "radio": {},
    "blank": [
        "Demographics_Mother",
        "Demographics_Father",
        "Demographics_MotherInheritance",
        "Demographics_FatherInheritance",
    ],
}

PERSONAS = {"A": PERSONA_A, "B": PERSONA_B, "C": PERSONA_C}

PERSONA_DESCRIPTIONS = {
    "A": "spends it — entries of ToyLifecycleTool.xlsx, full Inh_Followup chain",
    "B": "no reaction — spending unchanged, own inheritance affects them (Inh_Followup_A only)",
    "C": "spends less — lower spending in some years, no own inheritance, skips Inh_Followup",
}


# ---------------------------------------------------------------------------
# Build merged value tables for the active persona
# ---------------------------------------------------------------------------

def _build_number_values(persona):
    merged = dict(NUMBER_VALUES_BASE)
    merged.update(persona["number"])
    return merged

def _build_radio_values(persona):
    merged = dict(RADIO_VALUES_BASE)
    merged.update(persona["radio"])
    return merged

def _build_blank_set(persona):
    return set(persona["blank"])


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
# Per-participant runner
# ---------------------------------------------------------------------------

def run_participant(
    page,
    participant_url,
    out_dir,
    folder_label,
    max_steps,
    number_values,
    blank_fields,
    radio_values,
    capture_once_labels,
    already_captured_once,
):
    page.goto(participant_url, wait_until="domcontentloaded")

    seen_labels = set()

    for step in range(1, max_steps + 1):
        page.wait_for_load_state("domcontentloaded")
        plabel = resolve_page_label(page)

        # --- Screenshot this page (once per label) ---
        if plabel not in seen_labels:
            should_capture = not (plabel in capture_once_labels and plabel in already_captured_once)
            if should_capture:
                file_name = f"{len(seen_labels) + 1:03d}_{plabel}.png"
                target = out_dir / folder_label / file_name
                target.parent.mkdir(parents=True, exist_ok=True)
                capture_page(page, target)
                if plabel in capture_once_labels:
                    already_captured_once.add(plabel)
            seen_labels.add(plabel)

        # --- BotScreening: enable the Next button via JS then submit ---
        if plabel == "BotScreening":
            if fast_forward_bot_screening(page):
                continue

        # --- Scenario pages: #nextBtn + #quick-alert DOM warning ---
        # These pages use a custom #nextBtn (not the oTree next button).
        # Clicking it within 10s reveals #quick-alert. We need to:
        #   1. Click #nextBtn  (alert appears, no navigation)
        #   2. Screenshot the alert
        #   3. Click #quick-alert-ok  (alert hides, warningConfirmed = true)
        #   4. Click #nextBtn again   (form.submit() → navigates)
        if page.locator("#nextBtn").count() > 0:
            fill_fields(page, number_values, blank_fields, radio_values)

            # Step 1: click Next — will trigger the warning alert
            page.locator("#nextBtn").click()
            page.wait_for_timeout(400)  # let the alert render

            alert = page.locator("#quick-alert")
            if alert.is_visible():
                # Step 2: screenshot page with alert visible
                alert_file = f"{len(seen_labels):03d}_{plabel}_warning_alert.png"
                alert_target = out_dir / folder_label / alert_file
                alert_target.parent.mkdir(parents=True, exist_ok=True)
                capture_page(page, alert_target)

                # Step 3: click Ok to dismiss alert
                page.locator("#quick-alert-ok").click()
                page.wait_for_timeout(200)

            # Step 4: click Next again — now submits
            url_before = page.url
            try:
                with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                    page.locator("#nextBtn").click()
            except PlaywrightTimeoutError:
                if page.url == url_before:
                    force_advance_form(page)
            continue

        # --- Normal pages: standard oTree Next button ---
        btn = next_button_locator(page)
        if btn is None:
            break

        fill_fields(page, number_values, blank_fields, radio_values)

        url_before = page.url
        try:
            with page.expect_navigation(wait_until="domcontentloaded", timeout=5000):
                btn.click()
        except PlaywrightTimeoutError:
            if page.url == url_before:
                # Navigation didn't happen — retry
                try:
                    btn.click()
                    page.wait_for_url(lambda u: u != url_before, timeout=5000)
                except Exception:
                    if not force_advance_form(page):
                        break
            if page.url == url_before:
                if not force_advance_form(page):
                    break

        if "LinkToProlific" in page.url:
            page.wait_for_load_state("domcontentloaded")
            end_label = resolve_page_label(page)
            target = out_dir / folder_label / f"{step + 1:03d}_{end_label}.png"
            capture_page(page, target)
            break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url",    default=BASE_URL)
    parser.add_argument("--app",         default=APP_NAME)
    parser.add_argument("--treatments",  type=int, default=NUM_TREATMENTS)
    parser.add_argument("--max-steps",   type=int, default=MAX_STEPS)
    parser.add_argument("--out",         default=OUT_DIR)
    parser.add_argument("--persona",     default=ACTIVE_PERSONA,
                        choices=["A", "B", "C"],
                        help="Override ACTIVE_PERSONA from CLI")
    parser.add_argument("--headed",      action="store_true", default=HEADED)
    parser.add_argument("--no-headed",   dest="headed", action="store_false")
    args = parser.parse_args()

    persona_key = args.persona.upper()
    persona = PERSONAS[persona_key]
    number_values = _build_number_values(persona)
    blank_fields   = _build_blank_set(persona)

    num_treatments = min(args.treatments, len(GROUPS))

    out_root = Path(args.out)
    # Output goes to: screenshots/CS1_personaA/treatment_01_natural_2_present_first_spendframe/ etc.
    out_dir = out_root / f"{args.app}_persona{persona_key}"
    out_dir.mkdir(parents=True, exist_ok=True)

    already_captured_once = set()

    print(f"\n{'='*60}")
    print(f"  CS1 Screenshot Capture")
    print(f"  Persona : {persona_key} — {PERSONA_DESCRIPTIONS[persona_key]}")
    print(f"  Output  : {out_dir.resolve()}")
    print(f"  Treatments: {num_treatments}  |  Headed: {args.headed}")
    print(f"{'='*60}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        setup_page = browser.new_page(viewport={"width": 1440, "height": 1100})

        print(f"Creating session with {num_treatments} participant slots…")
        participant_links = create_session_and_get_links(
            page=setup_page,
            base_url=args.base_url,
            app_name=args.app,
            expected_links=num_treatments,
        )
        setup_page.close()

        for t_idx in range(num_treatments):
            if t_idx >= len(participant_links):
                print(f"  Warning: ran out of links at treatment {t_idx + 1}")
                break

            group_str  = GROUPS[t_idx]
            radio_values = _build_radio_values(persona)

            folder_label = f"treatment_{t_idx + 1:02d}_{group_str}"
            url = participant_links[t_idx]

            print(f"  [{t_idx + 1:02d}/{num_treatments}] {group_str}")

            run_page = browser.new_page(viewport={"width": 1440, "height": 1100})
            run_participant(
                page=run_page,
                participant_url=url,
                out_dir=out_dir,
                folder_label=folder_label,
                max_steps=args.max_steps,
                number_values=number_values,
                blank_fields=blank_fields,
                radio_values=radio_values,
                capture_once_labels=CAPTURE_ONCE_LABELS,
                already_captured_once=already_captured_once,
            )
            run_page.close()

        browser.close()

    print(f"\nDone — Persona {persona_key} screenshots saved to: {out_dir.resolve()}")
    print("\nNext steps:")
    print("  1. Review screenshots in the folder above")
    print("  2. Run:  otree resetdb")
    next_p = {"A": "B", "B": "C", "C": "— all done!"}.get(persona_key, "")
    if next_p != "— all done!":
        print(f"  3. Change ACTIVE_PERSONA = \"{next_p}\" at the top of this script")
        print(f"  4. Rerun script")
    else:
        print(f"  3. {next_p}")


if __name__ == "__main__":
    main()