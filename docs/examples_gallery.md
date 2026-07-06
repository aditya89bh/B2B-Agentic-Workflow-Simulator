# Examples Gallery

Three bundled workflow examples ship with the simulator.  Each represents a
realistic B2B process with a "before" (fully human) and "after" (AI-assisted)
variant.

Use the `generate-example-gallery` command to regenerate all outputs with
consistent settings:

```bash
b2b-simulator generate-example-gallery --output-dir examples/outputs
```

---

## 1. Sales Lead Qualification

**What it represents:** An outbound sales process where leads arrive, are
researched, go through a discovery call, and either advance to a qualified
handoff or are disqualified.

**Before:** Every stage is handled by human SDRs and Account Executives.

**After:** Lead intake, initial research, and proposal drafting are automated
with AI agents.  The discovery call stays human because it depends on judgment
and rapport.

**Command to run:**

```bash
b2b-simulator executive-snapshot sales-lead-qualification --cases 300 --seed 42
b2b-simulator visualize-workflow sales-lead-qualification --format mermaid
b2b-simulator roi-waterfall sales-lead-qualification --cases 300 --implementation-cost 5000
```

**Expected qualitative result:**
- Significant cycle-time reduction on intake and research stages
- AI escalation rate may be notable; ensure human AEs can absorb escalations
- Completion rate maintained or improved in the after variant

**When this example is useful:**
- Demonstrating AI ROI to a VP of Sales
- Estimating headcount requirements after automation
- Validating that AI error rates don't materially affect qualified lead volume

**Assumptions to tune:**
- `ai_error_rate_multiplier`: default is 1.0; raise to 2.0 for pessimistic AI reliability
- `implementation_cost`: reflects cost of AI platform setup, training, and onboarding
- `arrival_interval_minutes`: model realistic lead arrival rates (e.g. 30 min)

**Sample output:** `examples/outputs/sales_lead_snapshot.txt`

---

## 2. Invoice Processing (Accounts Payable)

**What it represents:** An AP workflow where invoices are ingested, validated,
approved, entered into the ERP, and scheduled for payment.  Exception paths handle
missing POs, mismatched amounts, and vendor data issues.

**Before:** AP clerks and a controller handle all stages manually.

**After:** Intake and validation are automated with AI agents; human approval is
retained for the controller stage; ERP entry and payment scheduling are also AI.

**Command to run:**

```bash
b2b-simulator executive-snapshot invoice-processing --cases 300 --seed 42 --implementation-cost 8000
b2b-simulator roi-waterfall invoice-processing --cases 300 --implementation-cost 8000 --format svg --output roi.svg
b2b-simulator bottleneck-heatmap invoice-processing --cases 300 --arrival-interval 10
```

**Expected qualitative result:**
- Cost per case drops significantly as AI agents replace manual data entry
- Cycle time improvement depends on the approval stage, which remains human
- Exception rates drive much of the variance; tune AI error rates for sensitivity

**When this example is useful:**
- Finance transformation presentations
- Justifying ERP integration investment
- Modeling SLA impact of AI adoption in finance

**Assumptions to tune:**
- `ai_error_rate_multiplier`: raise for conservative estimates in a regulated environment
- `implementation_cost`: ERP integration projects typically cost $5k–$50k
- `arrival_interval_minutes`: model invoice batch arrival patterns (e.g. 10 min)

**Sample outputs:**
- `examples/outputs/invoice_processing_snapshot.txt`
- `examples/outputs/invoice_processing_roi_waterfall.svg`
- `examples/outputs/invoice_processing_bottleneck_heatmap.svg`

---

## 3. Customer Support Ticket Resolution

**What it represents:** A multi-tier support process where tickets are triaged,
an AI bot attempts a response, unresolved cases escalate to a specialist, and
resolved cases are reviewed before closure.

**Before:** Human agents handle triage, response, and review.

**After:** Triage and initial response are AI-handled; specialist escalation and
review are retained as human stages.

**Command to run:**

```bash
b2b-simulator executive-snapshot customer-support-ticket-resolution --cases 300 --seed 42
b2b-simulator consultant-packet customer-support-ticket-resolution --cases 300 --output-dir cs_packet
```

**Expected qualitative result:**
- Escalation rate is the key metric to watch — high escalations erode the AI benefit
- Cycle time improvement visible when triage and first response are fast
- Failure-rate difference is small in both variants

**When this example is useful:**
- Customer experience improvement projects
- Demonstrating self-service automation ROI
- Modeling staffing requirements for a hybrid human/AI support team

**Assumptions to tune:**
- `ai_error_rate_multiplier`: higher rates model an AI bot that frequently needs
  human review even before escalation
- `implementation_cost`: covers AI chatbot, integration, and training data

**Sample output:** `examples/outputs/customer_support_snapshot.txt`

---

## Re-generating gallery outputs

```bash
b2b-simulator generate-example-gallery --output-dir examples/outputs
```

This command uses a fixed seed (42) and 300 cases for all examples, producing
deterministic output files every time.
