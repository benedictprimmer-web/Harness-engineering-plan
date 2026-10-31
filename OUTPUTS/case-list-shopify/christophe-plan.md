# The Case List: plan to address Christophe's points

Source: Christophe's emails of 30 Oct (14:58) and 31 Oct (16:01), thread "Referral feature & tomorrow's email". Deadline: his Monday 2 Nov morning send.

## Where we are

From your own replies (I can't see the store directly, no Shopify connector in this session):

- Club Perks page live, word for word, linked in the footer (thecaselist.com/pages/club-perks).
- Referrals running through Smile (free plan): £10 off a friend's first order, £10 off the member's next order once the friend's order is paid. Flat £10 each, not per case.
- Tested end to end on 30 Oct; PDF sent to Christophe.
- Open from you: Smile premium is £15/month, you suggested staying on free.
- Christophe owns the T&Cs update.

## His points and what to do

| # | Point | Action | Effort | Needs Christophe? |
|---|-------|--------|--------|-------------------|
| 1 | Log Out missing from My Account | Restore the link (customer account menu / theme). Likely broke when the Refer a Friend and Track my Order items went in. | Small | No |
| 2 | Instagram icon | Add https://www.instagram.com/the_caselist/ to the icon | Small | No |
| 3 | Reorder account menu: Profile, Orders, Track your Order, Refer a Friend, Log Out | Reorder in the same pass as #1 | Small | No |
| 4 | Can Smile do the referral link and the email push together? | Check Smile settings: referral link sharing and the "email a friend" invite are normally both on the same widget. Confirm both are enabled, then test. | Small | No |
| 5 | WhatsApp button on desktop | Show the existing mobile button on desktop (theme setting or app display rule) | Small | No |
| 6 | Change the £50 minimum for the £10 off | Smile reward setting: lower or remove the minimum. Needs a number from him. | Small | Yes: new threshold |
| 7 | Friend's code reusable by many first-timers? Lock to the friend's account? | Answer: yes, as set up, anyone holding the code can use it once as a new customer. Locking it to the friend means sign-in at checkout. He leans towards locking. Recommend locking, since it stops code sharing. | Small | Yes: confirm |
| 8 | Replace Smile's standard invite email with his copy, with referrer name and referee first name | Paste his text into the Smile email template. Map variables to Smile's own tags (referrer and friend names, referral link). Subject: "{{referrer name}} thinks you might like The Case List". Send a test to yourself. Custom email editing may be a premium-only feature on Smile, so check this first. | Medium | No, copy received |
| 9 | Monday email should link to the Refer a Friend page in My Account, not Club Perks | Get the exact My Account referral URL. Logged-out visitors hit the login page, so check they land on the referral page after signing in. Club Perks stays in the footer. | Small | No |

## Order of work

1. **Today, 30 minutes:** #1, #2, #3, #5 (all theme/menu changes). Check on phone and laptop.
2. **Then Smile:** #4, #6, #7, #8. Do #8 first, because it decides whether the premium plan question comes back.
3. **Before Monday:** #9. Send Christophe the final URL and a test invite email, with a screenshot of the new menu.
4. **Reply to Christophe** with answers to #4 and #7, a question on #6, and a decision on the £15 plan if #8 needs it.

## Risks

- #8 may force the £15/month plan. If so, fall back to Smile's standard email with only a light edit, and tell Christophe why.
- #9 depends on the login redirect working. If it doesn't, link to the Refer a Friend page with a "log in to refer" note.
- Anything marked done above is from your emails. Check the store before telling him it's live.

## Questions for you

1. What new minimum order value should apply to the £10 off (or none)?
2. Lock the friend's code to their account, yes or no?
3. Stay on Smile free if the custom email isn't available?
