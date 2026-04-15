# InvoiceAgent Plan 4: Contracts & E-Signatures

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add contract templates, AI contract generation, and electronic signatures. Contracts link to invoices — when a contract is signed, the first invoice can be auto-generated. Deposits can be required before work begins.

**Architecture:** Contracts stored in Supabase as HTML content. AI generates contract text via Claude Haiku. E-signatures captured as canvas drawings, stored as images in Supabase Storage. Public signing page at `/sign/{id}` — no account needed for the signer. Contract → Invoice linking via `linked_invoice_id`.

**Tech Stack:** Claude Haiku (contract generation), HTML canvas (signature capture), Supabase Storage (signature images)

**Depends on:** Plan 2 completed (auth, clients, invoices)

**Project path:** `/Users/zhanggongqing/project/孵化项目/cloudwork/workspace/invoice-agent`

---

## File Structure (new/modified files)

```
src/
├── app/
│   ├── (app)/
│   │   └── contracts/
│   │       ├── page.tsx                # Contract list
│   │       ├── new/page.tsx            # Create contract (AI + form)
│   │       └── [id]/page.tsx           # Contract detail/edit
│   │
│   └── sign/
│       └── [id]/page.tsx               # Public signing page (no auth)
│
├── components/
│   ├── contract/
│   │   ├── contract-form.tsx           # Contract editor (rich text + AI)
│   │   ├── contract-preview.tsx        # Contract HTML preview
│   │   ├── contract-ai-input.tsx       # AI: describe project → contract
│   │   ├── signature-pad.tsx           # Canvas signature capture
│   │   └── contract-template-selector.tsx  # Industry template picker
│   └── app/
│       └── contract-list.tsx           # Contract table in dashboard
│
├── lib/
│   ├── ai/
│   │   └── contract-prompts.ts         # AI prompts for contract generation
│   ├── actions/
│   │   └── contracts.ts                # Server actions: CRUD contracts
│   └── data/
│       └── contract-templates.ts       # 10+ industry contract templates
```

---

## Task 1: Contract Data + Templates

**Files:**
- Create: `src/lib/data/contract-templates.ts`
- Create: `src/lib/ai/contract-prompts.ts`
- Create: `src/lib/actions/contracts.ts`

- [ ] **Step 1: Create contract templates**

Create `src/lib/data/contract-templates.ts`:
```typescript
export interface ContractTemplate {
  id: string;
  name: string;
  industry: string;
  sections: {
    title: string;
    content: string;
  }[];
}

export const contractTemplates: ContractTemplate[] = [
  {
    id: "freelance-general",
    name: "General Freelance Agreement",
    industry: "general",
    sections: [
      { title: "Scope of Work", content: "The Contractor agrees to perform the following services: [SCOPE]" },
      { title: "Timeline", content: "Work shall begin on [START_DATE] and be completed by [END_DATE]." },
      { title: "Payment Terms", content: "Total fee: [AMOUNT] [CURRENCY]. Payment schedule: [PAYMENT_TERMS]." },
      { title: "Revisions", content: "This agreement includes [NUMBER] rounds of revisions. Additional revisions will be billed at [RATE] per hour." },
      { title: "Intellectual Property", content: "Upon full payment, all intellectual property rights to the deliverables transfer to the Client." },
      { title: "Cancellation", content: "Either party may cancel with [NOTICE_DAYS] days written notice. Work completed to date will be billed proportionally." },
      { title: "Confidentiality", content: "Both parties agree to keep project details confidential and not share proprietary information with third parties." },
    ],
  },
  {
    id: "web-development",
    name: "Web Development Agreement",
    industry: "web-developer",
    sections: [
      { title: "Project Scope", content: "The Developer agrees to build: [SCOPE]. Technologies: [TECH_STACK]." },
      { title: "Milestones", content: "Project will be delivered in the following milestones: [MILESTONES]" },
      { title: "Payment Schedule", content: "Total: [AMOUNT]. 50% deposit due upon signing. 50% due upon project completion." },
      { title: "Hosting & Maintenance", content: "Post-launch maintenance: [MAINTENANCE_TERMS]. Hosting is the Client's responsibility unless otherwise agreed." },
      { title: "Source Code", content: "Upon full payment, source code and all assets are delivered to the Client." },
      { title: "Bug Fixes", content: "Bug fixes within 30 days of delivery are included at no charge. New feature requests are billed separately." },
    ],
  },
  {
    id: "photography",
    name: "Photography Service Agreement",
    industry: "photography",
    sections: [
      { title: "Event/Session Details", content: "Date: [DATE]. Location: [LOCATION]. Duration: [DURATION]." },
      { title: "Deliverables", content: "Photographer will deliver [NUMBER] edited digital images within [DAYS] business days." },
      { title: "Payment", content: "Session fee: [AMOUNT]. 50% non-refundable deposit due at booking. Remaining balance due [PAYMENT_TERMS]." },
      { title: "Usage Rights", content: "Client receives personal use license. Commercial use requires separate licensing agreement." },
      { title: "Cancellation", content: "Cancellations within 48 hours of the session forfeit the deposit. Rescheduling is subject to availability." },
    ],
  },
  // Add: design, consulting, tutoring, cleaning, construction, marketing, writing, video
];

export function getContractTemplate(id: string) {
  return contractTemplates.find((t) => t.id === id);
}
```

- [ ] **Step 2: Create AI contract prompts**

Create `src/lib/ai/contract-prompts.ts`:
```typescript
export function getContractGenerationPrompt(description: string): string {
  return `You are a contract drafting assistant. Generate a professional freelance service contract based on this description:

"${description}"

Return a JSON object with this structure:
{
  "title": "Contract title",
  "sections": [
    { "title": "Section title", "content": "Section content in plain text" }
  ]
}

Rules:
- Include sections: Scope of Work, Timeline, Payment Terms, Revisions/Changes, Intellectual Property, Cancellation, Confidentiality
- Use professional but readable language
- Fill in specific details from the description where possible
- Use [PLACEHOLDER] for any information not provided
- Keep each section 2-4 sentences
- Return ONLY valid JSON, no markdown or explanation`;
}
```

- [ ] **Step 3: Create contract server actions**

Create `src/lib/actions/contracts.ts`:
```typescript
"use server";

import { createServerSupabaseClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";
import { generateShortId } from "@/lib/utils/short-id";

export async function getContracts() {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not authenticated");

  const { data, error } = await supabase
    .from("contracts")
    .select("*, clients(name)")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  if (error) throw error;
  return data;
}

export async function getContract(id: string) {
  const supabase = await createServerSupabaseClient();
  const { data, error } = await supabase.from("contracts").select("*").eq("id", id).single();
  if (error) throw error;
  return data;
}

export async function createContract(data: {
  title: string;
  contentHtml: string;
  clientId?: string;
  depositRequired?: boolean;
  depositPercentage?: number;
  expiresAt?: string;
}) {
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not authenticated");

  const signingId = generateShortId(10);

  const { data: contract, error } = await supabase.from("contracts").insert({
    user_id: user.id,
    client_id: data.clientId || null,
    title: data.title,
    content_html: data.contentHtml,
    status: "draft",
    deposit_required: data.depositRequired || false,
    deposit_percentage: data.depositPercentage || null,
    expires_at: data.expiresAt || null,
    // Store signing ID in a way that allows public access
    // We'll use the contract's own ID + a signing token approach
  }).select().single();

  if (error) throw error;
  revalidatePath("/contracts");
  return contract;
}

export async function signContract(contractId: string, signatureUrl: string) {
  const supabase = await createServerSupabaseClient();

  const { error } = await supabase.from("contracts").update({
    status: "signed",
    signed_at: new Date().toISOString(),
    signature_url: signatureUrl,
  }).eq("id", contractId);

  if (error) throw error;
  revalidatePath("/contracts");
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: contract data — templates, AI prompts, server actions"
```

---

## Task 2: Signature Pad + Signing Page

**Files:**
- Create: `src/components/contract/signature-pad.tsx`
- Create: `src/app/sign/[id]/page.tsx`

- [ ] **Step 1: Create signature pad**

Create `src/components/contract/signature-pad.tsx`:
```tsx
"use client";

import { useRef, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Eraser } from "lucide-react";

interface SignaturePadProps {
  onSign: (dataUrl: string) => void;
}

export function SignaturePad({ onSign }: SignaturePadProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasDrawn, setHasDrawn] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.strokeStyle = "#1f2937";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
  }, []);

  function getCoords(e: React.MouseEvent | React.TouchEvent) {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    if ("touches" in e) {
      return { x: e.touches[0].clientX - rect.left, y: e.touches[0].clientY - rect.top };
    }
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function startDrawing(e: React.MouseEvent | React.TouchEvent) {
    e.preventDefault();
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const { x, y } = getCoords(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
    setIsDrawing(true);
    setHasDrawn(true);
  }

  function draw(e: React.MouseEvent | React.TouchEvent) {
    e.preventDefault();
    if (!isDrawing) return;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const { x, y } = getCoords(e);
    ctx.lineTo(x, y);
    ctx.stroke();
  }

  function stopDrawing() {
    setIsDrawing(false);
  }

  function clear() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasDrawn(false);
  }

  function handleSign() {
    const canvas = canvasRef.current;
    if (!canvas || !hasDrawn) return;
    onSign(canvas.toDataURL("image/png"));
  }

  return (
    <div className="space-y-3">
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-1">
        <canvas
          ref={canvasRef}
          width={500}
          height={150}
          className="w-full cursor-crosshair bg-white rounded"
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={stopDrawing}
          onMouseLeave={stopDrawing}
          onTouchStart={startDrawing}
          onTouchMove={draw}
          onTouchEnd={stopDrawing}
        />
      </div>
      <div className="flex justify-between">
        <Button variant="outline" size="sm" onClick={clear}>
          <Eraser className="h-4 w-4 mr-1" /> Clear
        </Button>
        <Button onClick={handleSign} disabled={!hasDrawn}>
          Sign Contract
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create public signing page**

Create `src/app/sign/[id]/page.tsx`:
```tsx
import { createServerSupabaseClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { SignaturePad } from "@/components/contract/signature-pad";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function SignContractPage({ params }: Props) {
  const { id } = await params;
  const supabase = await createServerSupabaseClient();

  const { data: contract } = await supabase
    .from("contracts")
    .select("*")
    .eq("id", id)
    .in("status", ["draft", "sent"])
    .single();

  if (!contract) notFound();

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold">{contract.title}</h1>
        <p className="text-gray-600 mt-1">Please review and sign below</p>
      </div>

      {/* Contract content */}
      <div
        className="prose prose-gray max-w-none mb-8 p-6 border rounded-lg bg-white"
        dangerouslySetInnerHTML={{ __html: contract.content_html }}
      />

      {/* Signature */}
      {contract.status === "signed" ? (
        <div className="text-center p-8 bg-green-50 rounded-lg border border-green-200">
          <p className="text-green-700 font-medium">This contract has been signed.</p>
          <p className="text-sm text-green-600 mt-1">Signed on {new Date(contract.signed_at).toLocaleDateString()}</p>
        </div>
      ) : (
        <div className="p-6 border rounded-lg bg-gray-50">
          <h3 className="font-semibold mb-3">Your Signature</h3>
          <SignaturePad
            onSign={async (dataUrl) => {
              "use server";
              // Upload signature to Supabase Storage and update contract
              // This will be handled via a client-side fetch to an API route
            }}
          />
        </div>
      )}
    </div>
  );
}
```

Note: The signing action needs a client-side API call to upload the signature image and update contract status. Create `src/app/api/contracts/sign/route.ts` that:
1. Receives the base64 signature image
2. Uploads to Supabase Storage
3. Updates contract status to "signed"
4. Returns success

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: e-signatures — signature pad canvas + public signing page"
```

---

## Task 3: Contract UI (Dashboard)

**Files:**
- Create: `src/components/contract/contract-form.tsx`
- Create: `src/components/contract/contract-ai-input.tsx`
- Create: `src/components/contract/contract-preview.tsx`
- Create: `src/components/app/contract-list.tsx`
- Create: `src/app/(app)/contracts/page.tsx`
- Create: `src/app/(app)/contracts/new/page.tsx`
- Create: `src/app/(app)/contracts/[id]/page.tsx`

- [ ] **Step 1: Create contract AI input**

Create `src/components/contract/contract-ai-input.tsx` — similar to invoice AI input but for contracts. User describes the project and AI generates contract sections.

- [ ] **Step 2: Create contract form**

Create `src/components/contract/contract-form.tsx` — editable sections from AI generation or template selection. Each section has title + textarea content. Add/remove sections. Deposit toggle + percentage input.

- [ ] **Step 3: Create contract list and pages**

Create contract management pages:
- `contracts/page.tsx` — list all contracts with status badges (Draft/Sent/Signed/Expired)
- `contracts/new/page.tsx` — AI input or template selection → form → preview → save
- `contracts/[id]/page.tsx` — contract detail with send link, view signature, link to invoice

- [ ] **Step 4: Update sidebar**

Add "Contracts" nav item to `src/components/app/sidebar.tsx` with a `ScrollText` icon.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: contract management UI — create, list, detail, AI generation"
```

---

## Summary

| Task | What it delivers | Estimated time |
|------|-----------------|---------------|
| 1. Contract Data + Templates | Templates, AI prompts, server actions | 25 min |
| 2. Signature Pad + Signing | Canvas e-signature, public signing page | 30 min |
| 3. Contract UI | Dashboard pages for contract management | 30 min |
| **Total** | | **~1.5 hours** |
