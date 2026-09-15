"""The FAQ database — rebuilt from the real production FAQ table (issue_id,
name, title, answer columns from the "Popular Questions" sheet, 2026-09-08)
rather than the original prototype's condensed paraphrases. `sub_issue` now
holds the real user-facing question text (the sheet's `title` column) since
that's the best keyword/phrasing source there is — actual users' own words.

The sheet's numeric `type`/`feedback_type` columns have no legend we were
given, so `feedback` below is our own read of each answer's actual content
(does it end in "raise a ticket" with no self-serve alternative at all ->
raise_complaint_only; is it a pure informational answer with nothing to
escalate -> feedback_only; anything with a self-serve step AND a "still
stuck? raise a ticket" fallback -> both) — not a direct field mapping.

`audience`: "user" | "listener" | "both"
`landing_category`: which guided-flow list surfaces this FAQ as a card —
    "calls" | "transactions_user" | "earnings" | "payouts" | None (only
    reachable via free-text / agent search, not a guided card)
`refund_driven`: True for the three categories the v1.1 refund-automation
    PRD actually runs against (see app/services/refund_service.py).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Faq:
    id: str
    category: str
    sub_issue: str
    audience: str
    keywords: tuple[str, ...]
    feedback: str
    answer: str
    landing_category: str | None = None
    refund_driven: bool = False


FAQS: list[Faq] = [
    # ------------------------------- Calls (User) ------------------------------- #
    Faq(
        id="charged_incorrectly",
        category="Charged Incorrectly for Call",
        sub_issue="I was charged incorrectly for this call. What should I do?",
        audience="user",
        landing_category="calls",
        keywords=("charged incorrectly", "charged", "deduct", "coins deducted", "wrongly charged", "no call happened", "overcharged", "extra coins", "money cut"),
        feedback="both",
        refund_driven=True,
        answer=(
            "I'm sorry about the coin deduction on that call. Let me check it against our "
            "automated refund rules using your account and this call's details — if coins were "
            "deducted but no call took place, and our checks confirm it, we'll refund your coins."
        ),
    ),
    Faq(
        id="cannot_hear",
        category="Cannot Hear Dostt's Voice",
        sub_issue="I'm unable to hear the listener's voice. What should I do?",
        audience="user",
        landing_category="calls",
        keywords=("cannot hear", "can't hear", "no voice", "no sound", "voice not coming", "audio missing", "silent call", "unable to hear"),
        feedback="both",
        refund_driven=True,
        answer=(
            "Sorry you couldn't hear them clearly. First, a couple of quick checks: make sure "
            "your internet connection is stable, and that your phone's volume is turned up and "
            "not on silent/Do Not Disturb. If it still happens, I'll check your account and this "
            "call against our refund rules for audio issues."
        ),
    ),
    Faq(
        id="not_showing_face",
        category="Dostt Not Showing Face",
        sub_issue="What should I do if a Listener is not showing their face on a video call?",
        audience="user",
        landing_category="calls",
        keywords=("not showing face", "camera off", "video not visible", "cant see", "can't see", "face not visible", "black screen"),
        feedback="both",
        refund_driven=True,
        answer=(
            "If a Listener isn't in the camera frame, their video feed is automatically paused — "
            "this is a safety feature to protect you from suspicious activity, so we're sorry for "
            "the inconvenience it can cause. Let me check this against our refund rules; if it "
            "keeps happening for an extended period, our Trust & Safety team also reviews these "
            "cases within 24-48 hours."
        ),
    ),
    Faq(
        id="preferred_listener",
        category="Favourite Listener Unavailable",
        sub_issue="I'm unable to reach my favorite Listener. Why?",
        audience="user",
        keywords=("favourite listener not available", "preferred listener offline", "cant find my listener", "unable to reach my favorite listener"),
        feedback="feedback_only",
        answer=(
            "Listener availability depends on things like their login time, activity status, and "
            "whether they're already on another call — even if they appear online, they may not "
            "be able to answer right away. We'd recommend waiting a bit and trying again, or "
            "connecting with another available Listener in the meantime."
        ),
    ),
    Faq(
        id="no_listener_online",
        category="No Listener Online",
        sub_issue="Why am I unable to connect with any Listeners?",
        audience="user",
        keywords=("no listener online", "unable to connect with any listeners", "nobody online", "no one available"),
        feedback="feedback_only",
        answer=(
            "Listener availability depends on login time, activity, and demand — even online "
            "Listeners may already be on a call or briefly away. If you can't connect, try "
            "waiting a few minutes and retrying, connect with a different available Listener, and "
            "double-check your own internet connection, since that can also affect call setup."
        ),
    ),
    # --------------------------- Calls / Tech (Listener) --------------------------- #
    Faq(
        id="unable_pick_calls",
        category="Expert Unable to Pick Call",
        sub_issue="Why am I not able to pick up calls?",
        audience="listener",
        landing_category="calls",
        keywords=("cant pick", "can't pick", "unable to pick", "missed the call", "call disconnected before i answered", "not able to pick call"),
        feedback="feedback_only",
        answer=(
            "Calls need to be answered within 7 seconds of ringing, or they're automatically "
            "marked as missed/disconnected. Keep the app active with a stable internet "
            "connection, and make sure notifications and call permissions are enabled, to avoid "
            "missing calls."
        ),
    ),
    Faq(
        id="not_getting_calls",
        category="Not Getting Calls",
        sub_issue="Why am I not getting calls?",
        audience="listener",
        landing_category="calls",
        keywords=("not getting calls", "no calls coming", "no incoming calls", "not receiving calls"),
        feedback="feedback_only",
        answer=(
            "Make sure your Audio and Video toggles are both ON while you're live, and that "
            "notifications are on so you're not missing call alerts. Try to pick up within 7 "
            "seconds of ringing. Peak hours on Dostt are 6 PM to 4 AM — staying active during "
            "that window usually helps a lot."
        ),
    ),
    Faq(
        id="video_calls_not_enabled",
        category="Account - Not Getting Video Calls",
        sub_issue="Why am I not getting any video calls?",
        audience="listener",
        keywords=("not getting video calls", "video not enabled", "why no video calls", "video calls disabled"),
        feedback="feedback_only",
        answer=(
            "All Listeners start with audio calls only — video calls earn more, so that feature "
            "unlocks once you meet certain performance criteria. Our onboarding team reviews "
            "performance periodically and enables video calling for eligible Listeners. Keep "
            "taking calls and improving your performance in the meantime!"
        ),
    ),
    Faq(
        id="tech_audio_video",
        category="Tech - Audio Issue",
        sub_issue="I'm experiencing audio issues during my call. What should I do?",
        audience="both",
        landing_category="calls",
        keywords=("app not working", "audio issue", "mic not working", "no sound", "distorted audio", "one-way audio"),
        feedback="both",
        answer=(
            "Sorry about the audio trouble. Please share a bit more detail — what exactly is "
            "happening (no sound, distorted audio, or one-way audio) — and I'll raise a ticket "
            "with our tech team so they can look into it and help resolve it as quickly as "
            "possible."
        ),
    ),
    Faq(
        id="tech_video_issue",
        category="Tech - Video Issue",
        sub_issue="Why is the video not working during my call?",
        audience="both",
        landing_category="calls",
        keywords=("video issue", "video not working", "blurred video", "laggy video", "camera not working"),
        feedback="both",
        answer=(
            "For the best video experience, make sure your face is clearly visible on camera — "
            "the app automatically turns off video if a face isn't detected, for both users and "
            "Listeners. A weak internet connection can also affect video quality, so try a "
            "well-lit space with a stable connection. If it still seems like a technical issue "
            "(no video, blurred, distorted, or laggy video), I can raise a ticket with the details."
        ),
    ),
    Faq(
        id="calls_disconnecting",
        category="Calls Disconnecting",
        sub_issue="My calls keep disconnecting or I'm not able to connect at all. What should I do?",
        audience="both",
        landing_category="calls",
        keywords=("calls disconnecting", "not able to connect", "call drops", "connection failing", "call keeps cutting"),
        feedback="both",
        answer=(
            "Sorry about the dropped connection. This is usually a network-side issue, so please "
            "check that your internet connection is stable and try switching between Wi-Fi and "
            "mobile data. If it keeps happening across multiple attempts, I can raise a ticket for "
            "our team to check for a server-side sync issue on your account."
        ),
    ),
    Faq(
        id="audio_not_enabled",
        category="Audio Not Enabled",
        sub_issue="I can't get an audio call to start. How do I enable audio?",
        audience="both",
        landing_category="calls",
        keywords=("audio not enabled", "cant enable audio", "no audio option", "enable audio calls"),
        feedback="feedback_only",
        answer=(
            "Make sure to tap the audio option when the call comes in to activate it, and check "
            "that microphone permissions are enabled for Dostt in your device's app settings. That "
            "should let you use the audio feature normally."
        ),
    ),
    Faq(
        id="app_crash_freeze",
        category="Tech - App Related Issue",
        sub_issue="App freezes or closes unexpectedly, how can I fix it?",
        audience="both",
        keywords=("app freezes", "app crashes", "app closes", "app not working", "update the app"),
        feedback="both",
        answer=(
            "First, please make sure you're on the latest version of the app — on Android via "
            "the Play Store, on iOS via the App Store. If it still happens after updating, I can "
            "raise a ticket — it helps to include your phone model, when it happens, and a "
            "screenshot if you have one."
        ),
    ),
    # ------------------------------ Transactions (User) ----------------------------- #
    Faq(
        id="recharge_not_added",
        category="Recharged but Coins Not Added",
        sub_issue="Why are coins not added to my wallet even after recharge?",
        audience="user",
        landing_category="transactions_user",
        keywords=("recharge", "coins not added", "paid but no coins", "payment done no coins", "wallet not updated"),
        feedback="both",
        answer=(
            "Sorry about that — please allow up to 72 hours for the coins to be credited. If "
            "they're still not reflected after that, the amount is automatically refunded to your "
            "original payment method within 4-5 working days. It's also worth refreshing the app "
            "in case the coins already landed but the balance just looks stale. If it's still not "
            "sorted, let me know and I'll raise a ticket."
        ),
    ),
    Faq(
        id="recharge_twice",
        category="Recharged Twice by Mistake",
        sub_issue="I accidentally recharged twice. What should I do?",
        audience="user",
        landing_category="transactions_user",
        keywords=("recharged twice", "double charged", "charged twice", "duplicate recharge", "paid two times"),
        feedback="both",
        answer=(
            "Apologies for the inconvenience — let me check your recent transactions. If there "
            "really was a duplicate charge, I'll raise a ticket with your transaction IDs, date, "
            "and amount so our team can review and process any eligible refund."
        ),
    ),
    Faq(
        id="negative_balance",
        category="Wallet Balance is Negative",
        sub_issue="Why is my account balance negative?",
        audience="both",
        landing_category="transactions_user",
        keywords=("negative balance", "wallet negative", "balance is minus", "coins negative"),
        feedback="raise_complaint_only",
        answer=(
            "We're sorry about the inconvenience of seeing a negative wallet balance. This needs "
            "to be reviewed by our backend team against your recent transactions — I can raise a "
            "ticket now so they can investigate and correct it."
        ),
    ),
    # ------------------------------ Transactions (Listener) -------------------------- #
    Faq(
        id="withdrawal_not_received",
        category="Withdrawal Amount Not Received",
        sub_issue="Why did I not receive my withdrawal amount?",
        audience="listener",
        landing_category="payouts",
        keywords=("withdrawal not received", "payout not received", "money not credited", "withdraw pending", "payout stuck"),
        feedback="both",
        answer=(
            "Withdrawals are usually instant and land within a few minutes, but bank-side delays "
            "can happen — please allow 4-5 working days in that case, since it may already be "
            "released from our side but stuck at the gateway or bank. If a wallet-to-bank "
            "transfer fails outright, the amount returns to your Dostt Wallet within 72 hours so "
            "you can retry the withdrawal. If it's still not resolved after that, I can raise a "
            "ticket with your UPI ID and any screenshots."
        ),
    ),
    Faq(
        id="withdrawal_guidance",
        category="Withdrawal Assistance and Guidance",
        sub_issue="How do I withdraw money from my wallet?",
        audience="listener",
        landing_category="payouts",
        keywords=("how to withdraw", "withdrawal guidance", "how do i withdraw", "payout process", "add upi"),
        feedback="both",
        answer=(
            "To withdraw, make sure: your wallet balance is at least ₹50, you've added and "
            "selected your UPI ID and KYC details under Withdrawal, and your name matches your "
            "UPI details exactly. Once that's all set, you'll be able to place a withdrawal "
            "request. If you're still stuck, let me know and I'll raise a ticket with the details."
        ),
    ),
    Faq(
        id="tds_help",
        category="TDS Deduction Help",
        sub_issue="What is TDS and how much is deducted for me?",
        audience="listener",
        landing_category="payouts",
        keywords=("tds", "tax deducted", "why tds", "kyc tax"),
        feedback="feedback_only",
        answer=(
            "TDS (Tax Deducted at Source) is a portion of your earnings automatically deducted as "
            "tax before payout, based on your lifetime earnings and your KYC status. If you're "
            "KYC verified, a much lower TDS rate applies (as low as 1%); if not, a higher rate "
            "applies. Completing KYC is the best way to reduce this going forward."
        ),
    ),
    Faq(
        id="earnings_info",
        category="Earnings",
        sub_issue="What is Tiers and how do I increase it, and how do earnings work?",
        audience="listener",
        landing_category="earnings",
        keywords=("how do i earn", "earnings info", "how much do i earn", "earning rate", "check my earnings", "tiers"),
        feedback="feedback_only",
        answer=(
            "You earn from both calls and gifts sent during calls, with your rate set by your "
            "Tier — Tiers range from Basic to Diamond, starting at ₹0.9/min for audio and ₹5/min "
            "for video, and a higher tier can pay up to 2X. Based on your daily performance you "
            "get promoted; staying active, taking more calls, and keeping performance consistent "
            "is what boosts both your tier and your visibility."
        ),
    ),
    Faq(
        id="earnings_mismatch",
        category="Earning Not Matching With Call Duration",
        sub_issue="Why is my earning less than the call duration?",
        audience="listener",
        landing_category="earnings",
        keywords=("earnings dont match", "earning mismatch", "wrong earning", "earning less than expected"),
        feedback="both",
        answer=(
            "Your earning is based on the actual (payable) call duration, which can sometimes "
            "differ from what's shown on the app screen. Common reasons for a lower payout: your "
            "face wasn't visible during part of the call, you were inactive/unresponsive for part "
            "of it, or the customer raised a concern and received a refund for that portion. Let "
            "me check your recent call if you'd like."
        ),
    ),
    Faq(
        id="call_earnings_not_credited",
        category="Call Completed Money Not Added",
        sub_issue="My call ended but the earnings weren't added to my balance. What should I do?",
        audience="listener",
        landing_category="earnings",
        keywords=("call completed money not added", "earnings not added", "call ended no money", "session earnings missing"),
        feedback="both",
        answer=(
            "Sorry about the delay — call earnings can occasionally take a little while to reflect "
            "due to a backend sync. Please give it some time and check again; if it's still "
            "missing, let me know the approximate call time and I'll raise a ticket with that "
            "booking so our team can audit and credit it manually."
        ),
    ),
    Faq(
        id="gift_earnings",
        category="Gift",
        sub_issue="Do gifts sent by users during a call count towards my earnings?",
        audience="listener",
        landing_category="earnings",
        keywords=("gifts earnings", "gift money", "do gifts count", "gift during call"),
        feedback="feedback_only",
        answer=(
            "Yes — gifts sent by users during a call are added to your earnings from that call. "
            "The more engaging the session, the more likely you are to receive them, so it's worth "
            "keeping the conversation warm and active!"
        ),
    ),
    Faq(
        id="change_upi",
        category="Change UPI Details",
        sub_issue="How do I add/change my UPI ID?",
        audience="listener",
        keywords=("change upi", "update upi", "wrong upi", "add upi id"),
        feedback="feedback_only",
        answer=(
            "You can add up to 3 UPI IDs under Wallet/Withdrawal → Add UPI ID — just make sure "
            "the name matches your KYC PAN details exactly. If you've already added 3, you'll "
            "need to wait 24 hours before adding another (and note there's a limit of 5 new UPI "
            "IDs per year)."
        ),
    ),
    Faq(
        id="change_profile_pic",
        category="Change Profile Picture",
        sub_issue="Can I use my own photo as my profile picture?",
        audience="both",
        keywords=("change profile pic", "change profile picture", "own photo profile", "upload photo"),
        feedback="feedback_only",
        answer=(
            "We currently use avatars for profile review, and for privacy and safety reasons we "
            "aren't able to allow personal photos as profile pictures. Thanks for understanding — "
            "it helps us keep the platform safe and respectful for everyone."
        ),
    ),
    Faq(
        id="recharge_offers_info",
        category="Recharge Offers Info",
        sub_issue="Are there any offers when I recharge?",
        audience="user",
        keywords=("recharge offers", "high price", "any discounts", "coin offers"),
        feedback="feedback_only",
        answer=(
            "Recharge offers are available in the Wallet section of the app — we'd recommend "
            "checking there regularly, since new offers and promotions are rolled out and shown "
            "there as soon as they're live."
        ),
    ),
    Faq(
        id="abroad_customer_inr_payment",
        category="Abroad Customer Payment in INR",
        sub_issue="I'm outside India — how can I pay?",
        audience="user",
        keywords=("pay from abroad", "international payment", "outside india recharge", "foreign card"),
        feedback="feedback_only",
        answer=(
            "You can complete your payment using a Visa credit or debit card. Depending on your "
            "card issuer or bank, foreign transaction charges may apply, so it's worth checking "
            "with your bank about any additional fees before you proceed."
        ),
    ),
    # --------------------------------- KYC (Listener) -------------------------------- #
    Faq(
        id="kyc_how_to",
        category="KYC - How to Complete",
        sub_issue="How do I complete my KYC?",
        audience="listener",
        keywords=("complete kyc", "how do i kyc", "kyc verification steps", "verify pan"),
        feedback="feedback_only",
        answer=(
            "To complete KYC you'll need a valid PAN and UPI ID, with your gender matching your "
            "PAN, a PAN that hasn't been used on Dostt before, and a bank account holder name "
            "matching your PAN. Go to Profile → Earnings → Verify, enter your PAN and UPI ID, and "
            "confirm — verification usually takes under 30 seconds."
        ),
    ),
    Faq(
        id="kyc_mandatory",
        category="KYC - Is It Mandatory",
        sub_issue="What is KYC and is this mandatory?",
        audience="listener",
        keywords=("what is kyc", "is kyc mandatory", "kyc required"),
        feedback="feedback_only",
        answer=(
            "KYC (Know Your Customer) verifies your identity so your account stays secure and "
            "payouts comply with regulations. It's mandatory once your earnings are high enough — "
            "accounts without KYC can face restrictions, including a higher TDS rate."
        ),
    ),
    Faq(
        id="kyc_reverify",
        category="KYC - Why Redo It",
        sub_issue="I've already completed PAN/KYC verification. Why do I need to verify again?",
        audience="listener",
        keywords=("kyc again", "verify again", "redo kyc", "already completed kyc"),
        feedback="feedback_only",
        answer=(
            "If you're being asked to re-verify even after completing KYC before, it's usually "
            "because we've periodically tightened our verification criteria for security. Please "
            "go ahead and re-verify with the correct details."
        ),
    ),
    Faq(
        id="kyc_limit_exceeded",
        category="KYC Limit Exceeded",
        sub_issue="Getting error as 'your KYC limit is exceeded', what to do?",
        audience="listener",
        keywords=("kyc limit exceeded", "kyc attempts", "kyc error"),
        feedback="raise_complaint_only",
        answer=(
            "We allow up to 20 KYC attempts — this error means several submissions had incorrect "
            "info. Double-check that your PAN is linked to your Aadhaar, your PAN gender matches "
            "your Dostt profile, and your bank account holder name exactly matches your PAN. I "
            "can raise a ticket with the correct details for our team to complete it for you."
        ),
    ),
    Faq(
        id="gender_mismatch",
        category="Gender Mismatch (KYC)",
        sub_issue="Getting error as PAN GENDER NOT MATCHING, what to do?",
        audience="listener",
        keywords=("gender not matching", "pan gender mismatch", "gender mismatch error"),
        feedback="raise_complaint_only",
        answer=(
            "This happens when the gender you selected differs from your PAN. Ideally use your "
            "own PAN; if you don't have one, you can use an immediate family member's PAN with "
            "proof of relationship (e.g. a ration card or matching Aadhaar details). I can raise a "
            "ticket with these documents for our team to verify."
        ),
    ),
    Faq(
        id="kyc_pan_delink",
        category="KYC - PAN Linked to Another User",
        sub_issue="My PAN is showing as linked to another user. How do I resolve this?",
        audience="listener",
        keywords=("pan linked", "pan already used", "pan delink", "kyc pan issue"),
        feedback="raise_complaint_only",
        answer=(
            "This means the same PAN was already used for KYC on another Dostt account — each "
            "PAN can only be linked to one account. First double-check you entered it correctly; "
            "if it's genuinely yours, I can raise a ticket with your PAN and supporting documents "
            "for our Trust & Support team to review."
        ),
    ),
    Faq(
        id="pan_delink_transfer",
        category="PAN Delink and Link to Other Account",
        sub_issue="How can I remove my PAN from my old account and link it to a new account?",
        audience="listener",
        keywords=("move pan", "transfer pan", "link pan new account", "pan to new account"),
        feedback="raise_complaint_only",
        answer=(
            "I can raise this for you — please share your old and new phone numbers, old and new "
            "user IDs, and your PAN number. Our team will review and complete the transfer, which "
            "can take up to 72 hours to reflect."
        ),
    ),
    # ------------------------------------ Account ------------------------------------ #
    Faq(
        id="change_language",
        category="Change Language",
        sub_issue="How do I change my language?",
        audience="both",
        keywords=("change language", "app language", "switch language"),
        feedback="feedback_only",
        answer="You can change your app language from Profile → Language — just pick your preferred language from the list and confirm.",
    ),
    Faq(
        id="multiple_languages_request",
        category="Add One More Language",
        sub_issue="How do I select multiple languages to get calls from all languages?",
        audience="listener",
        keywords=("multiple languages", "more than one language", "add another language"),
        feedback="raise_complaint_only",
        answer=(
            "Currently you can only select one language on the platform. I can raise a request to "
            "change it if you'd like, though note this may lead to your account being "
            "re-verified — our team is continuously looking at expanding this in the future."
        ),
    ),
    Faq(
        id="gender_change",
        category="Gender Change",
        sub_issue="How to change my gender?",
        audience="both",
        keywords=("change gender", "gender change", "wrong gender"),
        feedback="raise_complaint_only",
        answer=(
            "Gender is set when your account is created and isn't normally meant to change. If "
            "there's an urgent need, I can raise a request — our team may call you for "
            "verification, though approval isn't guaranteed."
        ),
    ),
    Faq(
        id="change_username",
        category="Change Username",
        sub_issue="How can I change my username?",
        audience="listener",
        keywords=("change username", "change user name", "wrong username"),
        feedback="raise_complaint_only",
        answer=(
            "Your username is set at signup and isn't normally meant to change. If there's an "
            "urgent need, I can raise a request for our team to review — though we can't "
            "guarantee it'll be approved."
        ),
    ),
    Faq(
        id="account_suspended",
        category="Account Suspended",
        sub_issue="When will my suspension be revoked?",
        audience="both",
        keywords=("account suspended", "suspension", "when will suspension end"),
        feedback="both",
        answer=(
            "If you see a countdown timer on your screen, your account reactivates automatically "
            "once it finishes. If there's no timer, let me know and I'll raise a ticket. Also, "
            "please review our platform guidelines to help avoid this happening again."
        ),
    ),
    Faq(
        id="access_request",
        category="SDT Access Request",
        sub_issue="Wants to become a Listener / Super Dostt",
        audience="user",
        keywords=("become a listener", "become super dostt", "access request", "switch to listener", "how to become sdt"),
        feedback="feedback_only",
        answer=(
            "You can apply to become a Super Dostt (Listener) directly from your account by "
            "selecting 'Switch to Listener'. Once submitted, our onboarding team reviews your "
            "profile and calls you to complete verification."
        ),
    ),
    Faq(
        id="account_blocked",
        category="Account is Permanently Blocked",
        sub_issue="Why is my account blocked?",
        audience="both",
        keywords=("account blocked", "banned", "account suspended permanently", "why is my account blocked"),
        feedback="raise_complaint_only",
        answer=(
            "Your account was blocked due to a violation of our platform guidelines, confirmed "
            "after review. This action is permanent and generally cannot be reinstated. If you "
            "believe this was in error, I can raise a ticket for our team to take another look."
        ),
    ),
    Faq(
        id="delete_account",
        category="Account Deletion Request",
        sub_issue="How do I delete my account?",
        audience="both",
        keywords=("delete my account", "delete account", "close my account", "remove my account"),
        feedback="feedback_only",
        answer=(
            "Go to Profile → Switch to Dostt → Account Settings → Delete Account, and follow the "
            "on-screen steps. This deletes your account as both a user and a listener — after "
            "deleting, please don't log back in for 30 days, as that can interfere with the "
            "deletion process."
        ),
    ),
    Faq(
        id="delete_call_history",
        category="Delete Call History",
        sub_issue="How do I delete the call history?",
        audience="both",
        keywords=("delete call history", "clear call log", "remove call history"),
        feedback="feedback_only",
        answer=(
            "There isn't currently an option to delete call history/logs within the app, but your "
            "information is kept secure and private. We'll keep this feedback in mind for future "
            "updates."
        ),
    ),
    Faq(
        id="duplicate",
        category="Duplicate",
        sub_issue="Same concern raised again",
        audience="both",
        keywords=("already raised", "raised this before", "duplicate ticket", "same issue again"),
        feedback="feedback_only",
        answer=(
            "It looks like you may have raised this already recently — we're tracking it under "
            "your existing ticket, so there's no need to raise a new one."
        ),
    ),
    # --------------------------------- Trust & Safety --------------------------------- #
    Faq(
        id="report_user",
        category="Inappropriate Behaviour",
        sub_issue="A user/listener is behaving inappropriately, what should I do?",
        audience="both",
        keywords=("report user", "inappropriate behaviour", "rude", "misbehaved", "behaving inappropriately"),
        feedback="raise_complaint_only",
        answer=(
            "I'm sorry this happened — that's against our community guidelines and taken very "
            "seriously. Please report it: go to Past Sessions, tap the three-dot icon on that "
            "session, select Report, choose the reason, and submit. Our Trust & Safety team "
            "reviews and takes action within 24-48 hours."
        ),
    ),
    Faq(
        id="personal_info_request",
        category="Asking for Personal Info",
        sub_issue="What should I do if someone is asking for my personal information?",
        audience="both",
        keywords=("asked for my number", "asked for otp", "asked for password", "asked for instagram", "sharing personal info", "asking for personal information"),
        feedback="raise_complaint_only",
        answer=(
            "Our platform never asks you to share phone numbers, social handles, passwords, "
            "OTPs, or payment details over calls or chat. Please don't share this with anyone — "
            "report it immediately from that session's three-dot menu → Report User, so our team "
            "can investigate."
        ),
    ),
    Faq(
        id="otp_sharing_warning",
        category="OTP Shared With Someone",
        sub_issue="I shared my OTP with someone and money was withdrawn. What should I do?",
        audience="both",
        keywords=("shared my otp", "otp withdrawn money", "otp fraud"),
        feedback="feedback_only",
        answer=(
            "OTPs are strictly personal and should never be shared with anyone, including friends "
            "or family — they verify your identity for transactions. If an OTP was shared and a "
            "transaction happened as a result, we're not able to reverse it, since it's considered "
            "authorised by the account holder. Please never share your OTP with anyone going "
            "forward."
        ),
    ),
    Faq(
        id="app_usage",
        category="App Usage Guidance",
        sub_issue="General how-to-use-the-app questions",
        audience="both",
        keywords=("how does dostt work", "how to use app", "how to make a call", "how to recharge", "app guidance"),
        feedback="feedback_only",
        answer=(
            "Quick overview: log in with mobile + OTP, recharge to buy coins from Account, then "
            "use coins for audio/video calls with available Listeners. You can update your "
            "profile/language in Settings, and reach Help & Support anytime from the app."
        ),
    ),
    Faq(
        id="competition_info",
        category="App Usage Guide - Competitions",
        sub_issue="What are competitions and where can I get more information?",
        audience="listener",
        keywords=("competitions", "contest", "competition info"),
        feedback="feedback_only",
        answer=(
            "You can find details on active competitions under Profile → Competitions in the app, "
            "and we also share updates, rules, and winner announcements in our official WhatsApp "
            "group — just ask if you'd like the link!"
        ),
    ),
    Faq(
        id="certification_info",
        category="Listener Certification",
        sub_issue="What is certification and how do I get certified?",
        audience="listener",
        keywords=("certification", "certified", "nsdc", "mental wellbeing certificate"),
        feedback="feedback_only",
        answer=(
            "The Mental Wellbeing Certification is an NSDC-aligned Skill India program to build "
            "your communication and listening skills. You can enroll via the NSDC Certification "
            "banner on the Dostt home page, complete Aadhaar verification and the training "
            "modules, then pass the final assessment to get your official certificate."
        ),
    ),
    # -------------------------------- AI Dostt (Dia) --------------------------------- #
    Faq(
        id="ai_dostt_offensive",
        category="AI Dostt Said Something Wrong",
        sub_issue="AI Dostt (Dia) said something wrong or offensive",
        audience="both",
        keywords=("dia said something wrong", "ai dostt offensive", "dia rude", "ai companion inappropriate"),
        feedback="feedback_only",
        answer=(
            "Dia is an AI and can sometimes respond in unexpected ways. Please tap \"Report this "
            "chat\" so our team can review the conversation and improve her responses — for "
            "anything that felt genuinely harmful, please also use Safety & Abuse."
        ),
    ),
    Faq(
        id="ai_dostt_not_responding",
        category="AI Dostt Not Responding",
        sub_issue="AI Dostt (Dia) is not responding / chat not loading",
        audience="both",
        keywords=("dia not responding", "ai dostt chat not loading", "dia stuck"),
        feedback="feedback_only",
        answer=(
            "Try closing and reopening the chat, and check your internet connection. If Dia "
            "still doesn't respond after 30 seconds, exit and re-enter the chat. If it keeps "
            "happening, please report it so our team can investigate."
        ),
    ),
    Faq(
        id="ai_dostt_real_person",
        category="Is AI Dostt a Real Person",
        sub_issue="Is AI Dostt (Dia) a real person?",
        audience="both",
        keywords=("is dia real", "ai dostt real person", "is ai dostt human"),
        feedback="feedback_only",
        answer=(
            "No — Dia is an AI companion, not a real person. She's designed to feel warm and "
            "natural, but she's fully AI-powered. If you're looking to connect with a real human, "
            "try our Listeners feature."
        ),
    ),
    Faq(
        id="ai_dostt_memory",
        category="Does AI Dostt Remember Conversations",
        sub_issue="Will AI Dostt (Dia) remember our previous conversations?",
        audience="both",
        keywords=("dia remember", "ai dostt memory", "does dia remember me"),
        feedback="feedback_only",
        answer=(
            "Dia remembers everything within a session, and across sessions she holds on to "
            "important things you've shared — like your name and what matters to you — so she "
            "doesn't feel like a stranger each time. She won't recall every message, but gets more "
            "personalised the more you chat."
        ),
    ),
]

FAQS_BY_ID: dict[str, Faq] = {f.id: f for f in FAQS}

CALLS_FAQ_IDS = {
    "user": ("charged_incorrectly", "cannot_hear", "not_showing_face"),
    "listener": ("unable_pick_calls", "not_getting_calls", "tech_audio_video", "tech_video_issue"),
}
TX_FAQ_IDS_USER = ("recharge_not_added", "recharge_twice", "negative_balance")
TX_FAQ_IDS_EARNINGS = ("earnings_info", "earnings_mismatch")
TX_FAQ_IDS_PAYOUTS = ("withdrawal_not_received", "withdrawal_guidance", "tds_help", "kyc_pan_delink")
