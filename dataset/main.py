# -*- coding: utf-8 -*-
"""
Message Notification Router
===========================

Deterministic, explainable routing engine for the HackerRank Orchestrate
Message Notification Router challenge.

For every incoming message in `dataset/messages.csv`, the engine decides:

  * `notify`  : important enough to interrupt the user now
  * `digest`  : useful, but can be shown later
  * `mute`    : low-value, repetitive, unwanted, suspicious, or unsafe

The engine fuses:

  * message content (text) + media type
  * sender/business trust (verification, domain, age, reports)
  * user-specific engagement (opt-ins/outs, historical reactions)
  * group context (admin, group type, muted state)
  * historical evidence (message_history + message_events)

It is fully deterministic (no network / no API keys) and writes
`dataset/output.csv` with the exact required columns.

Run:
    python code/main.py
"""

import csv
import os
import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
OUTPUT_PATH = os.path.join(DATASET_DIR, "output.csv")


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def load_csv(filename):
    path = os.path.join(DATASET_DIR, filename)
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

class Context:
    def __init__(self):
        self.users = {}
        self.groups = {}
        self.group_members = {}
        self.businesses = {}
        self.user_business = {}
        self.history_by_user = defaultdict(list)
        self.events = {}
        self.events_by_user = defaultdict(list)
        self.images = {}
        self.voice_notes = {}
        self.daily_summary = defaultdict(list)

    def group_member(self, group_id, user_id):
        return self.group_members.get((group_id, user_id))

    def business(self, business_id):
        return self.businesses.get(business_id)

    def user_biz(self, user_id, business_id):
        return self.user_business.get((user_id, business_id))


def build_context():
    ctx = Context()
    for row in load_csv("users.csv"):
        ctx.users[row["user_id"]] = row
    for row in load_csv("groups.csv"):
        ctx.groups[row["group_id"]] = row
    for row in load_csv("group_members.csv"):
        ctx.group_members[(row["group_id"], row["user_id"])] = row
    for row in load_csv("business_accounts.csv"):
        ctx.businesses[row["business_id"]] = row
    for row in load_csv("user_business_history.csv"):
        ctx.user_business[(row["user_id"], row["business_id"])] = row
    for row in load_csv("message_history.csv"):
        ctx.history_by_user[row["user_id"]].append(row)
    for row in load_csv("message_events.csv"):
        ctx.events[row["message_id"]] = row
        ctx.events_by_user[row["user_id"]].append(row)
    for row in load_csv("images.csv"):
        ctx.images[row["image_id"]] = row
    for row in load_csv("voice_notes.csv"):
        ctx.voice_notes[row["voice_note_id"]] = row
    for row in load_csv("daily_notification_summary.csv"):
        ctx.daily_summary[row["user_id"]].append(row)
    return ctx


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "to",
    "of", "in", "on", "at", "for", "with", "and", "or", "but", "if", "then",
    "this", "that", "these", "those", "it", "its", "your", "you", "my", "me",
    "i", "we", "us", "our", "they", "them", "he", "she", "his", "her", "have",
    "has", "had", "do", "does", "did", "will", "would", "can", "could", "should",
    "please", "pls", "kindly", "today", "tomorrow", "now", "just", "also",
    "from", "into", "over", "under", "before", "after", "during", "about",
    "need", "needs", "want", "wants", "hi", "hello", "dear", "team", "re",
    "fwd", "forwarded", "forward", "msg", "message", "get", "got", "let",
    "one", "two", "when", "what", "who", "why", "how", "all", "any", "some",
    "reply", "respond", "check", "see", "view", "open", "click", "tap",
    "below", "share", "sending", "send", "sent", "make", "keep", "still",
    "evening", "morning", "night", "day", "time", "pm", "am", "eod", "etc",
}


def normalize_text(text):
    if not text:
        return []
    text = text.lower()
    text = re.sub(r"[^\w\s@]", " ", text)
    return [t for t in text.split() if t not in STOPWORDS and len(t) > 1]


def contains_any(text, keywords):
    """Word-boundary substring check."""
    if not text:
        return False
    low = text.lower()
    for kw in keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", low):
            return True
    return False


def overlap_score(a_tokens, b_text):
    b_tokens = normalize_text(b_text)
    if not a_tokens or not b_tokens:
        return 0.0
    a = set(a_tokens)
    b = set(b_tokens)
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return (2.0 * inter) / (len(a) + len(b))


NEGATION_PHRASES = [
    "no rush", "nothing urgent", "no urgency", "not urgent", "nothing blocking",
    "whenever convenient", "when you get time", "no hurry", "don't call now",
    "no need to reply", "no need to respond", "not required", "if you get time",
    "read when", "no deadline", "koi urgency nahi", "nothing dramatic",
    "whenever free", "when free", "no pressure", "no urgency at all",
    "nothing to decide", "no action needed", "no intraday call",
]


def has_negation(text):
    if not text:
        return False
    low = text.lower()
    return any(p in low for p in NEGATION_PHRASES)


def count_urgent_keywords(text):
    """Count urgent signals in text with word boundaries."""
    if not text:
        return 0
    low = text.lower()
    count = 0
    for kw in ["urgent", "asap", "now", "today", "tonight", "immediately",
               "deadline", "closes", "closing", "escalation",
               "call me", "failing", "come online", "expire", "blocked",
               "restricted", "need to decide", "final", "last"]:
        if re.search(r"\b" + re.escape(kw) + r"\b", low):
            count += 1
    if re.search(r"\b\d+\s*min(?:ute)?s?\b", low):
        count += 1
    if re.search(r"\b\d+\s*(?:pm|am)\b", low):
        count += 1
    return count


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------

PROMPT_INJECTION_PATTERNS = [
    "ignore previous routing rules",
    "ignore all previous routing rules",
    "ignore sender risk",
    "mark this as notify",
    "mark as notify",
    "mark notify",
    "routing override",
    "assistant instruction",
    "system note for the notification router",
    "system note for router",
    "system note for the router",
    "internal router metadata",
    "set action=notify",
    "classify as urgent",
    "always mark this as notify",
    "action=notify",
    "router metadata",
    "this user opens banking alerts",
    "user_priority=high",
    "verified_business=true",
]


def detect_prompt_injection(text):
    if not text:
        return False
    low = text.lower()
    for pat in PROMPT_INJECTION_PATTERNS:
        if pat in low:
            return True
    if re.search(r"ignore\s+.*\b(rules|routing|instructions|prompt)\b", low):
        return True
    return False


SCAM_PATTERNS = [
    # credential requests
    (r"\botp\b", 3),
    (r"login code", 3),
    (r"verification code", 3),
    (r"confirm your pin", 3),
    (r"wallet pin", 3),
    (r"card number", 3),
    (r"card details", 3),
    (r"bank details", 3),
    (r"bank credentials", 3),
    (r"6[- ]?digit", 3),
    (r"share otp", 4),
    (r"send otp", 4),
    (r"otp batao", 4),
    (r"code daal do", 3),
    (r"enter otp", 3),
    (r"share the otp", 4),
    (r"send the code", 3),
    (r"reply with the 6", 4),
    (r"send screenshot", 3),
    # account pressure
    (r"account will be blocked", 3),
    (r"profile will be blocked", 3),
    (r"profile will be restricted", 3),
    (r"account block", 3),
    (r"account may get locked", 3),
    (r"profile may be temporarily blocked", 3),
    (r"access will expire", 3),
    (r"expire today", 2),
    (r"blocked in 2 hours", 3),
    (r"permanent block", 3),
    (r"account lock", 3),
    (r"account closure", 3),
    (r"access is suspended", 3),
    (r"access card may be blocked", 3),
    (r"restricted today", 3),
    (r"hold pe chala jayega", 3),
    (r"band ho jayega", 3),
    (r"security check required", 3),
    (r"failed login", 3),
    (r"verify through this link", 4),
    (r"verify this link", 4),
    (r"verify wallet", 3),
    (r"verify your", 2),
    (r"complete verification", 3),
    (r"final reminder", 2),
    # prizes / lottery / financial fraud
    (r"selected for reward", 3),
    (r"number was selected", 3),
    (r"voucher expires", 3),
    (r"claim today", 2),
    (r"claim before", 2),
    (r"congrats", 1),
    (r"guaranteed returns", 3),
    (r"crypto arbitrage", 3),
    (r"daily return", 3),
    (r"loan approved", 3),
    (r"processing fee", 3),
    (r"pay processing fee", 4),
    (r"token booking", 2),
    (r"token amount", 2),
    (r"registry papers", 2),
    (r"pay rs ?[0-9,]+ token", 3),
    (r"assured appreciation", 3),
    # payment/link pressure
    (r"scan this qr", 3),
    (r"scan the qr", 3),
    (r"scan and pay", 3),
    (r"scan a qr", 2),
    (r"send screenshot after", 3),
    (r"send screenshot once done", 3),
    (r"share your account number", 3),
    (r"account number", 1),
    (r"refund could not be processed", 3),
    (r"reattempt charge", 3),
    (r"reattempt fee", 3),
    (r"release the amount", 2),
    (r"approval window closes", 2),
    (r"urgent document", 2),
    (r"claim benefits", 2),
    (r"final warning", 2),
    (r"clearance amount", 2),
    (r"service stops today", 2),
    (r"service reactivation fee", 3),
    (r"penalty list", 2),
    (r"use this link", 2),
    # suspicious domains / links
    (r"bit\.ly", 4),
    (r"account-login", 4),
    (r"account-help", 4),
    (r"chase-secure-alert", 5),
    (r"hsbc-alerts", 5),
    (r"amazonpay-delivery", 5),
    (r"razorpayx-payouts", 5),
    (r"pay-check-secure", 5),
    (r"verify-quick", 4),
    (r"secure-alert", 3),
    (r"-kyc\.in", 4),
    (r"lucky-draw", 3),
    (r"vl\.gl", 4),
    (r"shorturl", 3),
    (r"weurl", 2),
    (r"refund pending", 2),
    (r"verify pending", 2),
    (r"not real bank site", 4),
    (r"asks username and otp", 4),
]


def scam_signals(text):
    if not text:
        return [], 0.0
    low = text.lower()
    matched = []
    total = 0.0
    for pattern, weight in SCAM_PATTERNS:
        if re.search(pattern, low):
            matched.append(pattern)
            total += weight
    return matched, total


# ---------------------------------------------------------------------------
# Business-level scam detection
# ---------------------------------------------------------------------------

def business_scam_score(biz):
    if not biz:
        return 0.0
    verified = int(biz.get("verified", 0) or 0)
    try:
        age = int(biz.get("account_age_days", 0) or 0)
    except ValueError:
        age = 0
    try:
        domain_age = int(biz.get("domain_used_by_sender_age_days", 0) or 0)
    except ValueError:
        domain_age = 0
    try:
        reports = int(biz.get("user_reports_30d", 0) or 0)
    except ValueError:
        reports = 0

    official = (biz.get("official_domain") or "").strip().lower()
    used = (biz.get("domain_used_by_sender") or "").strip().lower()

    score = 0.0
    if verified == 0:
        score += 2.0
    if used and official and used != official:
        score += 2.5
    if age < 60:
        score += 2.0
    if domain_age < 30:
        score += 1.5
    if reports >= 20:
        score += 2.0
    elif reports >= 8:
        score += 1.0
    return score


def is_legit_local_business(biz):
    if not biz:
        return False
    try:
        age = int(biz.get("account_age_days", 0) or 0)
    except ValueError:
        age = 0
    try:
        reports = int(biz.get("user_reports_30d", 0) or 0)
    except ValueError:
        reports = 0
    verified = int(biz.get("verified", 0) or 0)
    return verified == 0 and age > 180 and reports <= 2


# ---------------------------------------------------------------------------
# Evidence retrieval
# ---------------------------------------------------------------------------

def _recency_bonus(hist_row, msg):
    try:
        import datetime as dt
        h = dt.datetime.fromisoformat(hist_row["created_at"])
        m = dt.datetime.fromisoformat(msg["created_at"])
        days = (m - h).days
        if days <= 14:
            return 1.0
        if days <= 30:
            return 0.5
        if days <= 60:
            return 0.25
    except Exception:
        pass
    return 0.0


def retrieve_evidence(msg, ctx, prefer="engage", limit=3):
    """Find the most relevant historical messages for this incoming message."""
    user_id = msg["user_id"]
    hist = ctx.history_by_user.get(user_id, [])
    if not hist:
        return []

    incoming_tokens = normalize_text(msg.get("message_text", ""))
    ctype = msg.get("conversation_type")

    primary = []
    for h in hist:
        if ctype == "business" and h.get("conversation_type") == "business" and \
                h.get("business_id") == msg.get("business_id"):
            primary.append(h)
        elif ctype == "group" and h.get("conversation_type") == "group" and \
                h.get("group_id") == msg.get("group_id"):
            primary.append(h)
        elif ctype == "personal" and h.get("conversation_type") == "personal" and \
                h.get("sender_user_id") and h.get("sender_user_id") == msg.get("sender_user_id"):
            primary.append(h)

    pool = primary if primary else hist

    scored = []
    for h in pool:
        match = 0.0
        if ctype == "business" and h.get("business_id") == msg.get("business_id"):
            match += 3.0
        elif ctype == "group" and h.get("group_id") == msg.get("group_id"):
            match += 2.5
            if h.get("sender_user_id") and h.get("sender_user_id") == msg.get("sender_user_id"):
                match += 1.0
        elif ctype == "personal" and h.get("sender_user_id") and h.get("sender_user_id") == msg.get("sender_user_id"):
            match += 3.0

        sim = overlap_score(incoming_tokens, h.get("message_text", ""))
        score = match + (sim * 4.0) + _recency_bonus(h, msg)

        ev = ctx.events.get(h["message_id"])
        if ev:
            opened = int(ev.get("message_opened", 0) or 0)
            replied = int(ev.get("message_replied", 0) or 0)
            dismissed = int(ev.get("notification_dismissed", 0) or 0)
            muted = int(ev.get("muted_after_message", 0) or 0)
            reported = int(ev.get("message_reported", 0) or 0)
            if prefer == "engage":
                score += replied * 1.5 + opened * 0.5 - (muted + reported) * 1.0
            else:
                score += (muted + dismissed + reported) * 1.0 - replied * 1.0

        if score > 0:
            scored.append((score, h["message_id"]))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [mid for _, mid in scored[:limit]]


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------

def clamp_conf(v):
    return round(max(0.0, min(1.0, v)), 2)


# ---------------------------------------------------------------------------
# Router helpers
# ---------------------------------------------------------------------------

def user_engagement_profile(ctx, user_id, sender_user_id=None, group_id=None, business_id=None):
    opened = replied = dismissed = muted = reported = 0
    count = 0
    for h in ctx.history_by_user.get(user_id, []):
        relevant = False
        if sender_user_id and h.get("sender_user_id") == sender_user_id:
            relevant = True
        if group_id and h.get("group_id") == group_id:
            relevant = True
        if business_id and h.get("business_id") == business_id:
            relevant = True
        if not relevant:
            continue
        ev = ctx.events.get(h["message_id"])
        if ev:
            count += 1
            opened += int(ev.get("message_opened", 0) or 0)
            replied += int(ev.get("message_replied", 0) or 0)
            dismissed += int(ev.get("notification_dismissed", 0) or 0)
            muted += int(ev.get("muted_after_message", 0) or 0)
            reported += int(ev.get("message_reported", 0) or 0)
    return {
        "count": count, "opened": opened, "replied": replied,
        "dismissed": dismissed, "muted": muted, "reported": reported,
    }


def is_forward_chain(text, forwarded_count):
    if int(forwarded_count or 0) >= 6:
        return True
    if not text:
        return False
    low = text.lower()
    return ("forward this to" in low or "share this with" in low or
            "send this to" in low or "forward to" in low or
            "share in all" in low or "share with" in low or
            "fwd as received" in low or "fwd from" in low)


def is_greeting(text):
    if not text:
        return False
    low = text.lower()
    return any(k in low for k in [
        "good morning", "blessed", "blessing", "good vibes", "stay positive",
        "keep smiling", "positive energy", "bhagwan", "sabka bhala",
        "have a good day", "peaceful day", "good day", "smile today",
    ])


def is_health_forward(text):
    if not text:
        return False
    low = text.lower()
    return any(k in low for k in [
        "warm water", "health secret", "health tip", "herbal mix", "natural cure",
        "cures diabetes", "stop all tablets", "share in family groups",
        "elders at home", "drink warm water", "share with elders",
        "good health", "simple habit will fix health",
    ])


def has_direct_address(text):
    if not text:
        return False
    low = text.lower()
    if "can you collect" in low or "aside for you" in low or "kept the" in low:
        return True
    if re.search(r"\b(can you|please|could you|pls)\b", low):
        return True
    return False


def has_deadline(text):
    if not text:
        return False
    low = text.lower()
    if re.search(r"\b\d+\s*(?:pm|am)\b", low):
        return True
    if re.search(r"\b(today|tonight|weekend|tomorrow|by 6|by 5|before \d)", low):
        return True
    return False


def is_in_dnd(msg, user_row):
    """Check if msg created_at falls inside the user's do-not-disturb window."""
    try:
        import datetime as dt
        t = dt.datetime.fromisoformat(msg.get("created_at", ""))
        dnd = (user_row or {}).get("do_not_disturb_window", "")
        if not dnd or "-" not in dnd:
            return False
        start_s, end_s = dnd.split("-")
        start = dt.datetime.strptime(start_s.strip(), "%H:%M").time()
        end = dt.datetime.strptime(end_s.strip(), "%H:%M").time()
        tm = t.time()
        if start <= end:
            return start <= tm <= end
        return tm >= start or tm <= end
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Routing: business
# ---------------------------------------------------------------------------

BUSINESS_TRANSACTIONAL_KEYWORDS = [
    "order", "packed", "delivery", "refund", "pickup", "statement", "bill",
    "card payment", "appointment", "prescription", "booking", "driver",
    "arrival", "payout", "account update", "return", "challan", "insurance",
    "renewal", "banking", "repair", "utility", "outage", "route", "fare",
    "class", "reservation", "fee receipt", "consent", "amount due",
]

BUSINESS_PROMO_KEYWORDS = [
    "off", "offer", "discount", "sale", "coupon", "benefit", "reward",
    "cashback", "shopping", "unsubscribe", "opt out", "expires", "welcome",
    "ladakh", "travel deal", "package", "limited", "saved", "launch",
    "let's connect", "resonate", "pain points", "help simplify", "collection",
]

BUSINESS_FEEDBACK_KEYWORDS = [
    "feedback", "review", "survey", "session update", "share your experience",
    "how has your experience", "tell us how", "valuable feedback",
    "3-minute", "minutes to understand", "take a few minutes",
]

APPOINTMENT_TYPE_KEYWORDS = [
    "appointment", "prescription", "booking", "clinic", "consult", "reservation",
    "payout profile", "pickup", "return", "scheduled",
]


def route_business(msg, ctx):
    biz = ctx.business(msg.get("business_id", ""))
    text = msg.get("message_text", "") or ""
    media = msg.get("media_type", "") or ""
    user_id = msg["user_id"]
    signals = []

    if detect_prompt_injection(text):
        return {
            "action": "mute", "message_type": "scam",
            "reason": "The message tries to instruct the router, but the routing decision should be based on the actual content and risk.",
            "confidence": 0.86,
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    # Strong business-metadata phishing signal.
    scam_biz_score = business_scam_score(biz)
    if not is_legit_local_business(biz) and scam_biz_score >= 5.0:
        return {
            "action": "mute", "message_type": "scam",
            "reason": "The sender is an unverified account with a suspicious domain and a high report rate.",
            "confidence": 0.87,
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    matched, scam_weight = scam_signals(text)
    if scam_weight >= 6.0:
        return {
            "action": "mute", "message_type": "scam",
            "reason": "The message shows strong scam signals: credential requests, suspicious links, or financial pressure.",
            "confidence": clamp_conf(0.85 + 0.01 * min(3, len(matched))),
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    ub = ctx.user_biz(user_id, msg.get("business_id", ""))
    prof = user_engagement_profile(ctx, user_id, business_id=msg.get("business_id", ""))

    opted_out = bool(ub and ub.get("promotions_opted_out_at"))
    implicit_opt_out = (prof.get("muted", 0) + prof.get("reported", 0)) > 0 and prof.get("replied", 0) == 0
    opted_out = opted_out or implicit_opt_out
    allows_promos = bool(ub and int(ub.get("allows_promotions", 0) or 0) == 1)

    is_promo = contains_any(text, BUSINESS_PROMO_KEYWORDS) or (media == "image" and not text)
    is_feedback = contains_any(text, BUSINESS_FEEDBACK_KEYWORDS)
    is_transactional = contains_any(text, BUSINESS_TRANSACTIONAL_KEYWORDS)

    # Voice notes
    if media == "voice":
        if opted_out:
            return {
                "action": "mute", "message_type": "promotion",
                "reason": "The user has opted out of or repeatedly dismissed similar marketing messages.",
                "confidence": 0.83,
                "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
            }
        if ub and (allows_promos or (ub.get("activity_count_180d") and int(ub.get("activity_count_180d")) > 0)):
            return {
                "action": "digest", "message_type": "promotion",
                "reason": "The message is from a business the user has an active relationship with, but it does not require immediate attention.",
                "confidence": 0.80,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        return {
            "action": "digest", "message_type": "business_update",
            "reason": "A legitimate business sent a voice update that can be reviewed later.",
            "confidence": 0.78,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # Opted-out promo -> mute
    if is_promo and opted_out:
        return {
            "action": "mute", "message_type": "promotion",
            "reason": "The user has opted out of or repeatedly dismissed similar marketing messages.",
            "confidence": 0.84,
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    # Promo pitch (B2B / offers)
    if is_promo and (contains_any(text, ["let's connect", "resonate", "pain points", "welcome"]) or not is_transactional):
        if allows_promos:
            return {
                "action": "digest", "message_type": "promotion",
                "reason": "The message is promotional but matches a topic or business the user has opted into.",
                "confidence": 0.81,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        return {
            "action": "digest", "message_type": "promotion",
            "reason": "The message is promotional but does not need immediate attention.",
            "confidence": 0.79,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # Transactional with active relationship -> notify
    if is_transactional and ub and ub.get("activity_count_180d") and int(ub.get("activity_count_180d")) >= 1:
        signals.append("active_relationship")
        if contains_any(text, APPOINTMENT_TYPE_KEYWORDS):
            mtype = "event"
        else:
            mtype = "business_update"
        return {
            "action": "notify", "message_type": mtype,
            "reason": "A verified business sent an update that matches the user's recent activity or relationship.",
            "confidence": clamp_conf(0.88 + 0.01 * min(3, len(signals) + prof.get("replied", 0))),
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # Verified transactional without relationship -> digest
    if is_transactional and biz and int(biz.get("verified", 0) or 0) == 1:
        return {
            "action": "digest", "message_type": "business_update",
            "reason": "A legitimate business sent a non-urgent update that can be read later.",
            "confidence": 0.81,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # Feedback / survey -> digest
    if is_feedback:
        return {
            "action": "digest", "message_type": "business_update",
            "reason": "A legitimate business sent a non-urgent update that can be read later.",
            "confidence": 0.80,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # Generic promo
    if is_promo:
        return {
            "action": "digest", "message_type": "promotion",
            "reason": "The message is promotional but does not need immediate attention.",
            "confidence": 0.79,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # Verified generic
    if biz and int(biz.get("verified", 0) or 0) == 1:
        return {
            "action": "digest", "message_type": "business_update",
            "reason": "A legitimate business sent a non-urgent update that can be read later.",
            "confidence": 0.80,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # Local legit business (Green Cross style)
    if is_legit_local_business(biz):
        return {
            "action": "digest", "message_type": "business_update",
            "reason": "A trusted local business sent an update that can be read later.",
            "confidence": 0.80,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    return {
        "action": "digest", "message_type": "unknown",
        "reason": "The sender is unfamiliar, but the message does not show urgency, payment pressure, or safety risk.",
        "confidence": 0.78,
        "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
    }


# ---------------------------------------------------------------------------
# Routing: group
# ---------------------------------------------------------------------------

def route_group(msg, ctx):
    group = ctx.groups.get(msg.get("group_id", ""), {})
    group_type = group.get("group_type", "")
    text = msg.get("message_text", "") or ""
    media = msg.get("media_type", "") or ""
    sender = msg.get("sender_user_id", "")
    user_id = msg["user_id"]
    forwarded = int(msg.get("forwarded_count", 0) or 0)

    sender_member = ctx.group_member(msg.get("group_id", ""), sender)
    is_admin_sender = bool(sender_member and sender_member.get("role") == "admin")

    prof = user_engagement_profile(ctx, user_id, sender_user_id=sender, group_id=msg.get("group_id", ""))

    if detect_prompt_injection(text):
        return {
            "action": "mute", "message_type": "scam",
            "reason": "The message tries to instruct the router, but the routing decision should be based on the actual content and risk.",
            "confidence": 0.87,
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    matched, scam_weight = scam_signals(text)

    # 1) Strong scam text
    if scam_weight >= 6.0:
        return {
            "action": "mute", "message_type": "scam",
            "reason": "The message shows strong scam signals: credential requests, suspicious links, or financial pressure.",
            "confidence": clamp_conf(0.85 + 0.01 * min(3, len(matched))),
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    # 2) Non-admin financial pressure in noise-prone groups -> scam
    if not is_admin_sender and group_type in ("society", "school_group", "finance_help", "real_estate", "marketplace"):
        low = text.lower()
        fin_pressure = contains_any(text, ["pay", "qr", "link", "otp", "screenshot", "payment", "token", "scan"]) or "bank details" in low
        if fin_pressure and (prof.get("muted", 0) + prof.get("reported", 0) > 0 or prof.get("replied", 0) == 0):
            return {
                "action": "mute", "message_type": "scam",
                "reason": "A non-admin sender is applying payment or verification pressure that the user has historically muted or reported.",
                "confidence": 0.85,
                "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
            }

    is_mention = bool(re.search(r"@" + re.escape(user_id) + r"\b", text))

    # 3) Direct mention + action -> notify
    if is_mention and contains_any(text, ["call", "pls", "please", "need", "check",
                                          "can you", "confirm", "send", "come",
                                          "urgent", "now", "before", "quick", "move"]):
        if has_negation(text):
            return {
                "action": "notify", "message_type": "personal",
                "reason": "The sender directly asks this user for a response or action.",
                "confidence": 0.83,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        if has_deadline(text) or count_urgent_keywords(text) >= 1:
            return {
                "action": "notify", "message_type": "urgent",
                "reason": "The sender directly asks this user for a response or action with a time constraint.",
                "confidence": 0.87,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        return {
            "action": "notify", "message_type": "personal",
            "reason": "The sender directly asks this user for a response or action.",
            "confidence": 0.85,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # 4) Admin handling
    if is_admin_sender:
        low = text.lower()
        urgent = count_urgent_keywords(text)
        if media == "voice":
            return {
                "action": "notify", "message_type": "event",
                "reason": "A trusted group admin sent a same-day update the user is likely to need immediately.",
                "confidence": 0.83,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        if urgent >= 2 or any(k in low for k in ["urgent", "leaving in", "collect now", "now",
                                                  "closes", "blocked"]):
            return {
                "action": "notify", "message_type": "urgent",
                "reason": "A trusted group admin sent a time-sensitive update that should interrupt the user.",
                "confidence": clamp_conf(0.87 + 0.01 * min(3, urgent)),
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        if not has_negation(text) and (urgent >= 1 or group_type in ("society", "school_group", "coworker")):
            return {
                "action": "notify", "message_type": "event",
                "reason": "A trusted group admin sent a same-day update the user is likely to need immediately.",
                "confidence": clamp_conf(0.85 + 0.01 * urgent),
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        # Informational admin announcement -> digest
        return {
            "action": "digest", "message_type": "event",
            "reason": "The message is useful group information, but it is not urgent enough to interrupt the user.",
            "confidence": 0.82,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # 5) Direct address + deadline + engagement -> notify personal
    if has_direct_address(text) and has_deadline(text) and prof.get("replied", 0) > 0:
        return {
            "action": "notify", "message_type": "personal",
            "reason": "The sender directly asks this user for a response or action with a deadline.",
            "confidence": 0.84,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # 6) Forward chains
    if is_forward_chain(text, forwarded):
        if is_greeting(text):
            return {
                "action": "mute", "message_type": "greeting",
                "reason": "The sender has a pattern of repeated forwards or greetings that the user usually ignores.",
                "confidence": 0.84,
                "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
            }
        if is_health_forward(text):
            return {
                "action": "mute", "message_type": "forward",
                "reason": "The sender has a pattern of repeated forwards that the user usually ignores.",
                "confidence": 0.84,
                "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
            }
        # Selling/promotional forward -> engagement-based
        if contains_any(text, ["selling", "sale", "discount", "offer", "plots", "token", "deal", "price"]):
            if prof.get("replied", 0) > 0 or prof.get("opened", 0) > prof.get("count", 0) * 0.5:
                return {
                    "action": "digest", "message_type": "promotion",
                    "reason": "The message matches the user's known interests but is still low priority.",
                    "confidence": 0.81,
                    "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
                }
            return {
                "action": "mute", "message_type": "promotion",
                "reason": "Similar historical messages were ignored, dismissed, or muted by this user.",
                "confidence": 0.84,
                "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
            }
        # General forward with positive engagement -> digest
        if prof.get("opened", 0) > 0 and prof.get("muted", 0) + prof.get("reported", 0) == 0:
            return {
                "action": "digest", "message_type": "personal",
                "reason": "The message is from a sender the user usually reads, but it does not need immediate attention.",
                "confidence": 0.80,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        return {
            "action": "mute", "message_type": "forward",
            "reason": "The sender has a pattern of repeated forwards that the user usually ignores.",
            "confidence": 0.83,
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    # 7) Marketplace / sales content
    high_noise_groups = {"marketplace", "real_estate", "investment_tips", "finance_help"}
    is_sell = contains_any(text, ["selling", "sale", "price", "rs ", "pickup", "dm if interested",
                                  "discount", "offer", "available", "buyer cancelled", "stock",
                                  "plots", "land", "token", "deal", "worn once", "barely used"])
    if is_sell and group_type in high_noise_groups:
        if prof.get("replied", 0) > 0 or prof.get("opened", 0) > prof.get("count", 0) * 0.5:
            return {
                "action": "digest", "message_type": "promotion",
                "reason": "The message matches the user's known interests but is still low priority.",
                "confidence": 0.82,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        return {
            "action": "mute", "message_type": "promotion",
            "reason": "Similar historical messages were ignored, dismissed, or muted by this user.",
            "confidence": 0.84,
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }
    if is_sell:
        return {
            "action": "digest", "message_type": "promotion",
            "reason": "The offer is potentially relevant, but it does not need immediate attention.",
            "confidence": 0.79,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # 8) Voice notes
    if media == "voice":
        if group_type in high_noise_groups and prof.get("muted", 0) + prof.get("dismissed", 0) > prof.get("opened", 0):
            return {
                "action": "mute", "message_type": "promotion",
                "reason": "Similar historical messages from this channel were ignored, dismissed, or muted by this user.",
                "confidence": 0.82,
                "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
            }
        return {
            "action": "digest", "message_type": "personal",
            "reason": "The sender is trusted, but the message has no urgent action or safety relevance.",
            "confidence": 0.80,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # 9) Greeting
    if is_greeting(text):
        return {
            "action": "digest", "message_type": "greeting",
            "reason": "The message is a harmless greeting that can be read later.",
            "confidence": 0.81,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # 10) Generic urgent / time-sensitive
    if contains_any(text, ["urgent", "need to decide", "call me", "come on", "escalation",
                           "failing", "deadline", "retries", "rollback", "incident",
                           "regression", "outage", "blocked now", "right now"]) or count_urgent_keywords(text) >= 2:
        # But check for negation ("nothing urgent", "no urgency")
        if not has_negation(text):
            return {
                "action": "notify", "message_type": "urgent",
                "reason": "The message is time-sensitive or asks for quick action from the user.",
                "confidence": 0.85,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }

    # 11) Event-like informational
    if contains_any(text, ["closes", "form", "submit", "circular", "consent", "registration",
                           "reminder", "schedule", "moved to", "changed", "today", "tomorrow",
                           "postponed", "deadline"]):
        if not has_negation(text):
            return {
                "action": "digest", "message_type": "event",
                "reason": "The message is useful information, but it is not urgent enough to interrupt the user.",
                "confidence": 0.82,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }

    # 12) Default: casual/personal -> digest
    return {
        "action": "digest", "message_type": "personal",
        "reason": "The message is safe casual chat with no urgent action required.",
        "confidence": 0.80,
        "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
    }


# ---------------------------------------------------------------------------
# Routing: personal
# ---------------------------------------------------------------------------

def route_personal(msg, ctx):
    text = msg.get("message_text", "") or ""
    sender = msg.get("sender_user_id", "")
    user_id = msg["user_id"]

    if detect_prompt_injection(text):
        return {
            "action": "mute", "message_type": "scam",
            "reason": "The message tries to instruct the router, but the routing decision should be based on the actual content and risk.",
            "confidence": 0.87,
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    matched, scam_weight = scam_signals(text)
    if scam_weight >= 5.0:
        return {
            "action": "mute", "message_type": "scam",
            "reason": "The message shows strong scam signals: credential requests, suspicious links, or financial pressure.",
            "confidence": clamp_conf(0.86 + 0.01 * min(3, len(matched))),
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    prof = user_engagement_profile(ctx, user_id, sender_user_id=sender)

    low = text.lower()
    negation = has_negation(text)
    urgent_hits = count_urgent_keywords(text)

    # Couriers / delivery / pickup direct asks with deadline (known sender)
    if contains_any(text, ["gate", "pickup", "flat confirmation", "collect", "courier",
                           "aside for you", "kept the"]):
        if prof.get("replied", 0) > 0 and has_deadline(text):
            return {
                "action": "notify", "message_type": "personal",
                "reason": "The sender directly asks this user for a response or action with a deadline.",
                "confidence": 0.84,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        if prof.get("replied", 0) > 0:
            return {
                "action": "digest", "message_type": "personal",
                "reason": "The sender is trusted, but the message has no deadline requiring immediate attention.",
                "confidence": 0.80,
                "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
            }
        return {
            "action": "mute", "message_type": "promotion",
            "reason": "Similar historical messages were ignored, dismissed, or muted by this user.",
            "confidence": 0.84,
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    # Forwarded health tips -> mute
    if is_health_forward(text) or int(msg.get("forwarded_count", 0) or 0) >= 6:
        return {
            "action": "mute", "message_type": "forward",
            "reason": "The sender has a pattern of repeated forwards that the user usually ignores.",
            "confidence": 0.84,
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    is_ask = bool(re.search(r"can you|could you|pls|please|call me|need you|send", low))

    # Urgent direct ask, not negated -> notify
    if not negation and (urgent_hits >= 2 or any(k in low for k in [
            "call me now", "come online now", "escalation starts", "right away",
            "need to decide in next", "10 minutes", "10 min", "20 minutes",
            "right now", "must"])):
        return {
            "action": "notify", "message_type": "urgent",
            "reason": "The message is from a known sender and contains a direct deadline or urgent request.",
            "confidence": 0.87,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    if not negation and is_ask and urgent_hits >= 1:
        return {
            "action": "notify", "message_type": "personal",
            "reason": "The sender directly asks this user for a response or action.",
            "confidence": 0.85,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # Trusted sender with history
    trusted = prof.get("count", 0) >= 2 and prof.get("opened", 0) > 0
    if is_ask and trusted:
        return {
            "action": "notify", "message_type": "personal",
            "reason": "The sender directly asks this user for a response or action.",
            "confidence": 0.84,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # Trusted casual -> digest
    if trusted:
        return {
            "action": "digest", "message_type": "personal",
            "reason": "The sender is trusted, but the message has no urgent action or safety relevance.",
            "confidence": 0.81,
            "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
        }

    # Unknown sender with urgent/verify/pay pressure -> mute/scam
    if contains_any(text, ["urgent", "otp", "verify", "pay", "blocked", "expire",
                           "password", "pin", "code"]):
        return {
            "action": "mute", "message_type": "scam",
            "reason": "The sender is unfamiliar and the message shows urgency or verification pressure.",
            "confidence": 0.84,
            "evidence": retrieve_evidence(msg, ctx, prefer="mute"),
        }

    # Courier / workshop from unknown but benign -> digest
    return {
        "action": "digest", "message_type": "unknown",
        "reason": "The sender is unfamiliar, but the message does not show urgency, payment pressure, or safety risk.",
        "confidence": 0.80,
        "evidence": retrieve_evidence(msg, ctx, prefer="engage"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def route(msg, ctx):
    ctype = msg.get("conversation_type", "")
    if ctype == "business":
        res = route_business(msg, ctx)
    elif ctype == "group":
        res = route_group(msg, ctx)
    else:
        res = route_personal(msg, ctx)

    # Quiet-hours downgrade: a message that would otherwise interrupt the
    # user right now should wait if it lands inside their configured
    # do-not-disturb window. Safety mutes are left untouched.
    if res.get("action") == "notify":
        user_row = ctx.users.get(msg.get("user_id", ""))
        if is_in_dnd(msg, user_row):
            res = dict(res)
            res["action"] = "digest"
            res["reason"] = res["reason"] + " Held back because it arrived during the user's do-not-disturb hours."
            res["confidence"] = clamp_conf(res.get("confidence", 0.8) - 0.03)
    return res


def main():
    print("Building context from dataset/ ...")
    ctx = build_context()

    messages = load_csv("messages.csv")
    print(f"Routing {len(messages)} messages ...")

    rows = []
    for msg in messages:
        res = route(msg, ctx)
        ev = ";".join(res["evidence"]) if res["evidence"] else "none"
        rows.append({
            "message_id": msg["message_id"],
            "action": res["action"],
            "message_type": res["message_type"],
            "reason": res["reason"],
            "confidence": f"{res['confidence']:.2f}",
            "evidence_message_ids": ev,
        })

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "message_id", "action", "message_type", "reason", "confidence",
            "evidence_message_ids",
        ])
        writer.writeheader()
        writer.writerows(rows)

    # Validation
    assert len(rows) == len(messages), "Row count mismatch!"
    from collections import Counter
    action_counts = Counter(r["action"] for r in rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    print("Action distribution:", dict(action_counts))

    print("\nFirst 12 predictions:")
    for r in rows[:12]:
        print(r["message_id"], r["action"], r["message_type"], r["confidence"], r["evidence_message_ids"])


if __name__ == "__main__":
    main()

