# InvoiceAgent Plan 2: Client CRM + Invoice Tracking

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user authentication, client management, invoice persistence, and invoice lifecycle tracking (Draft → Sent → Viewed → Paid → Overdue). This transforms the free tool into a product with user accounts and data that persists.

**Architecture:** Supabase Auth for sign up/login (email + Google OAuth). Client and invoice data stored in Supabase PostgreSQL with RLS. Invoice online links with view tracking via a public page + pixel. Authenticated (app) route group for dashboard, client list, and invoice management.

**Tech Stack:** Supabase Auth + SSR, Next.js middleware for auth guards, Supabase Realtime for status updates

**Depends on:** Plan 1 completed (project scaffold, DB schema, AI engine, invoice form)

**Project path:** `/Users/zhanggongqing/project/孵化项目/cloudwork/workspace/invoice-agent`

---

## File Structure (new/modified files)

```
src/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx              # Login page
│   │   ├── signup/page.tsx             # Sign up page
│   │   └── callback/route.ts           # OAuth callback handler
│   │
│   ├── (app)/
│   │   ├── layout.tsx                  # Authenticated layout with sidebar
│   │   ├── dashboard/page.tsx          # Dashboard overview
│   │   ├── invoices/
│   │   │   ├── page.tsx                # Invoice list (all statuses)
│   │   │   ├── new/page.tsx            # Create new invoice (AI + form)
│   │   │   └── [id]/
│   │   │       ├── page.tsx            # Invoice detail/edit
│   │   │       └── send/route.ts       # API: send invoice via email
│   │   └── clients/
│   │       ├── page.tsx                # Client list
│   │       ├── new/page.tsx            # Add client
│   │       └── [id]/page.tsx           # Client detail + invoice history
│   │
│   ├── i/[id]/
│   │   └── page.tsx                    # Public invoice view (updates: add tracking)
│   │
│   └── api/
│       └── track/
│           └── [id]/route.ts           # 1x1 tracking pixel endpoint
│
├── components/
│   ├── auth/
│   │   ├── login-form.tsx              # Email + password + Google login
│   │   └── signup-form.tsx             # Registration form
│   ├── app/
│   │   ├── sidebar.tsx                 # App sidebar navigation
│   │   ├── invoice-list.tsx            # Invoice table with status badges
│   │   ├── invoice-status-badge.tsx    # Status pill (Draft/Sent/Viewed/Paid/Overdue)
│   │   ├── client-list.tsx             # Client table
│   │   ├── client-form.tsx             # Add/edit client form
│   │   └── dashboard-cards.tsx         # Summary cards (total/outstanding/overdue)
│   └── invoice/
│       └── send-dialog.tsx             # Dialog to send invoice via link/email
│
├── lib/
│   ├── supabase/
│   │   └── middleware.ts               # Auth middleware for protected routes
│   ├── actions/
│   │   ├── invoices.ts                 # Server actions: CRUD invoices
│   │   ├── clients.ts                  # Server actions: CRUD clients
│   │   └── auth.ts                     # Server actions: login/signup/logout
│   └── utils/
│       └── short-id.ts                 # Generate short IDs for invoice links
│
└── middleware.ts                        # Next.js middleware (auth guard)
```

---

## Task 1: Authentication (Supabase Auth)

**Files:**
- Create: `src/middleware.ts`
- Create: `src/lib/supabase/middleware.ts`
- Create: `src/app/(auth)/login/page.tsx`
- Create: `src/app/(auth)/signup/page.tsx`
- Create: `src/app/(auth)/callback/route.ts`
- Create: `src/components/auth/login-form.tsx`
- Create: `src/components/auth/signup-form.tsx`
- Create: `src/lib/actions/auth.ts`

- [ ] **Step 1: Create auth middleware**

Create `src/lib/supabase/middleware.ts`:
```typescript
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Protected routes — redirect to login if not authenticated
  if (!user && request.nextUrl.pathname.startsWith("/dashboard")) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("redirect", request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }

  // Redirect authenticated users away from auth pages
  if (user && (request.nextUrl.pathname === "/login" || request.nextUrl.pathname === "/signup")) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return supabaseResponse;
}
```

Create `src/middleware.ts`:
```typescript
import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  matcher: ["/dashboard/:path*", "/invoices/:path*", "/clients/:path*", "/login", "/signup"],
};
```

- [ ] **Step 2: Create auth server actions**

Create `src/lib/actions/auth.ts`:
```typescript
"use server";

import { redirect } from "next/navigation";
import { createServerSupabaseClient } from "@/lib/supabase/server";

export async function signUp(formData: FormData) {
  const supabase = await createServerSupabaseClient();
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;
  const fullName = formData.get("fullName") as string;

  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: { data: { full_name: fullName } },
  });

  if (error) {
    return { error: error.message };
  }

  redirect("/dashboard");
}

export async function signIn(formData: FormData) {
  const supabase = await createServerSupabaseClient();
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;

  const { error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    return { error: error.message };
  }

  const redirectTo = formData.get("redirect") as string;
  redirect(redirectTo || "/dashboard");
}

export async function signInWithGoogle() {
  const supabase = await createServerSupabaseClient();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: `${process.env.NEXT_PUBLIC_SITE_URL}/callback` },
  });

  if (error) {
    return { error: error.message };
  }

  redirect(data.url);
}

export async function signOut() {
  const supabase = await createServerSupabaseClient();
  await supabase.auth.signOut();
  redirect("/");
}
```

- [ ] **Step 3: Create login page**

Create `src/components/auth/login-form.tsx`:
```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { signIn, signInWithGoogle } from "@/lib/actions/auth";
import Link from "next/link";

export function LoginForm({ redirect }: { redirect?: string }) {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(formData: FormData) {
    setLoading(true);
    setError("");
    if (redirect) formData.set("redirect", redirect);
    const result = await signIn(formData);
    if (result?.error) {
      setError(result.error);
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-sm mx-auto space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">Welcome back</h1>
        <p className="text-gray-600 text-sm mt-1">Sign in to manage your invoices</p>
      </div>

      <Button variant="outline" className="w-full" onClick={() => signInWithGoogle()}>
        Sign in with Google
      </Button>

      <div className="relative">
        <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white px-2 text-gray-500">Or</span>
        </div>
      </div>

      <form action={handleSubmit} className="space-y-4">
        <div><Label htmlFor="email">Email</Label><Input id="email" name="email" type="email" required /></div>
        <div><Label htmlFor="password">Password</Label><Input id="password" name="password" type="password" required /></div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </Button>
      </form>

      <p className="text-center text-sm text-gray-600">
        No account? <Link href="/signup" className="text-blue-600 hover:underline">Sign up free</Link>
      </p>
    </div>
  );
}
```

Create `src/app/(auth)/login/page.tsx`:
```tsx
import { LoginForm } from "@/components/auth/login-form";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ redirect?: string }> }) {
  const { redirect } = await searchParams;
  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <LoginForm redirect={redirect} />
    </div>
  );
}
```

Create `src/components/auth/signup-form.tsx` and `src/app/(auth)/signup/page.tsx` following the same pattern with an additional "Full Name" field and calling `signUp`.

Create `src/app/(auth)/callback/route.ts`:
```typescript
import { NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  if (code) {
    const supabase = await createServerSupabaseClient();
    await supabase.auth.exchangeCodeForSession(code);
  }

  return NextResponse.redirect(`${origin}/dashboard`);
}
```

- [ ] **Step 4: Update header with auth state**

Modify `src/components/layout/header.tsx` to show "Sign in" / "Dashboard" based on auth state:
```tsx
import Link from "next/link";
import { FileText } from "lucide-react";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import { Button } from "@/components/ui/button";

export async function Header() {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();

  return (
    <header className="border-b bg-white">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-bold text-lg">
          <FileText className="h-5 w-5 text-blue-600" />
          <span>InvoiceAgent</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6 text-sm">
          <Link href="/receipt-generator" className="text-gray-600 hover:text-gray-900">Receipt</Link>
          <Link href="/quote-generator" className="text-gray-600 hover:text-gray-900">Quote</Link>
          <Link href="/estimate-generator" className="text-gray-600 hover:text-gray-900">Estimate</Link>
          {user ? (
            <Link href="/dashboard"><Button size="sm">Dashboard</Button></Link>
          ) : (
            <Link href="/login"><Button size="sm" variant="outline">Sign in</Button></Link>
          )}
        </nav>
      </div>
    </header>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: authentication — Supabase Auth with email + Google OAuth"
```

---

## Task 2: Client CRM

**Files:**
- Create: `src/lib/actions/clients.ts`
- Create: `src/components/app/client-list.tsx`
- Create: `src/components/app/client-form.tsx`
- Create: `src/app/(app)/clients/page.tsx`
- Create: `src/app/(app)/clients/new/page.tsx`
- Create: `src/app/(app)/clients/[id]/page.tsx`

- [ ] **Step 1: Create client server actions**

Create `src/lib/actions/clients.ts`:
```typescript
"use server";

import { createServerSupabaseClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";

export async function getClients() {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not authenticated");

  const { data, error } = await supabase
    .from("clients")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  if (error) throw error;
  return data;
}

export async function getClient(id: string) {
  const supabase = await createServerSupabaseClient();
  const { data, error } = await supabase.from("clients").select("*").eq("id", id).single();
  if (error) throw error;
  return data;
}

export async function createClient(formData: FormData) {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not authenticated");

  const { error } = await supabase.from("clients").insert({
    user_id: user.id,
    name: formData.get("name") as string,
    email: formData.get("email") as string,
    company: formData.get("company") as string,
    address: formData.get("address") as string,
    phone: formData.get("phone") as string,
    payment_terms_days: parseInt(formData.get("payment_terms_days") as string) || 30,
    notes: formData.get("notes") as string,
  });

  if (error) throw error;
  revalidatePath("/clients");
}

export async function updateClient(id: string, formData: FormData) {
  const supabase = await createServerSupabaseClient();
  const { error } = await supabase.from("clients").update({
    name: formData.get("name") as string,
    email: formData.get("email") as string,
    company: formData.get("company") as string,
    address: formData.get("address") as string,
    phone: formData.get("phone") as string,
    payment_terms_days: parseInt(formData.get("payment_terms_days") as string) || 30,
    notes: formData.get("notes") as string,
  }).eq("id", id);

  if (error) throw error;
  revalidatePath("/clients");
}

export async function deleteClient(id: string) {
  const supabase = await createServerSupabaseClient();
  const { error } = await supabase.from("clients").delete().eq("id", id);
  if (error) throw error;
  revalidatePath("/clients");
}
```

- [ ] **Step 2: Create client UI components**

Create `src/components/app/client-form.tsx` — a form with fields: name, email, company, address, phone, payment terms, notes. Uses `createClient` or `updateClient` server action.

Create `src/components/app/client-list.tsx` — a table displaying clients with columns: Name, Company, Email, Invoices count, Total billed, Actions (edit/delete).

- [ ] **Step 3: Create client pages**

Create `src/app/(app)/clients/page.tsx` — lists all clients using `getClients()`, renders `ClientList`.

Create `src/app/(app)/clients/new/page.tsx` — renders `ClientForm` for creating a new client.

Create `src/app/(app)/clients/[id]/page.tsx` — shows client detail + list of invoices for this client.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: client CRM — CRUD clients with server actions"
```

---

## Task 3: Invoice Persistence + Management

**Files:**
- Create: `src/lib/actions/invoices.ts`
- Create: `src/lib/utils/short-id.ts`
- Create: `src/components/app/invoice-list.tsx`
- Create: `src/components/app/invoice-status-badge.tsx`
- Create: `src/app/(app)/invoices/page.tsx`
- Create: `src/app/(app)/invoices/new/page.tsx`
- Create: `src/app/(app)/invoices/[id]/page.tsx`

- [ ] **Step 1: Create short ID utility**

Create `src/lib/utils/short-id.ts`:
```typescript
const CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789";

export function generateShortId(length = 8): string {
  let result = "";
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  for (let i = 0; i < length; i++) {
    result += CHARS[array[i] % CHARS.length];
  }
  return result;
}
```

- [ ] **Step 2: Create invoice server actions**

Create `src/lib/actions/invoices.ts`:
```typescript
"use server";

import { createServerSupabaseClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";
import { generateShortId } from "@/lib/utils/short-id";
import type { InvoiceData } from "@/lib/types/invoice";

export async function getInvoices(status?: string) {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not authenticated");

  let query = supabase
    .from("invoices")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  if (status && status !== "all") {
    query = query.eq("status", status);
  }

  const { data, error } = await query;
  if (error) throw error;
  return data;
}

export async function getInvoice(id: string) {
  const supabase = await createServerSupabaseClient();
  const { data, error } = await supabase.from("invoices").select("*").eq("id", id).single();
  if (error) throw error;
  return data;
}

export async function saveInvoice(invoiceData: InvoiceData, clientId?: string) {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not authenticated");

  const onlineLinkId = generateShortId();

  const { data, error } = await supabase.from("invoices").insert({
    user_id: user.id,
    client_id: clientId || null,
    invoice_number: invoiceData.invoiceNumber,
    status: "draft",
    document_type: "invoice",
    sender_name: invoiceData.senderName,
    sender_email: invoiceData.senderEmail,
    sender_address: invoiceData.senderAddress,
    sender_phone: invoiceData.senderPhone,
    client_name: invoiceData.clientName,
    client_email: invoiceData.clientEmail,
    client_address: invoiceData.clientAddress,
    client_company: invoiceData.clientCompany,
    items: invoiceData.items,
    subtotal: invoiceData.subtotal,
    tax_rate: invoiceData.taxRate,
    tax_amount: invoiceData.taxAmount,
    total: invoiceData.total,
    currency: invoiceData.currency,
    issue_date: invoiceData.issueDate,
    due_date: invoiceData.dueDate,
    payment_terms: invoiceData.paymentTerms,
    notes: invoiceData.notes,
    terms: invoiceData.terms,
    online_link_id: onlineLinkId,
  }).select().single();

  if (error) throw error;
  revalidatePath("/invoices");
  return data;
}

export async function updateInvoiceStatus(id: string, status: string) {
  const supabase = await createServerSupabaseClient();
  const updates: Record<string, unknown> = { status };
  if (status === "sent") updates.sent_at = new Date().toISOString();
  if (status === "paid") updates.paid_at = new Date().toISOString();

  const { error } = await supabase.from("invoices").update(updates).eq("id", id);
  if (error) throw error;
  revalidatePath("/invoices");
}

export async function deleteInvoice(id: string) {
  const supabase = await createServerSupabaseClient();
  const { error } = await supabase.from("invoices").delete().eq("id", id);
  if (error) throw error;
  revalidatePath("/invoices");
}
```

- [ ] **Step 3: Create invoice status badge**

Create `src/components/app/invoice-status-badge.tsx`:
```tsx
import { Badge } from "@/components/ui/badge";

const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  draft: { label: "Draft", variant: "secondary" },
  sent: { label: "Sent", variant: "outline" },
  viewed: { label: "Viewed", variant: "default" },
  paid: { label: "Paid", variant: "default" },
  overdue: { label: "Overdue", variant: "destructive" },
  cancelled: { label: "Cancelled", variant: "secondary" },
};

export function InvoiceStatusBadge({ status }: { status: string }) {
  const config = statusConfig[status] || statusConfig.draft;
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
```

- [ ] **Step 4: Create invoice list and pages**

Create `src/components/app/invoice-list.tsx` — table with columns: Invoice #, Client, Amount, Status (badge), Due Date, Actions.

Create `src/app/(app)/invoices/page.tsx` — invoice list with status filter tabs (All, Draft, Sent, Overdue, Paid).

Create `src/app/(app)/invoices/new/page.tsx` — reuses AIInput + InvoiceForm from Plan 1, but with a "Save" button that calls `saveInvoice`, plus a client dropdown to link to existing clients.

Create `src/app/(app)/invoices/[id]/page.tsx` — invoice detail view with edit, send, download, mark as paid, delete actions.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: invoice management — save, list, status tracking, CRUD"
```

---

## Task 4: Invoice Online Links + View Tracking

**Files:**
- Modify: `src/app/i/[id]/page.tsx`
- Create: `src/app/api/track/[id]/route.ts`
- Create: `src/components/invoice/send-dialog.tsx`

- [ ] **Step 1: Create public invoice view page**

Modify `src/app/i/[id]/page.tsx`:
```tsx
import { createServerSupabaseClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { InvoicePreview } from "@/components/invoice/invoice-preview";
import type { InvoiceData } from "@/lib/types/invoice";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function PublicInvoicePage({ params }: Props) {
  const { id } = await params;
  const supabase = await createServerSupabaseClient();

  const { data: invoice } = await supabase
    .from("invoices")
    .select("*")
    .eq("online_link_id", id)
    .single();

  if (!invoice) notFound();

  // Record view (fire and forget)
  await supabase.from("invoice_views").insert({
    invoice_id: invoice.id,
    viewer_ip_hash: "anonymous", // In production, hash the IP
    user_agent: "server",
  });

  // Update status to viewed if currently sent
  if (invoice.status === "sent") {
    await supabase.from("invoices")
      .update({ status: "viewed", viewed_at: new Date().toISOString() })
      .eq("id", invoice.id);
  }

  const invoiceData: InvoiceData = {
    senderName: invoice.sender_name || "",
    senderEmail: invoice.sender_email || "",
    senderAddress: invoice.sender_address || "",
    senderPhone: invoice.sender_phone || "",
    clientName: invoice.client_name || "",
    clientEmail: invoice.client_email || "",
    clientAddress: invoice.client_address || "",
    clientCompany: invoice.client_company,
    invoiceNumber: invoice.invoice_number,
    issueDate: invoice.issue_date,
    dueDate: invoice.due_date,
    paymentTerms: invoice.payment_terms || "",
    items: invoice.items as InvoiceData["items"],
    subtotal: invoice.subtotal,
    taxRate: invoice.tax_rate,
    taxAmount: invoice.tax_amount,
    total: invoice.total,
    currency: invoice.currency,
    notes: invoice.notes,
    terms: invoice.terms,
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="text-center mb-6">
        <p className="text-sm text-gray-500">Invoice from {invoice.sender_name}</p>
        <h1 className="text-2xl font-bold">{invoice.invoice_number}</h1>
        <p className="text-lg font-semibold text-blue-600 mt-1">
          Total: {invoice.currency} {invoice.total}
        </p>
      </div>
      <InvoicePreview data={invoiceData} template="modern" />
      {/* Future: Add Stripe/PayPal pay button here for Pro users */}
    </div>
  );
}
```

- [ ] **Step 2: Create send dialog**

Create `src/components/invoice/send-dialog.tsx` — a dialog that shows the shareable link (`/i/{short_id}`), copy button, and optional email send (for Pro users in Plan 3).

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: invoice online links — public view page with view tracking"
```

---

## Task 5: App Dashboard

**Files:**
- Create: `src/components/app/sidebar.tsx`
- Create: `src/components/app/dashboard-cards.tsx`
- Create: `src/app/(app)/layout.tsx`
- Modify: `src/app/(app)/dashboard/page.tsx`

- [ ] **Step 1: Create app sidebar**

Create `src/components/app/sidebar.tsx`:
```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, Users, LayoutDashboard, Settings, LogOut } from "lucide-react";
import { signOut } from "@/lib/actions/auth";

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/invoices", icon: FileText, label: "Invoices" },
  { href: "/clients", icon: Users, label: "Clients" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 border-r bg-gray-50 min-h-screen p-4 flex flex-col">
      <Link href="/" className="flex items-center gap-2 font-bold text-lg mb-8">
        <FileText className="h-5 w-5 text-blue-600" />
        InvoiceAgent
      </Link>
      <nav className="space-y-1 flex-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
              pathname.startsWith(item.href)
                ? "bg-blue-50 text-blue-700 font-medium"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </Link>
        ))}
      </nav>
      <button onClick={() => signOut()} className="flex items-center gap-3 px-3 py-2 text-sm text-gray-500 hover:text-gray-900">
        <LogOut className="h-4 w-4" /> Sign out
      </button>
    </aside>
  );
}
```

- [ ] **Step 2: Create dashboard cards**

Create `src/components/app/dashboard-cards.tsx`:
```tsx
import { FileText, Clock, AlertTriangle, CheckCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/lib/data/currencies";

interface DashboardStats {
  totalInvoices: number;
  totalAmount: number;
  outstandingAmount: number;
  overdueAmount: number;
  paidAmount: number;
  currency: string;
}

export function DashboardCards({ stats }: { stats: DashboardStats }) {
  const cards = [
    { title: "Total Invoices", value: stats.totalInvoices.toString(), icon: FileText, color: "text-blue-600" },
    { title: "Outstanding", value: formatCurrency(stats.outstandingAmount, stats.currency), icon: Clock, color: "text-yellow-600" },
    { title: "Overdue", value: formatCurrency(stats.overdueAmount, stats.currency), icon: AlertTriangle, color: "text-red-600" },
    { title: "Collected", value: formatCurrency(stats.paidAmount, stats.currency), icon: CheckCircle, color: "text-green-600" },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">{card.title}</CardTitle>
            <card.icon className={`h-4 w-4 ${card.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create app layout and dashboard page**

Create `src/app/(app)/layout.tsx`:
```tsx
import { Sidebar } from "@/components/app/sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
```

Update `src/app/(app)/dashboard/page.tsx` to fetch invoice stats and render `DashboardCards` + recent invoices list.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: app dashboard — sidebar, stats cards, authenticated layout"
```

---

## Summary

| Task | What it delivers | Estimated time |
|------|-----------------|---------------|
| 1. Authentication | Sign up/login with email + Google OAuth | 30 min |
| 2. Client CRM | CRUD clients, client list, client detail | 30 min |
| 3. Invoice Management | Save invoices, list, status tracking, CRUD | 40 min |
| 4. Invoice Links + Tracking | Public invoice view, view tracking, send dialog | 25 min |
| 5. App Dashboard | Sidebar, stats cards, authenticated layout | 25 min |
| **Total** | | **~2.5 hours** |
