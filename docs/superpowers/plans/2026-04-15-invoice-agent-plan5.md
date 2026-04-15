# InvoiceAgent Plan 5: Financial Dashboard + Stripe Payments

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the financial dashboard (revenue charts, aging report, tax export), Stripe subscription for Pro plan, Stripe Connect for in-invoice payments, recurring invoices, and monthly email reports. This completes the full product vision.

**Architecture:** Stripe Checkout for Pro subscriptions. Stripe Connect (Express) for users to accept payments through invoice links. Vercel Cron for recurring invoice generation and monthly reports. Charts via recharts library. Tax export as CSV download.

**Tech Stack:** Stripe (Checkout + Connect + Webhooks), recharts (charts), Resend (monthly reports), Vercel Cron

**Depends on:** Plan 2 + Plan 3 completed (auth, invoices, clients, collection agent)

**Project path:** `/Users/zhanggongqing/project/孵化项目/cloudwork/workspace/invoice-agent`

---

## File Structure (new/modified files)

```
src/
├── app/
│   ├── (app)/
│   │   ├── dashboard/page.tsx          # UPGRADE: full financial dashboard
│   │   ├── reports/
│   │   │   └── page.tsx                # Tax report + CSV export
│   │   └── settings/
│   │       ├── page.tsx                # Account settings
│   │       ├── billing/page.tsx        # Subscription management
│   │       └── payments/page.tsx       # Stripe Connect setup
│   │
│   ├── api/
│   │   ├── stripe/
│   │   │   ├── checkout/route.ts       # Create Stripe Checkout session
│   │   │   ├── portal/route.ts         # Customer portal for managing subscription
│   │   │   ├── connect/route.ts        # Stripe Connect onboarding
│   │   │   └── webhook/route.ts        # Stripe webhook handler
│   │   └── cron/
│   │       ├── recurring/route.ts      # Generate recurring invoices
│   │       └── monthly-report/route.ts # Send monthly email reports
│   │
│   └── i/[id]/
│       └── page.tsx                    # UPGRADE: add Stripe payment button
│
├── components/
│   ├── app/
│   │   ├── dashboard-cards.tsx         # UPGRADE: add "collected via Agent" card
│   │   ├── revenue-chart.tsx           # Monthly revenue bar chart
│   │   ├── aging-report.tsx            # Overdue invoices by age
│   │   ├── client-leaderboard.tsx      # Top clients by revenue
│   │   └── tax-export.tsx              # CSV export button + filters
│   ├── settings/
│   │   ├── profile-form.tsx            # Update profile/company info
│   │   ├── subscription-card.tsx       # Current plan + upgrade/manage
│   │   └── stripe-connect-setup.tsx    # Connect Stripe account for payments
│   └── invoice/
│       ├── payment-button.tsx          # Stripe payment button on public invoice
│       └── recurring-config.tsx        # Recurring invoice settings
│
├── lib/
│   ├── stripe/
│   │   ├── client.ts                   # Stripe SDK client
│   │   ├── checkout.ts                 # Create checkout session
│   │   ├── connect.ts                  # Connect account helpers
│   │   └── webhook-handlers.ts         # Handle subscription + payment events
│   ├── actions/
│   │   ├── reports.ts                  # Server actions: dashboard data, CSV export
│   │   └── recurring.ts               # Server actions: recurring invoice config
│   └── email/
│       └── templates/
│           └── monthly-report-email.tsx # Monthly report email template
```

---

## Task 1: Stripe Subscription (Pro Plan)

**Files:**
- Create: `src/lib/stripe/client.ts`
- Create: `src/lib/stripe/checkout.ts`
- Create: `src/app/api/stripe/checkout/route.ts`
- Create: `src/app/api/stripe/portal/route.ts`
- Create: `src/app/api/stripe/webhook/route.ts`
- Create: `src/lib/stripe/webhook-handlers.ts`
- Create: `src/components/settings/subscription-card.tsx`
- Create: `src/app/(app)/settings/billing/page.tsx`

- [ ] **Step 1: Install Stripe**

```bash
npm install stripe @stripe/stripe-js
```

- [ ] **Step 2: Create Stripe client**

Create `src/lib/stripe/client.ts`:
```typescript
import Stripe from "stripe";

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2025-03-31.basil",
});

export const PRICE_ID = process.env.STRIPE_PRO_PRICE_ID!;
```

Add to `.env.local`:
```
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
STRIPE_PRO_PRICE_ID=price_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
```

- [ ] **Step 3: Create checkout session API**

Create `src/app/api/stripe/checkout/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import { stripe, PRICE_ID } from "@/lib/stripe/client";

export async function POST(request: NextRequest) {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  // Get or create Stripe customer
  const { data: profile } = await supabase
    .from("profiles")
    .select("stripe_customer_id, email")
    .eq("id", user.id)
    .single();

  let customerId = profile?.stripe_customer_id;

  if (!customerId) {
    const customer = await stripe.customers.create({
      email: profile?.email || user.email,
      metadata: { supabase_user_id: user.id },
    });
    customerId = customer.id;
    await supabase.from("profiles").update({ stripe_customer_id: customerId }).eq("id", user.id);
  }

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://invoiceagent.ai";

  const session = await stripe.checkout.sessions.create({
    customer: customerId,
    line_items: [{ price: PRICE_ID, quantity: 1 }],
    mode: "subscription",
    success_url: `${siteUrl}/dashboard?upgraded=true`,
    cancel_url: `${siteUrl}/settings/billing`,
  });

  return NextResponse.json({ url: session.url });
}
```

- [ ] **Step 4: Create customer portal API**

Create `src/app/api/stripe/portal/route.ts`:
```typescript
import { NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import { stripe } from "@/lib/stripe/client";

export async function POST() {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { data: profile } = await supabase
    .from("profiles")
    .select("stripe_customer_id")
    .eq("id", user.id)
    .single();

  if (!profile?.stripe_customer_id) {
    return NextResponse.json({ error: "No subscription" }, { status: 400 });
  }

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://invoiceagent.ai";

  const session = await stripe.billingPortal.sessions.create({
    customer: profile.stripe_customer_id,
    return_url: `${siteUrl}/settings/billing`,
  });

  return NextResponse.json({ url: session.url });
}
```

- [ ] **Step 5: Create webhook handler**

Create `src/lib/stripe/webhook-handlers.ts`:
```typescript
import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function handleSubscriptionCreated(subscription: Stripe.Subscription) {
  const customerId = subscription.customer as string;
  await supabase
    .from("profiles")
    .update({ plan: "pro" })
    .eq("stripe_customer_id", customerId);
}

export async function handleSubscriptionDeleted(subscription: Stripe.Subscription) {
  const customerId = subscription.customer as string;
  await supabase
    .from("profiles")
    .update({ plan: "free" })
    .eq("stripe_customer_id", customerId);
}

export async function handlePaymentSucceeded(invoice: Stripe.Invoice) {
  // Log successful payment — useful for analytics
  console.log(`Payment succeeded for customer ${invoice.customer}`);
}
```

Create `src/app/api/stripe/webhook/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { stripe } from "@/lib/stripe/client";
import { handleSubscriptionCreated, handleSubscriptionDeleted, handlePaymentSucceeded } from "@/lib/stripe/webhook-handlers";

export async function POST(request: NextRequest) {
  const body = await request.text();
  const signature = request.headers.get("stripe-signature")!;

  let event;
  try {
    event = stripe.webhooks.constructEvent(body, signature, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch {
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
  }

  switch (event.type) {
    case "customer.subscription.created":
    case "customer.subscription.updated":
      await handleSubscriptionCreated(event.data.object);
      break;
    case "customer.subscription.deleted":
      await handleSubscriptionDeleted(event.data.object);
      break;
    case "invoice.payment_succeeded":
      await handlePaymentSucceeded(event.data.object);
      break;
  }

  return NextResponse.json({ received: true });
}
```

- [ ] **Step 6: Create billing settings page**

Create `src/components/settings/subscription-card.tsx`:
```tsx
"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Check } from "lucide-react";

interface SubscriptionCardProps {
  plan: "free" | "pro";
}

const proFeatures = [
  "Unlimited invoices & clients",
  "AI auto-collection agent",
  "Invoice status tracking",
  "Online payments via Stripe",
  "Contract templates & e-signatures",
  "Recurring invoices",
  "Financial dashboard & reports",
  "Monthly email reports",
];

export function SubscriptionCard({ plan }: SubscriptionCardProps) {
  async function handleUpgrade() {
    const res = await fetch("/api/stripe/checkout", { method: "POST" });
    const { url } = await res.json();
    window.location.href = url;
  }

  async function handleManage() {
    const res = await fetch("/api/stripe/portal", { method: "POST" });
    const { url } = await res.json();
    window.location.href = url;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {plan === "pro" ? "Pro Plan" : "Free Plan"}
        </CardTitle>
        <CardDescription>
          {plan === "pro" ? "$17/month — Full collection agent" : "Basic invoice generation"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {plan === "pro" ? (
          <div className="space-y-4">
            <ul className="space-y-2">
              {proFeatures.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm">
                  <Check className="h-4 w-4 text-green-600" /> {f}
                </li>
              ))}
            </ul>
            <Button variant="outline" onClick={handleManage}>Manage Subscription</Button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">Upgrade to unlock the full AI collection agent and all Pro features.</p>
            <Button onClick={handleUpgrade}>Upgrade to Pro — $17/month</Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

Create `src/app/(app)/settings/billing/page.tsx` — renders `SubscriptionCard` with the user's current plan.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: Stripe subscription — checkout, portal, webhook, billing page"
```

---

## Task 2: Stripe Connect (Invoice Payments)

**Files:**
- Create: `src/lib/stripe/connect.ts`
- Create: `src/app/api/stripe/connect/route.ts`
- Create: `src/components/settings/stripe-connect-setup.tsx`
- Create: `src/components/invoice/payment-button.tsx`
- Modify: `src/app/i/[id]/page.tsx`
- Create: `src/app/(app)/settings/payments/page.tsx`

- [ ] **Step 1: Create Connect helpers**

Create `src/lib/stripe/connect.ts`:
```typescript
import { stripe } from "./client";

export async function createConnectAccount(userId: string, email: string) {
  const account = await stripe.accounts.create({
    type: "express",
    email,
    metadata: { supabase_user_id: userId },
    capabilities: {
      card_payments: { requested: true },
      transfers: { requested: true },
    },
  });
  return account;
}

export async function createAccountLink(accountId: string, returnUrl: string) {
  const link = await stripe.accountLinks.create({
    account: accountId,
    refresh_url: `${returnUrl}?refresh=true`,
    return_url: `${returnUrl}?success=true`,
    type: "account_onboarding",
  });
  return link;
}

export async function createPaymentIntent(
  amount: number,
  currency: string,
  connectedAccountId: string,
  invoiceId: string,
  applicationFeePercent: number = 1
) {
  const applicationFee = Math.round(amount * (applicationFeePercent / 100));

  const paymentIntent = await stripe.paymentIntents.create({
    amount: Math.round(amount * 100), // Stripe uses cents
    currency: currency.toLowerCase(),
    application_fee_amount: applicationFee,
    transfer_data: { destination: connectedAccountId },
    metadata: { invoice_id: invoiceId },
  });

  return paymentIntent;
}
```

- [ ] **Step 2: Create Connect onboarding API**

Create `src/app/api/stripe/connect/route.ts`:
```typescript
import { NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import { createConnectAccount, createAccountLink } from "@/lib/stripe/connect";

export async function POST() {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { data: profile } = await supabase
    .from("profiles")
    .select("stripe_connect_id, email")
    .eq("id", user.id)
    .single();

  let connectId = profile?.stripe_connect_id;

  if (!connectId) {
    const account = await createConnectAccount(user.id, profile?.email || user.email!);
    connectId = account.id;
    await supabase.from("profiles").update({ stripe_connect_id: connectId }).eq("id", user.id);
  }

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://invoiceagent.ai";
  const link = await createAccountLink(connectId, `${siteUrl}/settings/payments`);

  return NextResponse.json({ url: link.url });
}
```

Note: This requires adding a `stripe_connect_id` column to the profiles table:
```sql
alter table public.profiles add column stripe_connect_id text;
```

- [ ] **Step 3: Create payment button for public invoice**

Create `src/components/invoice/payment-button.tsx`:
```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CreditCard, Loader2 } from "lucide-react";

interface PaymentButtonProps {
  invoiceId: string;
  amount: number;
  currency: string;
}

export function PaymentButton({ invoiceId, amount, currency }: PaymentButtonProps) {
  const [loading, setLoading] = useState(false);

  async function handlePay() {
    setLoading(true);
    try {
      const res = await fetch("/api/stripe/pay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invoiceId }),
      });
      const { url } = await res.json();
      if (url) window.location.href = url;
    } catch {
      setLoading(false);
    }
  }

  return (
    <Button onClick={handlePay} disabled={loading} size="lg" className="w-full">
      {loading ? (
        <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Processing...</>
      ) : (
        <><CreditCard className="mr-2 h-4 w-4" /> Pay {currency} {amount.toFixed(2)}</>
      )}
    </Button>
  );
}
```

- [ ] **Step 4: Update public invoice page**

Modify `src/app/i/[id]/page.tsx` to check if the invoice owner has Stripe Connect set up. If yes, show the PaymentButton. If not, just show the invoice.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Stripe Connect — accept payments through invoices"
```

---

## Task 3: Financial Dashboard

**Files:**
- Create: `src/lib/actions/reports.ts`
- Create: `src/components/app/revenue-chart.tsx`
- Create: `src/components/app/aging-report.tsx`
- Create: `src/components/app/client-leaderboard.tsx`
- Create: `src/components/app/tax-export.tsx`
- Modify: `src/app/(app)/dashboard/page.tsx`
- Create: `src/app/(app)/reports/page.tsx`

- [ ] **Step 1: Install recharts**

```bash
npm install recharts
```

- [ ] **Step 2: Create report server actions**

Create `src/lib/actions/reports.ts`:
```typescript
"use server";

import { createServerSupabaseClient } from "@/lib/supabase/server";

export async function getDashboardStats() {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not authenticated");

  const { data: invoices } = await supabase
    .from("invoices")
    .select("status, total, currency, due_date, paid_at, created_at, client_name")
    .eq("user_id", user.id)
    .eq("document_type", "invoice");

  if (!invoices) return null;

  const now = new Date();
  const stats = {
    totalInvoices: invoices.length,
    totalAmount: invoices.reduce((s, i) => s + Number(i.total), 0),
    paidAmount: invoices.filter((i) => i.status === "paid").reduce((s, i) => s + Number(i.total), 0),
    outstandingAmount: invoices.filter((i) => ["sent", "viewed"].includes(i.status)).reduce((s, i) => s + Number(i.total), 0),
    overdueAmount: invoices.filter((i) => i.status === "overdue").reduce((s, i) => s + Number(i.total), 0),
    currency: "USD", // Use the most common currency
  };

  // Monthly revenue for chart (last 12 months)
  const monthlyRevenue = Array.from({ length: 12 }, (_, i) => {
    const date = new Date(now.getFullYear(), now.getMonth() - 11 + i, 1);
    const monthStr = date.toISOString().slice(0, 7); // YYYY-MM
    const monthInvoices = invoices.filter(
      (inv) => inv.status === "paid" && inv.paid_at && inv.paid_at.startsWith(monthStr)
    );
    return {
      month: date.toLocaleDateString("en-US", { month: "short", year: "2-digit" }),
      revenue: monthInvoices.reduce((s, i) => s + Number(i.total), 0),
    };
  });

  // Aging report
  const aging = {
    current: invoices.filter((i) => ["sent", "viewed"].includes(i.status) && new Date(i.due_date) >= now).reduce((s, i) => s + Number(i.total), 0),
    days1to30: invoices.filter((i) => {
      if (i.status !== "overdue") return false;
      const overdueDays = (now.getTime() - new Date(i.due_date).getTime()) / 86400000;
      return overdueDays > 0 && overdueDays <= 30;
    }).reduce((s, i) => s + Number(i.total), 0),
    days31to60: invoices.filter((i) => {
      if (i.status !== "overdue") return false;
      const overdueDays = (now.getTime() - new Date(i.due_date).getTime()) / 86400000;
      return overdueDays > 30 && overdueDays <= 60;
    }).reduce((s, i) => s + Number(i.total), 0),
    days60plus: invoices.filter((i) => {
      if (i.status !== "overdue") return false;
      const overdueDays = (now.getTime() - new Date(i.due_date).getTime()) / 86400000;
      return overdueDays > 60;
    }).reduce((s, i) => s + Number(i.total), 0),
  };

  // Top clients
  const clientMap = new Map<string, number>();
  invoices.filter((i) => i.status === "paid").forEach((i) => {
    const name = i.client_name || "Unknown";
    clientMap.set(name, (clientMap.get(name) || 0) + Number(i.total));
  });
  const topClients = Array.from(clientMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, total]) => ({ name, total }));

  return { stats, monthlyRevenue, aging, topClients };
}

export async function exportTaxCSV(year: number) {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not authenticated");

  const { data: invoices } = await supabase
    .from("invoices")
    .select("*")
    .eq("user_id", user.id)
    .eq("document_type", "invoice")
    .gte("issue_date", `${year}-01-01`)
    .lte("issue_date", `${year}-12-31`)
    .order("issue_date");

  if (!invoices) return "";

  const header = "Invoice #,Client,Issue Date,Due Date,Status,Subtotal,Tax Rate,Tax Amount,Total,Currency,Paid Date\n";
  const rows = invoices.map((i) =>
    `"${i.invoice_number}","${i.client_name}","${i.issue_date}","${i.due_date}","${i.status}",${i.subtotal},${i.tax_rate}%,${i.tax_amount},${i.total},"${i.currency}","${i.paid_at || ""}"`
  ).join("\n");

  return header + rows;
}
```

- [ ] **Step 3: Create revenue chart**

Create `src/components/app/revenue-chart.tsx`:
```tsx
"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface RevenueChartProps {
  data: { month: string; revenue: number }[];
  currency: string;
}

export function RevenueChart({ data, currency }: RevenueChartProps) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <XAxis dataKey="month" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${currency}${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`} />
          <Tooltip formatter={(value: number) => [`${currency}${value.toFixed(2)}`, "Revenue"]} />
          <Bar dataKey="revenue" fill="#2563eb" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 4: Create aging report and client leaderboard**

Create `src/components/app/aging-report.tsx`:
```tsx
import { formatCurrency } from "@/lib/data/currencies";

interface AgingData {
  current: number;
  days1to30: number;
  days31to60: number;
  days60plus: number;
}

export function AgingReport({ data, currency }: { data: AgingData; currency: string }) {
  const segments = [
    { label: "Current", amount: data.current, color: "bg-green-500" },
    { label: "1-30 days", amount: data.days1to30, color: "bg-yellow-500" },
    { label: "31-60 days", amount: data.days31to60, color: "bg-orange-500" },
    { label: "60+ days", amount: data.days60plus, color: "bg-red-500" },
  ];

  const total = segments.reduce((s, seg) => s + seg.amount, 0);

  return (
    <div className="space-y-3">
      {/* Stacked bar */}
      <div className="h-4 flex rounded-full overflow-hidden bg-gray-100">
        {segments.map((seg) => (
          seg.amount > 0 && (
            <div key={seg.label} className={`${seg.color}`} style={{ width: `${(seg.amount / total) * 100}%` }} />
          )
        ))}
      </div>
      {/* Legend */}
      <div className="grid grid-cols-2 gap-2">
        {segments.map((seg) => (
          <div key={seg.label} className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${seg.color}`} />
              {seg.label}
            </span>
            <span className="font-medium">{formatCurrency(seg.amount, currency)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Create `src/components/app/client-leaderboard.tsx`:
```tsx
import { formatCurrency } from "@/lib/data/currencies";

interface ClientRevenue {
  name: string;
  total: number;
}

export function ClientLeaderboard({ clients, currency }: { clients: ClientRevenue[]; currency: string }) {
  return (
    <div className="space-y-3">
      {clients.map((client, i) => (
        <div key={client.name} className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-400 w-5">{i + 1}</span>
            <span className="text-sm font-medium">{client.name}</span>
          </div>
          <span className="text-sm font-semibold">{formatCurrency(client.total, currency)}</span>
        </div>
      ))}
      {clients.length === 0 && <p className="text-sm text-gray-500">No paid invoices yet.</p>}
    </div>
  );
}
```

- [ ] **Step 5: Create tax export component**

Create `src/components/app/tax-export.tsx`:
```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Download } from "lucide-react";
import { exportTaxCSV } from "@/lib/actions/reports";

export function TaxExport() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear.toString());

  async function handleExport() {
    const csv = await exportTaxCSV(parseInt(year));
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `invoices-${year}-tax-report.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex items-center gap-3">
      <Select value={year} onValueChange={setYear}>
        <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
        <SelectContent>
          {[currentYear, currentYear - 1, currentYear - 2].map((y) => (
            <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button onClick={handleExport} variant="outline">
        <Download className="h-4 w-4 mr-2" /> Export CSV
      </Button>
    </div>
  );
}
```

- [ ] **Step 6: Upgrade dashboard page**

Update `src/app/(app)/dashboard/page.tsx` to call `getDashboardStats()` and render the full dashboard: DashboardCards + RevenueChart + AgingReport + ClientLeaderboard.

Create `src/app/(app)/reports/page.tsx` — tax export page with TaxExport component + year filter.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: financial dashboard — revenue chart, aging report, tax CSV export"
```

---

## Task 4: Recurring Invoices + Monthly Reports

**Files:**
- Create: `src/components/invoice/recurring-config.tsx`
- Create: `src/lib/actions/recurring.ts`
- Create: `src/app/api/cron/recurring/route.ts`
- Create: `src/app/api/cron/monthly-report/route.ts`
- Create: `src/lib/email/templates/monthly-report-email.tsx`
- Modify: `vercel.json` (add cron jobs)

- [ ] **Step 1: Create recurring invoice config component**

Create `src/components/invoice/recurring-config.tsx`:
```tsx
"use client";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useState } from "react";

export interface RecurringConfig {
  enabled: boolean;
  frequency: "weekly" | "biweekly" | "monthly" | "quarterly" | "yearly";
  nextDate: string;
  endDate?: string;
}

interface RecurringConfigProps {
  config: RecurringConfig;
  onChange: (config: RecurringConfig) => void;
}

export function RecurringConfigPanel({ config, onChange }: RecurringConfigProps) {
  return (
    <div className="space-y-4 p-4 border rounded-lg bg-gray-50">
      <div className="flex items-center justify-between">
        <Label>Recurring Invoice</Label>
        <Switch checked={config.enabled} onCheckedChange={(enabled) => onChange({ ...config, enabled })} />
      </div>
      {config.enabled && (
        <div className="space-y-3">
          <div>
            <Label>Frequency</Label>
            <Select value={config.frequency} onValueChange={(v) => onChange({ ...config, frequency: v as RecurringConfig["frequency"] })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="biweekly">Bi-weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
                <SelectItem value="quarterly">Quarterly</SelectItem>
                <SelectItem value="yearly">Yearly</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Next Invoice Date</Label>
            <Input type="date" value={config.nextDate} onChange={(e) => onChange({ ...config, nextDate: e.target.value })} />
          </div>
          <div>
            <Label>End Date (optional)</Label>
            <Input type="date" value={config.endDate || ""} onChange={(e) => onChange({ ...config, endDate: e.target.value || undefined })} />
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create recurring invoice cron**

Create `src/app/api/cron/recurring/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { generateShortId } from "@/lib/utils/short-id";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function GET(request: NextRequest) {
  const authHeader = request.headers.get("authorization");
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const today = new Date().toISOString().split("T")[0];

  // Find invoices with recurring config where next_date is today
  const { data: invoices } = await supabase
    .from("invoices")
    .select("*")
    .not("recurring_config", "is", null)
    .eq("recurring_config->>enabled", "true")
    .lte("recurring_config->>nextDate", today);

  if (!invoices || invoices.length === 0) {
    return NextResponse.json({ message: "No recurring invoices due", processed: 0 });
  }

  let processed = 0;

  for (const invoice of invoices) {
    const config = invoice.recurring_config as { enabled: boolean; frequency: string; nextDate: string; endDate?: string };

    // Check end date
    if (config.endDate && config.endDate < today) continue;

    // Clone the invoice with new number and dates
    const newNumber = `${invoice.invoice_number.replace(/-\d+$/, "")}-${Date.now().toString(36).toUpperCase()}`;

    const { error } = await supabase.from("invoices").insert({
      user_id: invoice.user_id,
      client_id: invoice.client_id,
      invoice_number: newNumber,
      status: "draft",
      document_type: "invoice",
      sender_name: invoice.sender_name,
      sender_email: invoice.sender_email,
      sender_address: invoice.sender_address,
      sender_phone: invoice.sender_phone,
      client_name: invoice.client_name,
      client_email: invoice.client_email,
      client_address: invoice.client_address,
      client_company: invoice.client_company,
      items: invoice.items,
      subtotal: invoice.subtotal,
      tax_rate: invoice.tax_rate,
      tax_amount: invoice.tax_amount,
      total: invoice.total,
      currency: invoice.currency,
      issue_date: today,
      due_date: calculateDueDate(today, invoice.payment_terms),
      payment_terms: invoice.payment_terms,
      notes: invoice.notes,
      terms: invoice.terms,
      online_link_id: generateShortId(),
    });

    if (!error) {
      // Update next date on original invoice
      const nextDate = calculateNextDate(today, config.frequency);
      await supabase.from("invoices").update({
        recurring_config: { ...config, nextDate },
      }).eq("id", invoice.id);
      processed++;
    }
  }

  return NextResponse.json({ processed });
}

function calculateDueDate(issueDate: string, terms?: string): string {
  const days = terms?.match(/\d+/)?.[0] ? parseInt(terms.match(/\d+/)![0]) : 30;
  const date = new Date(issueDate);
  date.setDate(date.getDate() + days);
  return date.toISOString().split("T")[0];
}

function calculateNextDate(current: string, frequency: string): string {
  const date = new Date(current);
  switch (frequency) {
    case "weekly": date.setDate(date.getDate() + 7); break;
    case "biweekly": date.setDate(date.getDate() + 14); break;
    case "monthly": date.setMonth(date.getMonth() + 1); break;
    case "quarterly": date.setMonth(date.getMonth() + 3); break;
    case "yearly": date.setFullYear(date.getFullYear() + 1); break;
  }
  return date.toISOString().split("T")[0];
}
```

- [ ] **Step 3: Create monthly report cron + email**

Create `src/lib/email/templates/monthly-report-email.tsx`:
```tsx
import { Html, Head, Body, Container, Section, Text, Hr } from "@react-email/components";

interface MonthlyReportProps {
  userName: string;
  month: string;
  collected: string;
  outstanding: string;
  overdue: string;
  invoicesSent: number;
  invoicesPaid: number;
  collectedViaAgent: string;
}

export function MonthlyReportEmail(props: MonthlyReportProps) {
  return (
    <Html>
      <Head />
      <Body style={{ fontFamily: "Arial, sans-serif", backgroundColor: "#f9fafb", padding: "20px" }}>
        <Container style={{ maxWidth: "560px", margin: "0 auto", backgroundColor: "#ffffff", borderRadius: "8px", padding: "32px" }}>
          <Text style={{ fontSize: "20px", fontWeight: "bold", color: "#1f2937" }}>
            {props.month} Report
          </Text>
          <Text style={{ fontSize: "14px", color: "#6b7280" }}>Hi {props.userName}, here is your monthly summary.</Text>

          <Section style={{ display: "flex", justifyContent: "space-between", margin: "24px 0" }}>
            <div style={{ textAlign: "center", flex: 1 }}>
              <Text style={{ fontSize: "12px", color: "#6b7280", margin: 0 }}>Collected</Text>
              <Text style={{ fontSize: "24px", fontWeight: "bold", color: "#16a34a", margin: "4px 0" }}>{props.collected}</Text>
            </div>
            <div style={{ textAlign: "center", flex: 1 }}>
              <Text style={{ fontSize: "12px", color: "#6b7280", margin: 0 }}>Outstanding</Text>
              <Text style={{ fontSize: "24px", fontWeight: "bold", color: "#ca8a04", margin: "4px 0" }}>{props.outstanding}</Text>
            </div>
            <div style={{ textAlign: "center", flex: 1 }}>
              <Text style={{ fontSize: "12px", color: "#6b7280", margin: 0 }}>Overdue</Text>
              <Text style={{ fontSize: "24px", fontWeight: "bold", color: "#dc2626", margin: "4px 0" }}>{props.overdue}</Text>
            </div>
          </Section>

          <Hr />
          <Text style={{ fontSize: "13px", color: "#374151" }}>
            Invoices sent: {props.invoicesSent} | Paid: {props.invoicesPaid}
          </Text>
          {props.collectedViaAgent !== "$0" && (
            <Text style={{ fontSize: "13px", color: "#16a34a" }}>
              Collected via AI Agent: {props.collectedViaAgent}
            </Text>
          )}
          <Hr />
          <Text style={{ fontSize: "12px", color: "#9ca3af", textAlign: "center" }}>InvoiceAgent — your AI billing assistant</Text>
        </Container>
      </Body>
    </Html>
  );
}
```

Create `src/app/api/cron/monthly-report/route.ts` — queries all Pro users, calculates their monthly stats, sends report email via Resend.

- [ ] **Step 4: Update vercel.json with new crons**

Update `vercel.json`:
```json
{
  "crons": [
    { "path": "/api/cron/collection", "schedule": "0 9 * * *" },
    { "path": "/api/cron/recurring", "schedule": "0 6 * * *" },
    { "path": "/api/cron/monthly-report", "schedule": "0 8 1 * *" }
  ]
}
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: recurring invoices + monthly email reports"
```

---

## Task 5: Settings Pages

**Files:**
- Create: `src/components/settings/profile-form.tsx`
- Create: `src/app/(app)/settings/page.tsx`

- [ ] **Step 1: Create profile settings**

Create `src/components/settings/profile-form.tsx` — form to update: full name, company name, company address, phone, default currency, default tax rate, default payment terms, logo upload (Supabase Storage).

Create `src/app/(app)/settings/page.tsx` — renders profile form.

- [ ] **Step 2: Update sidebar**

Add Settings and Reports nav items to sidebar:
```typescript
{ href: "/reports", icon: BarChart3, label: "Reports" },
{ href: "/settings", icon: Settings, label: "Settings" },
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: settings — profile, billing, payment setup pages"
```

---

## Summary

| Task | What it delivers | Estimated time |
|------|-----------------|---------------|
| 1. Stripe Subscription | Pro plan checkout, portal, webhooks | 35 min |
| 2. Stripe Connect | Accept payments through invoices | 30 min |
| 3. Financial Dashboard | Revenue chart, aging report, CSV export | 35 min |
| 4. Recurring + Reports | Auto-generate invoices, monthly email | 30 min |
| 5. Settings Pages | Profile, billing, payment settings | 15 min |
| **Total** | | **~2.5 hours** |
