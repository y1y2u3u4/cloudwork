# InvoiceAgent Plan 1: Foundation + AI Engine + pSEO

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the free-tier SEO acquisition engine — AI invoice generation, PDF export, document matrix (receipt/quote/estimate), and 200+ industry pSEO pages. Deployable to Vercel with Supabase backend ready for future paid features.

**Architecture:** Next.js 15 App Router with a (marketing) route group for all free/public pages (SSG/ISR) and a (app) route group stub for future authenticated features. AI generation via Supabase Edge Function calling Claude Haiku. PDF rendering via @react-pdf/renderer on the client. pSEO pages generated at build time from a JSON data file containing industry-specific content.

**Tech Stack:** Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, @react-pdf/renderer, Supabase (Auth + DB + Edge Functions), Vercel

**Project path:** `/Users/zhanggongqing/project/孵化项目/cloudwork/workspace/invoice-agent`

---

## File Structure

```
invoice-agent/
├── .env.local                          # Supabase + API keys
├── next.config.ts                      # Next.js config
├── tailwind.config.ts                  # Tailwind config
├── package.json
├── tsconfig.json
│
├── supabase/
│   ├── config.toml                     # Supabase project config
│   ├── migrations/
│   │   └── 001_initial_schema.sql      # Users, clients, invoices, documents tables
│   └── functions/
│       └── ai-generate/
│           └── index.ts                # Edge Function: Claude Haiku invoice generation
│
├── src/
│   ├── app/
│   │   ├── layout.tsx                  # Root layout (fonts, metadata, analytics)
│   │   ├── page.tsx                    # Homepage: AI Invoice Generator
│   │   ├── globals.css                 # Tailwind base styles
│   │   │
│   │   ├── (marketing)/               # Public pages (SSG)
│   │   │   ├── receipt-generator/
│   │   │   │   └── page.tsx            # Receipt generator page
│   │   │   ├── quote-generator/
│   │   │   │   └── page.tsx            # Quote generator page
│   │   │   ├── estimate-generator/
│   │   │   │   └── page.tsx            # Estimate generator page
│   │   │   └── invoice-template/
│   │   │       └── [industry]/
│   │   │           └── page.tsx        # pSEO industry template pages
│   │   │
│   │   ├── (app)/                      # Authenticated pages (stub for Plan 2+)
│   │   │   └── dashboard/
│   │   │       └── page.tsx            # Placeholder dashboard
│   │   │
│   │   ├── api/
│   │   │   └── ai/
│   │   │       └── generate/
│   │   │           └── route.ts        # API route: proxy to Supabase Edge Function
│   │   │
│   │   └── i/
│   │       └── [id]/
│   │           └── page.tsx            # Public invoice view page (future: tracking)
│   │
│   ├── components/
│   │   ├── ui/                         # shadcn/ui components (button, input, card, etc.)
│   │   ├── invoice/
│   │   │   ├── ai-input.tsx            # Natural language input with examples
│   │   │   ├── invoice-form.tsx        # Editable invoice form (pre-filled by AI)
│   │   │   ├── invoice-preview.tsx     # Live HTML preview of the invoice
│   │   │   ├── pdf-document.tsx        # @react-pdf/renderer PDF template
│   │   │   ├── pdf-download.tsx        # Download button with PDF generation
│   │   │   └── template-selector.tsx   # Template style picker
│   │   ├── document/
│   │   │   ├── receipt-form.tsx        # Receipt-specific form
│   │   │   ├── quote-form.tsx          # Quote-specific form
│   │   │   └── estimate-form.tsx       # Estimate-specific form
│   │   ├── layout/
│   │   │   ├── header.tsx              # Site header with nav
│   │   │   ├── footer.tsx              # Site footer with SEO links
│   │   │   └── cta-banner.tsx          # "Sign up free" / "Upgrade to Pro" banner
│   │   └── seo/
│   │       ├── faq-schema.tsx          # FAQ JSON-LD schema component
│   │       └── industry-content.tsx    # pSEO content section for industry pages
│   │
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts              # Browser Supabase client
│   │   │   └── server.ts              # Server Supabase client
│   │   ├── ai/
│   │   │   ├── generate-invoice.ts    # Client-side function to call AI API
│   │   │   └── prompts.ts            # System prompts and JSON schema for Claude
│   │   ├── pdf/
│   │   │   └── generate-pdf.ts        # PDF generation utility
│   │   ├── types/
│   │   │   └── invoice.ts             # TypeScript types: Invoice, InvoiceItem, Client, etc.
│   │   └── data/
│   │       ├── industries.ts          # 200+ industry definitions (name, slug, sample data, SEO content)
│   │       ├── currencies.ts          # Currency list with symbols and formatting
│   │       └── tax-rates.ts           # Tax rate presets by country/region
│   │
│   └── __tests__/
│       ├── lib/
│       │   ├── ai/generate-invoice.test.ts
│       │   └── pdf/generate-pdf.test.ts
│       └── components/
│           ├── invoice/ai-input.test.tsx
│           └── invoice/invoice-form.test.tsx
│
└── public/
    ├── og-image.png                    # Default Open Graph image
    └── favicon.ico
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `invoice-agent/` (entire project scaffold)
- Create: `package.json`, `tsconfig.json`, `next.config.ts`, `tailwind.config.ts`
- Create: `src/app/layout.tsx`, `src/app/page.tsx`, `src/app/globals.css`

- [ ] **Step 1: Create Next.js project**

```bash
cd "/Users/zhanggongqing/project/孵化项目/cloudwork/workspace"
npx create-next-app@latest invoice-agent --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
```

Expected: New `invoice-agent/` directory with Next.js 15 setup.

- [ ] **Step 2: Install dependencies**

```bash
cd "/Users/zhanggongqing/project/孵化项目/cloudwork/workspace/invoice-agent"
npm install @react-pdf/renderer @supabase/supabase-js @supabase/ssr lucide-react clsx tailwind-merge class-variance-authority
npm install -D @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom @types/jest ts-jest
```

- [ ] **Step 3: Initialize shadcn/ui**

```bash
npx shadcn@latest init -d
npx shadcn@latest add button input textarea card select label tabs badge separator sheet dialog dropdown-menu toast
```

- [ ] **Step 4: Create .env.local**

Create `.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
ANTHROPIC_API_KEY=your_anthropic_key
```

- [ ] **Step 5: Create TypeScript types**

Create `src/lib/types/invoice.ts`:
```typescript
export type DocumentType = "invoice" | "receipt" | "quote" | "estimate";

export interface InvoiceItem {
  description: string;
  quantity: number;
  rate: number;
  amount: number;
}

export interface InvoiceData {
  // Sender
  senderName: string;
  senderEmail: string;
  senderAddress: string;
  senderPhone: string;
  logoUrl?: string;

  // Client
  clientName: string;
  clientEmail: string;
  clientAddress: string;
  clientCompany?: string;

  // Invoice details
  invoiceNumber: string;
  issueDate: string;
  dueDate: string;
  paymentTerms: string;

  // Items
  items: InvoiceItem[];

  // Totals
  subtotal: number;
  taxRate: number;
  taxAmount: number;
  total: number;
  currency: string;

  // Notes
  notes?: string;
  terms?: string;
}

export interface ReceiptData {
  businessName: string;
  businessAddress: string;
  customerName?: string;
  receiptNumber: string;
  date: string;
  items: InvoiceItem[];
  subtotal: number;
  taxRate: number;
  taxAmount: number;
  total: number;
  paymentMethod: string;
  currency: string;
}

export interface QuoteData {
  senderName: string;
  senderEmail: string;
  senderAddress: string;
  clientName: string;
  clientEmail: string;
  clientAddress: string;
  quoteNumber: string;
  issueDate: string;
  validUntil: string;
  items: InvoiceItem[];
  subtotal: number;
  taxRate: number;
  taxAmount: number;
  total: number;
  currency: string;
  notes?: string;
}

export interface EstimateData {
  senderName: string;
  senderEmail: string;
  senderAddress: string;
  clientName: string;
  clientEmail: string;
  clientAddress: string;
  estimateNumber: string;
  issueDate: string;
  validUntil: string;
  items: InvoiceItem[];
  subtotal: number;
  taxRate: number;
  taxAmount: number;
  total: number;
  currency: string;
  notes?: string;
  scope?: string;
}

export type TemplateStyle = "modern" | "classic" | "minimal" | "bold" | "elegant";

export interface AIGenerateRequest {
  prompt: string;
  documentType: DocumentType;
}

export interface AIGenerateResponse {
  data: InvoiceData | ReceiptData | QuoteData | EstimateData;
  documentType: DocumentType;
}
```

- [ ] **Step 6: Create currency and tax data**

Create `src/lib/data/currencies.ts`:
```typescript
export interface Currency {
  code: string;
  symbol: string;
  name: string;
  locale: string;
}

export const currencies: Currency[] = [
  { code: "USD", symbol: "$", name: "US Dollar", locale: "en-US" },
  { code: "EUR", symbol: "€", name: "Euro", locale: "de-DE" },
  { code: "GBP", symbol: "£", name: "British Pound", locale: "en-GB" },
  { code: "CAD", symbol: "CA$", name: "Canadian Dollar", locale: "en-CA" },
  { code: "AUD", symbol: "A$", name: "Australian Dollar", locale: "en-AU" },
  { code: "JPY", symbol: "¥", name: "Japanese Yen", locale: "ja-JP" },
  { code: "INR", symbol: "₹", name: "Indian Rupee", locale: "en-IN" },
  { code: "BRL", symbol: "R$", name: "Brazilian Real", locale: "pt-BR" },
  { code: "MXN", symbol: "MX$", name: "Mexican Peso", locale: "es-MX" },
  { code: "CHF", symbol: "CHF", name: "Swiss Franc", locale: "de-CH" },
];

export function formatCurrency(amount: number, currencyCode: string): string {
  const currency = currencies.find((c) => c.code === currencyCode) || currencies[0];
  return new Intl.NumberFormat(currency.locale, {
    style: "currency",
    currency: currency.code,
  }).format(amount);
}
```

Create `src/lib/data/tax-rates.ts`:
```typescript
export interface TaxPreset {
  country: string;
  name: string;
  rate: number;
  label: string;
}

export const taxPresets: TaxPreset[] = [
  { country: "US", name: "No Tax", rate: 0, label: "None" },
  { country: "US", name: "US Average Sales Tax", rate: 7.12, label: "Sales Tax" },
  { country: "US", name: "California", rate: 7.25, label: "CA Sales Tax" },
  { country: "US", name: "New York", rate: 8.0, label: "NY Sales Tax" },
  { country: "US", name: "Texas", rate: 6.25, label: "TX Sales Tax" },
  { country: "UK", name: "UK VAT Standard", rate: 20, label: "VAT" },
  { country: "UK", name: "UK VAT Reduced", rate: 5, label: "VAT (Reduced)" },
  { country: "EU", name: "EU VAT Standard", rate: 21, label: "VAT" },
  { country: "DE", name: "Germany VAT", rate: 19, label: "MwSt" },
  { country: "FR", name: "France VAT", rate: 20, label: "TVA" },
  { country: "AU", name: "Australia GST", rate: 10, label: "GST" },
  { country: "CA", name: "Canada HST (Ontario)", rate: 13, label: "HST" },
  { country: "CA", name: "Canada GST", rate: 5, label: "GST" },
  { country: "IN", name: "India GST", rate: 18, label: "GST" },
  { country: "JP", name: "Japan Consumption Tax", rate: 10, label: "消費税" },
];
```

- [ ] **Step 7: Verify dev server starts**

```bash
cd "/Users/zhanggongqing/project/孵化项目/cloudwork/workspace/invoice-agent"
npm run dev
```

Expected: Server starts on localhost:3000, default Next.js page loads.

- [ ] **Step 8: Commit**

```bash
git init
git add -A
git commit -m "feat: project scaffold — Next.js 15 + Tailwind + shadcn/ui + types"
```

---

## Task 2: Supabase Setup + Database Schema

**Files:**
- Create: `supabase/migrations/001_initial_schema.sql`
- Create: `src/lib/supabase/client.ts`
- Create: `src/lib/supabase/server.ts`

- [ ] **Step 1: Initialize Supabase**

```bash
npx supabase init
```

- [ ] **Step 2: Create initial migration**

Create `supabase/migrations/001_initial_schema.sql`:
```sql
-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Users profile (extends Supabase Auth)
create table public.profiles (
  id uuid references auth.users on delete cascade primary key,
  email text not null,
  full_name text,
  company_name text,
  company_address text,
  phone text,
  logo_url text,
  default_currency text default 'USD',
  default_tax_rate numeric(5,2) default 0,
  default_payment_terms text default 'Net 30',
  plan text default 'free' check (plan in ('free', 'pro')),
  stripe_customer_id text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Clients
create table public.clients (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  email text,
  company text,
  address text,
  phone text,
  payment_terms_days integer default 30,
  notes text,
  tags text[] default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Invoices
create table public.invoices (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  client_id uuid references public.clients(id) on delete set null,
  invoice_number text not null,
  status text default 'draft' check (status in ('draft', 'sent', 'viewed', 'paid', 'overdue', 'cancelled')),
  document_type text default 'invoice' check (document_type in ('invoice', 'receipt', 'quote', 'estimate', 'credit_note')),
  
  -- Sender info (snapshot at creation time)
  sender_name text,
  sender_email text,
  sender_address text,
  sender_phone text,
  logo_url text,
  
  -- Client info (snapshot)
  client_name text,
  client_email text,
  client_address text,
  client_company text,
  
  -- Financial
  items jsonb not null default '[]',
  subtotal numeric(12,2) not null default 0,
  tax_rate numeric(5,2) default 0,
  tax_amount numeric(12,2) default 0,
  total numeric(12,2) not null default 0,
  currency text default 'USD',
  
  -- Dates
  issue_date date default current_date,
  due_date date,
  
  -- Payment
  payment_terms text,
  payment_method text,
  
  -- Online link
  online_link_id text unique,
  
  -- Recurring
  recurring_config jsonb,
  
  -- Notes
  notes text,
  terms text,
  
  -- Tracking
  sent_at timestamptz,
  viewed_at timestamptz,
  paid_at timestamptz,
  
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Contracts
create table public.contracts (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  client_id uuid references public.clients(id) on delete set null,
  title text not null,
  content_html text,
  status text default 'draft' check (status in ('draft', 'sent', 'signed', 'expired', 'cancelled')),
  signed_at timestamptz,
  signature_url text,
  deposit_required boolean default false,
  deposit_percentage numeric(5,2),
  deposit_amount numeric(12,2),
  linked_invoice_id uuid references public.invoices(id) on delete set null,
  sent_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Collection actions (AI reminder log)
create table public.collection_actions (
  id uuid default uuid_generate_v4() primary key,
  invoice_id uuid references public.invoices(id) on delete cascade not null,
  action_type text not null check (action_type in ('reminder', 'follow_up', 'final_notice', 'manual')),
  escalation_level integer default 1,
  email_subject text,
  email_body text,
  sent_at timestamptz,
  opened_at timestamptz,
  result text check (result in ('pending', 'opened', 'paid', 'ignored')),
  created_at timestamptz default now()
);

-- Invoice views (tracking pixel)
create table public.invoice_views (
  id uuid default uuid_generate_v4() primary key,
  invoice_id uuid references public.invoices(id) on delete cascade not null,
  viewer_ip_hash text,
  user_agent text,
  viewed_at timestamptz default now()
);

-- Row Level Security
alter table public.profiles enable row level security;
alter table public.clients enable row level security;
alter table public.invoices enable row level security;
alter table public.contracts enable row level security;
alter table public.collection_actions enable row level security;
alter table public.invoice_views enable row level security;

-- Profiles: users can only read/update their own
create policy "Users can view own profile" on public.profiles for select using (auth.uid() = id);
create policy "Users can update own profile" on public.profiles for update using (auth.uid() = id);

-- Clients: users can CRUD their own
create policy "Users can view own clients" on public.clients for select using (auth.uid() = user_id);
create policy "Users can insert own clients" on public.clients for insert with check (auth.uid() = user_id);
create policy "Users can update own clients" on public.clients for update using (auth.uid() = user_id);
create policy "Users can delete own clients" on public.clients for delete using (auth.uid() = user_id);

-- Invoices: users can CRUD their own
create policy "Users can view own invoices" on public.invoices for select using (auth.uid() = user_id);
create policy "Users can insert own invoices" on public.invoices for insert with check (auth.uid() = user_id);
create policy "Users can update own invoices" on public.invoices for update using (auth.uid() = user_id);
create policy "Users can delete own invoices" on public.invoices for delete using (auth.uid() = user_id);

-- Public invoice viewing (for online links)
create policy "Anyone can view invoices by link" on public.invoices for select using (online_link_id is not null);

-- Invoice views: anyone can insert (tracking), owner can read
create policy "Anyone can track views" on public.invoice_views for insert with check (true);
create policy "Invoice owner can view tracking" on public.invoice_views for select using (
  exists (select 1 from public.invoices where invoices.id = invoice_views.invoice_id and invoices.user_id = auth.uid())
);

-- Contracts: users can CRUD their own
create policy "Users can view own contracts" on public.contracts for select using (auth.uid() = user_id);
create policy "Users can insert own contracts" on public.contracts for insert with check (auth.uid() = user_id);
create policy "Users can update own contracts" on public.contracts for update using (auth.uid() = user_id);
create policy "Users can delete own contracts" on public.contracts for delete using (auth.uid() = user_id);

-- Collection actions: users can view for their invoices
create policy "Users can view own collection actions" on public.collection_actions for select using (
  exists (select 1 from public.invoices where invoices.id = collection_actions.invoice_id and invoices.user_id = auth.uid())
);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, new.raw_user_meta_data->>'full_name');
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Updated_at trigger
create or replace function public.update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger profiles_updated_at before update on public.profiles for each row execute procedure public.update_updated_at();
create trigger clients_updated_at before update on public.clients for each row execute procedure public.update_updated_at();
create trigger invoices_updated_at before update on public.invoices for each row execute procedure public.update_updated_at();
create trigger contracts_updated_at before update on public.contracts for each row execute procedure public.update_updated_at();
```

- [ ] **Step 3: Create Supabase client utilities**

Create `src/lib/supabase/client.ts`:
```typescript
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

Create `src/lib/supabase/server.ts`:
```typescript
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createServerSupabaseClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        },
      },
    }
  );
}
```

- [ ] **Step 4: Apply migration to Supabase project**

```bash
npx supabase db push
```

Or apply via Supabase dashboard SQL editor if using hosted project.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Supabase setup — schema, RLS policies, client utilities"
```

---

## Task 3: AI Generation Engine

**Files:**
- Create: `src/lib/ai/prompts.ts`
- Create: `src/lib/ai/generate-invoice.ts`
- Create: `src/app/api/ai/generate/route.ts`
- Create: `supabase/functions/ai-generate/index.ts` (alternative)

- [ ] **Step 1: Create AI system prompts**

Create `src/lib/ai/prompts.ts`:
```typescript
import type { DocumentType } from "@/lib/types/invoice";

const INVOICE_SCHEMA = `{
  "senderName": "string (sender/freelancer full name)",
  "senderEmail": "string (sender email, or empty)",
  "senderAddress": "string (sender address, or empty)",
  "senderPhone": "string (sender phone, or empty)",
  "clientName": "string (client/company name)",
  "clientEmail": "string (client email, or empty)",
  "clientAddress": "string (client address, or empty)",
  "clientCompany": "string (client company name, or same as clientName)",
  "invoiceNumber": "string (e.g. INV-001)",
  "issueDate": "string (YYYY-MM-DD, today if not specified)",
  "dueDate": "string (YYYY-MM-DD, calculated from payment terms)",
  "paymentTerms": "string (e.g. Net 30, Due on Receipt)",
  "items": [{"description": "string", "quantity": number, "rate": number, "amount": number}],
  "subtotal": number,
  "taxRate": number (percentage, 0 if not mentioned),
  "taxAmount": number,
  "total": number,
  "currency": "string (3-letter code, USD if not specified)",
  "notes": "string (optional notes)",
  "terms": "string (optional payment terms text)"
}`;

const RECEIPT_SCHEMA = `{
  "businessName": "string",
  "businessAddress": "string (or empty)",
  "customerName": "string (or empty)",
  "receiptNumber": "string (e.g. REC-001)",
  "date": "string (YYYY-MM-DD)",
  "items": [{"description": "string", "quantity": number, "rate": number, "amount": number}],
  "subtotal": number,
  "taxRate": number,
  "taxAmount": number,
  "total": number,
  "paymentMethod": "string (e.g. Cash, Credit Card, Bank Transfer)",
  "currency": "string (3-letter code)"
}`;

const QUOTE_SCHEMA = `{
  "senderName": "string",
  "senderEmail": "string (or empty)",
  "senderAddress": "string (or empty)",
  "clientName": "string",
  "clientEmail": "string (or empty)",
  "clientAddress": "string (or empty)",
  "quoteNumber": "string (e.g. QUO-001)",
  "issueDate": "string (YYYY-MM-DD)",
  "validUntil": "string (YYYY-MM-DD, 30 days from issue if not specified)",
  "items": [{"description": "string", "quantity": number, "rate": number, "amount": number}],
  "subtotal": number,
  "taxRate": number,
  "taxAmount": number,
  "total": number,
  "currency": "string",
  "notes": "string (optional)"
}`;

const ESTIMATE_SCHEMA = `{
  "senderName": "string",
  "senderEmail": "string (or empty)",
  "senderAddress": "string (or empty)",
  "clientName": "string",
  "clientEmail": "string (or empty)",
  "clientAddress": "string (or empty)",
  "estimateNumber": "string (e.g. EST-001)",
  "issueDate": "string (YYYY-MM-DD)",
  "validUntil": "string (YYYY-MM-DD)",
  "items": [{"description": "string", "quantity": number, "rate": number, "amount": number}],
  "subtotal": number,
  "taxRate": number,
  "taxAmount": number,
  "total": number,
  "currency": "string",
  "notes": "string (optional)",
  "scope": "string (project scope description, optional)"
}`;

const schemas: Record<DocumentType, string> = {
  invoice: INVOICE_SCHEMA,
  receipt: RECEIPT_SCHEMA,
  quote: QUOTE_SCHEMA,
  estimate: ESTIMATE_SCHEMA,
};

export function getSystemPrompt(documentType: DocumentType): string {
  const today = new Date().toISOString().split("T")[0];
  return `You are an AI assistant that extracts structured ${documentType} data from natural language descriptions.

Today's date is ${today}.

The user will describe a ${documentType} in plain English. Extract all relevant information and return a JSON object matching this exact schema:

${schemas[documentType]}

Rules:
- Return ONLY valid JSON, no markdown, no explanation, no code fences.
- Calculate all amounts correctly: amount = quantity * rate, subtotal = sum of amounts, taxAmount = subtotal * taxRate / 100, total = subtotal + taxAmount.
- If currency is not specified, default to USD.
- If tax is not mentioned, set taxRate to 0.
- If payment terms are not specified, default to "Net 30" for invoices, "Due on Receipt" for receipts.
- For dates, use YYYY-MM-DD format. If not specified, use today (${today}).
- For due dates, calculate from issue date + payment terms (e.g. Net 30 = 30 days).
- Generate a reasonable document number if not specified.
- If information is missing, use empty strings for text fields, not null.
- Be generous in interpretation — if the user says "3 hours at 150", that means quantity=3, rate=150.`;
}
```

- [ ] **Step 2: Create API route**

Create `src/app/api/ai/generate/route.ts`:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { getSystemPrompt } from "@/lib/ai/prompts";
import type { DocumentType } from "@/lib/types/invoice";

export async function POST(request: NextRequest) {
  const { prompt, documentType = "invoice" } = (await request.json()) as {
    prompt: string;
    documentType?: DocumentType;
  };

  if (!prompt || prompt.trim().length < 5) {
    return NextResponse.json(
      { error: "Please provide a description of your invoice." },
      { status: 400 }
    );
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { error: "AI service not configured." },
      { status: 500 }
    );
  }

  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 1024,
        system: getSystemPrompt(documentType),
        messages: [{ role: "user", content: prompt }],
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Claude API error:", errorData);
      return NextResponse.json(
        { error: "AI generation failed. Please try again." },
        { status: 502 }
      );
    }

    const result = await response.json();
    const text = result.content[0]?.text;

    if (!text) {
      return NextResponse.json(
        { error: "Empty response from AI." },
        { status: 502 }
      );
    }

    const data = JSON.parse(text);

    return NextResponse.json({ data, documentType });
  } catch (error) {
    console.error("AI generation error:", error);
    return NextResponse.json(
      { error: "Failed to parse AI response. Please try again." },
      { status: 500 }
    );
  }
}
```

- [ ] **Step 3: Create client-side generation function**

Create `src/lib/ai/generate-invoice.ts`:
```typescript
import type { AIGenerateRequest, AIGenerateResponse } from "@/lib/types/invoice";

export async function generateFromPrompt(
  request: AIGenerateRequest
): Promise<AIGenerateResponse> {
  const response = await fetch("/api/ai/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Generation failed");
  }

  return response.json();
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: AI generation engine — Claude Haiku prompts + API route"
```

---

## Task 4: Invoice Form + Live Preview

**Files:**
- Create: `src/components/invoice/ai-input.tsx`
- Create: `src/components/invoice/invoice-form.tsx`
- Create: `src/components/invoice/invoice-preview.tsx`
- Create: `src/components/invoice/template-selector.tsx`

- [ ] **Step 1: Create AI input component**

Create `src/components/invoice/ai-input.tsx`:
```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, Loader2 } from "lucide-react";
import { generateFromPrompt } from "@/lib/ai/generate-invoice";
import type { DocumentType, InvoiceData } from "@/lib/types/invoice";

const EXAMPLES = [
  "I did 3 hours of consulting for Acme Corp at $150/hr, net 30",
  "Web design project for Sarah Johnson, $2,500 total, due in 14 days",
  "Photography shoot — 4 hours at $200/hr plus $150 travel expenses for Blue Sky Events",
  "Monthly retainer for social media management, $1,500/month for TechStart Inc",
];

interface AIInputProps {
  documentType: DocumentType;
  onGenerated: (data: InvoiceData) => void;
}

export function AIInput({ documentType, onGenerated }: AIInputProps) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate() {
    if (!prompt.trim()) return;
    setLoading(true);
    setError("");

    try {
      const result = await generateFromPrompt({ prompt, documentType });
      onGenerated(result.data as InvoiceData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium text-gray-700 mb-1 block">
          Describe your {documentType} in plain English
        </label>
        <Textarea
          placeholder={EXAMPLES[Math.floor(Math.random() * EXAMPLES.length)]}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          className="resize-none"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              handleGenerate();
            }
          }}
        />
      </div>

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      <Button onClick={handleGenerate} disabled={loading || !prompt.trim()} className="w-full">
        {loading ? (
          <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating...</>
        ) : (
          <><Sparkles className="mr-2 h-4 w-4" /> Generate {documentType}</>
        )}
      </Button>

      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((example, i) => (
          <button
            key={i}
            onClick={() => setPrompt(example)}
            className="text-xs text-gray-500 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-full px-3 py-1 transition-colors"
          >
            {example.slice(0, 50)}...
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create invoice form component**

Create `src/components/invoice/invoice-form.tsx`:
```tsx
"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2 } from "lucide-react";
import { currencies } from "@/lib/data/currencies";
import { taxPresets } from "@/lib/data/tax-rates";
import type { InvoiceData, InvoiceItem } from "@/lib/types/invoice";

interface InvoiceFormProps {
  data: InvoiceData;
  onChange: (data: InvoiceData) => void;
}

export function InvoiceForm({ data, onChange }: InvoiceFormProps) {
  function updateField<K extends keyof InvoiceData>(key: K, value: InvoiceData[K]) {
    onChange({ ...data, [key]: value });
  }

  function updateItem(index: number, field: keyof InvoiceItem, value: string | number) {
    const items = [...data.items];
    items[index] = { ...items[index], [field]: value };
    if (field === "quantity" || field === "rate") {
      items[index].amount = Number(items[index].quantity) * Number(items[index].rate);
    }
    const subtotal = items.reduce((sum, item) => sum + item.amount, 0);
    const taxAmount = subtotal * (data.taxRate / 100);
    onChange({ ...data, items, subtotal, taxAmount, total: subtotal + taxAmount });
  }

  function addItem() {
    onChange({
      ...data,
      items: [...data.items, { description: "", quantity: 1, rate: 0, amount: 0 }],
    });
  }

  function removeItem(index: number) {
    const items = data.items.filter((_, i) => i !== index);
    const subtotal = items.reduce((sum, item) => sum + item.amount, 0);
    const taxAmount = subtotal * (data.taxRate / 100);
    onChange({ ...data, items, subtotal, taxAmount, total: subtotal + taxAmount });
  }

  function handleTaxRateChange(rate: string) {
    const taxRate = parseFloat(rate);
    const taxAmount = data.subtotal * (taxRate / 100);
    onChange({ ...data, taxRate, taxAmount, total: data.subtotal + taxAmount });
  }

  return (
    <div className="space-y-6">
      {/* From / To */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-3">
          <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wider">From</h3>
          <div><Label>Name</Label><Input value={data.senderName} onChange={(e) => updateField("senderName", e.target.value)} /></div>
          <div><Label>Email</Label><Input type="email" value={data.senderEmail} onChange={(e) => updateField("senderEmail", e.target.value)} /></div>
          <div><Label>Address</Label><Input value={data.senderAddress} onChange={(e) => updateField("senderAddress", e.target.value)} /></div>
        </div>
        <div className="space-y-3">
          <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wider">Bill To</h3>
          <div><Label>Client Name</Label><Input value={data.clientName} onChange={(e) => updateField("clientName", e.target.value)} /></div>
          <div><Label>Email</Label><Input type="email" value={data.clientEmail} onChange={(e) => updateField("clientEmail", e.target.value)} /></div>
          <div><Label>Address</Label><Input value={data.clientAddress} onChange={(e) => updateField("clientAddress", e.target.value)} /></div>
        </div>
      </div>

      {/* Invoice Details */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div><Label>Invoice #</Label><Input value={data.invoiceNumber} onChange={(e) => updateField("invoiceNumber", e.target.value)} /></div>
        <div><Label>Issue Date</Label><Input type="date" value={data.issueDate} onChange={(e) => updateField("issueDate", e.target.value)} /></div>
        <div><Label>Due Date</Label><Input type="date" value={data.dueDate} onChange={(e) => updateField("dueDate", e.target.value)} /></div>
        <div>
          <Label>Currency</Label>
          <Select value={data.currency} onValueChange={(v) => updateField("currency", v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {currencies.map((c) => (
                <SelectItem key={c.code} value={c.code}>{c.symbol} {c.code}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Line Items */}
      <div>
        <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wider mb-3">Items</h3>
        <div className="space-y-2">
          {data.items.map((item, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-end">
              <div className="col-span-5">
                {i === 0 && <Label className="text-xs">Description</Label>}
                <Input value={item.description} onChange={(e) => updateItem(i, "description", e.target.value)} />
              </div>
              <div className="col-span-2">
                {i === 0 && <Label className="text-xs">Qty</Label>}
                <Input type="number" min={0} value={item.quantity} onChange={(e) => updateItem(i, "quantity", parseFloat(e.target.value) || 0)} />
              </div>
              <div className="col-span-2">
                {i === 0 && <Label className="text-xs">Rate</Label>}
                <Input type="number" min={0} step={0.01} value={item.rate} onChange={(e) => updateItem(i, "rate", parseFloat(e.target.value) || 0)} />
              </div>
              <div className="col-span-2">
                {i === 0 && <Label className="text-xs">Amount</Label>}
                <Input value={item.amount.toFixed(2)} disabled className="bg-gray-50" />
              </div>
              <div className="col-span-1">
                <Button variant="ghost" size="icon" onClick={() => removeItem(i)} disabled={data.items.length <= 1}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
        <Button variant="outline" size="sm" onClick={addItem} className="mt-2">
          <Plus className="h-4 w-4 mr-1" /> Add Item
        </Button>
      </div>

      {/* Tax */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <Label>Tax Preset</Label>
          <Select onValueChange={handleTaxRateChange}>
            <SelectTrigger><SelectValue placeholder="Select tax rate" /></SelectTrigger>
            <SelectContent>
              {taxPresets.map((t, i) => (
                <SelectItem key={i} value={t.rate.toString()}>{t.name} ({t.rate}%)</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Tax Rate (%)</Label>
          <Input type="number" min={0} max={100} step={0.01} value={data.taxRate} onChange={(e) => handleTaxRateChange(e.target.value)} />
        </div>
      </div>

      {/* Notes */}
      <div>
        <Label>Notes</Label>
        <Textarea value={data.notes || ""} onChange={(e) => updateField("notes", e.target.value)} rows={2} placeholder="Thank you for your business!" />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create live preview component**

Create `src/components/invoice/invoice-preview.tsx`:
```tsx
"use client";

import { formatCurrency } from "@/lib/data/currencies";
import type { InvoiceData, TemplateStyle } from "@/lib/types/invoice";

interface InvoicePreviewProps {
  data: InvoiceData;
  template?: TemplateStyle;
}

export function InvoicePreview({ data, template = "modern" }: InvoicePreviewProps) {
  const accentColor = {
    modern: "#2563eb",
    classic: "#1f2937",
    minimal: "#6b7280",
    bold: "#dc2626",
    elegant: "#7c3aed",
  }[template];

  return (
    <div className="bg-white border rounded-lg shadow-sm p-8 text-sm" style={{ minHeight: 600 }}>
      {/* Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: accentColor }}>INVOICE</h1>
          <p className="text-gray-500 mt-1">{data.invoiceNumber}</p>
        </div>
        <div className="text-right">
          <p className="font-semibold">{data.senderName}</p>
          {data.senderEmail && <p className="text-gray-500">{data.senderEmail}</p>}
          {data.senderAddress && <p className="text-gray-500">{data.senderAddress}</p>}
        </div>
      </div>

      {/* Bill To + Dates */}
      <div className="grid grid-cols-2 gap-8 mb-8">
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase mb-1">Bill To</p>
          <p className="font-semibold">{data.clientName}</p>
          {data.clientCompany && data.clientCompany !== data.clientName && (
            <p className="text-gray-600">{data.clientCompany}</p>
          )}
          {data.clientEmail && <p className="text-gray-500">{data.clientEmail}</p>}
          {data.clientAddress && <p className="text-gray-500">{data.clientAddress}</p>}
        </div>
        <div className="text-right space-y-1">
          <div><span className="text-gray-400 text-xs">Issue Date:</span> <span>{data.issueDate}</span></div>
          <div><span className="text-gray-400 text-xs">Due Date:</span> <span>{data.dueDate}</span></div>
          <div><span className="text-gray-400 text-xs">Terms:</span> <span>{data.paymentTerms}</span></div>
        </div>
      </div>

      {/* Items Table */}
      <table className="w-full mb-8">
        <thead>
          <tr className="border-b-2" style={{ borderColor: accentColor }}>
            <th className="text-left py-2 text-xs font-semibold text-gray-500 uppercase">Description</th>
            <th className="text-right py-2 text-xs font-semibold text-gray-500 uppercase w-20">Qty</th>
            <th className="text-right py-2 text-xs font-semibold text-gray-500 uppercase w-24">Rate</th>
            <th className="text-right py-2 text-xs font-semibold text-gray-500 uppercase w-28">Amount</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((item, i) => (
            <tr key={i} className="border-b border-gray-100">
              <td className="py-3">{item.description}</td>
              <td className="py-3 text-right">{item.quantity}</td>
              <td className="py-3 text-right">{formatCurrency(item.rate, data.currency)}</td>
              <td className="py-3 text-right">{formatCurrency(item.amount, data.currency)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Totals */}
      <div className="flex justify-end">
        <div className="w-64 space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-500">Subtotal</span>
            <span>{formatCurrency(data.subtotal, data.currency)}</span>
          </div>
          {data.taxRate > 0 && (
            <div className="flex justify-between">
              <span className="text-gray-500">Tax ({data.taxRate}%)</span>
              <span>{formatCurrency(data.taxAmount, data.currency)}</span>
            </div>
          )}
          <div className="flex justify-between font-bold text-lg border-t-2 pt-2" style={{ borderColor: accentColor }}>
            <span>Total</span>
            <span style={{ color: accentColor }}>{formatCurrency(data.total, data.currency)}</span>
          </div>
        </div>
      </div>

      {/* Notes */}
      {data.notes && (
        <div className="mt-8 pt-4 border-t border-gray-100">
          <p className="text-xs font-semibold text-gray-400 uppercase mb-1">Notes</p>
          <p className="text-gray-600">{data.notes}</p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Create template selector**

Create `src/components/invoice/template-selector.tsx`:
```tsx
"use client";

import type { TemplateStyle } from "@/lib/types/invoice";

interface TemplateSelectorProps {
  selected: TemplateStyle;
  onSelect: (style: TemplateStyle) => void;
}

const templates: { style: TemplateStyle; name: string; color: string }[] = [
  { style: "modern", name: "Modern", color: "#2563eb" },
  { style: "classic", name: "Classic", color: "#1f2937" },
  { style: "minimal", name: "Minimal", color: "#6b7280" },
  { style: "bold", name: "Bold", color: "#dc2626" },
  { style: "elegant", name: "Elegant", color: "#7c3aed" },
];

export function TemplateSelector({ selected, onSelect }: TemplateSelectorProps) {
  return (
    <div className="flex gap-2">
      {templates.map((t) => (
        <button
          key={t.style}
          onClick={() => onSelect(t.style)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
            selected === t.style
              ? "bg-gray-900 text-white shadow-sm"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          <span className="w-3 h-3 rounded-full" style={{ backgroundColor: t.color }} />
          {t.name}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: invoice form — AI input, editable form, live preview, template selector"
```

---

## Task 5: PDF Generation + Download

**Files:**
- Create: `src/components/invoice/pdf-document.tsx`
- Create: `src/components/invoice/pdf-download.tsx`

- [ ] **Step 1: Create PDF document template**

Create `src/components/invoice/pdf-document.tsx`:
```tsx
import { Document, Page, View, Text, StyleSheet, Font } from "@react-pdf/renderer";
import type { InvoiceData } from "@/lib/types/invoice";
import { formatCurrency } from "@/lib/data/currencies";

const styles = StyleSheet.create({
  page: { padding: 40, fontSize: 10, fontFamily: "Helvetica", color: "#1f2937" },
  header: { flexDirection: "row", justifyContent: "space-between", marginBottom: 30 },
  title: { fontSize: 24, fontWeight: "bold", color: "#2563eb" },
  invoiceNumber: { fontSize: 10, color: "#6b7280", marginTop: 4 },
  senderBlock: { textAlign: "right" },
  senderName: { fontWeight: "bold", fontSize: 11 },
  grayText: { color: "#6b7280", marginTop: 2 },
  billSection: { flexDirection: "row", justifyContent: "space-between", marginBottom: 30 },
  sectionLabel: { fontSize: 8, fontWeight: "bold", color: "#9ca3af", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 },
  clientName: { fontWeight: "bold", fontSize: 11 },
  dateRow: { flexDirection: "row", justifyContent: "flex-end", marginBottom: 2 },
  dateLabel: { color: "#9ca3af", fontSize: 8, marginRight: 8 },
  table: { marginBottom: 30 },
  tableHeader: { flexDirection: "row", borderBottomWidth: 2, borderBottomColor: "#2563eb", paddingBottom: 6, marginBottom: 4 },
  tableHeaderCell: { fontSize: 8, fontWeight: "bold", color: "#6b7280", textTransform: "uppercase" },
  tableRow: { flexDirection: "row", paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: "#f3f4f6" },
  descCol: { flex: 1 },
  qtyCol: { width: 50, textAlign: "right" },
  rateCol: { width: 70, textAlign: "right" },
  amountCol: { width: 80, textAlign: "right" },
  totalsBlock: { alignItems: "flex-end" },
  totalRow: { flexDirection: "row", justifyContent: "space-between", width: 200, marginBottom: 4 },
  totalLabel: { color: "#6b7280" },
  totalLine: { flexDirection: "row", justifyContent: "space-between", width: 200, borderTopWidth: 2, borderTopColor: "#2563eb", paddingTop: 6 },
  totalAmount: { fontWeight: "bold", fontSize: 14, color: "#2563eb" },
  totalText: { fontWeight: "bold", fontSize: 14 },
  notes: { marginTop: 30, paddingTop: 12, borderTopWidth: 1, borderTopColor: "#f3f4f6" },
  notesLabel: { fontSize: 8, fontWeight: "bold", color: "#9ca3af", textTransform: "uppercase", marginBottom: 4 },
  notesText: { color: "#4b5563" },
});

interface PDFDocumentProps {
  data: InvoiceData;
}

export function InvoicePDFDocument({ data }: PDFDocumentProps) {
  return (
    <Document>
      <Page size="A4" style={styles.page}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>INVOICE</Text>
            <Text style={styles.invoiceNumber}>{data.invoiceNumber}</Text>
          </View>
          <View style={styles.senderBlock}>
            <Text style={styles.senderName}>{data.senderName}</Text>
            {data.senderEmail ? <Text style={styles.grayText}>{data.senderEmail}</Text> : null}
            {data.senderAddress ? <Text style={styles.grayText}>{data.senderAddress}</Text> : null}
          </View>
        </View>

        {/* Bill To + Dates */}
        <View style={styles.billSection}>
          <View>
            <Text style={styles.sectionLabel}>Bill To</Text>
            <Text style={styles.clientName}>{data.clientName}</Text>
            {data.clientEmail ? <Text style={styles.grayText}>{data.clientEmail}</Text> : null}
            {data.clientAddress ? <Text style={styles.grayText}>{data.clientAddress}</Text> : null}
          </View>
          <View>
            <View style={styles.dateRow}><Text style={styles.dateLabel}>Issue Date:</Text><Text>{data.issueDate}</Text></View>
            <View style={styles.dateRow}><Text style={styles.dateLabel}>Due Date:</Text><Text>{data.dueDate}</Text></View>
            <View style={styles.dateRow}><Text style={styles.dateLabel}>Terms:</Text><Text>{data.paymentTerms}</Text></View>
          </View>
        </View>

        {/* Items Table */}
        <View style={styles.table}>
          <View style={styles.tableHeader}>
            <Text style={[styles.tableHeaderCell, styles.descCol]}>Description</Text>
            <Text style={[styles.tableHeaderCell, styles.qtyCol]}>Qty</Text>
            <Text style={[styles.tableHeaderCell, styles.rateCol]}>Rate</Text>
            <Text style={[styles.tableHeaderCell, styles.amountCol]}>Amount</Text>
          </View>
          {data.items.map((item, i) => (
            <View key={i} style={styles.tableRow}>
              <Text style={styles.descCol}>{item.description}</Text>
              <Text style={styles.qtyCol}>{item.quantity}</Text>
              <Text style={styles.rateCol}>{formatCurrency(item.rate, data.currency)}</Text>
              <Text style={styles.amountCol}>{formatCurrency(item.amount, data.currency)}</Text>
            </View>
          ))}
        </View>

        {/* Totals */}
        <View style={styles.totalsBlock}>
          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Subtotal</Text>
            <Text>{formatCurrency(data.subtotal, data.currency)}</Text>
          </View>
          {data.taxRate > 0 && (
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Tax ({data.taxRate}%)</Text>
              <Text>{formatCurrency(data.taxAmount, data.currency)}</Text>
            </View>
          )}
          <View style={styles.totalLine}>
            <Text style={styles.totalText}>Total</Text>
            <Text style={styles.totalAmount}>{formatCurrency(data.total, data.currency)}</Text>
          </View>
        </View>

        {/* Notes */}
        {data.notes ? (
          <View style={styles.notes}>
            <Text style={styles.notesLabel}>Notes</Text>
            <Text style={styles.notesText}>{data.notes}</Text>
          </View>
        ) : null}
      </Page>
    </Document>
  );
}
```

- [ ] **Step 2: Create PDF download button**

Create `src/components/invoice/pdf-download.tsx`:
```tsx
"use client";

import { useState } from "react";
import { pdf } from "@react-pdf/renderer";
import { Button } from "@/components/ui/button";
import { Download, Loader2 } from "lucide-react";
import { InvoicePDFDocument } from "./pdf-document";
import type { InvoiceData } from "@/lib/types/invoice";

interface PDFDownloadProps {
  data: InvoiceData;
}

export function PDFDownload({ data }: PDFDownloadProps) {
  const [generating, setGenerating] = useState(false);

  async function handleDownload() {
    setGenerating(true);
    try {
      const blob = await pdf(<InvoicePDFDocument data={data} />).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${data.invoiceNumber || "invoice"}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF generation failed:", err);
    } finally {
      setGenerating(false);
    }
  }

  const isValid = data.items.length > 0 && data.items.some((item) => item.amount > 0);

  return (
    <Button onClick={handleDownload} disabled={generating || !isValid} size="lg" className="w-full">
      {generating ? (
        <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating PDF...</>
      ) : (
        <><Download className="mr-2 h-4 w-4" /> Download PDF — Free, No Watermark</>
      )}
    </Button>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: PDF generation — @react-pdf/renderer document template + download"
```

---

## Task 6: Homepage — AI Invoice Generator

**Files:**
- Modify: `src/app/page.tsx`
- Create: `src/app/layout.tsx` (update with branding)
- Create: `src/components/layout/header.tsx`
- Create: `src/components/layout/footer.tsx`

- [ ] **Step 1: Create header and footer**

Create `src/components/layout/header.tsx`:
```tsx
import Link from "next/link";
import { FileText } from "lucide-react";

export function Header() {
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
        </nav>
      </div>
    </header>
  );
}
```

Create `src/components/layout/footer.tsx`:
```tsx
import Link from "next/link";

const industries = [
  "consulting", "photography", "plumber", "electrician", "graphic-designer",
  "web-developer", "cleaning-services", "tutoring", "lawyer", "contractor",
  "freelance-writer", "personal-trainer", "landscaping", "caregiver", "bookkeeper",
];

export function Footer() {
  return (
    <footer className="bg-gray-50 border-t mt-20">
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <h4 className="font-semibold text-sm mb-3">Tools</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li><Link href="/" className="hover:text-gray-900">Invoice Generator</Link></li>
              <li><Link href="/receipt-generator" className="hover:text-gray-900">Receipt Generator</Link></li>
              <li><Link href="/quote-generator" className="hover:text-gray-900">Quote Generator</Link></li>
              <li><Link href="/estimate-generator" className="hover:text-gray-900">Estimate Generator</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-sm mb-3">Invoice Templates</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              {industries.slice(0, 8).map((industry) => (
                <li key={industry}>
                  <Link href={`/invoice-template/${industry}`} className="hover:text-gray-900 capitalize">
                    {industry.replace(/-/g, " ")}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-sm mb-3">More Templates</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              {industries.slice(8).map((industry) => (
                <li key={industry}>
                  <Link href={`/invoice-template/${industry}`} className="hover:text-gray-900 capitalize">
                    {industry.replace(/-/g, " ")}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-sm mb-3">InvoiceAgent</h4>
            <p className="text-sm text-gray-600">AI-powered invoice generator for freelancers and small businesses. Create professional invoices in seconds — free.</p>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t text-center text-sm text-gray-400">
          &copy; {new Date().getFullYear()} InvoiceAgent. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
```

- [ ] **Step 2: Update root layout**

Replace `src/app/layout.tsx`:
```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Invoice Generator — Free, No Sign Up | InvoiceAgent",
  description: "Create professional invoices in seconds with AI. Just describe your work in plain English — free PDF download, no watermark, no sign up required.",
  keywords: ["ai invoice generator", "free invoice generator", "invoice generator", "invoice maker online"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-white text-gray-900`}>
        <Header />
        <main className="min-h-screen">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Build homepage**

Replace `src/app/page.tsx`:
```tsx
"use client";

import { useState } from "react";
import { AIInput } from "@/components/invoice/ai-input";
import { InvoiceForm } from "@/components/invoice/invoice-form";
import { InvoicePreview } from "@/components/invoice/invoice-preview";
import { PDFDownload } from "@/components/invoice/pdf-download";
import { TemplateSelector } from "@/components/invoice/template-selector";
import type { InvoiceData, TemplateStyle } from "@/lib/types/invoice";

const emptyInvoice: InvoiceData = {
  senderName: "",
  senderEmail: "",
  senderAddress: "",
  senderPhone: "",
  clientName: "",
  clientEmail: "",
  clientAddress: "",
  invoiceNumber: "INV-001",
  issueDate: new Date().toISOString().split("T")[0],
  dueDate: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
  paymentTerms: "Net 30",
  items: [{ description: "", quantity: 1, rate: 0, amount: 0 }],
  subtotal: 0,
  taxRate: 0,
  taxAmount: 0,
  total: 0,
  currency: "USD",
};

export default function HomePage() {
  const [invoice, setInvoice] = useState<InvoiceData>(emptyInvoice);
  const [template, setTemplate] = useState<TemplateStyle>("modern");
  const [generated, setGenerated] = useState(false);

  function handleAIGenerated(data: InvoiceData) {
    setInvoice(data);
    setGenerated(true);
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Hero */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold tracking-tight mb-3">
          AI Invoice Generator
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Describe your work in one sentence. Get a professional invoice in seconds.
          Free PDF download — no sign up, no watermark.
        </p>
      </div>

      {/* AI Input */}
      <div className="max-w-2xl mx-auto mb-10">
        <AIInput documentType="invoice" onGenerated={handleAIGenerated} />
      </div>

      {/* Form + Preview */}
      {generated && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Edit Invoice</h2>
              <TemplateSelector selected={template} onSelect={setTemplate} />
            </div>
            <InvoiceForm data={invoice} onChange={setInvoice} />
            <PDFDownload data={invoice} />
          </div>
          <div className="hidden lg:block sticky top-4">
            <h2 className="text-lg font-semibold mb-4">Preview</h2>
            <InvoicePreview data={invoice} template={template} />
          </div>
        </div>
      )}

      {/* SEO Content */}
      <section className="mt-20 max-w-3xl mx-auto prose prose-gray">
        <h2>Create Professional Invoices with AI</h2>
        <p>InvoiceAgent uses AI to understand your work description and automatically generate a complete, professional invoice. No manual form filling — just describe what you did, for whom, and how much.</p>
        <h3>How it works</h3>
        <ol>
          <li><strong>Describe your work</strong> — Type something like &ldquo;3 hours of consulting for Acme Corp at $150/hr&rdquo;</li>
          <li><strong>AI fills the invoice</strong> — Client name, line items, amounts, due date — all extracted automatically</li>
          <li><strong>Review and edit</strong> — Make any adjustments to the pre-filled form</li>
          <li><strong>Download PDF</strong> — Free, professional, no watermark</li>
        </ol>
        <h3>Features</h3>
        <ul>
          <li>AI-powered natural language to invoice conversion</li>
          <li>5 professional templates (Modern, Classic, Minimal, Bold, Elegant)</li>
          <li>Multi-currency support (USD, EUR, GBP, CAD, AUD, and more)</li>
          <li>Tax presets for US, UK, EU, Australia, Canada, India, Japan</li>
          <li>Free PDF download — no watermark, no sign up</li>
        </ul>
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Verify the homepage works**

```bash
npm run dev
```

Visit http://localhost:3000. Verify:
1. Hero section renders
2. AI input accepts text
3. After generation, form and preview appear side by side
4. PDF download works

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: homepage — AI invoice generator with form, preview, and PDF download"
```

---

## Task 7: Document Matrix — Receipt, Quote, Estimate Pages

**Files:**
- Create: `src/components/document/receipt-form.tsx`
- Create: `src/components/document/quote-form.tsx`
- Create: `src/components/document/estimate-form.tsx`
- Create: `src/app/(marketing)/receipt-generator/page.tsx`
- Create: `src/app/(marketing)/quote-generator/page.tsx`
- Create: `src/app/(marketing)/estimate-generator/page.tsx`

- [ ] **Step 1: Create document-specific pages**

Each page follows the same pattern as the homepage but with a different `documentType` and slightly different form fields. For brevity, showing receipt-generator as the template — quote and estimate follow the same pattern with their respective types.

Create `src/app/(marketing)/receipt-generator/page.tsx`:
```tsx
"use client";

import { useState } from "react";
import { AIInput } from "@/components/invoice/ai-input";
import { InvoiceForm } from "@/components/invoice/invoice-form";
import { InvoicePreview } from "@/components/invoice/invoice-preview";
import { PDFDownload } from "@/components/invoice/pdf-download";
import { TemplateSelector } from "@/components/invoice/template-selector";
import type { InvoiceData, TemplateStyle } from "@/lib/types/invoice";

export const metadata = {
  title: "Free Receipt Generator — AI-Powered | InvoiceAgent",
  description: "Create professional receipts instantly with AI. Describe the transaction and get a downloadable PDF receipt — free, no sign up.",
};

const emptyReceipt: InvoiceData = {
  senderName: "",
  senderEmail: "",
  senderAddress: "",
  senderPhone: "",
  clientName: "",
  clientEmail: "",
  clientAddress: "",
  invoiceNumber: "REC-001",
  issueDate: new Date().toISOString().split("T")[0],
  dueDate: new Date().toISOString().split("T")[0],
  paymentTerms: "Paid",
  items: [{ description: "", quantity: 1, rate: 0, amount: 0 }],
  subtotal: 0,
  taxRate: 0,
  taxAmount: 0,
  total: 0,
  currency: "USD",
};

export default function ReceiptGeneratorPage() {
  const [data, setData] = useState<InvoiceData>(emptyReceipt);
  const [template, setTemplate] = useState<TemplateStyle>("modern");
  const [generated, setGenerated] = useState(false);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold tracking-tight mb-3">Free Receipt Generator</h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Describe the transaction in plain English. Get a professional receipt PDF in seconds — free.
        </p>
      </div>

      <div className="max-w-2xl mx-auto mb-10">
        <AIInput documentType="receipt" onGenerated={(d) => { setData(d as InvoiceData); setGenerated(true); }} />
      </div>

      {generated && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Edit Receipt</h2>
              <TemplateSelector selected={template} onSelect={setTemplate} />
            </div>
            <InvoiceForm data={data} onChange={setData} />
            <PDFDownload data={data} />
          </div>
          <div className="hidden lg:block sticky top-4">
            <h2 className="text-lg font-semibold mb-4">Preview</h2>
            <InvoicePreview data={data} template={template} />
          </div>
        </div>
      )}

      <section className="mt-20 max-w-3xl mx-auto prose prose-gray">
        <h2>Create Professional Receipts Instantly</h2>
        <p>Generate receipts for any transaction — retail sales, service payments, freelance work. Just describe what happened and our AI creates a complete, professional receipt.</p>
        <h3>Perfect for</h3>
        <ul>
          <li>Small business owners issuing purchase receipts</li>
          <li>Freelancers confirming payment received</li>
          <li>Service providers documenting completed work</li>
          <li>Anyone needing a professional receipt for records</li>
        </ul>
      </section>
    </div>
  );
}
```

Create `src/app/(marketing)/quote-generator/page.tsx` and `src/app/(marketing)/estimate-generator/page.tsx` following the same pattern, changing:
- Page title/description to "Quote Generator" / "Estimate Generator"
- `documentType` to `"quote"` / `"estimate"`
- `invoiceNumber` prefix to `"QUO-001"` / `"EST-001"`
- SEO content tailored to quotes/estimates

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: document matrix — receipt, quote, and estimate generator pages"
```

---

## Task 8: Industry pSEO Pages

**Files:**
- Create: `src/lib/data/industries.ts`
- Create: `src/app/(marketing)/invoice-template/[industry]/page.tsx`
- Create: `src/components/seo/faq-schema.tsx`
- Create: `src/components/seo/industry-content.tsx`

- [ ] **Step 1: Create industry data file**

Create `src/lib/data/industries.ts` with the first 30 industries (expandable to 200+):

```typescript
export interface Industry {
  slug: string;
  name: string;
  title: string;
  description: string;
  sampleItems: { description: string; quantity: number; rate: number; amount: number }[];
  paymentTerms: string;
  taxNote: string;
  faqs: { question: string; answer: string }[];
  content: string; // SEO article content (~300 words, expanded at build)
}

export const industries: Industry[] = [
  {
    slug: "consulting",
    name: "Consulting",
    title: "Consulting Invoice Template",
    description: "Free AI-powered consulting invoice template. Create professional invoices for consulting services — hourly, project-based, or retainer billing.",
    sampleItems: [
      { description: "Strategy consulting — Q1 planning session", quantity: 8, rate: 175, amount: 1400 },
      { description: "Market research report", quantity: 1, rate: 2500, amount: 2500 },
    ],
    paymentTerms: "Net 30",
    taxNote: "Consulting services are generally subject to state sales tax in the US. Check your state requirements.",
    faqs: [
      { question: "What should I include in a consulting invoice?", answer: "A consulting invoice should include: your business name and contact info, client details, invoice number, date, description of services (hours × rate or project fee), payment terms, and total amount due." },
      { question: "What are standard payment terms for consultants?", answer: "Most consultants use Net 30 (payment due within 30 days). For new clients, consider Net 15 or requiring a 50% deposit upfront." },
      { question: "Should I charge hourly or project-based?", answer: "Hourly works best for ongoing advisory work. Project-based is better for defined deliverables. Many consultants use a hybrid: a project fee with hourly overage for scope changes." },
      { question: "Do I need to charge sales tax on consulting?", answer: "It depends on your state and the type of consulting. Some states exempt professional services, others don't. Consult a tax professional for your specific situation." },
    ],
    content: "As a consultant, sending professional invoices is essential for maintaining credibility and ensuring timely payment. Whether you bill hourly or per project, a well-structured invoice clearly communicates what services were delivered and what is owed.",
  },
  {
    slug: "photography",
    name: "Photography",
    title: "Photography Invoice Template",
    description: "Free photography invoice template with AI. Bill for photo shoots, editing, prints, and licensing — professional PDF download.",
    sampleItems: [
      { description: "Portrait photography session (2 hours)", quantity: 1, rate: 350, amount: 350 },
      { description: "Photo editing and retouching (15 images)", quantity: 15, rate: 25, amount: 375 },
      { description: "Digital delivery — high resolution files", quantity: 1, rate: 100, amount: 100 },
    ],
    paymentTerms: "Due on Delivery",
    taxNote: "Photography services may be subject to sales tax. Digital deliveries may have different tax treatment than physical prints.",
    faqs: [
      { question: "What should a photography invoice include?", answer: "Include: shoot date and location, number of hours, number of edited images, licensing terms, equipment fees if applicable, and travel expenses." },
      { question: "Should I require a deposit for photo shoots?", answer: "Yes. Most photographers require 25-50% deposit at booking, with the remainder due on delivery of final images." },
      { question: "How do I invoice for photo licensing?", answer: "Specify the license type (personal use, commercial, exclusive), duration, and territory. Price licensing separately from the shoot fee." },
      { question: "What payment terms do photographers use?", answer: "Most photographers use Due on Delivery or Net 14. For weddings and events, 50% deposit at booking is standard." },
    ],
    content: "Professional photographers need invoices that clearly break down session fees, editing costs, and licensing terms. A well-designed photography invoice helps set expectations and ensures you get paid promptly for your creative work.",
  },
  // ... Add 28 more industries following the same pattern.
  // Priority: plumber, electrician, graphic-designer, web-developer, cleaning-services,
  // tutoring, lawyer, contractor, freelance-writer, personal-trainer, landscaping,
  // caregiver, bookkeeper, videographer, massage-therapist, yoga-instructor,
  // dog-walker, real-estate-agent, interior-designer, accountant, architect,
  // music-teacher, dj, makeup-artist, event-planner, translator, nutritionist, mechanic
];

export function getIndustry(slug: string): Industry | undefined {
  return industries.find((i) => i.slug === slug);
}

export function getAllIndustrySlugs(): string[] {
  return industries.map((i) => i.slug);
}
```

(The implementing agent should fill in all 30 industries with unique sample data, FAQs, and content.)

- [ ] **Step 2: Create FAQ schema component**

Create `src/components/seo/faq-schema.tsx`:
```tsx
interface FAQ {
  question: string;
  answer: string;
}

export function FAQSchema({ faqs }: { faqs: FAQ[] }) {
  const schema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
```

- [ ] **Step 3: Create industry page**

Create `src/app/(marketing)/invoice-template/[industry]/page.tsx`:
```tsx
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getIndustry, getAllIndustrySlugs } from "@/lib/data/industries";
import { FAQSchema } from "@/components/seo/faq-schema";
import { InvoicePreview } from "@/components/invoice/invoice-preview";
import type { InvoiceData } from "@/lib/types/invoice";
import Link from "next/link";

interface Props {
  params: Promise<{ industry: string }>;
}

export async function generateStaticParams() {
  return getAllIndustrySlugs().map((slug) => ({ industry: slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { industry: slug } = await params;
  const industry = getIndustry(slug);
  if (!industry) return {};
  return {
    title: `${industry.title} — Free AI Generator | InvoiceAgent`,
    description: industry.description,
  };
}

export default async function IndustryTemplatePage({ params }: Props) {
  const { industry: slug } = await params;
  const industry = getIndustry(slug);
  if (!industry) notFound();

  const sampleInvoice: InvoiceData = {
    senderName: "Your Name",
    senderEmail: "you@example.com",
    senderAddress: "123 Main St, Anytown, USA",
    senderPhone: "",
    clientName: "Client Name",
    clientEmail: "client@example.com",
    clientAddress: "456 Oak Ave, Othertown, USA",
    invoiceNumber: "INV-001",
    issueDate: new Date().toISOString().split("T")[0],
    dueDate: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
    paymentTerms: industry.paymentTerms,
    items: industry.sampleItems,
    subtotal: industry.sampleItems.reduce((s, i) => s + i.amount, 0),
    taxRate: 0,
    taxAmount: 0,
    total: industry.sampleItems.reduce((s, i) => s + i.amount, 0),
    currency: "USD",
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <FAQSchema faqs={industry.faqs} />

      {/* Hero */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold tracking-tight mb-3">{industry.title}</h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">{industry.description}</p>
        <Link
          href="/"
          className="inline-block mt-4 px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
        >
          Create Your {industry.name} Invoice — Free
        </Link>
      </div>

      {/* Sample Preview */}
      <div className="max-w-2xl mx-auto mb-16">
        <h2 className="text-lg font-semibold mb-4">Sample {industry.name} Invoice</h2>
        <InvoicePreview data={sampleInvoice} template="modern" />
      </div>

      {/* SEO Content */}
      <div className="max-w-3xl mx-auto prose prose-gray">
        <h2>What to Include in a {industry.name} Invoice</h2>
        <p>{industry.content}</p>

        {/* FAQ */}
        <h2>Frequently Asked Questions</h2>
        {industry.faqs.map((faq, i) => (
          <div key={i}>
            <h3>{faq.question}</h3>
            <p>{faq.answer}</p>
          </div>
        ))}

        {/* Tax Note */}
        <h3>Tax Considerations for {industry.name}</h3>
        <p>{industry.taxNote}</p>
      </div>

      {/* CTA */}
      <div className="text-center mt-16">
        <Link
          href="/"
          className="inline-block px-8 py-4 bg-blue-600 text-white rounded-lg font-medium text-lg hover:bg-blue-700 transition-colors"
        >
          Create Your {industry.name} Invoice Now — Free
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify pSEO pages render**

```bash
npm run dev
```

Visit http://localhost:3000/invoice-template/consulting and http://localhost:3000/invoice-template/photography. Verify sample invoice renders with industry-specific data and FAQ section.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: pSEO — industry template pages with FAQ schema and sample invoices"
```

---

## Task 9: SEO Optimization + Deployment Config

**Files:**
- Create: `src/app/sitemap.ts`
- Create: `src/app/robots.ts`
- Modify: `next.config.ts`

- [ ] **Step 1: Create sitemap**

Create `src/app/sitemap.ts`:
```typescript
import type { MetadataRoute } from "next";
import { getAllIndustrySlugs } from "@/lib/data/industries";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://invoiceagent.ai"; // Update with actual domain

  const industryPages = getAllIndustrySlugs().map((slug) => ({
    url: `${baseUrl}/invoice-template/${slug}`,
    lastModified: new Date(),
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));

  return [
    { url: baseUrl, lastModified: new Date(), changeFrequency: "weekly", priority: 1.0 },
    { url: `${baseUrl}/receipt-generator`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.8 },
    { url: `${baseUrl}/quote-generator`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.8 },
    { url: `${baseUrl}/estimate-generator`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.8 },
    ...industryPages,
  ];
}
```

- [ ] **Step 2: Create robots.txt**

Create `src/app/robots.ts`:
```typescript
import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: "https://invoiceagent.ai/sitemap.xml",
  };
}
```

- [ ] **Step 3: Update next.config.ts for production**

Update `next.config.ts`:
```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "*.supabase.co" },
    ],
  },
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
};

export default nextConfig;
```

- [ ] **Step 4: Build and verify**

```bash
npm run build
```

Expected: Build succeeds, pSEO pages are statically generated.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: SEO — sitemap, robots.txt, build optimization"
```

---

## Task 10: Final Verification + Deploy

- [ ] **Step 1: Full integration test**

```bash
npm run dev
```

Manually verify:
1. Homepage: AI input → generates invoice → form editable → PDF downloads
2. Receipt page: AI input → receipt generation works
3. Quote page: AI input → quote generation works
4. Estimate page: AI input → estimate generation works
5. Industry pSEO pages: /invoice-template/consulting renders with sample invoice + FAQ
6. Template selector: switching templates changes preview colors
7. Currency selector: changing currency updates formatting
8. Tax presets: selecting a preset updates calculations correctly
9. Mobile responsive: pages work on mobile viewport

- [ ] **Step 2: Deploy to Vercel**

```bash
npm install -g vercel
vercel --prod
```

Or connect GitHub repo to Vercel dashboard for auto-deploys.

- [ ] **Step 3: Submit to Google Search Console**

After deployment:
1. Add property in Google Search Console
2. Submit sitemap: `https://yourdomain.com/sitemap.xml`
3. Request indexing for homepage and key pages

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: InvoiceAgent v1 — AI invoice generator with pSEO, ready for production"
```

---

## Summary

| Task | What it delivers | Estimated time |
|------|-----------------|---------------|
| 1. Scaffolding | Next.js + Tailwind + shadcn + types | 15 min |
| 2. Supabase | DB schema + RLS + client utils | 15 min |
| 3. AI Engine | Claude Haiku integration + API route | 20 min |
| 4. Invoice Form | AI input + editable form + live preview | 30 min |
| 5. PDF Generation | @react-pdf/renderer PDF template + download | 20 min |
| 6. Homepage | Full AI invoice generator page | 20 min |
| 7. Document Matrix | Receipt, quote, estimate pages | 20 min |
| 8. pSEO Pages | 30 industry template pages + FAQ schema | 40 min |
| 9. SEO Config | Sitemap, robots.txt, build optimization | 10 min |
| 10. Deploy | Verification + Vercel deployment | 15 min |
| **Total** | | **~3.5 hours** |
