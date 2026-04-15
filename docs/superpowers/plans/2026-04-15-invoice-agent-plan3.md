# InvoiceAgent Plan 3: AI Collection Agent + Email

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core paid feature — an AI-powered autonomous collection agent that automatically sends personalized payment reminders, escalates overdue invoices, and logs all collection actions. This is the primary monetization driver and product differentiator.

**Architecture:** Vercel Cron Job runs daily, queries overdue invoices for Pro users, generates AI-personalized reminder emails via Claude Haiku, sends via Resend API, and logs actions in `collection_actions` table. Users can preview/edit auto-generated emails before sending, or enable full auto-pilot mode.

**Tech Stack:** Vercel Cron, Claude Haiku (email generation), Resend (email delivery), Supabase (state management)

**Depends on:** Plan 2 completed (auth, clients, invoice persistence + status tracking)

**Project path:** `/Users/zhanggongqing/project/孵化项目/cloudwork/workspace/invoice-agent`

---

## File Structure (new/modified files)

```
src/
├── app/
│   ├── api/
│   │   ├── cron/
│   │   │   └── collection/route.ts     # Vercel Cron: daily overdue invoice check
│   │   └── email/
│   │       ├── send-invoice/route.ts   # Send invoice via email
│   │       └── send-reminder/route.ts  # Send collection reminder
│   │
│   └── (app)/
│       └── invoices/
│           └── [id]/
│               └── collection/page.tsx # Collection history for an invoice
│
├── components/
│   └── app/
│       ├── collection-timeline.tsx     # Visual timeline of collection actions
│       ├── reminder-preview.tsx        # AI-generated reminder email preview
│       └── collection-settings.tsx     # User's auto-collection preferences
│
├── lib/
│   ├── ai/
│   │   └── collection-prompts.ts       # AI prompts for collection email generation
│   ├── email/
│   │   ├── resend.ts                   # Resend client + send helper
│   │   ├── templates/
│   │   │   ├── invoice-email.tsx       # React Email: invoice delivery
│   │   │   └── reminder-email.tsx      # React Email: payment reminder
│   │   └── send-invoice.ts            # Send invoice email function
│   └── actions/
│       └── collection.ts              # Server actions: collection CRUD
│
└── vercel.json                         # Cron job configuration
```

---

## Task 1: Email Infrastructure (Resend)

**Files:**
- Create: `src/lib/email/resend.ts`
- Create: `src/lib/email/templates/invoice-email.tsx`
- Create: `src/lib/email/templates/reminder-email.tsx`
- Create: `src/lib/email/send-invoice.ts`

- [ ] **Step 1: Install Resend**

```bash
npm install resend react-email @react-email/components
```

- [ ] **Step 2: Create Resend client**

Create `src/lib/email/resend.ts`:
```typescript
import { Resend } from "resend";

export const resend = new Resend(process.env.RESEND_API_KEY);

export const FROM_EMAIL = process.env.FROM_EMAIL || "invoices@invoiceagent.ai";
export const FROM_NAME = "InvoiceAgent";
```

Add to `.env.local`:
```
RESEND_API_KEY=re_xxxxxxxxxxxxx
FROM_EMAIL=invoices@yourdomain.com
```

- [ ] **Step 3: Create invoice email template**

Create `src/lib/email/templates/invoice-email.tsx`:
```tsx
import { Html, Head, Body, Container, Section, Text, Link, Hr } from "@react-email/components";

interface InvoiceEmailProps {
  senderName: string;
  clientName: string;
  invoiceNumber: string;
  total: string;
  currency: string;
  dueDate: string;
  viewUrl: string;
}

export function InvoiceEmail({ senderName, clientName, invoiceNumber, total, currency, dueDate, viewUrl }: InvoiceEmailProps) {
  return (
    <Html>
      <Head />
      <Body style={{ fontFamily: "Arial, sans-serif", backgroundColor: "#f9fafb", padding: "20px" }}>
        <Container style={{ maxWidth: "560px", margin: "0 auto", backgroundColor: "#ffffff", borderRadius: "8px", padding: "32px" }}>
          <Text style={{ fontSize: "16px", color: "#374151" }}>Hi {clientName},</Text>
          <Text style={{ fontSize: "16px", color: "#374151" }}>
            {senderName} has sent you an invoice.
          </Text>
          <Section style={{ backgroundColor: "#f3f4f6", borderRadius: "8px", padding: "20px", margin: "20px 0" }}>
            <Text style={{ fontSize: "14px", color: "#6b7280", margin: 0 }}>Invoice {invoiceNumber}</Text>
            <Text style={{ fontSize: "28px", fontWeight: "bold", color: "#1f2937", margin: "8px 0" }}>{currency} {total}</Text>
            <Text style={{ fontSize: "14px", color: "#6b7280", margin: 0 }}>Due: {dueDate}</Text>
          </Section>
          <Link href={viewUrl} style={{ display: "block", textAlign: "center", backgroundColor: "#2563eb", color: "#ffffff", padding: "12px 24px", borderRadius: "6px", textDecoration: "none", fontWeight: "bold", fontSize: "16px" }}>
            View Invoice
          </Link>
          <Hr style={{ marginTop: "32px" }} />
          <Text style={{ fontSize: "12px", color: "#9ca3af", textAlign: "center" }}>Sent via InvoiceAgent</Text>
        </Container>
      </Body>
    </Html>
  );
}
```

- [ ] **Step 4: Create reminder email template**

Create `src/lib/email/templates/reminder-email.tsx`:
```tsx
import { Html, Head, Body, Container, Text, Link, Hr } from "@react-email/components";

interface ReminderEmailProps {
  subject: string;
  body: string;
  viewUrl: string;
}

export function ReminderEmail({ subject, body, viewUrl }: ReminderEmailProps) {
  return (
    <Html>
      <Head />
      <Body style={{ fontFamily: "Arial, sans-serif", backgroundColor: "#f9fafb", padding: "20px" }}>
        <Container style={{ maxWidth: "560px", margin: "0 auto", backgroundColor: "#ffffff", borderRadius: "8px", padding: "32px" }}>
          <Text style={{ fontSize: "16px", color: "#374151", whiteSpace: "pre-line" }}>{body}</Text>
          <Link href={viewUrl} style={{ display: "block", textAlign: "center", backgroundColor: "#2563eb", color: "#ffffff", padding: "12px 24px", borderRadius: "6px", textDecoration: "none", fontWeight: "bold", fontSize: "16px", marginTop: "24px" }}>
            View Invoice
          </Link>
          <Hr style={{ marginTop: "32px" }} />
          <Text style={{ fontSize: "12px", color: "#9ca3af", textAlign: "center" }}>Sent via InvoiceAgent</Text>
        </Container>
      </Body>
    </Html>
  );
}
```

- [ ] **Step 5: Create invoice send function**

Create `src/lib/email/send-invoice.ts`:
```typescript
import { resend, FROM_EMAIL, FROM_NAME } from "./resend";
import { InvoiceEmail } from "./templates/invoice-email";

interface SendInvoiceParams {
  to: string;
  senderName: string;
  clientName: string;
  invoiceNumber: string;
  total: string;
  currency: string;
  dueDate: string;
  viewUrl: string;
}

export async function sendInvoiceEmail(params: SendInvoiceParams) {
  const { data, error } = await resend.emails.send({
    from: `${FROM_NAME} <${FROM_EMAIL}>`,
    to: params.to,
    subject: `Invoice ${params.invoiceNumber} from ${params.senderName}`,
    react: InvoiceEmail(params),
  });

  if (error) throw error;
  return data;
}
```

- [ ] **Step 6: Create send invoice API route**

Create `src/app/api/email/send-invoice/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import { sendInvoiceEmail } from "@/lib/email/send-invoice";

export async function POST(request: NextRequest) {
  const { invoiceId } = await request.json();
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { data: invoice } = await supabase
    .from("invoices")
    .select("*")
    .eq("id", invoiceId)
    .eq("user_id", user.id)
    .single();

  if (!invoice) return NextResponse.json({ error: "Not found" }, { status: 404 });
  if (!invoice.client_email) return NextResponse.json({ error: "Client email missing" }, { status: 400 });

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://invoiceagent.ai";
  const viewUrl = `${siteUrl}/i/${invoice.online_link_id}`;

  await sendInvoiceEmail({
    to: invoice.client_email,
    senderName: invoice.sender_name,
    clientName: invoice.client_name,
    invoiceNumber: invoice.invoice_number,
    total: invoice.total.toString(),
    currency: invoice.currency,
    dueDate: invoice.due_date,
    viewUrl,
  });

  await supabase.from("invoices").update({
    status: "sent",
    sent_at: new Date().toISOString(),
  }).eq("id", invoiceId);

  return NextResponse.json({ success: true });
}
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: email infrastructure — Resend integration, invoice + reminder templates"
```

---

## Task 2: AI Collection Engine

**Files:**
- Create: `src/lib/ai/collection-prompts.ts`
- Create: `src/lib/actions/collection.ts`
- Create: `src/app/api/email/send-reminder/route.ts`

- [ ] **Step 1: Create AI collection prompts**

Create `src/lib/ai/collection-prompts.ts`:
```typescript
interface CollectionContext {
  senderName: string;
  clientName: string;
  invoiceNumber: string;
  total: string;
  currency: string;
  dueDate: string;
  daysOverdue: number;
  escalationLevel: number;
  previousReminders: number;
  clientPaymentHistory?: string; // "always on time" | "sometimes late" | "frequently late" | "new client"
}

export function getCollectionPrompt(ctx: CollectionContext): string {
  const toneGuide = {
    1: "friendly and casual, like a gentle nudge between colleagues",
    2: "professional and polite, slightly more formal",
    3: "firm but respectful, make it clear payment is expected",
    4: "very formal and serious, mention consequences of continued non-payment",
  }[ctx.escalationLevel] || "professional";

  return `You are writing a payment reminder email on behalf of ${ctx.senderName} to ${ctx.clientName}.

Invoice details:
- Invoice number: ${ctx.invoiceNumber}
- Amount due: ${ctx.currency} ${ctx.total}
- Original due date: ${ctx.dueDate}
- Days overdue: ${ctx.daysOverdue}
- This is reminder #${ctx.previousReminders + 1}
- Client payment history: ${ctx.clientPaymentHistory || "unknown"}

Tone: ${toneGuide}

Rules:
- Return a JSON object with "subject" and "body" fields only.
- The body should be plain text (no HTML), ready to be sent as an email.
- Keep it concise — 3-5 sentences max.
- Be human, not robotic. No "Dear valued client" or "as per our records".
- Reference the specific invoice number and amount.
- ${ctx.escalationLevel >= 3 ? "Mention that you'll need to escalate if payment isn't received within 7 days." : ""}
- Sign off with the sender's name.
- Do NOT include greetings like "Dear" — start with "Hi {clientName}," or similar.`;
}
```

- [ ] **Step 2: Create collection server actions**

Create `src/lib/actions/collection.ts`:
```typescript
"use server";

import { createServerSupabaseClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";

export async function getCollectionHistory(invoiceId: string) {
  const supabase = await createServerSupabaseClient();
  const { data, error } = await supabase
    .from("collection_actions")
    .select("*")
    .eq("invoice_id", invoiceId)
    .order("created_at", { ascending: true });

  if (error) throw error;
  return data;
}

export async function generateReminder(invoiceId: string) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_SITE_URL}/api/email/send-reminder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ invoiceId, preview: true }),
  });
  return response.json();
}

export async function sendReminder(invoiceId: string, subject: string, body: string) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_SITE_URL}/api/email/send-reminder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ invoiceId, subject, body, send: true }),
  });
  return response.json();
}
```

- [ ] **Step 3: Create reminder API route**

Create `src/app/api/email/send-reminder/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import { getCollectionPrompt } from "@/lib/ai/collection-prompts";
import { resend, FROM_EMAIL, FROM_NAME } from "@/lib/email/resend";
import { ReminderEmail } from "@/lib/email/templates/reminder-email";

export async function POST(request: NextRequest) {
  const { invoiceId, preview, send, subject: overrideSubject, body: overrideBody } = await request.json();
  const supabase = await createServerSupabaseClient();

  // Fetch invoice
  const { data: invoice } = await supabase.from("invoices").select("*").eq("id", invoiceId).single();
  if (!invoice) return NextResponse.json({ error: "Not found" }, { status: 404 });

  // Count previous reminders
  const { count } = await supabase
    .from("collection_actions")
    .select("*", { count: "exact", head: true })
    .eq("invoice_id", invoiceId);

  const previousReminders = count || 0;
  const daysOverdue = Math.floor((Date.now() - new Date(invoice.due_date).getTime()) / 86400000);
  const escalationLevel = Math.min(4, Math.floor(daysOverdue / 7) + 1);

  // Generate AI email
  let subject: string;
  let body: string;

  if (overrideSubject && overrideBody) {
    subject = overrideSubject;
    body = overrideBody;
  } else {
    const prompt = getCollectionPrompt({
      senderName: invoice.sender_name,
      clientName: invoice.client_name,
      invoiceNumber: invoice.invoice_number,
      total: invoice.total.toString(),
      currency: invoice.currency,
      dueDate: invoice.due_date,
      daysOverdue,
      escalationLevel,
      previousReminders,
    });

    const aiResponse = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": process.env.ANTHROPIC_API_KEY!,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 512,
        messages: [{ role: "user", content: prompt }],
      }),
    });

    const result = await aiResponse.json();
    const parsed = JSON.parse(result.content[0].text);
    subject = parsed.subject;
    body = parsed.body;
  }

  // Preview mode — return generated email without sending
  if (preview) {
    return NextResponse.json({ subject, body, escalationLevel, daysOverdue });
  }

  // Send mode
  if (send && invoice.client_email) {
    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://invoiceagent.ai";
    const viewUrl = `${siteUrl}/i/${invoice.online_link_id}`;

    await resend.emails.send({
      from: `${FROM_NAME} <${FROM_EMAIL}>`,
      to: invoice.client_email,
      subject,
      react: ReminderEmail({ subject, body, viewUrl }),
    });

    // Log collection action
    await supabase.from("collection_actions").insert({
      invoice_id: invoiceId,
      action_type: escalationLevel <= 1 ? "reminder" : escalationLevel <= 3 ? "follow_up" : "final_notice",
      escalation_level: escalationLevel,
      email_subject: subject,
      email_body: body,
      sent_at: new Date().toISOString(),
      result: "pending",
    });

    return NextResponse.json({ success: true, escalationLevel });
  }

  return NextResponse.json({ error: "Specify preview or send" }, { status: 400 });
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: AI collection engine — personalized reminder generation + send"
```

---

## Task 3: Automated Cron Collection

**Files:**
- Create: `src/app/api/cron/collection/route.ts`
- Create: `vercel.json`

- [ ] **Step 1: Create cron job**

Create `src/app/api/cron/collection/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { getCollectionPrompt } from "@/lib/ai/collection-prompts";
import { resend, FROM_EMAIL, FROM_NAME } from "@/lib/email/resend";
import { ReminderEmail } from "@/lib/email/templates/reminder-email";

// Use service role key for cron (no user session)
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function GET(request: NextRequest) {
  // Verify cron secret
  const authHeader = request.headers.get("authorization");
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Find overdue invoices for Pro users with auto-collection enabled
  const { data: overdueInvoices } = await supabase
    .from("invoices")
    .select("*, profiles!inner(plan)")
    .in("status", ["sent", "viewed", "overdue"])
    .lt("due_date", new Date().toISOString().split("T")[0])
    .eq("profiles.plan", "pro");

  if (!overdueInvoices || overdueInvoices.length === 0) {
    return NextResponse.json({ message: "No overdue invoices", processed: 0 });
  }

  let processed = 0;
  let errors = 0;

  for (const invoice of overdueInvoices) {
    try {
      if (!invoice.client_email) continue;

      // Check if reminder was already sent today
      const { count } = await supabase
        .from("collection_actions")
        .select("*", { count: "exact", head: true })
        .eq("invoice_id", invoice.id)
        .gte("sent_at", new Date().toISOString().split("T")[0]);

      if (count && count > 0) continue;

      // Check escalation schedule
      const { count: totalReminders } = await supabase
        .from("collection_actions")
        .select("*", { count: "exact", head: true })
        .eq("invoice_id", invoice.id);

      const daysOverdue = Math.floor((Date.now() - new Date(invoice.due_date).getTime()) / 86400000);
      const escalationLevel = Math.min(4, Math.floor(daysOverdue / 7) + 1);

      // Only send at escalation milestones: day 3, 7, 14, 30
      const shouldSend = [3, 7, 14, 30].includes(daysOverdue);
      if (!shouldSend) continue;

      // Generate AI email
      const prompt = getCollectionPrompt({
        senderName: invoice.sender_name,
        clientName: invoice.client_name,
        invoiceNumber: invoice.invoice_number,
        total: invoice.total.toString(),
        currency: invoice.currency,
        dueDate: invoice.due_date,
        daysOverdue,
        escalationLevel,
        previousReminders: totalReminders || 0,
      });

      const aiResponse = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": process.env.ANTHROPIC_API_KEY!,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: "claude-haiku-4-5-20251001",
          max_tokens: 512,
          messages: [{ role: "user", content: prompt }],
        }),
      });

      const result = await aiResponse.json();
      const { subject, body } = JSON.parse(result.content[0].text);

      const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://invoiceagent.ai";
      const viewUrl = `${siteUrl}/i/${invoice.online_link_id}`;

      // Send email
      await resend.emails.send({
        from: `${FROM_NAME} <${FROM_EMAIL}>`,
        to: invoice.client_email,
        subject,
        react: ReminderEmail({ subject, body, viewUrl }),
      });

      // Log action
      await supabase.from("collection_actions").insert({
        invoice_id: invoice.id,
        action_type: escalationLevel <= 1 ? "reminder" : escalationLevel <= 3 ? "follow_up" : "final_notice",
        escalation_level: escalationLevel,
        email_subject: subject,
        email_body: body,
        sent_at: new Date().toISOString(),
        result: "pending",
      });

      // Update invoice status to overdue if not already
      if (invoice.status !== "overdue") {
        await supabase.from("invoices").update({ status: "overdue" }).eq("id", invoice.id);
      }

      processed++;
    } catch (err) {
      console.error(`Error processing invoice ${invoice.id}:`, err);
      errors++;
    }
  }

  return NextResponse.json({ processed, errors, total: overdueInvoices.length });
}
```

- [ ] **Step 2: Create Vercel cron config**

Create `vercel.json`:
```json
{
  "crons": [
    {
      "path": "/api/cron/collection",
      "schedule": "0 9 * * *"
    }
  ]
}
```

Add to `.env.local`:
```
CRON_SECRET=your_cron_secret_here
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: automated collection cron — daily overdue check + AI reminder send"
```

---

## Task 4: Collection UI

**Files:**
- Create: `src/components/app/collection-timeline.tsx`
- Create: `src/components/app/reminder-preview.tsx`
- Create: `src/app/(app)/invoices/[id]/collection/page.tsx`

- [ ] **Step 1: Create collection timeline component**

Create `src/components/app/collection-timeline.tsx`:
```tsx
import { Mail, Eye, CheckCircle, AlertTriangle } from "lucide-react";

interface CollectionAction {
  id: string;
  action_type: string;
  escalation_level: number;
  email_subject: string;
  email_body: string;
  sent_at: string;
  opened_at: string | null;
  result: string;
}

export function CollectionTimeline({ actions }: { actions: CollectionAction[] }) {
  const getIcon = (type: string) => {
    switch (type) {
      case "reminder": return Mail;
      case "follow_up": return AlertTriangle;
      case "final_notice": return AlertTriangle;
      default: return Mail;
    }
  };

  const getColor = (level: number) => {
    if (level <= 1) return "text-blue-500 bg-blue-50 border-blue-200";
    if (level <= 2) return "text-yellow-500 bg-yellow-50 border-yellow-200";
    return "text-red-500 bg-red-50 border-red-200";
  };

  if (actions.length === 0) {
    return <p className="text-sm text-gray-500">No collection actions yet.</p>;
  }

  return (
    <div className="space-y-4">
      {actions.map((action) => {
        const Icon = getIcon(action.action_type);
        const colorClass = getColor(action.escalation_level);
        return (
          <div key={action.id} className={`flex gap-3 p-4 rounded-lg border ${colorClass}`}>
            <Icon className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-start">
                <p className="font-medium text-sm">{action.email_subject}</p>
                <span className="text-xs text-gray-500 whitespace-nowrap ml-2">
                  {new Date(action.sent_at).toLocaleDateString()}
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-1 line-clamp-2">{action.email_body}</p>
              <div className="flex gap-3 mt-2 text-xs text-gray-500">
                <span>Level {action.escalation_level}/4</span>
                {action.opened_at && (
                  <span className="flex items-center gap-1"><Eye className="h-3 w-3" /> Opened</span>
                )}
                {action.result === "paid" && (
                  <span className="flex items-center gap-1 text-green-600"><CheckCircle className="h-3 w-3" /> Paid</span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create reminder preview component**

Create `src/components/app/reminder-preview.tsx`:
```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sparkles, Send, Loader2 } from "lucide-react";

interface ReminderPreviewProps {
  invoiceId: string;
  onSent: () => void;
}

export function ReminderPreview({ invoiceId, onSent }: ReminderPreviewProps) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [generated, setGenerated] = useState(false);

  async function handleGenerate() {
    setLoading(true);
    const res = await fetch("/api/email/send-reminder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ invoiceId, preview: true }),
    });
    const data = await res.json();
    setSubject(data.subject);
    setBody(data.body);
    setGenerated(true);
    setLoading(false);
  }

  async function handleSend() {
    setSending(true);
    await fetch("/api/email/send-reminder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ invoiceId, subject, body, send: true }),
    });
    setSending(false);
    onSent();
  }

  return (
    <div className="space-y-4">
      {!generated ? (
        <Button onClick={handleGenerate} disabled={loading}>
          {loading ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating...</> : <><Sparkles className="mr-2 h-4 w-4" /> Generate AI Reminder</>}
        </Button>
      ) : (
        <>
          <div><Label>Subject</Label><Input value={subject} onChange={(e) => setSubject(e.target.value)} /></div>
          <div><Label>Body</Label><Textarea value={body} onChange={(e) => setBody(e.target.value)} rows={6} /></div>
          <div className="flex gap-2">
            <Button onClick={handleGenerate} variant="outline" disabled={loading}>
              <Sparkles className="mr-2 h-4 w-4" /> Regenerate
            </Button>
            <Button onClick={handleSend} disabled={sending}>
              {sending ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending...</> : <><Send className="mr-2 h-4 w-4" /> Send Reminder</>}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create collection page**

Create `src/app/(app)/invoices/[id]/collection/page.tsx` — shows collection timeline + reminder preview. Fetches invoice and collection history, renders both components.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: collection UI — timeline, AI reminder preview, manual send"
```

---

## Summary

| Task | What it delivers | Estimated time |
|------|-----------------|---------------|
| 1. Email Infrastructure | Resend + invoice/reminder email templates | 30 min |
| 2. AI Collection Engine | AI reminder generation + send API | 30 min |
| 3. Automated Cron | Daily overdue check + auto-send | 25 min |
| 4. Collection UI | Timeline, preview, manual send | 25 min |
| **Total** | | **~2 hours** |
