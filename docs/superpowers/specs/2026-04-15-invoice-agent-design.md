# InvoiceAgent — Product Design Spec

> Date: 2026-04-15
> Status: Approved
> Author: Claude + User

---

## 1. Product Vision

### One-liner

AI-powered freelance billing agent — from invoice to payment, autopilot.

### What it is

An AI Agent that helps freelancers and small service businesses go from "I finished the work" to "money in my account" with minimal effort. The free tier is an AI invoice generator (SEO entry point). The paid tier is an autonomous collection agent that tracks, reminds, and collects on your behalf.

### What it is NOT

- Not an accounting software (no ledger, no bookkeeping)
- Not a project management tool (no tasks, no timelines)
- Not a full-suite business platform (no proposals, no scheduling)
- Focused solely on: **generate → send → track → collect → report**

---

## 2. Target Users

| Segment | Examples | Core Pain | Willingness to Pay |
|---------|---------|-----------|-------------------|
| Freelancers | designers, developers, writers, translators | "I hate chasing payments" | Medium ($10-20/mo) |
| Small service businesses | plumbers, cleaners, photographers, tutors | "I need a professional invoice fast" | Medium-High ($15-30/mo) |
| EU solo entrepreneurs | any self-employed in EU | "I must invoice every transaction by law" | Medium |
| Wave/Fiverr refugees | users migrating from shut-down or newly-paid tools | "I need a free replacement now" | Low initially, converts later |

---

## 3. Free vs Paid Boundary

### Free Tier (SEO acquisition engine, no signup required)

Core principle: **anyone can generate a professional invoice in 30 seconds without registering.**

| Feature | Details |
|---------|---------|
| AI Invoice Generation | Natural language → structured invoice → PDF download |
| Document Matrix | Invoice + Receipt + Quote + Estimate generators |
| 200+ Industry Template Pages | pSEO landing pages per industry |
| Multi-currency & Multi-tax | USD/EUR/GBP/AUD + Sales Tax/VAT/GST/HST |
| 3-5 Professional Templates | Clean, modern designs, no watermark |
| PDF Export | @react-pdf/renderer, free, unlimited |

Limits: no history saved, no client management, one invoice at a time.

### Free Registered Tier (converts visitors to users)

| Feature | Details |
|---------|---------|
| Client List | Save client info, auto-fill on repeat invoices |
| Invoice History | Up to 10 invoices saved |
| Invoice Online Link | Shareable link for clients to view/download |
| View Notifications | Get notified when client opens invoice (limit 3/mo) |
| Company Branding | Upload logo, set default company info |

### Paid Tier — $17/month "Pro" (the Collection Agent)

| Feature | Details |
|---------|---------|
| Unlimited invoices & clients | No caps |
| Invoice Status Tracking | Draft → Sent → Viewed → Paid → Overdue |
| AI Auto-Collection | Smart reminders with AI-generated personalized copy |
| Collection Timing | AI picks optimal day/time based on industry data |
| Escalation Strategy | Gentle → Formal → Firm, automatic progression |
| Online Payments | Stripe/PayPal link embedded in invoice |
| Recurring Invoices | Monthly auto-generate and send |
| Contract Templates | Per-industry, AI-generated |
| E-Signatures | Client signs online |
| Deposit Terms | Require upfront payment via contract |
| Financial Dashboard | Monthly income, outstanding, overdue |
| Annual Tax Export | CSV by client/month/category |
| Revenue Trend Charts | MoM / YoY visualization |
| Multi-language Invoices | Spanish, French, German, Portuguese |

---

## 4. Aha Moments Design

Each Aha Moment is a specific emotional shift that moves the user down the funnel.

### Aha 1 — "It understood me" (Free, instant)

- **Trigger:** User types natural language, AI generates complete invoice
- **Feeling:** "I said one sentence and got a full invoice — this is different"
- **Metric:** Generation completion rate > 80%
- **Design:** Input is a single text area with placeholder examples, not a form. The form appears AFTER AI fills it, for editing.

### Aha 2 — "This looks professional" (Free, 30 seconds)

- **Trigger:** User sees the rendered PDF preview
- **Feeling:** "This looks better than what I was making in Word"
- **Metric:** PDF download rate > 60%
- **Design:** Live preview next to the editor. PDF uses clean typography, proper alignment, subtle color accents.

### Aha 3 — "It remembers me" (Registered, second visit)

- **Trigger:** User returns, agent auto-fills their company info and suggests recent clients
- **Feeling:** "I don't have to re-enter everything — this is MY tool now"
- **Metric:** Registration rate > 15% of repeat visitors
- **Design:** Soft prompt on second visit: "Save your info so you never type it again — free account"

### Aha 4 — "My invoice is alive" (Registered, passive)

- **Trigger:** Email notification: "Acme Corp viewed your invoice #007"
- **Feeling:** "I can see they got it — I'm not sending into a void"
- **Metric:** Invoice link send rate > 30%
- **Design:** After PDF download, suggest: "Or send an online link — you'll know when they open it"

### Aha 5 — "It offered to do the awkward part" (Paywall trigger)

- **Trigger:** Invoice overdue 7 days → Agent message: "Invoice #007 is 7 days overdue. Want me to send a friendly reminder?"
- **Feeling:** "I was dreading sending that email — yes, please do it for me"
- **Metric:** Paywall conversion > 5%
- **Design:** In-app notification + email. Show a preview of the AI-drafted reminder. Upgrade button right there.

### Aha 6 — "It actually worked" (Paid, first collection)

- **Trigger:** Client pays after AI-sent reminder
- **Feeling:** "$17/month just got me paid $3,000 — this pays for itself 176x over"
- **Metric:** Payment within 7 days of auto-reminder > 40%
- **Design:** Celebration moment: "Payment received! Invoice #007 marked as paid." + running total of money collected via Agent.

### Aha 7 — "It's my financial partner" (Paid, monthly)

- **Trigger:** Monthly report email: "April: $8,400 collected, $2,100 pending, $600 overdue (being followed up)"
- **Feeling:** "I know exactly where I stand financially without opening a spreadsheet"
- **Metric:** Monthly report open rate > 60%
- **Design:** Clean email with 3 numbers + trend arrow. Link to full dashboard.

---

## 5. Feature Modules

### Module 1: AI Invoice Engine (Free Core)

The entry point. A conversational interface, not a form.

**Input flow:**
```
User types: "I did 3 hours of consulting for Acme Corp at $150/hr, net 30"

AI extracts:
{
  client: { name: "Acme Corp" },
  items: [{ description: "Consulting services", quantity: 3, rate: 150 }],
  terms: "Net 30",
  due_date: "2026-05-15",
  currency: "USD"
}

→ Renders editable form (pre-filled)
→ User adjusts if needed
→ Live PDF preview updates
→ Download or Send
```

**AI capabilities:**
- Natural language → structured invoice data
- Paste email/contract text → extract billing details
- Suggest tax rates based on location
- Auto-detect currency from context

**Tech:** Claude Haiku via Edge Function. Cost < $0.002/generation.

### Module 2: Document Matrix (Free, pSEO)

Each document type is a separate tool page, sharing the same AI engine but with different templates and fields.

| Document | URL | Target Keyword | Volume |
|----------|-----|---------------|--------|
| Invoice | / | ai invoice generator | 4K |
| Receipt | /receipt-generator | receipt generator | 15K |
| Quote | /quote-generator | quote generator | 12K |
| Estimate | /estimate-generator | estimate generator | 8K |
| Credit Note | /credit-note-generator | credit note template | 3K |

### Module 3: Industry pSEO Pages

200+ pages, one per industry. URL: `/invoice-template/{industry}`

Each page contains:
1. Industry-specific invoice template preview (pre-filled with realistic sample data)
2. AI generator embedded (pre-configured for that industry's typical fields)
3. SEO content: "What to include in a {industry} invoice" (~800 words)
4. FAQ schema markup
5. Related industry links (internal linking)
6. Download options: PDF / Google Sheets / Excel

**Priority industries (highest search volume):**
consulting, photography, tutoring, lawyer, caregiver, plumber, electrician, graphic-designer, web-developer, cleaning-services, landscaping, personal-trainer, contractor, freelance-writer, videographer, bookkeeper, real-estate-agent, dog-walker, yoga-instructor, massage-therapist

### Module 4: Client CRM

| Feature | Free | Pro |
|---------|------|-----|
| Add clients | 5 max | Unlimited |
| Client contact info | Yes | Yes |
| Auto-fill on new invoice | Yes | Yes |
| Client invoice history | Last 3 | Full |
| Client payment history | No | Yes |
| Client tags/groups | No | Yes |
| Client notes | No | Yes |

### Module 5: Invoice Lifecycle Tracking

Status flow:
```
Draft → Sent → Viewed → Paid
                  ↓
              Overdue → Reminder Sent → Paid / Escalated
```

| Feature | Free | Pro |
|---------|------|-----|
| Draft/download invoices | Unlimited | Unlimited |
| Send invoice link | 3/month | Unlimited |
| View notifications | 3/month | Unlimited |
| Status tracking | No | Full lifecycle |
| Payment confirmation | No | Auto-detect via Stripe webhook |

### Module 6: AI Collection Agent (Pro Only)

The core differentiator. Not template emails — AI-written, personalized, context-aware.

**How it works:**
1. Invoice becomes overdue (past due date)
2. Agent evaluates: client history, overdue duration, relationship length, industry norms
3. Agent drafts a reminder email (user can preview/edit or auto-send)
4. Escalation timeline:
   - Day 3: Gentle nudge ("Just a friendly reminder...")
   - Day 7: Professional follow-up ("Following up on invoice #007...")
   - Day 14: Firm reminder ("This invoice is now 14 days overdue...")
   - Day 30: Final notice ("Please arrange payment within 7 days...")
5. User can customize escalation rules or let Agent decide

**AI inputs for tone/timing:**
- Client's past payment behavior (always late? always on time?)
- Industry norms (construction = net 60 is normal, consulting = net 30)
- Day of week (Tuesday 10am > Friday 5pm)
- Amount (larger invoices get more formal tone)

**Email sending:** via Resend API, from user's own domain or Agent-provided address.

### Module 7: Contracts & E-Signatures (Pro Only)

| Feature | Details |
|---------|---------|
| Template Library | 10+ industry-specific contract templates |
| AI Contract Generation | Describe the project → full contract with scope, timeline, payment terms |
| Online Signing | Client receives link → signs in browser → PDF with signature stored |
| Deposit Enforcement | Contract can require X% upfront before work begins |
| Contract → Invoice Link | When contract is signed, auto-generate first invoice |

### Module 8: Financial Dashboard (Pro Only)

| Feature | Details |
|---------|---------|
| Overview Cards | Total earned (this month), Outstanding, Overdue, Collected via Agent |
| Revenue Chart | Monthly revenue bar chart, 12-month view |
| Client Leaderboard | Top clients by revenue |
| Aging Report | Invoices by days overdue (0-30, 30-60, 60-90, 90+) |
| Tax Export | CSV download: all invoices for tax year, by client/month |
| Monthly Email Report | Auto-send on 1st of each month |

---

## 6. Technical Architecture

### Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | Next.js 15 (App Router) | SSR/SSG for SEO, React Server Components |
| Styling | Tailwind CSS + shadcn/ui | Fast development, clean design |
| Database | Supabase (PostgreSQL) | Auth + DB + Storage + Edge Functions, free tier generous |
| AI | Claude Haiku via Supabase Edge Functions | Low cost (<$0.002/call), structured output |
| PDF | @react-pdf/renderer | React-native PDF, no watermark, full control |
| Payments | Stripe (Subscriptions + Connect) | Subscriptions for Pro, Connect for user's client payments |
| Email | Resend | Developer-friendly, good deliverability, $0 for 3K/mo |
| Hosting | Vercel | Free tier, edge functions, cron jobs |
| Analytics | Plausible or PostHog | Privacy-friendly, funnel tracking |

### Database Schema (Supabase PostgreSQL)

```sql
-- Users
users (id, email, name, company_name, company_address, logo_url, 
       default_currency, default_tax_rate, stripe_customer_id, 
       plan, created_at)

-- Clients
clients (id, user_id, name, email, company, address, 
         payment_terms_days, notes, tags[], created_at)

-- Invoices
invoices (id, user_id, client_id, invoice_number, status,
          items jsonb, subtotal, tax_rate, tax_amount, total,
          currency, due_date, sent_at, viewed_at, paid_at,
          payment_method, online_link_id, recurring_config jsonb,
          created_at)

-- Invoice Items (denormalized in jsonb but also queryable)
-- [{description, quantity, rate, amount}]

-- Documents (receipts, quotes, estimates, credit notes)
documents (id, user_id, client_id, type, data jsonb, 
           created_at)

-- Contracts
contracts (id, user_id, client_id, title, content_html, 
           status, signed_at, signature_url, deposit_required,
           deposit_amount, linked_invoice_id, created_at)

-- Collection Actions (AI reminder log)
collection_actions (id, invoice_id, action_type, 
                    email_subject, email_body, sent_at, 
                    escalation_level, opened_at, result)

-- Invoice Views (tracking)
invoice_views (id, invoice_id, viewer_ip_hash, 
               user_agent, viewed_at)
```

### Key Technical Decisions

**1. AI Generation Architecture**
```
User Input (text) 
  → Supabase Edge Function 
  → Claude Haiku (system prompt with JSON schema) 
  → Structured invoice data (JSON)
  → Return to client
  → Client renders form + PDF preview
```

System prompt enforces output schema. No hallucination risk — it's extraction, not generation.

**2. Invoice Online Links**
- Each invoice gets a unique public URL: `/i/{short_id}`
- No auth required to view (client doesn't need an account)
- View event tracked → triggers notification to user
- Stripe/PayPal payment button embedded if Pro user

**3. Auto-Collection Cron**
- Vercel Cron runs daily at 9am UTC
- Queries all overdue invoices for Pro users
- For each: evaluate escalation level → generate AI email → send via Resend
- Log in collection_actions table
- User receives summary notification

**4. pSEO Page Generation**
- 200+ industry pages generated at build time (SSG)
- Template component with dynamic content per industry
- Industry data stored in JSON/MDX files
- Each page: unique sample invoice + SEO content + embedded generator

---

## 7. SEO Strategy

### URL Structure

```
/                                    → AI Invoice Generator (home)
/receipt-generator                   → Receipt Generator
/quote-generator                     → Quote Generator  
/estimate-generator                  → Estimate Generator
/credit-note-generator               → Credit Note Generator
/invoice-template/consulting         → Consulting Invoice Template
/invoice-template/photography        → Photography Invoice Template
/invoice-template/plumber            → Plumber Invoice Template
/invoice-template/...                → 200+ industries
/blog/how-to-create-invoice          → Content marketing
/blog/invoice-vs-receipt             → Content marketing
/blog/freelance-payment-terms        → Content marketing
```

### Keyword Targeting Priority

| Priority | Keywords | Volume | KD | Page |
|----------|---------|--------|-----|------|
| P0 | ai invoice generator | 4K | 24 | Homepage |
| P0 | ai invoice generator free | 1.5K | ~20 | Homepage |
| P1 | receipt generator | 15K | ~40 | /receipt-generator |
| P1 | quote generator | 12K | ~38 | /quote-generator |
| P1 | invoice template {industry} | 500-2K each | 2-6 | /invoice-template/* |
| P2 | invoice generator free | 33K | 50 | Homepage (long-term) |
| P2 | free invoice generator | 85K | 52 | Homepage (long-term) |
| P3 | invoice generator | 305K | 54 | Homepage (long-term) |

### pSEO Content Template

Each industry page follows this structure:
1. H1: "{Industry} Invoice Template — Free AI Generator"
2. Live invoice preview with industry-specific sample data
3. Embedded AI generator (pre-configured for industry)
4. SEO content (~800 words):
   - What to include in a {industry} invoice
   - {Industry} invoice example
   - Common payment terms for {industry}
   - Tax considerations for {industry}
5. FAQ (schema markup, 4-6 questions)
6. Related templates (internal links)
7. CTA: "Create Your {Industry} Invoice Now — Free"

---

## 8. Monetization

### Revenue Streams

| Stream | Timeline | Mechanism |
|--------|----------|-----------|
| Google AdSense | Month 1+ | Display ads on free tool pages |
| Pro Subscription | Month 2+ | $17/month or $144/year ($12/mo) |
| Stripe Connect fees | Month 4+ | Users collect payments → platform takes 0.5-1% |
| Contract e-sign upsell | Month 4+ | Included in Pro, drives upgrades |

### Unit Economics Target

| Metric | Target |
|--------|--------|
| CAC (via SEO) | ~$0 |
| ARPU (Pro) | $17/month |
| Churn | < 5%/month |
| LTV | $340 (20-month avg lifetime) |
| Break-even | 100 Pro users = $1,700 MRR |

### Revenue Projections

| Month | SEO Traffic | Registered Users | Pro Users | MRR |
|-------|------------|-----------------|-----------|-----|
| 3 | 5K | 200 | 5 | $85 + AdSense |
| 6 | 15K | 1,000 | 30 | $510 + AdSense |
| 12 | 50K | 5,000 | 150 | $2,550 + AdSense |
| 24 | 150K | 20,000 | 600 | $10,200 + AdSense + Stripe fees |

---

## 9. Risks & Mitigations

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| invoice-generator.com adds AI | High | Medium | First-mover on AI + pSEO combination; they have no pSEO |
| Big platforms (Canva/Notion) add AI invoicing | High | Medium | Focus on collection agent, not just generation |
| AI API costs at scale | Medium | Low | Haiku is cheap; rate-limit free tier (20/day per IP) |
| Email deliverability issues (auto-reminders) | High | Medium | Use Resend, proper SPF/DKIM, warm up domain |
| Stripe Connect compliance | Medium | Low | Start with simple payment links, defer full Connect |
| SEO window closes (AI content flood) | Medium | High | Build pSEO + product moat before window closes |
| Low conversion free → paid | Medium | Medium | Aha moment 5 (overdue trigger) is the key; optimize relentlessly |
| Scope creep into accounting | Low | High | Hard rule: no ledger, no bookkeeping, ever |

---

## 10. Success Metrics

### North Star Metric

**Total dollars collected through the Agent per month** — this directly measures user value delivered.

### Supporting Metrics

| Category | Metric | Target |
|----------|--------|--------|
| Acquisition | Monthly organic traffic | 50K by month 12 |
| Activation | Aha 1 rate (AI generation completion) | > 80% |
| Activation | Aha 2 rate (PDF download) | > 60% |
| Registration | Aha 3 rate (repeat visitor → registered) | > 15% |
| Engagement | Invoice link send rate | > 30% of registered users |
| Revenue | Free → Pro conversion | > 5% of users with overdue invoices |
| Retention | Monthly Pro churn | < 5% |
| Value | Payment rate after auto-reminder | > 40% within 7 days |
| Value | Monthly report open rate | > 60% |

---

## 11. Domain & Branding

### Name Options (to be validated for availability)

| Option | Rationale |
|--------|-----------|
| invoiceagent.ai | Direct, matches product concept |
| getpaid.ai | Outcome-focused, memorable |
| billbot.ai | Friendly, approachable |
| invoicepilot.com | "Autopilot" metaphor |
| collectr.ai | Collection-focused |

### Brand Personality

- **Tone:** Friendly but professional. Like a capable assistant, not a corporate tool.
- **Visual:** Clean, modern, minimal. White space. One accent color.
- **Voice:** "I'll handle it" energy. Confident but not pushy.
